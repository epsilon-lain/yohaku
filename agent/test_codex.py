import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import yohaku_codex as c
import yohaku_agent as a
import yohaku_tools as local

PEER=r'''
import json,sys
mode=sys.argv[1]
ready=mode not in ('not-ready','update-required','setup-success','setup-early','setup-failed','setup-timeout','setup-wrong-mode','setup-not-started','setup-still-not-ready')
def out(v):print(json.dumps(v),flush=True)
if mode=='boot-stall':
 out({'yohakuStage':'compile-host'})
 for line in sys.stdin:pass
 sys.exit()
if mode=='stages':out({'yohakuStage':'prepare-auth'})
out({'yohakuBridge':{'version':'1','cwd':'C:\\private\\workspace','outside':'C:\\private\\outside','readProbe':'C:\\private\\read-probe'}})
for line in sys.stdin:
 v=json.loads(line);method=v.get('method')
 if method=='initialize' and mode=='rpc-stall':
  out({'yohakuStage':'native-started'})
  continue
 if mode=='stages':out({'yohakuStage':'native-started'})
 if 'method' not in v:
  assert v['id']==501 and v['result']['success']
  out({'method':'item/completed','params':{'item':{'type':'agentMessage','id':'m1','text':'Created through Yohaku tools'}}})
  out({'method':'turn/completed','params':{'threadId':'thread-1','turn':{'id':'turn-1','status':'completed'}}})
  continue
 if 'id' not in v:continue
 result={}
 if method=='config/read':
  result={'config':{'features':{'shell_tool':False,'apps':False,'plugins':False},'windows':{'sandbox':'elevated'},'hooks':{event:[] for event in ('PreToolUse','PermissionRequest','PostToolUse','PreCompact','PostCompact','SessionStart','SessionEnd','UserPromptSubmit','SubagentStart','SubagentStop','Stop','Interrupt')}}}
  if mode=='inherited':result['config']['mcp_servers']={'unsafe':{'command':'host-writer'}}
  if mode=='engine-unset':result['config'].pop('windows')
  if mode=='engine-unelevated':result['config']['windows']['sandbox']='unelevated'
 elif method=='permissionProfile/list':
  result={'data':[{'id':'yohaku-control','allowed':True}]}
  if mode=='profile-missing':result={'data':[]}
  if mode=='profile-denied':result={'data':[{'id':'yohaku-control','allowed':False}]}
  if mode=='profile-page' and not v['params'].get('cursor'):result={'data':[{'id':':read-only','allowed':True}],'nextCursor':'page2'}
 elif method=='windowsSandbox/readiness':
  assert v['params'] is None
  result={'status':'ready' if ready else ('updateRequired' if mode=='update-required' else 'notConfigured')}
  if mode=='readiness-unknown':result={'status':'unrecognized'}
 elif method=='windowsSandbox/setupStart':
  assert mode.startswith('setup-'), 'normal Connect must never run setup'
  assert v['params']['mode']=='elevated' and v['params']['cwd']=='C:\\private\\workspace'
  result={'started':mode!='setup-not-started'}
  if mode=='setup-early':
   ready=True
   out({'method':'windowsSandbox/setupCompleted','params':{'mode':'elevated','success':True,'error':None}})
 elif method=='command/exec':
  assert ready, 'normal Connect must stop before probing an unconfigured engine'
  assert v['params']['permissionProfile']=='yohaku-control'
  assert 'sandboxPolicy' not in v['params']
  assert 'read-control' in v['params']['command'][-1]
  result={'exitCode':9 if mode=='unrestricted' else 0,'stdout':'YOHAKU_READ_ONLY_OK'}
  if mode=='control-unreadable':result={'exitCode':8,'stdout':''}
  if mode=='probe-timeout':result={'exitCode':124,'stdout':''}
  if mode=='probe-no-result':result={'exitCode':0,'stdout':''}
 elif method=='account/read':
  assert not mode.startswith('setup-'), 'setup must not read accounts or call models'
  result={'account':None if mode=='logged-out' else {'type':'chatgpt'},'requiresOpenaiAuth':True}
 elif method=='model/list':result={'data':[{'id':'existing-local-model','isDefault':True}]}
 elif method=='thread/start':
  assert v['params']['permissions']=='yohaku-control' and v['params']['ephemeral']
  assert 'sandbox' not in v['params']
  assert not any(t['name']=='yohaku_import_document' for t in v['params']['dynamicTools'])
  assert all(t.get('type')=='function' for t in v['params']['dynamicTools'])
  result={'thread':{'id':'thread-1'},'activePermissionProfile':{'id':':read-only' if mode=='thread-profile-wrong' else 'yohaku-control'}}
 elif method=='turn/start':
  assert v['params']['permissions']=='yohaku-control'
  assert 'sandboxPolicy' not in v['params']
  result={'turn':{'id':'turn-1'}}
 if method=='turn/start' and mode=='early':
  out({'method':'item/completed','params':{'item':{'type':'agentMessage','id':'early','text':'Early progress'}}})
 out({'id':v['id'],'result':result})
 if method=='windowsSandbox/setupStart' and mode not in ('setup-early','setup-timeout','setup-not-started'):
  ready=mode not in ('setup-failed','setup-still-not-ready')
  out({'method':'windowsSandbox/setupCompleted','params':{'mode':'unelevated' if mode=='setup-wrong-mode' else 'elevated','success':mode!='setup-failed','error':'secret-token'}})
 if method=='turn/start':
  if mode=='failed':out({'method':'turn/completed','params':{'threadId':'thread-1','turn':{'id':'turn-1','status':'failed'}}})
  else:out({'id':501,'method':'item/tool/call','params':{'threadId':'thread-1','tool':'yohaku_create_document','arguments':{'name':'codex-demo.py','body':'print("inside Yohaku")\n'}}})
'''

