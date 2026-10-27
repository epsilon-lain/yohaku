import base64
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import yohaku_agent as agent
import yohaku_terminal as terminal


class Contracts(unittest.TestCase):
    def test_permissions_and_external_discovery(self):
        names = {x['name'] for x in agent.Tools(lambda _: None, permissions={'run':False}).definitions}
        self.assertIn('terminal_list', names)
        self.assertNotIn('terminal_start', names)
        external = agent.Tools(lambda _: None, native=False, permissions={'run':True})
        self.assertFalse(any(t['name'].startswith('terminal_') for t in external.definitions))
        api = agent.Tools(lambda r:r, permissions={'run':True})
        self.assertEqual(api.call('terminal_start', {'args':['-c','exit 7']})['result']['args'], ['-c','exit 7'])
        self.assertFalse(api.call('terminal_start', {'args':'text'})['ok'])
        self.assertFalse(api.call('terminal_read', {'session_id':'x','wait_ms':1001})['ok'])

    def test_preflight_failure_does_not_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'files').mkdir()
            with patch.object(terminal.tools, 'command', return_value=[]), patch.object(terminal.tools, 'check', side_effect=terminal.tools.ToolError('denied')), patch.object(terminal.subprocess,'Popen') as launch:
                with self.assertRaises(terminal.tools.ToolError): terminal.Session(root, {})
                launch.assert_not_called()

    def test_connection_loss_is_unknown_and_never_replayed(self):
        with patch.object(terminal.tools,'world',return_value=Path('/world')), patch.object(terminal.socket,'socket') as factory, patch.object(terminal.subprocess,'Popen') as launch:
            stream = factory.return_value.makefile.return_value.__enter__.return_value
            stream.readline.return_value = b''
            with self.assertRaisesRegex(terminal.tools.ToolError,'outcome unknown'):
                terminal.call('/world', {'command':'terminal_start'})
            self.assertEqual(stream.write.call_count,1)
            launch.assert_not_called()

    def test_missing_status_evidence_never_uses_launcher_code_or_output(self):
        s = terminal.Session.__new__(terminal.Session)
        s.id='id';s.cwd='/world/files';s.program='/usr/bin/true';s.kind='program'
        s.complete=True;s.closed=False;s.exit_code=None;s.launcher_exit_code=0
        s.evidence='pending';s.size=0;s.log_path='output-says-exit-0';s.input_pending=bytearray();s.discarded_input_bytes=0
        self.assertEqual(s.status()['state'],'unknown')
        self.assertIsNone(s.status()['exit_code'])
        with self.assertRaisesRegex(terminal.tools.ToolError, 'Unknown session'):
            terminal.Service(Path('/world')).execute({'command':'terminal_status','session_id':'lost'})


