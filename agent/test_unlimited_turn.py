"""Offline whole-turn policy + actual wire startup tests. No real model connection."""
import os,sys,json,signal,socket,subprocess,tempfile,time,types,unittest
from pathlib import Path
from unittest.mock import patch
import yohaku_agent as a
import yohaku_codex as c
import yohaku_codex_diagnostics as d
import yohaku_provider_transport as t
from test_ai_limits import connection_fixture,fixture_tools
PEER=r'''
import json,sys
mode=sys.argv[1]
def emit(v):print(json.dumps(v),flush=True)
for line in sys.stdin:
 v=json.loads(line);m=v.get('method')
 if m=='thread/start':emit({'id':v['id'],'result':{'thread':{'id':'offline-thread'},'activePermissionProfile':{'id':'yohaku-control'}}})
 elif m=='config/read':emit({'id':v['id'],'result':{'config':{'features':{'shell_tool':False,'apps':False,'plugins':False}}}})
 elif m=='turn/start':
  emit({'id':v['id'],'result':{'turn':{'id':'offline-turn'}}})
  if mode=='tool':emit({'id':9,'method':'item/tool/call','params':{'threadId':'offline-thread','turnId':'offline-turn','tool':'yohaku_read_text','arguments':{'path':'files/offline'}}})
'''
def worker(mode,entry):
 sys.path.insert(0,str(Path(entry).resolve().parent))
 import yohaku_agent as agent,yohaku_codex as codex
 def connect(address,diagnostic=None):
  child=subprocess.Popen([sys.executable,'-B','-c',PEER,mode],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  child.yohaku_linux=True;connection=codex.Connection(child,diagnostic);connection.info={'cwd':'offline-control'}
  return connection,{'model':'offline-model','models':['offline-model']}
 codex.connect=connect
 agent.Tools.bootstrap=lambda self,context:context
 sys.argv=[str(entry),'wire'];agent.main()

class UnlimitedTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.patch=patch.object(d,'DIRECTORY',self.root/'diagnostics');self.patch.start();self.addCleanup(self.patch.stop)
  self.events=[];self.calls=[]
 def evidence(self,name,value):
  folder=os.environ.get('YOHAKU_UNLIMITED_EVIDENCE')
  if folder:
   p=Path(folder);p.mkdir(parents=True,exist_ok=True);(p/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2))
 def test_default_unlimited_keeps_real_protocol_tool_progress_past_900(self):
  real=time.monotonic;offset=[0]
  def emit(e):
   self.events.append(e)
   if e.get('event')=='status' and str(e.get('text','')).startswith('Codex connected'):offset[0]=901
   if e.get('event')=='tool_result':offset[0]+=1000
  tools=fixture_tools(lambda *args:(self.calls.append(args) or {'ok':True}))
  with patch.object(c.time,'monotonic',side_effect=lambda:real()+offset[0]),patch.object(c,'connect',side_effect=connection_fixture(3)):
   result=c.run({'config':{},'context':{},'prompt':'offline >900 clock'},tools,emit)
  self.assertEqual(result['tool_calls'],3);self.assertGreater(offset[0],900)
  policy=next(e for e in self.events if e['event']=='turn_settings');self.assertEqual(policy['mode'],'unlimited');self.assertIsNone(policy['seconds'])
  self.evidence('unlimited-clock',dict(simulated_elapsed=offset[0],tools=len(self.calls),policy=policy,events=self.events))
 def test_unlimited_quiet_poll_after_900_is_not_a_total_deadline(self):
  clock=[0];timeouts=[]
  peer=types.SimpleNamespace(child=types.SimpleNamespace(poll=lambda:None))
  def receive(timeout):
   timeouts.append(timeout);clock[0]+=901
   if len(timeouts)<3:raise c.CodexTimeout('quiet fixture')
   return {'method':'completed'}
  peer.receive=receive
  with patch.object(c.time,'monotonic',side_effect=lambda:clock[0]):
   result=c.wait_for_turn_event(peer,None,self.events.append,None,0,'worker default: unlimited')
  self.assertEqual(timeouts,[60,60,60]);self.assertEqual(clock[0],2703)
  self.evidence('quiet-poll',dict(simulated_elapsed=clock[0],poll_timeouts=timeouts,events=self.events))
 def test_explicit_finite_budget_still_expires_with_activity(self):
  real=time.monotonic;offset=[0]
  def emit(e):
   self.events.append(e)
   if e.get('event')=='status' and str(e.get('text','')).startswith('Codex connected'):offset[0]=8
  with patch.object(c.time,'monotonic',side_effect=lambda:real()+offset[0]),patch.object(c,'connect',side_effect=connection_fixture(1)):
   with self.assertRaisesRegex(c.CodexError,'exceeded 7 seconds'):
    c.run({'config':{'turn_timeout':7},'context':{},'prompt':'offline finite'},fixture_tools(lambda *x:self.calls.append(x)),emit)
  self.assertEqual(self.calls,[])
  self.evidence('finite-clock',dict(simulated_elapsed=8,events=self.events))
 def test_none_never_arms_relay_timer_but_finite_and_cancel_remain(self):
  recovery=t.Recovery()
  with patch.object(t.threading,'Timer') as timer:
   recovery.set_budget(None);timer.assert_not_called();self.assertIsNone(recovery.deadline)
   recovery.set_budget(2);self.assertEqual(timer.call_args.args[0],2)
   recovery.finish_budget();timer.return_value.cancel.assert_called()
  recovery.cancel()
  with self.assertRaises(t.RecoveryCancelled):recovery.run(lambda:self.fail('Stopped request restarted'))
 def test_fresh_native_limits_override_cached_old_host_900_and_report_sources(self):
  project=self.root/'project';world=self.root/'world';(project/'config').mkdir(parents=True);(world/'memory').mkdir(parents=True)
  host=project/'config/ai.json';settings=world/'memory/socius.json';host.write_text('{}');settings.write_text('{}')
  initial={'config':{'turn_timeout':900,'model':'preserved','timeout':120},'context':{'root':str(world)}}
  resolved=t.resolve_turn_config(initial,project);self.assertIsNone(t.turn_seconds(resolved));self.assertEqual(resolved['model'],'preserved');self.assertEqual(resolved['timeout'],120)
  host.write_text('{"turn_timeout":3}');resolved=t.resolve_turn_config(initial,project)
  self.assertEqual(t.turn_policy(resolved)['seconds'],3);self.assertIn(str(host),t.turn_policy(resolved)['source'])
  settings.write_text('{"chat":{"limits":{"turn_timeout":null}}}');resolved=t.resolve_turn_config(initial,project);self.assertIsNone(t.turn_seconds(resolved));self.assertIn('#/chat/limits/turn_timeout',t.turn_policy(resolved)['source'])
  self.evidence('configuration-sources',t.turn_policy(resolved))
 def wire_stop(self,mode,hard=False):
  entry=Path(os.environ.get('YOHAKU_WIRE_ENTRY',a.__file__)).resolve();world=Path(os.environ.get('YOHAKU_NATIVE_WORLD',self.root/'world'));world.mkdir(exist_ok=True)
  env={**os.environ,'HOME':str(self.root),'PYTHONDONTWRITEBYTECODE':'1'}
  process=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--worker',mode,str(entry)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
  tool=None
  try:
   initial={'config':{'protocol':'codex-local','model':'offline-model','turn_timeout':900},'context':{'root':str(world)},'prompt':'offline stopped fixture'}
   # For standalone temp worlds without a project config, use explicit null.
   if not os.environ.get('YOHAKU_NATIVE_WORLD'):initial['config']['turn_timeout']=None
   process.stdin.write(json.dumps(initial)+'\n');process.stdin.flush();events=[]
   while True:
    line=process.stdout.readline();self.assertTrue(line,'wire exited before expected stage');event=json.loads(line);events.append(event)
    if mode=='wait' and event.get('event')=='status' and str(event.get('text','')).startswith('Codex connected'):break
    if mode=='tool' and event.get('event')=='request':break
   if mode=='tool':
    marker=self.root/'tool-saved';tool=subprocess.Popen([sys.executable,'-B','-c','import pathlib,sys,time;pathlib.Path(sys.argv[1]).write_text("saved");time.sleep(30)',str(marker)])
    end=time.monotonic()+2
    while not marker.exists() and time.monotonic()<end:time.sleep(.01)
    self.assertTrue(marker.exists())
   started=time.monotonic();process.send_signal(signal.SIGKILL if hard else signal.SIGTERM);out,err=process.communicate(timeout=4);events.extend(json.loads(x) for x in out.splitlines())
   self.assertLess(time.monotonic()-started,4);self.assertEqual(err,'');self.assertEqual(process.returncode,-9 if hard else 0)
   if not hard:
    self.assertEqual(events[-1]['event'],'error');self.assertIn('stopped',events[-1]['text'].lower())
   self.assertFalse(any(e.get('event')=='done' for e in events))
   policy=next(e for e in events if e.get('event')=='turn_settings');self.assertEqual(policy['mode'],'unlimited');self.assertEqual(Path(policy['worker_path']).resolve(),entry.parent/'yohaku_codex.py')
   if tool:self.assertIsNone(tool.poll());self.assertEqual(marker.read_text(),'saved')
   self.evidence('actual-wire-stop-'+('daily-kill-' if hard else '')+mode,dict(entry=str(entry),worker_exit_code=process.returncode,tool_survived_model_stop=tool is not None,events=events))
  finally:
   if process.poll() is None:process.kill();process.communicate()
   if tool and tool.poll() is None:tool.terminate();tool.wait()
 def test_stop_during_unlimited_response_wait(self):self.wire_stop('wait')
 def test_stop_during_dispatched_tool_preserves_independent_tool(self):self.wire_stop('tool')
 def test_current_daily_kill_stop_during_wait(self):self.wire_stop('wait',hard=True)
 def test_current_daily_kill_stop_during_tool(self):self.wire_stop('tool',hard=True)

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--worker':worker(sys.argv[2],sys.argv[3])
 else:unittest.main()
