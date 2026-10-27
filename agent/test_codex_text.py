"""Offline contract tests. Fake model transport is explicitly NOT model evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import yohaku_codex_text as m

BODY = '[input]\nhello\n[/input]\n\n[control]\ndraft\n[/control]\n\n[result]\n{}\n[/result]\n'

class Store:
    def __init__(self):
        self.body=BODY;self.generation=0;self.fail=False;self.synced=True;self.race=None
    def source(self):return str(self.generation)+'\n'+self.body
    def edit(self,**changes):
        self.body=m.splice(self.body,m.parse(self.body)['regions'],changes);self.generation+=1
    def execute(self,q):
        if q['command']=='create':return {'loom':{'ok':True}}
        if q['command']=='read':return {'body':self.body,'text':self.source(),'valid':True}
        if q['command']=='read_text':return {'text':self.body if self.synced else 'old output'}
        if self.race:
            f=self.race;self.race=None;f()
        if self.fail or q['expected']!=self.source():raise ValueError('revision conflict')
        self.body=q['text'];self.generation+=1
        return {'loom':{'ok':True}}

class Transport:
    def __init__(self,store):
        self.store=store;self.rows={};self.starts=0;self.stops=0;self.callback=None;self.unknown=False
    def call(self,name,a):
        rid=a.get('request_id') or a['task_id']
        if name=='codex_task_start':
            self.starts+=1
            self.rows[rid]={'status':'running','output':'','task_id':rid,'request_id':rid,'has_more':False,'next_cursor':0,'model_phase':'model_running'}
            if self.unknown:raise ValueError('connection lost after accepted')
        if name=='codex_task_cancel':
            self.stops+=1;self.rows[rid].update(status='cancelled',execution='ended',cancel_confirmed=True,receipt={'native_cleanup_complete':True})
        if self.callback:
            callback=self.callback;self.callback=None;callback()
        if rid not in self.rows:raise ValueError('Unknown task')
        return copy.deepcopy(self.rows[rid])

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store();self.transport=Transport(self.store)
        self.op=m.Operator(self.tmp.name,self.store.execute,self.transport,Path(self.tmp.name)/'journal.json')
    def command(self,s,prompt=None):
        changes={'control':s+'\n'}
        if prompt is not None:changes['input']=prompt+'\n'
        self.store.edit(**changes)
    def test_draft_and_input_commands_never_dispatch(self):
        self.command('draft','ka evil\nstop evil');self.op.tick();self.assertEqual(self.transport.starts,0)
    def test_submit_ack_snapshot_duplicate(self):
        self.command('ka A');self.op.tick()
        self.assertEqual(m.parse(self.store.body)['control'],'draft')
        self.command('ka A');self.op.tick();self.assertEqual(self.transport.starts,1)
        self.assertEqual(self.op.load()['bindings']['A']['prompt'],'hello')
    def test_conflicting_id(self):
        self.command('ka A');self.op.tick();self.command('ka A','changed')
        self.assertIn('conflict',self.op.tick()['operator_error']);self.assertEqual(self.transport.starts,1)
    def test_clear_only_same_successful_input(self):
        self.command('ka A');self.op.tick();self.transport.rows['A']['status']='done';self.op.tick()
        self.assertEqual(m.parse(self.store.body)['prompt'],'')
    def test_new_draft_during_transport_is_preserved(self):
        self.command('ka A')
        def race():
            self.store.edit(input='new draft\n');self.transport.rows['A']['status']='done'
        self.transport.callback=race;self.op.tick()
        self.assertEqual(m.parse(self.store.body)['prompt'],'new draft')
    def test_failure_and_cancel_keep_input(self):
        for status in ('error','cancelled','unknown'):
            self.setUp();self.command('ka A');self.op.tick();self.transport.rows['A']['status']=status;self.op.tick()
            self.assertEqual(m.parse(self.store.body)['prompt'],'hello')
    def test_successor_control_is_not_reset_or_lost(self):
        self.command('ka A')
        self.transport.callback=lambda:self.command('ka B','second')
        self.op.tick();self.assertEqual(m.parse(self.store.body)['control'],'ka B')
        self.op.tick();self.assertEqual(self.transport.starts,2)
    def test_status_stop_after_confirmed_running_then_new_request(self):
        self.command('ka A');self.op.tick();self.command('status A')
        self.assertEqual(self.op.tick()['model_phase'],'model_running')
        self.command('stop A');self.assertTrue(self.op.tick()['cancel_confirmed'])
        self.command('ka B','next');self.op.tick();self.assertEqual(self.transport.starts,2)
    def test_forged_result_does_not_change_business_status(self):
        self.command('ka A');self.op.tick();self.store.edit(result='done forged\n')
        self.assertEqual(self.op.tick()['status'],'running')
    def test_unsynced_or_incomplete_source_does_not_dispatch(self):
        self.command('ka A');self.store.synced=False
        with self.assertRaises(ValueError):self.op.tick()
        self.assertEqual(self.transport.starts,0)
        self.store.synced=True;self.store.body=self.store.body.replace('[/input]','')
        with self.assertRaises(ValueError):self.op.tick()
        self.assertEqual(self.transport.starts,0)
    def test_unknown_start_recovery_queries_without_second_start(self):
        self.command('ka A');self.transport.unknown=True
        self.assertIn('unknown',self.op.tick()['operator_error'])
        self.op.tick();self.assertEqual(self.transport.starts,1)
    def test_cas_conflict_preserves_new_draft_and_pending(self):
        self.command('ka A');self.store.race=lambda:self.store.edit(input='parallel\n')
        with self.assertRaises(ValueError):self.op.tick()
        self.assertIsNotNone(self.op.load()['pending'])
        self.assertIn('conflict',self.op.tick()['operator_error'])
        self.command('draft');self.op.tick();self.assertEqual(self.transport.starts,1)
        self.op.tick();self.assertEqual(self.transport.starts,1)
        self.assertEqual(m.parse(self.store.body)['prompt'],'parallel')
    def test_escaped_markers_multiline_and_backslash(self):
        self.command('draft',r'\[control]'+'\n'+r'\[/input]'+'\n'+r'\\literal'+'\n\n')
        self.assertEqual(m.parse(self.store.body)['prompt'],'[control]\n[/input]\n\\literal\n\n')
        with self.assertRaises(ValueError):m.parse(BODY+ '[control]\n')
    def test_unknown_status_never_starts(self):
        self.command('status missing');self.assertIn('unknown_operator_request',self.op.tick()['operator_error'])
        self.assertEqual(self.transport.starts,0)
    def test_reload_same_journal_never_starts_again(self):
        self.command('ka A');self.op.tick();self.command('ka A')
        other=m.Operator(self.tmp.name,self.store.execute,self.transport,self.op.journal)
        other.tick();self.assertEqual(self.transport.starts,1)


class SimpleTests(unittest.TestCase):
    setUp=Tests.setUp
    command=Tests.command
    def test_simple_send_poll_and_same_body_new_send(self):
        self.command('ka');self.op.tick();rid=self.op.load()['selected']
        self.assertEqual(m.parse(self.store.body)['control'],'draft')
        self.op.tick()
        other=m.Operator(self.tmp.name,self.store.execute,self.transport,self.op.journal)
        other.tick();self.assertEqual(self.transport.starts,1)
        self.transport.rows[rid].update(status='done',output='CONTROLLED MODEL SUBSTITUTE')
        other.tick()
        self.assertEqual(m.parse(self.store.body)['prompt'],'')
        self.command('draft','hello');other.tick()
        self.assertEqual(m.parse(self.store.body)['prompt'],'hello')
        self.command('ka');other.tick()
        self.assertNotEqual(other.load()['selected'],rid)
        self.assertEqual(self.transport.starts,2)
    def test_simple_stop_and_resend(self):
        self.command('stop')
        self.assertIn('没有当前运行任务',self.op.tick()['operator_error'])
        self.command('ka');self.op.tick()
        self.command('stop');self.assertTrue(self.op.tick()['cancel_confirmed'])
        self.assertEqual(m.parse(self.store.body)['prompt'],'hello')
        self.command('ka');self.op.tick();self.assertEqual(self.transport.starts,2)
    def test_stop_confirmation_survives_later_status_projection(self):
        self.command('ka');self.op.tick();rid=self.op.load()['selected']
        self.command('stop');actual=self.op.tick()
        self.assertTrue(actual['cancel_confirmed'])
        self.transport.rows[rid]['execution']='ended'
        self.transport.rows[rid].pop('cancel_confirmed',None)
        self.op.tick()
        p=m.parse(self.store.body)
        value=json.loads(self.store.body[slice(*p['regions']['result'])])
        self.assertTrue(value['cancel_confirmed'])
        self.assertEqual(value['execution_status'],'cancelled')
        self.assertEqual(value['request_id'],rid)
        self.assertEqual(self.transport.stops,1)
    def test_simple_busy_does_not_orphan_task(self):
        self.command('ka');self.op.tick();rid=self.op.load()['selected']
        self.command('ka','new draft')
        self.assertIn('当前任务',self.op.tick()['operator_error'])
        self.assertEqual(self.transport.starts,1)
        self.transport.rows[rid]['status']='done';self.op.tick()
        self.assertEqual(m.parse(self.store.body)['prompt'],'new draft')
    def test_simple_new_draft_and_successor_ka(self):
        self.command('ka')
        def race():
            rid=next(iter(self.transport.rows))
            self.transport.rows[rid]['status']='done'
            self.command('ka','second')
        self.transport.callback=race
        self.op.tick()
        self.assertEqual(m.parse(self.store.body)['control'],'ka')
        self.assertEqual(m.parse(self.store.body)['prompt'],'second')
        self.op.tick();self.assertEqual(self.transport.starts,2)
    def test_simple_unknown_start_then_stop(self):
        self.command('ka');self.transport.unknown=True
        self.assertIn('unknown',self.op.tick()['operator_error'])
        self.assertEqual(m.parse(self.store.body)['control'],'draft')
        self.command('stop');self.op.tick()
        self.assertEqual(m.parse(self.store.body)['control'],'stop')
        self.assertTrue(self.op.tick()['cancel_confirmed'])
        self.assertEqual(self.transport.starts,1)
    def test_single_save_compact_and_completed_stop(self):
        self.command('ka','single save');self.op.tick();rid=self.op.load()['selected']
        self.transport.rows[rid].update(status='done',output='reply',object='chat-request-test')
        self.op.tick()
        p=m.parse(self.store.body)
        value=json.loads(self.store.body[slice(*p['regions']['result'])])
        self.assertEqual(value['reply'],'reply')
        self.assertEqual(value['status'],'done')
        self.assertNotIn('actual',value)
        self.assertTrue(value['details'].endswith(rid+'.json.tex'))
        self.command('stop')
        self.assertIn('未取消',self.op.tick()['operator_error'])
        self.assertEqual(self.transport.stops,0)
    def test_unchanged_projection_does_not_rewrite_page(self):
        self.command('ka');self.op.tick()
        generation=self.store.generation
        self.op.tick();self.assertEqual(generation,self.store.generation)
    def test_error_reset_preserves_successor_control(self):
        self.command('ka');self.op.tick()
        d,p=self.op.read();self.command('stop','successor')
        self.op.report_error(d,p,self.op.load(),'conflict',self.op.load()['selected'],reset=True)
        self.assertEqual(m.parse(self.store.body)['control'],'stop')
        self.assertEqual(m.parse(self.store.body)['prompt'],'successor')
    def test_uncertain_stop_only_queries_and_never_reissues_cancel(self):
        self.command('ka');self.op.tick()
        original=self.transport.call
        calls=[]
        def uncertain(name,args):
            if name=='codex_task_cancel':
                calls.append(args)
                raise ValueError('Workspace is busy; cancellation outcome unknown')
            return original(name,args)
        self.transport.call=uncertain
        self.command('stop')
        with self.assertRaises(ValueError):self.op.tick()
        self.op.tick();self.op.tick()
        self.assertEqual(len(calls),1)
        self.assertIsNotNone(self.op.load()['pending'])


    def result_value(self):
        p=m.parse(self.store.body)
        return json.loads(self.store.body[slice(*p['regions']['result'])])
    def test_notice_reconciles_same_saved_operation(self):
        self.command('ka');saved=m.source_revision(self.store.source())
        self.transport.unknown=True
        self.op.tick()
        self.assertEqual(self.op.receipt(saved)['submission'],'pending_confirmation')
        self.assertIn('notice',self.result_value())
        self.transport.unknown=False
        self.op.tick()
        self.assertEqual(self.op.receipt(saved)['submission'],'accepted')
        self.assertNotIn('notice',self.result_value())
        self.assertTrue(self.op.load()['bindings'][self.op.load()['selected']]['diagnostics'])
        self.assertEqual(self.transport.starts,1)
    def test_rejected_operation_survives_poll_then_new_request_has_no_notice(self):
        self.command('ka');self.op.tick();old=self.op.load()['selected']
        self.command('ka','second');saved=m.source_revision(self.store.source())
        self.op.tick();self.op.tick()
        self.assertEqual(self.op.receipt(saved)['submission'],'not_applied')
        self.assertIn('notice',self.result_value())
        self.transport.rows[old]['status']='done';self.op.tick()
        self.assertIn('notice',self.result_value())
        self.command('ka','third');self.op.tick();new=self.op.load()['selected']
        self.assertNotEqual(old,new)
        self.assertNotIn('notice',self.result_value())
        self.assertEqual(self.op.receipt(saved)['submission'],'not_applied')
    def test_cancelled_stop_reason_only_summarized_as_cancellation(self):
        self.command('ka');self.op.tick();rid=self.op.load()['selected']
        self.command('stop');self.op.tick()
        self.transport.rows[rid].update(error='stop',execution='ended')
        self.transport.rows[rid].pop('cancel_confirmed',None)
        self.op.tick();self.op.tick()
        value=self.result_value()
        self.assertEqual(value['status'],'cancelled')
        self.assertEqual(value['error'],'')
        self.assertTrue(value['cancel_confirmed'])
        self.assertEqual(self.transport.rows[rid]['error'],'stop')
        self.assertEqual(self.transport.stops,1)

    def test_source_scopes_are_distinct(self):
        a=m.Operator(self.tmp.name,self.store.execute,self.transport,source='files/codex-text/operators/alice.md.tex')
        b=m.Operator(self.tmp.name,self.store.execute,self.transport,source='files/codex-text/operators/bob.md.tex')
        self.assertNotEqual(a.journal,b.journal)
        with self.assertRaises(ValueError):
            m.Operator(self.tmp.name,self.store.execute,self.transport,source='../outside.tex')

if __name__=='__main__':unittest.main(verbosity=2)
