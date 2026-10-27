import json
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import yohaku_codex as codex
import yohaku_codex_diagnostics as diagnostics


class SyntheticConnection(codex.Connection):
    def __init__(self, diagnostic, events, exit_code=0, stderr='', disconnect=False, send_failure=False):
        script = 'import sys;sys.stderr.write(' + repr(stderr) + ');sys.stderr.flush();'
        script += '' if disconnect else 'sys.stdin.read();'
        script += 'sys.exit(' + str(exit_code) + ')'
        child = subprocess.Popen([sys.executable, '-B', '-c', script], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        super().__init__(child, diagnostic)
        self.linux = True
        self.info = {'cwd':'synthetic-empty-control'}
        self.events = list(events)
        self.send_failure = send_failure

    def request(self, method, params):
        if method == 'thread/start':
            return {'thread':{'id':'thread-fixture'}, 'activePermissionProfile':{'id':'yohaku-control'}}
        if method == 'config/read':
            return {'config':{'features':{'shell_tool':False,'apps':False,'plugins':False}}}
        if method == 'turn/start':
            return {'turn':{'id':'turn-fixture'}}
        raise AssertionError(method)

    def receive(self, timeout=30):
        if self.events:
            return self.events.pop(0)
        return super().receive(min(timeout, 3))

    def send(self, value):
        if self.send_failure:
            raise codex.CodexError('Synthetic result pipe failed')
        return super().send(value)


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / 'private-diagnostics'
        self.directory_patch = patch.object(diagnostics, 'DIRECTORY', self.directory)
        self.directory_patch.start()
        self.addCleanup(self.directory_patch.stop)
        self.initial = dict(config={'codex_entry':'synthetic-only'}, prompt='PRIVATE USER CONVERSATION',
                            history=[dict(role='assistant', content='PRIVATE HISTORY CONTENT')])
        self.tools = types.SimpleNamespace(bootstrap=lambda value:value,
            definitions=[{'name':'read_text','description':'synthetic read','parameters':{'type':'object'}}],
            call=lambda name,args:dict(ok=True,result={'text':'PRIVATE TOOL BODY'}))
        from yohaku_codex_models import Control
        self.tools.enable_model_management=lambda config:setattr(self.tools,'model_control',Control(config))
        self.events = []

    def turn(self, status='completed', error=None):
        turn = dict(id='turn-fixture', status=status)
        if error is not None:
            turn['error'] = error
        return dict(method='turn/completed', params=dict(threadId='thread-fixture', turn=turn))

    def tool(self):
        return dict(id=501, method='item/tool/call', params=dict(threadId='thread-fixture',
                    tool='yohaku_read_text', arguments={'path':'memory/tools.json'}))

    def run_fixture(self, events, **options):
        def connect(address, diagnostic=None):
            self.peer = SyntheticConnection(diagnostic, events, **options)
            return self.peer, dict(model='synthetic-model', models=['synthetic-model'])
        with patch.object(codex, 'connect', side_effect=connect):
            return codex.run(self.initial, self.tools, self.events.append)

    def report(self):
        files = list(self.directory.glob('*.json'))
        self.assertEqual(len(files), 1)
        self.assertLessEqual(files[0].stat().st_size, 32768)
        self.assertEqual(files[0].stat().st_mode & 0o777, 0o600)
        return json.loads(files[0].read_text())

    def test_detailed_turn_error_and_stderr_are_redacted_and_saved_before_cleanup(self):
        key = 'synthetic-private-key-value'
        token = 'synthetic-private-token-value'
        jwt = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJzeW50aGV0aWMifQ.signature-for-offline-only'
        error = dict(message='Response rejected: '+key+' '+jwt+' PRIVATE USER CONVERSATION',
                     codexErrorInfo={'httpConnectionFailed':{'httpStatusCode':502}},
                     additionalDetails='Authorization: Bearer '+token)
        def connect(address, diagnostic=None):
            peer = SyntheticConnection(diagnostic, [self.turn('failed', error)],
                                       stderr='ERROR transport '+key+'\nPRIVATE HISTORY CONTENT\nERROR payload {"messages":["PRIVATE TOOL BODY"]}\n')
            relay = types.SimpleNamespace(key=key, token=token,recovery=types.SimpleNamespace(cancel=lambda:None), evidence=lambda:[dict(http_status=429,
                    target='https://api.deepseek.com/responses', request_model='deepseek-flash',
                    response_models=[], usage=None, completed=False)], close=lambda:None)
            peer.child.yohaku_provider_relay = relay
            diagnostic.attach(peer.child)
            def cleanup():
                self.assertIn('ERROR transport', self.report()['stderr_summary'])
                self.cleanup_observed = True
            peer.child.yohaku_runtime = types.SimpleNamespace(cleanup=cleanup)
            return peer, dict(model='synthetic-model', models=['synthetic-model'])
        with patch.object(codex, 'connect', side_effect=connect):
            with self.assertRaises(codex.CodexError) as failure:
                codex.run(self.initial, self.tools, self.events.append)
        self.assertIn('Response rejected', str(failure.exception))
        report = self.report()
        self.assertTrue(self.cleanup_observed)
        self.assertEqual(report['failure_stage'], 'turn/completed')
        self.assertEqual(report['errors'][-1]['error']['codexErrorInfo'], {'httpConnectionFailed':{'httpStatusCode':502}})
        self.assertEqual(report['provider_requests'][0]['http_status'], 429)
        self.assertEqual(report['process_exit_code'], 0)
        serialized = json.dumps(report) + str(failure.exception)
        for private in [key, token, jwt, 'PRIVATE USER CONVERSATION', 'PRIVATE HISTORY CONTENT', 'PRIVATE TOOL BODY']:
            self.assertNotIn(private, serialized)

    def test_failed_without_detail_does_not_invent_cause(self):
        with self.assertRaisesRegex(codex.CodexError, 'No detailed error supplied by Codex'):
            self.run_fixture([self.turn('failed')])
        report = self.report()
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['received_turn_status'], 'failed')
        self.assertEqual(report['provider_requests'], [])

    def test_error_notification_is_correlated_and_used_when_terminal_error_is_null(self):
        wrong = dict(method='error', params=dict(threadId='other-thread', turnId='turn-fixture',
                     error=dict(message='MUST NOT USE WRONG THREAD'), willRetry=False))
        error = dict(method='error', params=dict(threadId='thread-fixture', turnId='turn-fixture',
                     error=dict(message='Observed stream disconnected', codexErrorInfo='other'), willRetry=False))
        with self.assertRaisesRegex(codex.CodexError, 'Observed stream disconnected'):
            self.run_fixture([wrong, error, self.turn('failed')])
        self.assertEqual(len(self.report()['errors']), 1)

    def test_process_exit_retains_actual_code_and_bounded_stderr(self):
        with self.assertRaises(codex.CodexError):
            self.run_fixture([], exit_code=7, stderr='ERROR synthetic process failure\n' * 3000, disconnect=True)
        report = self.report()
        self.assertEqual(report['process_exit_code'], 7)
        self.assertFalse(report['process_killed_for_cleanup'])
        self.assertGreater(report['stderr_bytes_seen'], 16384)
        self.assertLessEqual(len(report['stderr_summary']), 1536)
        self.assertEqual(report['failure_stage'], 'waiting_for_turn')

    def test_tool_return_send_and_later_failed_event_are_distinct(self):
        with self.assertRaises(codex.CodexError):
            self.run_fixture([self.tool(), self.turn('failed')])
        item = self.report()['tools'][0]
        self.assertTrue(item['execution_returned'])
        self.assertTrue(item['tool_ok'])
        self.assertTrue(item['result_sent_to_codex_stdin'])
        self.assertTrue(item['followup_observed_from_codex'])
        self.assertEqual(item['followup_event'], 'turn/completed')

    def test_serialization_failure_is_not_reported_as_sent(self):
        self.tools.call = lambda name,args:dict(ok=True, result={'not-json'})
        with self.assertRaises(codex.CodexError):
            self.run_fixture([self.tool()])
        report = self.report()
        self.assertEqual(report['failure_stage'], 'tool_result_serialization')
        self.assertTrue(report['tools'][0]['execution_returned'])
        self.assertFalse(report['tools'][0]['result_sent_to_codex_stdin'])
        self.assertFalse(report['tools'][0]['followup_observed_from_codex'])

    def test_pipe_failure_is_not_reported_as_sent(self):
        with self.assertRaises(codex.CodexError):
            self.run_fixture([self.tool()], send_failure=True)
        report = self.report()
        self.assertEqual(report['failure_stage'], 'tool_result_return')
        self.assertFalse(report['tools'][0]['result_sent_to_codex_stdin'])

    def test_normal_completion_has_real_exit_and_no_conversation_log(self):
        result = self.run_fixture([self.tool(), self.turn()])
        report = self.report()
        self.assertEqual(report['status'], 'completed')
        self.assertIsNone(report['failure_stage'])
        self.assertEqual(report['process_exit_code'], 0)
        self.assertEqual(report['thread_id'], 'thread-fixture')
        self.assertEqual(report['turn_id'], 'turn-fixture')
        self.assertEqual(result['diagnostic_path'], str(next(self.directory.glob('*.json'))))
        self.assertNotIn('PRIVATE', json.dumps(report))

    def test_unsafe_directory_is_not_followed_or_silently_claimed_saved(self):
        self.directory.symlink_to(Path(self.temp.name), target_is_directory=True)
        report = diagnostics.TurnDiagnostics(self.initial)
        self.assertIn('unavailable', report.location())
        self.assertEqual(list(Path(self.temp.name).glob('*.json')), [])

    def test_unsupported_tool_returns_failure_result_without_crashing_diagnostics(self):
        request = self.tool()
        request['params']['tool'] = 'unsupported_tool'
        self.run_fixture([request, self.turn()])
        report = self.report()
        self.assertEqual(report['status'], 'completed')
        self.assertFalse(report['tools'][0]['tool_ok'])
        self.assertTrue(report['tools'][0]['result_sent_to_codex_stdin'])

    def test_replayed_tool_request_is_not_mistaken_for_followup(self):
        report = diagnostics.TurnDiagnostics(self.initial)
        report.identify('thread-fixture', 'turn-fixture')
        report.tool_start(501, 'yohaku_read_text')
        report.tool_executed(dict(ok=True))
        report.tool_sent()
        report.observe(self.tool())
        self.assertFalse(report.data['tools'][0]['followup_observed_from_codex'])
        report.observe(self.turn())
        self.assertTrue(report.data['tools'][0]['followup_observed_from_codex'])

    def test_rpc_error_code_is_kept_but_data_and_unicode_length_are_bounded(self):
        report = diagnostics.TurnDiagnostics(self.initial)
        for sequence in range(100):
            report.rpc_error('turn/start', dict(code=-32000, message='错' * 4000,
                            additionalDetails='误' * 4000, data={'input':'PRIVATE DATA MUST NOT BE SAVED'}))
        saved = self.report()
        self.assertEqual(saved['errors'][-1]['error']['code'], -32000)
        self.assertTrue(saved['errors'][-1]['error']['data_present_but_omitted'])
        self.assertNotIn('PRIVATE DATA', json.dumps(saved))

    def test_retry_error_notification_does_not_turn_normal_completion_into_failure(self):
        event = dict(method='error', params=dict(threadId='thread-fixture', turnId='turn-fixture',
                     error=dict(message='Synthetic retryable failure'), willRetry=True))
        self.run_fixture([event, self.turn()])
        saved = self.report()
        self.assertEqual(saved['status'], 'completed')
        self.assertTrue(saved['errors'][0]['willRetry'])

    def test_existing_wire_error_event_contains_detail_and_diagnostic_location(self):
        import yohaku_agent as agent
        initial = dict(self.initial, config={'codex_entry':'synthetic-only','protocol':'codex-local'})
        def connect(address, diagnostic=None):
            peer = SyntheticConnection(diagnostic, [self.turn('failed', dict(message='Synthetic precise wire failure'))])
            return peer, dict(model='synthetic-model',models=['synthetic-model'])
        output = io.StringIO()
        with patch.object(agent, 'Tools', return_value=self.tools), patch.object(codex, 'connect', side_effect=connect), \
             patch('sys.stdin', io.StringIO(json.dumps(initial)+'\n')), patch('sys.stdout', output):
            agent.wire()
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        error = next(event for event in events if event['event'] == 'error')
        self.assertIn('Synthetic precise wire failure', error['text'])
        self.assertIn(str(next(self.directory.glob('*.json'))), error['text'])
        self.assertFalse(any(event['event']=='done' for event in events))

    def test_forced_cleanup_is_distinguished_from_an_unexpected_process_exit(self):
        report = diagnostics.TurnDiagnostics(self.initial)
        child = subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(60)'],
                                 stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        connection = codex.Connection(child,report)
        real_wait = child.wait
        waits = []
        def bounded_wait(timeout=None):
            waits.append(timeout)
            return real_wait(timeout=0.02 if len(waits)==1 else timeout)
        with patch.object(child,'wait',side_effect=bounded_wait):
            connection.close()
        saved = self.report()
        self.assertEqual(saved['process_exit_code'], -9)
        self.assertTrue(saved['process_killed_for_cleanup'])

    def test_public_error_explanation_does_not_persist_continuation_payload(self):
        error = dict(message='', misalignment=dict(errorType='synthetic-category',
                     detailedExplanation='Synthetic public explanation', reviewTarget='PRIVATE OPAQUE TARGET',
                     steer={'message':'PRIVATE CONTINUATION CONTENT'}))
        with self.assertRaisesRegex(codex.CodexError, 'Synthetic public explanation'):
            self.run_fixture([self.turn('failed', error)])
        saved = json.dumps(self.report())
        self.assertNotIn('PRIVATE OPAQUE', saved)
        self.assertNotIn('PRIVATE CONTINUATION', saved)


if __name__ == '__main__':
    unittest.main()
