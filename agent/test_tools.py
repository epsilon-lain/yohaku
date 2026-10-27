import copy,json,os,socket,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import yohaku_tools as t

class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='yohaku-tool-test-');self.root=Path(self.temp.name)/'world'
        (self.root/'.yohaku').mkdir(parents=True);(self.root/'files').mkdir();(self.root/'memory').mkdir()
        (self.root/'.yohaku/files.json').write_text(json.dumps({'format':'yohaku-workspace/0.1'}))
        self.entry={'id':'python','name':'Python','program':'/usr/bin/python3','args':['-c','print("ok")'],'wayland':False}
    def tearDown(self):self.temp.cleanup()
    def test_mounts_environment_and_arguments_do_not_expose_host_data(self):
        argv=t.command(self.root,self.entry)
        self.assertIn('--unshare-all',argv);self.assertIn('--disable-userns',argv);self.assertIn('--new-session',argv)
        self.assertNotIn('--share-net',argv)
        mounts=[argv[i+1] for i,a in enumerate(argv) if a in ('--bind','--ro-bind')]
        self.assertEqual([p for p in mounts if p.startswith(str(self.root))],[str(self.root),str(self.root/'.yohaku')])
        self.assertNotIn('/root',mounts);self.assertNotIn('/mnt/c',mounts)
        env={argv[i+1]:argv[i+2] for i,a in enumerate(argv) if a=='--setenv'}
        self.assertNotIn('DISPLAY',env);self.assertNotIn('DBUS_SESSION_BUS_ADDRESS',env);self.assertNotIn('WSL_INTEROP',env)
        self.assertEqual(env['HOME'],'/world/tools/state/python');self.assertIn('--clearenv',argv)
        self.assertFalse((self.root/'tools').exists(),'Planning must not create host-side directories')
    def test_socket_only_maps_one_live_socket(self):
        path=Path(self.temp.name)/'yohaku-socket';path.touch()
        entry=copy.deepcopy(self.entry);entry['wayland']=True
        # Exercise planning in a runtime that disallows AF_UNIX creation.
        with patch.object(t.stat,'S_ISSOCK',return_value=True):
            argv=t.command(self.root,entry,str(path));i=argv.index(str(path))
            self.assertEqual(argv[i-1],'--ro-bind');self.assertEqual(argv[i+1],'/run/yohaku/wayland-0')
        with self.assertRaises(t.ToolError):t.command(self.root,entry,str(path))
        with self.assertRaises(t.ToolError):t.command(self.root,entry,None)
    def test_arguments_are_not_shell_interpolated_or_bwrap_options(self):
        self.entry['args']=['--bind','/root','/host','$(touch /outside)']
        argv=t.command(self.root,self.entry);end=argv.index('--')
        self.assertEqual(argv[end+2:],self.entry['args'])
    def test_registry_rejects_policy_overrides_and_world_escape(self):
        invalid=copy.deepcopy(self.entry);invalid['network']=True
        with self.assertRaises(t.ToolError):t.validate({'format':'yohaku-tools/1','tools':[invalid]})
        for name in ['../../outside','/root/file']:
            with self.assertRaises(t.ToolError):t.inside(self.root,name)
        (self.root/'escape').symlink_to('/root')
        with self.assertRaises(t.ToolError):t.inside(self.root,'escape/file')
    def test_pinned_mounts_use_fds_and_reject_last_moment_symlink(self):
        argv=t.command(self.root,self.entry)
        with t.PinnedMounts(argv,self.root) as pinned:
            self.assertIn('--bind-fd',pinned.argv);self.assertIn('--ro-bind-fd',pinned.argv)
            self.assertEqual(len(pinned.fds),2)
        path=self.root/'mutable';path.mkdir();args=['bwrap','--ro-bind',str(path),'/world/mutable']
        path.rmdir();path.symlink_to('/root')
        with self.assertRaises(t.ToolError):t.PinnedMounts(args,self.root)
    def test_failed_preflight_never_starts_program(self):
        (self.root/'memory/tools.json').write_text(json.dumps({'format':'yohaku-tools/1','tools':[self.entry]}))
        with patch.object(t,'check',side_effect=t.ToolError('namespace blocked')),patch.object(t.subprocess,'Popen') as popen:
            with self.assertRaises(t.ToolError):t.run(self.root,'python',None)
            popen.assert_not_called()
    def test_nested_host_mount_is_rejected(self):
        (self.root/'mounted').mkdir()
        original=os.path.ismount
        with patch.object(t.os.path,'ismount',side_effect=lambda p:Path(p)==self.root/'mounted' or original(p)):
            with self.assertRaises(t.ToolError):t.command(self.root,self.entry)
    def test_declared_parameters_validate_and_remain_single_arguments(self):
        entry=copy.deepcopy(self.entry)
        entry['parameters']=[{'name':'input','type':'world_file','default':'files/default.txt'}]
        (self.root/'files/default.txt').write_text('default')
        special='files/中文 space;$(echo bad).txt'
        (self.root/special).write_text('safe')
        argv=t.command(self.root,entry,parameters={'input':special})
        self.assertEqual(argv[-1],'/world/'+special)
        self.assertEqual(t.parameter_args(self.root,entry),['/world/files/default.txt'])
        for values in [[], {'unknown':'x'}, {'input':False}, {'input':'/etc/passwd'}, {'input':'../outside'}, {'input':'files/missing'}, {'input':'files'}, {'input':'files/\x00'}]:
            with self.assertRaises(t.ToolError):t.command(self.root,entry,parameters=values)
        (self.root/'files/link').symlink_to(self.root/'files/default.txt')
        with self.assertRaises(t.ToolError):t.command(self.root,entry,parameters={'input':'files/link'})
        with self.assertRaises(t.ToolError):t.command(self.root,self.entry,parameters={'input':special})

    def test_native_api_forwards_parameters_and_rejects_wrong_container(self):
        import yohaku_agent as agent
        calls=[]
        api=agent.Tools(lambda req: calls.append(req) or {'state':'finished'},native=True,permissions={'read':True,'write':True,'delete':True,'import':True,'run':True})
        response=api.call('run_tool',{'id':'python','parameters':{'input':'files/a'}})
        self.assertTrue(response['ok'],repr(response))
        self.assertEqual(calls[-1]['parameters'],{'input':'files/a'})
        self.assertFalse(api.call('run_tool',{'id':'python','parameters':[]})['ok'])

    def test_real_kernel_boundary(self):
        try:result=t.check(self.root)
        except t.ToolError as e:self.skipTest('Kernel sandbox not available here: '+str(e))
        self.assertTrue(result['ok'])

