"""Real Rust/Loom file boundary plus ordinary Tools save hook, offline transport."""
import hashlib,json,os,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import yohaku_agent as a
import yohaku_codex_text as m
from test_codex_text import Transport
R=Path(__file__).resolve().parents[1]

class RustFileTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.world=Path(self.tmp.name);shutil.copytree(R/'macros',self.world/'macros')
  self.ws=a.Workspace(self.world,R/'bin/loom-linux-x86_64',R/'bin/yohaku_workspace')
  self.ws.execute({'command':'create','directory':'codex-text','name':'OPERATOR.md','body':'[input]\nhello\n[/input]\n[control]\ndraft\n[/control]\n[result]\n{}\n[/result]\n'})
  self.transport=Transport(None)
  self.op=m.Operator(self.world,self.ws.execute,self.transport,self.world/'private-test-journal.json')
 def edit(self,control,prompt=None):
  d,p=self.op.read();changes={'control':control+'\n'}
  if prompt is not None:changes['input']=prompt+'\n'
  self.op.write(d,p,changes)
 def test_real_loom_and_expected_source_conflict(self):
  self.edit('ka rust-1');actual=self.op.tick()
  self.assertEqual(actual['status'],'running')
  d,p=self.op.read();self.assertEqual(p['control'],'draft')
  self.edit('draft','new draft')
  with self.assertRaises(a.ToolError):self.op.write(d,p,{'input':'lost\n'})
  self.transport.rows['rust-1'].update(status='done',output='controlled reply')
  self.op.tick();self.assertEqual(self.op.read()[1]['prompt'],'new draft')
 def test_atomic_snapshot_read_integrity(self):
  import threading
  candidate=R/'bin/yohaku_workspace'
  self.assertTrue(candidate.is_file(),'installed workspace program is required')
  ws=a.Workspace(self.world,R/'bin/loom-linux-x86_64',candidate)
  d,p=self.op.read();path=self.world/m.SOURCE
  versions=[d['text'],d['text'].replace('hello','parallel complete input')]
  stopped=threading.Event()
  def writer():
   import os
   n=0
   while not stopped.is_set():
    temporary=path.with_suffix('.race')
    temporary.write_text(versions[n%2]);os.replace(temporary,path);n+=1
  worker=threading.Thread(target=writer);worker.start()
  accepted=0
  try:
   for _ in range(15):
    try:r=ws.execute({'command':'read','source':m.SOURCE})
    except a.ToolError:continue
    self.assertIn(r['text'],versions)
    expected='parallel complete input' if 'parallel complete input' in r['text'] else 'hello'
    self.assertEqual(m.parse(r['body'])['prompt'],expected);accepted+=1
  finally:stopped.set();worker.join()
  r=ws.execute({'command':'read','source':m.SOURCE})
  self.assertTrue(r['valid'])
  self.assertGreater(accepted,0)
 def test_native_text_callback_uses_matching_installed_program(self):
  def obsolete_native(request):raise AssertionError('old embedded workspace must not handle /3 callback')
  tools=a.Tools(obsolete_native,permissions={'read':True,'write':True,'run':True})
  tools.host_world_root=str(self.world)
  result=tools.codex_text_execute({'command':'read','source':m.SOURCE})
  self.assertTrue(result['valid']);self.assertEqual(m.parse(result['body'])['prompt'],'hello')
  self.assertIsNone(tools.active_name)
 def test_ordinary_ai_save_hook_uses_fixed_service(self):
  tools=a.Tools(self.ws.execute,lambda:{'root':str(self.world),'dirty':False},permissions={'read':True,'write':True,'run':True},native=True)
  self.assertFalse(any(x['name'].startswith('codex_task_') for x in tools.definitions))
  d,p=self.op.read()
  with patch.object(m,'Operator',return_value=self.op):
   reply=tools.call('patch_document',{'source':m.SOURCE,'revision':a.revision(d['text']),'old':'draft','new':'ka ordinary-1','body_only':True})
  self.assertTrue(reply['ok'],reply)
  self.assertEqual(reply['result']['codex_text']['status'],'running')
  self.assertEqual(self.transport.starts,1)
 def test_coordinate_save_hook_runs_once_after_verification(self):
  tools=a.Tools(self.ws.execute,lambda:{'root':str(self.world),'dirty':False},permissions={'read':True,'write':True,'run':True})
  read=tools.call('read_range',{'path':m.SOURCE,'view':'body'})
  d,p=self.op.read();position=d['body'].index('draft');line=d['body'][:position].count('\n')+1
  with patch.object(m,'Operator',return_value=self.op) as factory:
   reply=tools.call('edit_range',{'path':m.SOURCE,'view':'body','revision':read['result']['revision'],'start_line':line,'start_column':1,'end_line':line,'end_column':6,'expected':'draft','text':'ka coordinate-1'})
  self.assertTrue(reply['ok'],reply);self.assertTrue(reply['result']['verified'],reply)
  self.assertEqual(factory.call_count,1);self.assertEqual(self.transport.starts,1)
 def test_permission_and_failed_loom_never_dispatch(self):
  for permissions,native in [({'read':True,'write':True,'run':False},True),({'read':True,'write':True,'run':True},False)]:
   tools=a.Tools(self.ws.execute,lambda:{'root':str(self.world)},permissions=permissions,native=native)
   d,p=self.op.read()
   with patch.object(m,'Operator') as factory:
    reply=tools.call('patch_document',{'source':m.SOURCE,'revision':a.revision(d['text']),'old':p['control'],'new':'draft','body_only':True})
    self.assertTrue(reply['ok'],reply);factory.assert_not_called()
 def test_native_context_and_workspace_rpc_tags_are_valid(self):
  holder={}
  def remote(request):
   expected={'read':'read_document','read_text':'read_text','save':'write_document','create':'create_document'}[request['command']]
   if holder['tools'].active_name != 'patch_document':
    self.assertEqual(holder['tools'].active_name,expected)
   return self.ws.execute(request)
  def context():
   self.assertEqual(holder['tools'].active_name,'context')
   return {'root':str(self.world),'dirty':False}
  tools=a.Tools(remote,context,permissions={'read':True,'write':True,'run':True});holder['tools']=tools
  factory=m.Operator
  def operator(root,execute):return factory(root,execute,self.transport,self.op.journal)
  d,p=self.op.read()
  with patch.object(m,'Operator',side_effect=operator):
   reply=tools.call('patch_document',{'source':m.SOURCE,'revision':a.revision(d['text']),'old':'draft','new':'ka rpc-1','body_only':True})
  self.assertTrue(reply['ok'],reply)
  self.assertEqual(reply['result']['codex_text']['status'],'running',reply)
  self.assertIsNone(tools.active_name)
 def test_dirty_human_draft_defers_hook(self):
  tools=a.Tools(self.ws.execute,lambda:{'root':str(self.world),'dirty':True,'source':m.SOURCE},permissions={'read':True,'write':True,'run':True})
  d,p=self.op.read()
  with patch.object(m,'Operator') as factory:
   reply=tools.call('patch_document',{'source':m.SOURCE,'revision':a.revision(d['text']),'old':'draft','new':'ka dirty-1','body_only':True})
  factory.assert_not_called();self.assertIn('Unsaved',reply['result']['codex_text']['operator_error'])


 def feedback_tools(self,execute=None):
  return a.Tools(execute or self.ws.execute,lambda:{'root':str(self.world),'dirty':False},
                 permissions={'read':True,'write':True,'run':True})
 def test_saved_then_start_busy_has_revision_and_request_without_replay(self):
  tools=self.feedback_tools();d,p=self.op.read()
  original=self.transport.call
  def busy(name,args):
   if name=='codex_task_start':
    original(name,args)
    raise ValueError('Workspace is busy; retry shortly')
   return original(name,args)
  self.transport.call=busy
  with patch.object(m,'Operator',return_value=self.op):
   reply=tools.call('patch_document',{'source':m.SOURCE,'revision':a.revision(d['text']),
       'body_only':True,'old':'draft','new':'ka'})
  self.assertTrue(reply['ok'],reply)
  value=reply['result'];receipt=value['codex_text']
  self.assertTrue(value['saved']);self.assertEqual(value['saved_revision'],receipt['saved_revision'])
  self.assertEqual(receipt['submission'],'pending_confirmation')
  self.assertEqual(receipt['execution_status'],'unknown')
  rid=receipt['request_id'];self.assertIn(rid,self.transport.rows)
  self.assertTrue(receipt['consumed']);self.assertFalse(receipt['replay_allowed'])
  self.op.tick();self.assertEqual(self.transport.starts,1)
  self.assertEqual(self.op.receipt(value['saved_revision'])['submission'],'accepted')
 def test_same_saved_version_accepted_explains_hook_exception(self):
  tools=self.feedback_tools();d,p=self.op.read()
  original=self.op.tick
  def raced():
   original()
   raise ValueError('Workspace is busy; retry shortly')
  with patch.object(m,'Operator',return_value=self.op), patch.object(self.op,'tick',side_effect=raced):
   reply=tools.call('patch_document',{'source':m.SOURCE,'revision':a.revision(d['text']),
       'body_only':True,'old':'draft','new':'ka'})
  value=reply['result']['codex_text']
  self.assertEqual(value['submission'],'accepted')
  self.assertNotIn('operator_error',value)
  self.assertIn('busy',value['diagnostic'])
  self.assertIn('已接受',value['notice'])
  self.assertEqual(value['saved_revision'],reply['result']['saved_revision'])
  self.assertEqual(self.transport.starts,1)
 def test_stop_consumed_between_save_and_readback_is_proven_by_source_revision(self):
  self.edit('ka');self.op.tick();rid=self.op.load()['selected']
  consumed=False
  def execute(q):
   nonlocal consumed
   result=self.ws.execute(q)
   if q['command']=='save' and q.get('text','').find('stop')>=0 and not consumed:
    consumed=True;self.op.tick()
   return result
  tools=self.feedback_tools(execute)
  page=tools.call('read_range',{'path':m.SOURCE,'view':'body'})['result']
  body=page['text'];pos=body.index('draft');line=body[:pos].count('\n')+1
  with patch.object(m,'Operator',return_value=self.op):
   reply=tools.call('edit_range',{'path':m.SOURCE,'view':'body','revision':page['revision'],
      'start_line':line,'start_column':1,'end_line':line,'end_column':6,'expected':'draft','text':'stop'})
  self.assertTrue(reply['ok'],reply);v=reply['result']
  self.assertTrue(v['saved'] and v['verified'])
  self.assertEqual(v['read_back'],'consumed_after_save')
  self.assertEqual(v['codex_text']['request_id'],rid)
  self.assertEqual(v['codex_text']['action'],'stop')
  self.assertEqual(v['codex_text']['execution_status'],'cancelled')
  self.assertEqual(self.transport.stops,1)
  self.assertEqual(self.op.read()[1]['control'],'draft')
 def test_dirty_draft_prevents_dispatch_after_save(self):
  tools=a.Tools(self.ws.execute,lambda:{'root':str(self.world),'dirty':True,'source':m.SOURCE},
                permissions={'read':True,'write':True,'run':True})
  d,p=self.op.read()
  with patch.object(m,'Operator',return_value=self.op):
   reply=tools.call('patch_document',{'source':m.SOURCE,'revision':a.revision(d['text']),
          'body_only':True,'old':'draft','new':'ka'})
  self.assertTrue(reply['ok']);self.assertTrue(reply['result']['saved'])
  self.assertEqual(self.transport.starts,0)
  self.assertIn('Unsaved human draft',reply['result']['codex_text']['operator_error'])

