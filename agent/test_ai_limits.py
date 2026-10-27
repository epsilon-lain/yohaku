import http.client
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

import yohaku_agent as agent
import yohaku_codex as codex
import yohaku_codex_diagnostics as diagnostics
import yohaku_codex_provider as provider
from test_agent import MockAPI, response


PEER = r'''
import json,sys
steps=int(sys.argv[1])
mode=sys.argv[2]
index=0
replayed=False
def emit(value):print(json.dumps(value),flush=True)
def call():
    emit({'id':1000+index,'method':'item/tool/call','params':{'threadId':'offline-thread','tool':'yohaku_read_text','arguments':{'path':'files/fixture.txt'}}})
for line in sys.stdin:
    value=json.loads(line)
    method=value.get('method')
    if method=='thread/start':
        emit({'id':value['id'],'result':{'thread':{'id':'offline-thread'},'activePermissionProfile':{'id':'yohaku-control'}}})
    elif method=='config/read':
        emit({'id':value['id'],'result':{'config':{'features':{'shell_tool':False,'apps':False,'plugins':False}}}})
    elif method=='turn/start':
        emit({'id':value['id'],'result':{'turn':{'id':'offline-turn'}}})
        call()
    elif method is None and 'result' in value:
        assert value['id']==1000+index
        assert value['result']['success'] is True
        if mode=='replay' and index==0 and not replayed:
            replayed=True
            call()
            continue
        index+=1
        if index<steps:
            call()
        else:
            if mode!='error':
                emit({'method':'item/completed','params':{'item':{'id':'offline-message','type':'agentMessage','text':'Offline loop complete'}}})
            turn={'id':'offline-turn','status':'failed' if mode=='error' else 'completed'}
            if mode=='error':turn['error']={'message':'Synthetic downstream failed after completed tools'}
            emit({'method':'turn/completed','params':{'threadId':'offline-thread','turn':turn}})
'''