class OnboardingTests(unittest.TestCase):
    def setUp(self):
        import yohaku_agent as agent
        self.agent=agent
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'world';self.root.mkdir()
        (self.root/'files/build').mkdir(parents=True)
        self.registry={'format':'yohaku-tools/1','tools':[{'id':'old','name':'Old','program':'/usr/bin/true','args':[],'wayland':False}]}
        self.text=json.dumps(self.registry);self.requests=[];self.conflict=False
        self.tools=agent.Tools(self.execute)
        self.entry={'id':'new','name':'New','args':[],'wayland':False}
    def execute(self, request):
        import yohaku_apps as apps
        self.requests.append(request)
        if request['command']=='tool_inspect':return apps.inspect_tool(request['path'],self.root)
        if request['command']=='read_text':return {'text':self.text,'revision':self.agent.revision(self.text)}
        if request['command']=='write_text':
            if self.conflict:self.text+='\n'
            if request.get('expected')!=self.text:raise self.agent.ToolError('File changed since reading')
            self.text=request['text'];return {'saved':True}
        raise AssertionError(request)
    def test_register_persists_rediscover_and_duplicate_does_not_overwrite(self):
        result=self.tools.call('register_tool',{'path':'/usr/bin/true','entry':self.entry})
        self.assertTrue(result['ok'],result);self.assertTrue(result['result']['registered'])
        fresh=self.agent.Tools(self.execute)
        self.assertEqual([entry['id'] for entry in fresh.call('list_tools',{})['result']['tools']],['old','new'])
        before=self.text
        self.assertFalse(fresh.call('register_tool',{'path':'/usr/bin/true','entry':self.entry})['ok'])
        self.assertEqual(before,self.text)
        self.assertFalse(any(request['command']=='tool_run' for request in self.requests))
    def test_registration_uses_real_rust_write_contract(self):
        import yohaku_apps as apps
        (self.root/'memory').mkdir(exist_ok=True)
        (self.root/'memory/tools.json').write_text(self.text)
        workspace=self.agent.Workspace(self.root,self.agent.ROOT/'bin/loom-linux-x86_64')
        def execute(request):
            if request['command']=='tool_inspect':return apps.inspect_tool(request['path'],self.root)
            return workspace.execute(request)
        api=self.agent.Tools(execute)
        result=api.call('register_tool',{'path':'/usr/bin/true','entry':self.entry})
        self.assertTrue(result['ok'],result)
        fresh=self.agent.Tools(execute).call('list_tools',{})
        self.assertTrue(fresh['ok'],fresh)
        self.assertEqual([entry['id'] for entry in fresh['result']['tools']],['old','new'])
    def test_registration_conflict_keeps_concurrent_change(self):
        self.conflict=True;before=self.text
        result=self.tools.call('register_tool',{'path':'/usr/bin/true','entry':self.entry})
        self.assertFalse(result['ok']);self.assertEqual(self.text,before+'\n')
    def test_invalid_entry_permission_and_program_override_fail(self):
        for changes in [{'program':'/usr/bin/false'},{'args':'not-argv'},{'parameters':[{'name':'out','type':'host_file','default':'files/x'}]}]:
            entry=dict(self.entry,**changes)
            result=self.tools.call('register_tool',{'path':'/usr/bin/true','entry':entry})
            self.assertFalse(result['ok'],result)
        restricted=self.agent.Tools(self.execute,permissions={'write':False})
        self.assertFalse(restricted.call('register_tool',{'path':'/usr/bin/true','entry':self.entry})['ok'])
        external=self.agent.Tools(self.execute,native=False)
        self.assertNotIn('register_tool',{item['name'] for item in external.definitions})
        self.assertEqual(json.loads(self.text),self.registry)
    def test_explicit_inspection_rejects_search_escape_symlink_and_nonexecutables(self):
        import yohaku_apps as apps
        self.assertFalse(apps.inspect_tool('/usr/bin/true',self.root)['executed'])
        (self.root/'files/plain').write_text('not executable')
        (self.root/'files/link').symlink_to('/usr/bin/true')
        for path in ['gcc','/etc/passwd','/world/../outside','/world/files/plain','/world/files/link']:
            with self.assertRaises((t.ToolError,OSError)):apps.inspect_tool(path,self.root)
    def test_output_paths_and_independent_argv_keep_boundary(self):
        entry=dict(self.entry,program='/usr/bin/true',parameters=[{'name':'output','type':'world_output','default':'files/build/result'}])
        special='files/build/中文 space;$(touch bad)'
        self.assertEqual(t.parameter_args(self.root,entry,{'output':special}),['/world/'+special])
        for path in ['../outside','/etc/result','files/missing/result','files/build']:
            with self.assertRaises(t.ToolError):t.parameter_args(self.root,entry,{'output':path})
        (self.root/'files/build/link').symlink_to('/tmp')
        with self.assertRaises(t.ToolError):t.parameter_args(self.root,entry,{'output':'files/build/link/result'})

if __name__=='__main__':unittest.main()