class SimpleRustTests(unittest.TestCase):
 setUp=RustFileTests.setUp
 edit=RustFileTests.edit
 def test_simple_real_file_send_autoreply_stop_resend(self):
  self.edit('ka')
  self.op.tick();rid=self.op.load()['selected']
  self.assertEqual(self.op.read()[1]['control'],'draft')
  self.op.tick();self.assertEqual(self.transport.starts,1)
  self.transport.rows[rid].update(status='done',output='controlled reply, not a model')
  self.op.tick()
  d,p=self.op.read()
  self.assertEqual(p['prompt'],'')
  projection=json.loads(d['body'][slice(*p['regions']['result'])])
  self.assertEqual(projection['reply'],'controlled reply, not a model')
  detail=self.ws.execute({'command':'read','source':projection['details']})
  actual=json.loads(detail['body'])['actual']
  self.assertEqual((projection['status'],projection['reply']),(actual['status'],actual['output']))
  self.assertLess(len(d['body'].splitlines()),35)
  self.edit('ka','wait');self.op.tick()
  self.edit('stop');self.assertTrue(self.op.tick()['cancel_confirmed'])
  self.edit('ka','hello');self.op.tick()
  self.assertEqual(self.transport.starts,3)
 def test_separate_registered_page_ordinary_hook(self):
  self.ws.execute({'command':'create','directory':'codex-text/operators','name':'alice.md','body':self.op.read()[0]['body']})
  op=m.Operator(self.world,self.ws.execute,self.transport,self.world/'alice-journal.json',source='files/codex-text/operators/alice.md.tex')
  tools=a.Tools(self.ws.execute,lambda:{'root':str(self.world),'dirty':False},permissions={'read':True,'write':True,'run':True},native=True)
  d,p=op.read()
  with patch.object(m,'Operator',return_value=op) as factory:
   reply=tools.call('patch_document',{'source':op.source,'revision':a.revision(d['text']),'old':'draft','new':'ka','body_only':True})
  self.assertTrue(reply['ok'],reply)
  self.assertEqual(reply['result']['codex_text']['status'],'running')
  self.assertEqual(factory.call_args.kwargs['source'],op.source)
  self.assertEqual(self.op.read()[1]['control'],'draft')