def connection_fixture(steps, mode='normal'):
    def connect(address, diagnostic=None):
        child=subprocess.Popen([sys.executable,'-B','-c',PEER,str(steps),mode],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        child.yohaku_linux=True
        peer=codex.Connection(child,diagnostic)
        peer.info={'cwd':'offline-empty-control'}
        return peer,{'model':'offline-model','models':['offline-model']}
    return connect


def fixture_tools(call):
    tools=agent.Tools(lambda request:None)
    tools.bootstrap=lambda context:context
    tools.definitions=[{'name':'read_text','description':'Offline fixture','parameters':{'type':'object'}}]
    tools.call=call
    return tools


class CountPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='yohaku-count-policy-')
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.calls=[]
        self.tools=fixture_tools(lambda name,args:self.record(name,args))
        self.diagnostic_patch=patch.object(diagnostics,'DIRECTORY',self.root/'diagnostics')
        self.diagnostic_patch.start()
        self.addCleanup(self.diagnostic_patch.stop)

    def record(self,name,args):
        self.calls.append((name,args))
        (self.root/'completed.txt').write_text(str(len(self.calls)))
        return {'ok':True,'result':{'text':'offline fixture'}}

    def config(self,api,**limits):
        value=api.config()
        value.pop('max_rounds')
        value.update(limits)
        return value

    def codex_run(self,steps=140,mode='normal',patches=(),**limits):
        initial={'config':{'codex_entry':'offline-only',**limits},'context':{},'prompt':'Offline regression'}
        for item in patches:item.start();self.addCleanup(item.stop)
        with patch.object(codex,'connect',side_effect=connection_fixture(steps,mode)):
            return codex.run(initial,self.tools,lambda value:None)

    def test_missing_and_null_are_unlimited_present_numbers_are_explicit(self):
        config=agent.read_config(self.root/'missing.json')
        self.assertNotIn('max_rounds',config)
        self.assertIsNone(agent.optional_count(config,'max_tool_calls'))
        self.assertIsNone(agent.optional_count({'max_rounds':None},'max_rounds'))
        path=self.root/'finite.json'
        path.write_text(json.dumps({'max_rounds':12,'max_tool_calls':0,'timeout':17,'max_tokens':123}))
        finite=agent.read_config(path)
        self.assertEqual(agent.optional_count(finite,'max_rounds'),12)
        self.assertEqual(agent.optional_count(finite,'max_tool_calls'),0)
        self.assertEqual((finite['timeout'],finite['max_tokens']),(17,123))
        for value in [-1,True,False,1.5,'12',[],{}]:
            with self.assertRaisesRegex(agent.ToolError,'nonnegative integer'):
                agent.optional_count({'max_rounds':value},'max_rounds')

    def test_direct_default_surpasses_old_12_and_50_round_limits(self):
        for protocol in ['chat','responses','anthropic']:
            self.calls.clear()
            with self.subTest(protocol=protocol),MockAPI(protocol,lambda body,number:(200,response(protocol,'read_text',{'path':'files/fixture.txt'}) if number<64 else response(protocol))) as api:
                result=agent.Agent(agent.Provider(self.config(api)),self.tools).run('offline',{})
                self.assertEqual(len(api.requests),65)
                self.assertEqual(result['tool_calls'],64)
                self.assertEqual(len(self.calls),64)

    def test_direct_explicit_round_budget_preserves_completed_work_and_no_50_clamp(self):
        with MockAPI('chat',lambda body,number:(200,response('chat','read_text',{}))) as api:
            with self.assertRaisesRegex(agent.ToolError,'round limit'):
                agent.Agent(agent.Provider(self.config(api,max_rounds=2)),self.tools).run('offline',{})
            self.assertEqual(len(api.requests),2)
            self.assertEqual((self.root/'completed.txt').read_text(),'2')
        self.calls.clear()
        with MockAPI('chat',lambda body,number:(200,response('chat','read_text',{}) if number<59 else response('chat'))) as api:
            result=agent.Agent(agent.Provider(self.config(api,max_rounds=60)),self.tools).run('offline',{})
            self.assertEqual(len(api.requests),60)
            self.assertEqual(result['tool_calls'],59)

    def test_batch_above_32_succeeds_but_explicit_tool_budget_stops_exactly(self):
        batch=response('chat','read_text',{})
        template=batch['choices'][0]['message']['tool_calls'][0]
        batch['choices'][0]['message']['tool_calls']=[dict(template,id='call-'+str(index)) for index in range(40)]
        with MockAPI('chat',lambda body,number:(200,batch if number==0 else response('chat'))) as api:
            result=agent.Agent(agent.Provider(self.config(api)),self.tools).run('offline',{})
            self.assertEqual(result['tool_calls'],40)
        self.calls.clear()
        with MockAPI('chat',lambda body,number:(200,batch)) as api:
            with self.assertRaisesRegex(agent.ToolError,'explicit max_tool_calls=3'):
                agent.Agent(agent.Provider(self.config(api,max_tool_calls=3)),self.tools).run('offline',{})
            self.assertEqual(len(self.calls),3)
            self.assertEqual(len(api.requests),1)
            self.assertNotIn('max_tool_calls',api.requests[0][2])

    def test_zero_round_budget_and_malformed_batch_never_execute(self):
        with MockAPI('chat',lambda body,number:(200,response('chat'))) as api:
            with self.assertRaisesRegex(agent.ToolError,'round limit'):
                agent.Agent(agent.Provider(self.config(api,max_rounds=0)),self.tools).run('offline',{})
            self.assertEqual(len(api.requests),0)
        batch=response('chat','read_text',{})
        batch['choices'][0]['message']['tool_calls']*=2
        with MockAPI('chat',lambda body,number:(200,batch)) as api:
            with self.assertRaisesRegex(agent.ToolError,'Invalid tool call batch'):
                agent.Agent(agent.Provider(self.config(api)),self.tools).run('offline',{})
            self.assertEqual(self.calls,[])

    def test_codex_real_stdio_peer_surpasses_100_and_replay_is_not_reexecuted(self):
        result=self.codex_run(mode='replay')
        self.assertEqual(result['tool_calls'],140)
        self.assertEqual(len(self.calls),140)
        report=json.loads(next((self.root/'diagnostics').glob('*.json')).read_text())
        self.assertEqual(report['status'],'completed')
        self.assertEqual(report['tool_count'],140)
        self.assertEqual(report['process_exit_code'],0)

    def test_codex_explicit_tool_budget_and_detailed_error_keep_progress(self):
        with self.assertRaisesRegex(codex.CodexError,'explicit max_tool_calls=3'):
            self.codex_run(max_tool_calls=3)
        self.assertEqual(len(self.calls),3)
        self.assertEqual((self.root/'completed.txt').read_text(),'3')
        self.calls.clear()
        with self.assertRaisesRegex(codex.CodexError,'Synthetic downstream failed'):
            self.codex_run(steps=140,mode='error')
        self.assertEqual(len(self.calls),140)
        reports=[json.loads(path.read_text()) for path in (self.root/'diagnostics').glob('*.json')]
        self.assertTrue(all(report['status']=='failed' and report['process_exit_code']==0 for report in reports))
        self.assertTrue(any(report.get('received_turn_status')=='failed' and report['errors'] for report in reports))

    def test_codex_unsupported_round_budget_is_refused_before_connect_not_ignored(self):
        with patch.object(codex,'connect') as connect:
            for limit in [0,3]:
                with self.assertRaisesRegex(codex.CodexError,'cannot enforce max_rounds'):
                    codex.run({'config':{'codex_entry':'offline','max_rounds':limit},'prompt':'offline'},self.tools,lambda value:None)
            connect.assert_not_called()
        self.assertEqual(self.calls,[])

    def test_codex_silent_turn_stops_at_configured_budget_without_resend(self):
        # A quiet stream is stopped at the configured total budget, not at a fixed 900s.
        emitted=[]
        silent=subprocess.Popen([sys.executable,'-B','-c','import sys\nfor line in sys.stdin:pass\n'],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        def connect(address,diagnostic=None):
            peer=codex.Connection(silent,diagnostic)
            peer.info={'cwd':'offline-empty-control'};peer.linux=True
            return peer,{'model':'offline-model','models':['offline-model']}
        def request(peer,method,params,timeout=30):
            if method=='permissionProfile/list':return {'data':[{'id':'yohaku-control','allowed':True}]}
            if method=='thread/start':return {'thread':{'id':'offline-thread'},'activePermissionProfile':{'id':'yohaku-control'}}
            if method=='config/read':return {'config':{'features':{'shell_tool':False,'apps':False,'plugins':False}}}
            if method=='turn/start':return {'turn':{'id':'offline-turn'}}
            return {}
        started=time.monotonic()
        try:
            with patch.object(codex,'connect',side_effect=connect),patch.object(codex.Connection,'request',request):
                with self.assertRaisesRegex(codex.CodexError,'exceeded 1 seconds'):
                    codex.run({'config':{'codex_entry':'offline','turn_timeout':1},'context':{},'prompt':'Offline budget'},self.tools,emitted.append)
        finally:
            if silent.poll() is None:silent.kill();silent.wait()
            silent.stdin.close();silent.stdout.close();silent.stderr.close()
        self.assertLess(time.monotonic()-started,8)
        self.assertEqual(self.calls,[])
        self.assertTrue(any('time budget:' in (value.get('text') or '') for value in emitted))
        default=codex.turn_timeout({})
        self.assertEqual(default,codex.TURN_TIMEOUT_DEFAULT)
        self.assertIsNone(default)

    def test_codex_long_task_preset_and_invalid_budgets(self):
        self.assertEqual(codex.turn_timeout({'turn_timeout_long':True}),codex.TURN_TIMEOUT_LONG)
        self.assertEqual(codex.turn_timeout({'turn_timeout':3600}),3600)
        self.assertEqual(codex.turn_timeout({'turn_timeout':3600,'turn_timeout_long':True}),max(3600,codex.TURN_TIMEOUT_LONG))
        self.assertEqual(codex.turn_timeout({'turn_timeout_long':False}),codex.TURN_TIMEOUT_DEFAULT)
        self.assertIn('exceeded 3600 seconds',codex.timeout_error(3600))
        with patch.object(codex,'connect') as connect:
            for timeout in [0,-5,True,1.5,'900',[]]:
                with self.assertRaisesRegex(codex.CodexError,'turn_timeout must be a positive integer'):
                    codex.run({'config':{'codex_entry':'offline','turn_timeout':timeout},'context':{},'prompt':'Offline budget'},self.tools,lambda value:None)
            connect.assert_not_called()
        self.assertEqual(self.calls,[])

    def test_direct_http_error_after_old_threshold_preserves_prior_work(self):
        with MockAPI('chat',lambda body,number:(200,response('chat','read_text',{})) if number<55 else (503,{'error':'synthetic'})) as api:
            with self.assertRaisesRegex(agent.ToolError,'503'):
                agent.Agent(agent.Provider(self.config(api)),self.tools).run('offline',{})
            self.assertEqual(len(self.calls),55)
            self.assertEqual((self.root/'completed.txt').read_text(),'55')
    def test_codex_turn_budget_is_total_time_a_long_activity_does_not_reset_it(self):
        # An explicit budget bounds the whole turn: once total elapsed time passes it,
        # the next event boundary stops the turn even though events kept arriving.
        real=time.monotonic
        offset=[0.0]
        def clock():return real()+offset[0]
        events=[]
        def emit(value):
            events.append(value)
            if str(value.get('text','')).startswith('Codex connected'):offset[0]=10**6
        initial={'config':{'codex_entry':'offline-only','turn_timeout':2},'context':{},'prompt':'Offline regression'}
        with patch.object(codex.time,'monotonic',clock),patch.object(codex,'connect',side_effect=connection_fixture(3)):
            with self.assertRaisesRegex(codex.CodexError,'exceeded 2 seconds'):
                codex.run(initial,self.tools,emit)
        self.assertEqual(self.calls,[])
        # The same busy fixture with the historical default completes normally.
        result=self.codex_run(steps=3)
        self.assertEqual(result['tool_calls'],3)

    def test_relay_surpasses_128_requests_without_fake_429_and_keeps_bounded_evidence(self):
        relay=provider.Relay('offline-fixture-not-a-real-key')
        self.addCleanup(relay.close)
        wire=b'data: {"type":"response.completed","response":{"model":"deepseek-flash","usage":{"input_tokens":1,"output_tokens":1}}}\n\n'
        def upstream_response():
            value=io.BytesIO(wire)
            value.status=200
            value.getheader=lambda *arguments:'text/event-stream'
            return value
        with patch.object(provider,'ObservedHTTPS') as upstream:
            upstream.return_value.getresponse.side_effect=upstream_response
            for index in range(140):
                connection=http.client.HTTPConnection('127.0.0.1',relay.server.server_port,timeout=5)
                try:
                    connection.request('POST','/responses',body=json.dumps({'model':provider.MODEL,'reasoning':{'effort':'high'}}),headers={'Authorization':'Bearer '+relay.token})
                    reply=connection.getresponse()
                    self.assertEqual(reply.status,200,index)
                    self.assertEqual(reply.read(),wire)
                finally:connection.close()
            self.assertEqual(upstream.call_count,140)
        self.assertEqual(relay.request_count,140)
        evidence=relay.evidence()
        self.assertEqual(len(evidence),128)
        self.assertEqual((evidence[0]['request_index'],evidence[-1]['request_index']),(13,140))
        report=diagnostics.TurnDiagnostics({'config':{}})
        child=types.SimpleNamespace(yohaku_provider_relay=relay)
        report.process_closed(child,diagnostics.StderrCapture(None),False)
        self.assertEqual(report.data['provider_request_count'],140)

    def test_real_stop_after_old_threshold_keeps_progress_and_closes_codex_peer(self):
        for mode in ['codex','direct']:
            with self.subTest(mode=mode):
                directory=self.root/mode
                directory.mkdir()
                child=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--offline-stop-worker',mode,str(directory)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                try:
                    for index in range(125):
                        line=child.stdout.readline()
                        self.assertEqual(line.strip(),'step '+str(index+1))
                    child.send_signal(signal.SIGTERM)
                    child.communicate(timeout=10)
                    self.assertNotEqual(child.returncode,0)
                    self.assertGreaterEqual(int((directory/'completed.txt').read_text()),125)
                    if mode=='codex':
                        report=json.loads(next((directory/'diagnostics').glob('*.json')).read_text())
                        # SIGTERM can land between the tool returning and its result being
                        # delivered to the peer. Both are truthful stop boundaries; neither
                        # may be retried. Require one of those exact states, not a fabricated
                        # generic success.
                        summary=report['exception_summary']
                        self.assertTrue('stopped' in summary or 'result delivery unknown' in summary,summary)
                        self.assertEqual(report['status'],'failed')
                        self.assertIsNotNone(report['process_exit_code'])
                    # A second worker must start after the first was stopped. This mirrors
                    # the UI's Send action after Stop without reusing or replaying the old turn.
                    again=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--offline-stop-worker',mode,str(directory)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                    try:
                        self.assertEqual(again.stdout.readline().strip(),'step 1')
                        again.send_signal(signal.SIGTERM)
                        again.communicate(timeout=10)
                        self.assertNotEqual(again.returncode,0)
                        self.assertGreaterEqual(int((directory/'completed.txt').read_text()),1)
                    finally:
                        if again.poll() is None:again.kill();again.wait()
                        again.stdout.close();again.stderr.close()
                finally:
                    if child.poll() is None:child.kill();child.wait()
                    child.stdout.close();child.stderr.close()


def stop_worker(mode,directory):
    directory=Path(directory)
    diagnostics.DIRECTORY=directory/'diagnostics'
    count=0
    def call(name,args):
        nonlocal count
        count+=1
        temporary=directory/'completed.pending'
        temporary.write_text(str(count))
        os.replace(temporary,directory/'completed.txt')
        print('step '+str(count),flush=True)
        return {'ok':True,'result':{}}
    tools=fixture_tools(call)
    if mode=='codex':
        with patch.object(codex,'connect',side_effect=connection_fixture(1000000)):
            try:codex.run({'config':{'codex_entry':'offline'},'prompt':'offline'},tools,lambda value:None)
            except codex.CodexError:return 2
    else:
        class Peer:
            config={}
            initial=lambda *arguments:[]
            append=lambda *arguments:None
            request=lambda *arguments:({},[{'id':'offline','name':'read_text','arguments':{}}],'',{})
        agent.Agent(Peer(),tools).run('offline',{})
    return 0


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--offline-stop-worker':
        raise SystemExit(stop_worker(sys.argv[2],sys.argv[3]))
    unittest.main()