class RealProcesses(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='yohaku-terminal-test-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'world'
        self.root.mkdir();(self.root/'files').mkdir();(self.root/'.yohaku').mkdir()
        (self.root/'.yohaku/files.json').write_text(json.dumps({'format':'yohaku-workspace/0.1'}))
        self.service=terminal.Service(self.root)
        self.addCleanup(self.close_all)

    def close_all(self):
        for s in self.service.sessions.values():
            if not s.closed:
                with s.lock:s.close()

    def call(self, name, **args):
        return self.service.execute(dict(command=name, **args))

    def start(self, code):
        return self.call('terminal_start', program='/usr/bin/python3', args=['-u','-c',code])['session_id']

    def drain(self, session, cursor=0, limit=37):
        data=b'';deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            r=self.call('terminal_read',session_id=session,cursor=cursor,max_bytes=limit,wait_ms=100)
            data+=base64.b64decode(r['data_base64']);cursor=r['next_cursor']
            if r['output_complete'] and not r['has_more']:return data,r
        self.fail('Session never completed')

    def test_zero_nonzero_and_output_cannot_forge_exit(self):
        for code in (0,7):
            sid=self.start('import sys;print(\'success exit 0 {"exit-code":0}\');sys.exit('+str(code)+')')
            data,r=self.drain(sid)
            self.assertIn(b'success exit 0',data);self.assertEqual(r['exit_code'],code)
            self.assertEqual(r['evidence'],'bubblewrap-json-status')

    def test_prompt_wait_input_unicode_batches_and_wait_is_not_exit(self):
        sid=self.start('import time;print("提示 prompt 😀",flush=True);v=input();print("received:"+v);time.sleep(.1);print("最后 end 🧸")')
        first=self.call('terminal_read',session_id=sid,wait_ms=1000)
        self.assertIn('提示 prompt 😀',first['text']);self.assertTrue(first['running'])
        wait=self.call('terminal_read',session_id=sid,cursor=first['next_cursor'],wait_ms=30)
        self.assertTrue(wait['running']);self.assertIsNone(wait['exit_code']);self.assertEqual(wait['text'],'')
        result=self.call('terminal_write',session_id=sid,text='中文 English emoji 😀\n')
        self.assertEqual(result['accepted_bytes'],result['input_bytes'])
        data,r=self.drain(sid,first['next_cursor'],7)
        self.assertIn('received:中文 English emoji 😀\n'.encode(),data)
        self.assertIn('最后 end 🧸\n'.encode(),data);self.assertEqual(r['exit_code'],0)

    def test_large_output_exact_pagination(self):
        expected=('中文 ABC 😀\n'*20000+'TAIL 最后 🧸\n').encode()
        sid=self.start('import sys;sys.stdout.write("中文 ABC 😀\\n"*20000+"TAIL 最后 🧸\\n")')
        data,r=self.drain(sid,limit=4093)
        self.assertEqual(data,expected);self.assertEqual(r['next_cursor'],len(expected))

    def test_two_sessions_interrupt_and_closed_rejection(self):
        a=self.start('print("A",flush=True);print(input())')
        b=self.start('print("B",flush=True);print(input())')
        self.call('terminal_read',session_id=a,wait_ms=1000)
        self.call('terminal_read',session_id=b,wait_ms=1000)
        self.call('terminal_write',session_id=a,text='only-a\n')
        da,ra=self.drain(a);self.assertIn(b'only-a',da)
        self.assertTrue(self.call('terminal_status',session_id=b)['running'])
        self.call('terminal_interrupt',session_id=b)
        db,rb=self.drain(b);self.assertNotIn(b'only-a',db);self.assertNotEqual(rb['exit_code'],0)
        self.call('terminal_close',session_id=b)
        for name,args in [('terminal_status',{}),('terminal_read',{}),('terminal_write',{'text':'x'}),('terminal_interrupt',{}),('terminal_close',{})]:
            with self.assertRaisesRegex(terminal.tools.ToolError,'closed'):self.call(name,session_id=b,**args)

    def test_shell_command_status_unknown_and_interrupt_keeps_shell(self):
        sid=self.call('terminal_start',kind='shell')['session_id']
        first=self.call('terminal_read',session_id=sid,wait_ms=300)
        self.call('terminal_write',session_id=sid,text='sleep 60\n')
        time.sleep(.2);self.call('terminal_interrupt',session_id=sid)
        self.assertTrue(self.call('terminal_status',session_id=sid)['running'])
        self.call('terminal_write',session_id=sid,text='printf "after-interrupt\\n"; false\n')
        r=self.call('terminal_read',session_id=sid,cursor=first['next_cursor'],wait_ms=300)
        self.assertIsNone(r['command_exit_code'])
        self.call('terminal_write',session_id=sid,text='exit 9\n')
        data,last=self.drain(sid,r['next_cursor']);self.assertEqual(last['exit_code'],9)
        self.assertIn('after-interrupt',r['text']+data.decode())

    def test_interrupt_running_program_and_no_control_fd_leak(self):
        sid=self.start('import os,time;print(sorted(int(x) for x in os.listdir("/proc/self/fd") if int(x)>2 and os.path.exists("/proc/self/fd/"+x)),flush=True);time.sleep(60)')
        first=self.call('terminal_read',session_id=sid,wait_ms=1000)
        self.assertEqual(first['text'],'[]\n')
        self.call('terminal_interrupt',session_id=sid)
        _,last=self.drain(sid,first['next_cursor'])
        self.assertFalse(last['running']);self.assertNotEqual(last['exit_code'],0)

    def test_close_kills_descendants_without_inventing_exit_code(self):
        sid=self.start('import subprocess,time;subprocess.Popen(["/usr/bin/python3","-c","import time,pathlib;time.sleep(.5);pathlib.Path(\'/world/files/escaped-child\').touch()"]);print("ready",flush=True);time.sleep(60)')
        first=self.call('terminal_read',session_id=sid,wait_ms=1000)
        self.assertIn('ready',first['text'])
        result=self.call('terminal_close',session_id=sid)
        self.assertEqual(result['state'],'closed');self.assertFalse(result['running'])
        # A killed launcher without a final child status is not an exit-0 result.
        if result['evidence'] != 'bubblewrap-json-status': self.assertIsNone(result['exit_code'])
        time.sleep(.7);self.assertFalse((self.root/'files/escaped-child').exists())

    def test_boundary_world_output_and_symlink_escape(self):
        outside=Path(self.temp.name)/'host-only';outside.write_text('host-private')
        (self.root/'files/escape').symlink_to(outside)
        code='''import os,pathlib
assert not pathlib.Path('/root').exists()
assert not pathlib.Path('/mnt/c').exists()
assert not pathlib.Path('/world/files/escape').exists()
assert not pathlib.Path(%r).exists()
for path in ['/usr/terminal-write-probe','/world/.yohaku/terminal-write-probe']:
 try: pathlib.Path(path).write_text('denied')
 except OSError: pass
 else: raise AssertionError(path)
pathlib.Path('/world/files/legal-output').write_text('世界 output 😀')
print(os.getcwd())
''' % str(outside)
        sid=self.start(code);data,r=self.drain(sid)
        self.assertEqual(r['exit_code'],0,data);self.assertIn(b'/world/files',data)
        self.assertEqual((self.root/'files/legal-output').read_text(),'世界 output 😀')
        for cwd in ('../outside','/root','files/escape'):
            with self.assertRaises(terminal.tools.ToolError):self.call('terminal_start',cwd=cwd)


class Transport(unittest.TestCase):
    def test_client_end_rediscovery_service_loss_and_no_replay(self):
        with tempfile.TemporaryDirectory(prefix='yohaku-terminal-transport-') as temp:
            root=Path(temp)/'world';(root/'files').mkdir(parents=True);(root/'.yohaku').mkdir()
            (root/'.yohaku/files.json').write_text(json.dumps({'format':'yohaku-workspace/0.1'}))
            server=None
            def launch():
                child=subprocess.Popen([sys.executable,'-B',terminal.__file__,'--root',str(root),'serve'],env={},stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                deadline=time.monotonic()+5
                while time.monotonic()<deadline:
                    with socket.socket(socket.AF_UNIX) as probe:
                        try:probe.connect(terminal.address(root))
                        except ConnectionRefusedError:time.sleep(.05);continue
                        # A malformed/empty client must not terminate the service.
                        probe.sendall(b'{}\n');probe.recv(4096);return child
                self.fail('service did not start')
            def execute(request):
                child=subprocess.run([sys.executable,'-B',terminal.__file__,'--root',str(root),'request'],input=json.dumps(request),capture_output=True,text=True,timeout=25)
                response=json.loads(child.stdout)
                if not response['ok']:raise agent.ToolError(response['error'])
                return response['result']
            try:
                server=launch()
                api=agent.Tools(execute,permissions={'run':True})
                result=api.call('terminal_start',{'program':'/usr/bin/python3','args':['-u','-c','print("persist",flush=True);print(input())']})
                self.assertTrue(result['ok'],result);sid=result['result']['session_id'];instance=result['result']['service_instance']
                # A fresh Tools object and a different short-lived client process.
                fresh=agent.Tools(execute,permissions={'run':True})
                listed=fresh.call('terminal_list',{})['result']
                self.assertEqual(listed['service_instance'],instance)
                self.assertIn(sid,[s['session_id'] for s in listed['sessions']])
                self.assertTrue(fresh.call('terminal_write',{'session_id':sid,'text':'continued 😀\n'})['ok'])
                cursor=0;data=''
                for _ in range(100):
                    r=fresh.call('terminal_read',{'session_id':sid,'cursor':cursor,'wait_ms':100})['result']
                    data+=r['text'];cursor=r['next_cursor']
                    if r['output_complete'] and not r['has_more']:break
                self.assertIn('continued 😀',data);self.assertEqual(r['exit_code'],0)
                self.assertTrue(fresh.call('terminal_close',{'session_id':sid})['ok'])
                self.assertFalse(fresh.call('terminal_status',{'session_id':sid})['ok'])
                binary=fresh.call('terminal_start',{'program':'/usr/bin/python3','args':['-u','-c','import sys;sys.stdout.buffer.write(bytes(65536))']})
                bid=binary['result']['session_id'];raw=b'';cursor=0
                for _ in range(100):
                    r=fresh.call('terminal_read',{'session_id':bid,'cursor':cursor,'max_bytes':65536,'wait_ms':100})['result']
                    raw+=base64.b64decode(r['data_base64']);cursor=r['next_cursor']
                    if r['output_complete'] and not r['has_more']:break
                self.assertEqual(raw,bytes(65536));self.assertEqual(r['exit_code'],0)
                self.assertTrue(fresh.call('terminal_close',{'session_id':bid})['ok'])
                # Disconnect after sending a start, before receiving its reply.
                with socket.socket(socket.AF_UNIX) as disconnected:
                    disconnected.connect(terminal.address(root))
                    disconnected.sendall(json.dumps({'command':'terminal_start','program':'/usr/bin/python3','args':['-u','-c','print("disconnected prompt",flush=True);input()']}).encode()+b'\n')
                listed=fresh.call('terminal_list',{})['result']['sessions']
                self.assertEqual(len(listed),1)
                did=listed[0]['session_id']
                self.assertTrue(fresh.call('terminal_status',{'session_id':did})['result']['running'])
                self.assertTrue(fresh.call('terminal_close',{'session_id':did})['ok'])
                server.terminate();server.wait(timeout=5);server.stderr.close();server=launch()
                lost=fresh.call('terminal_status',{'session_id':sid})
                self.assertFalse(lost['ok']);self.assertIn('no exit evidence',lost['error'])
                self.assertNotEqual(fresh.call('terminal_list',{})['result']['service_instance'],instance)
                self.assertEqual(fresh.call('terminal_list',{})['result']['sessions'],[])
            finally:
                if server is not None:
                    server.terminate();server.wait(timeout=5);server.stderr.close()


if __name__=='__main__': unittest.main()