import test_codex_tasks as host_tests
class ProcessOperatorTests(unittest.TestCase):
 setUp=host_tests.HostTaskTests.setUp
 status=host_tests.HostTaskTests.status
 wait=host_tests.HostTaskTests.wait
 def test_simple_operator_real_rust_and_controlled_processes(self):
  self.ws=a.Workspace(self.world,R/'bin/loom-linux-x86_64',R/'bin/yohaku_workspace')
  from test_codex_text import BODY
  self.ws.execute({'command':'create','directory':'codex-text/operators','name':'OPERATOR-PROCESS.md','body':BODY})
  op=m.Operator(self.world,self.ws.execute,self.control,self.home/'operator-journal.json',source='files/codex-text/operators/OPERATOR-PROCESS.md.tex')
  def edit(control,prompt=None):
   d,p=op.read();changes={'control':control+'\n'}
   if prompt is not None:changes['input']=prompt+'\n'
   op.write(d,p,changes)
  op.tick();self.assertEqual(self.launches,0)
  edit('ka','finish');first=op.tick();rid=op.load()['selected']
  op.tick();self.assertEqual(self.launches,1)
  done=self.wait(first['task_id'])
  op.tick();d,p=op.read()
  self.assertEqual(p['prompt'],'')
  self.assertEqual(json.loads(d['body'][slice(*p['regions']['result'])])['reply'],'controlled reply')
  edit('ka','wait');second=op.tick()
  running=self.wait(second['task_id'],lambda x:x.get('model_phase')=='model_running')
  edit('stop');cancel=op.tick()
  self.assertTrue(cancel['cancel_confirmed'])
  self.assertTrue(cancel['receipt']['native_cleanup_complete'])
  edit('ka','finish');third=op.tick()
  edit('draft','later draft');self.wait(third['task_id']);op.tick()
  self.assertEqual(op.read()[1]['prompt'],'later draft')
  self.assertEqual(self.launches,3)
  print(json.dumps({'evidence':'codex-text/3 controlled process flow','real_model':False,'first':done,'confirmed_running':running,'cancel':cancel,'third':self.status(third['task_id']),'new_draft':op.read()[1]['prompt'],'launches':self.launches},ensure_ascii=False),flush=True)

if __name__=='__main__':unittest.main(verbosity=2)