class CodexTests(unittest.TestCase):
    def test_chat_dynamic_tools_include_nodes_with_existing_permission_filter(self):
        names={tool['name'] for tool in c.dynamic_definitions(a.Tools(lambda request: None))}
        self.assertTrue({'yohaku_list_entry_nodes','yohaku_find_nodes','yohaku_get_node','yohaku_walk_nodes','yohaku_rebuild_node_index'} <= names)
        self.assertNotIn('yohaku_import_document',names)
        restricted=c.dynamic_definitions(a.Tools(lambda request: None,permissions={'read':False}))
        self.assertNotIn('yohaku_get_node',{tool['name'] for tool in restricted})

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.peer=self.base/'peer.py';self.peer.write_text(PEER)
    def tearDown(self):self.temp.cleanup()
    def child(self,mode='ok'):
        return subprocess.Popen([sys.executable,'-u',str(self.peer),mode],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    def test_handshake_verifies_restrictions_account_and_existing_model_without_inference(self):
        peer=c.Connection(self.child())
        try:self.assertEqual(peer.initialize(),{'model':'existing-local-model','models':['existing-local-model'],'auth_type':'chatgpt'})
        finally:peer.close()
        self.assertIsNotNone(peer.child.returncode)
    def test_missing_auth_unrestricted_execution_and_inherited_host_tools_fail_closed(self):
        for mode in ('logged-out','unrestricted','inherited'):
            peer=c.Connection(self.child(mode))
            try:
                with self.assertRaises(c.CodexError):peer.initialize()
            finally:peer.close()
    def test_profile_catalog_paginates_without_selecting_broad_builtin_profiles(self):
        peer=c.Connection(self.child('profile-page'))
        try:self.assertEqual(peer.initialize()['model'],'existing-local-model')
        finally:peer.close()

    def test_missing_or_disallowed_private_profile_blocks_before_model_calls(self):
        for mode in ('profile-missing','profile-denied'):
            peer=c.Connection(self.child(mode))
            try:
                with self.assertRaisesRegex(c.CodexError,'permission profile'):peer.initialize()
            finally:peer.close()

    def test_probe_cannot_succeed_when_control_read_or_execution_fails(self):
        for mode,reason in (('control-unreadable','could not read'),('probe-timeout','timed out'),('probe-no-result','verified result')):
            peer=c.Connection(self.child(mode))
            try:
                with self.assertRaisesRegex(c.CodexError,reason):peer.initialize()
            finally:peer.close()

    def test_profile_catalog_rejects_invalid_or_repeated_pagination(self):
        class Catalog:
            info={'cwd':'C:\\private\\workspace'}
            def __init__(self,response):self.response=response;self.calls=0
            def request(self,*args):self.calls+=1;return self.response
        for response in ({'data':None},{'data':[],'nextCursor':'repeat'},
                         {'data':[],'nextCursor':{}},{'data':[{'id':'yohaku-control','allowed':'true'}]}):
            peer=Catalog(response)
            with self.assertRaises(c.CodexError):c.verify_profile_catalog(peer)
            self.assertLessEqual(peer.calls,2)

    def test_thread_must_confirm_private_profile_before_any_model_turn(self):
        tools=a.Tools(lambda _:None,permissions={'read':True})
        with patch.object(c,'launch',side_effect=lambda _:self.child('thread-profile-wrong')):
            with self.assertRaisesRegex(c.CodexError,'thread did not confirm'):
                c.run({'config':{'codex_entry':'test'},'prompt':'test'},tools,lambda _:None)

    def test_unconfigured_engine_never_runs_setup_or_probe_during_normal_connect(self):
        for mode in ('not-ready','update-required','readiness-unknown','engine-unset','engine-unelevated'):
            peer=c.Connection(self.child(mode))
            try:
                with self.assertRaises(c.CodexError):peer.initialize()
            finally:peer.close()

    def test_explicit_setup_waits_for_completion_and_checks_boundaries_without_models(self):
        for mode in ('setup-success','setup-early','ok'):
            peer=c.Connection(self.child(mode))
            try:self.assertIn('no model task',peer.setup_windows()['text'])
            finally:peer.close()

    def test_setup_failure_mismatched_mode_and_false_start_cannot_pass(self):
        for mode in ('setup-failed','setup-wrong-mode','setup-not-started','setup-still-not-ready'):
            peer=c.Connection(self.child(mode))
            try:
                with self.assertRaises(c.CodexError) as error:peer.setup_windows()
                self.assertNotIn('secret-token',str(error.exception))
            finally:peer.close()

    def test_setup_has_a_fixed_completion_deadline_and_cleans_up(self):
        peer=c.Connection(self.child('setup-timeout'))
        try:
            with self.assertRaisesRegex(c.CodexError,'timeout.*explicit Windows sandbox setup'):
                peer.setup_windows(timeout=.03)
        finally:peer.close()
        self.assertIsNotNone(peer.child.returncode)

    def test_empty_serialized_hook_defaults_are_not_executable_hooks(self):
        config={'features':{'shell_tool':False,'apps':False,'plugins':False},'windows':{'sandbox':'elevated'}}
        for hooks in (None,{},dict.fromkeys(c.HOOK_EVENTS,[]),{'state':{}}):
            with self.subTest(hooks=hooks):
                c.verify_config(dict(config,hooks=hooks))

    def test_real_hook_handlers_still_block_connection(self):
        config={'features':{'shell_tool':False,'apps':False,'plugins':False},'windows':{'sandbox':'elevated'}}
        for event in c.HOOK_EVENTS:
            for handler in ({'type':'command','command':'host-writer'},
                            {'type':'mcp_tool','server':'host','tool':'writer'}):
                with self.subTest(event=event,handler=handler['type']):
                    with self.assertRaisesRegex(c.CodexError,'configured '+event+' hooks'):
                        c.verify_config(dict(config,hooks={event:[{'matcher':None,'hooks':[handler]}]}))

    def test_unknown_or_malformed_hook_shapes_fail_closed_without_echoing_contents(self):
        config={'features':{'shell_tool':False,'apps':False,'plugins':False},'windows':{'sandbox':'elevated'}}
        for hooks in ([],False,'private-value',{'Stop':None},{'Stop':{}},
                      {'future-private-key':[]},{'state':{'private-value':{'enabled':True}}}):
            with self.subTest(hooks=hooks):
                with self.assertRaises(c.CodexError) as error:
                    c.verify_config(dict(config,hooks=hooks))
                self.assertNotIn('private',str(error.exception))

    def test_real_world_mutation_uses_rust_and_loom_not_native_windows_writes(self):
        root=self.base/'world';root.mkdir()
        workspace=a.Workspace(root,local.PACKAGE/'bin/loom-linux-x86_64')
        workspace.execute({'command':'list'})
        tools=a.Tools(workspace.execute,permissions={'read':True,'write':True,'run':False})
        events=[]
        with patch.object(c,'launch',side_effect=lambda _:self.child()):
            result=c.run({'config':{'codex_entry':'test'},'prompt':'Create a Python document','context':{'root':str(root)},'history':[]},tools,events.append)
        self.assertEqual(result['tool_calls'],1)
        listing=workspace.execute({'command':'list'})
        self.assertIn('codex-demo.py',json.dumps(listing))
        outputs=list((root/'files').rglob('codex-demo.py'))
        self.assertEqual(len(outputs),1);self.assertEqual(outputs[0].read_text(),'print("inside Yohaku")\n')
        self.assertTrue(any(e['event']=='tool_result' and e['result']['ok'] for e in events))
    def test_early_notifications_are_preserved_until_turn_start_response(self):
        peer=c.Connection(self.child('early'))
        try:
            peer.initialize()
            result=peer.request('turn/start',{'permissions':'yohaku-control'})
            self.assertEqual(result['turn']['id'],'turn-1')
            early=peer.receive()
            self.assertEqual(early['params']['item']['text'],'Early progress')
        finally:peer.close()
    def test_failed_turn_is_never_reported_as_completed(self):
        tools=a.Tools(lambda _:None,permissions={'read':True})
        with patch.object(c,'launch',side_effect=lambda _:self.child('failed')):
            with self.assertRaisesRegex(c.CodexError,'failed'):c.run({'config':{'codex_entry':'test'},'prompt':'test'},tools,lambda _:None)
    def test_native_binary_resolution_does_not_execute_npm_shim(self):
        npm=self.base/'npm';npm.mkdir();shim=npm/'codex';shim.write_text('do not execute')
        native=npm/'node_modules/@openai/codex/vendor/x86_64-pc-windows-msvc/codex/codex.exe';native.parent.mkdir(parents=True);native.write_bytes(b'MZfixture')
        with patch.object(c.apps,'is_windows_path',return_value=True):self.assertEqual(c.native_executable(str(shim)),native)
    def test_malformed_protocol_is_bounded_and_connection_is_cleaned(self):
        child=subprocess.Popen([sys.executable,'-c','print("not json")'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        peer=c.Connection(child)
        try:
            with self.assertRaises(c.CodexError):peer.receive()
        finally:peer.close()

    def test_bridge_stages_do_not_replace_handshake_or_rpc_responses(self):
        peer=c.Connection(self.child('stages'))
        try:
            self.assertEqual(peer.initialize()['model'],'existing-local-model')
            self.assertEqual(peer.bridge_stage,'native-started')
        finally:peer.close()

    def test_startup_timeout_names_last_stage_and_child_is_cleaned(self):
        peer=c.Connection(self.child('boot-stall'))
        try:
            with self.assertRaisesRegex(c.CodexError,'Windows bridge startup.*compile-host'):peer.receive(timeout=.1)
        finally:peer.close()
        self.assertIsNotNone(peer.child.returncode)

    def test_rpc_timeout_names_method_and_does_not_confuse_progress_with_reply(self):
        peer=c.Connection(self.child('rpc-stall'))
        try:
            peer.receive()
            with self.assertRaisesRegex(c.CodexError,'RPC initialize.*native-started'):peer.request('initialize',{},timeout=.1)
        finally:peer.close()

    def test_progress_flood_does_not_extend_deadline_or_echo_untrusted_text(self):
        import queue,time
        peer=c.Connection.__new__(c.Connection)
        peer.phase='Windows bridge startup';peer.bridge_stage='not reported'
        class Progress:
            def get(self,timeout):return {'yohakuStage':'compile-host'}
        peer.queue=Progress();start=time.monotonic()
        with self.assertRaisesRegex(c.CodexError,'timeout.*compile-host'):peer._receive(.02)
        self.assertLess(time.monotonic()-start,1)
        peer.queue=queue.Queue();peer.queue.put({'yohakuStage':'secret-token-must-not-be-echoed'})
        with self.assertRaises(c.CodexError) as error:peer._receive(.1)
        self.assertNotIn('secret-token',str(error.exception))

if __name__=='__main__':unittest.main()
