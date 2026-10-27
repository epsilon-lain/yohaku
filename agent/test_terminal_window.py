import json,os,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import yohaku_terminal as terminal
import yohaku_agent as agent

class WindowContracts(unittest.TestCase):
    def test_resize_permission_and_bounds(self):
        definitions=agent.Tools(lambda r:r, permissions={'read':True,'run':False}).definitions
        self.assertNotIn('terminal_resize',{v['name'] for v in definitions})
        bridge=agent.Tools(lambda r:r,permissions={'run':True})
        for args in ({'rows':1,'cols':80},{'rows':24,'cols':401}):
            self.assertFalse(bridge.call('terminal_resize',dict(session_id='id',**args))['ok'])
        value=bridge.call('terminal_resize',dict(session_id='id',rows=30,cols=100))
        self.assertTrue(value['ok']);self.assertEqual(value['result']['command'],'terminal_resize')

    def test_stale_instance_has_no_side_effects(self):
        service=terminal.Service(Path('/world'))
        with patch.object(terminal,'Session') as start:
            with self.assertRaisesRegex(terminal.tools.ToolError,'instance changed'):
                service.execute(dict(command='terminal_write',session_id='old',service_instance='old',text='not sent'))
            start.assert_not_called()
        for value in (True,1,301,'24'):
            with self.assertRaises(terminal.tools.ToolError):terminal.integer(value,2,300)

class WindowRealProcess(unittest.TestCase):
    def test_resize_independent_pages_and_attach_replay(self):
        with tempfile.TemporaryDirectory(prefix='yohaku-window-') as tmp:
            root=Path(tmp);(root/'files').mkdir();(root/'.yohaku').mkdir()
            (root/'.yohaku/files.json').write_text(json.dumps({'format':'yohaku-workspace/0.1'}))
            svc=terminal.Service(root)
            def call(op,**kwargs):return svc.execute(dict(command=op,**kwargs))
            code="import os,signal; print('READY 中文 😀 '+str(tuple(os.get_terminal_size(0))),flush=True); signal.signal(signal.SIGWINCH,lambda *_:print('SIZE '+str(tuple(os.get_terminal_size(0))),flush=True)); value=input(); print('ECHO:'+value,flush=True); raise SystemExit(7)"
            started=call('terminal_start',program='/usr/bin/python3',args=['-u','-c',code],rows=21,cols=73)
            sid=started['session_id'];identity=dict(session_id=sid,service_instance=started['service_instance'])
            session=svc.sessions[sid];pid=session.child.pid
            try:
                first=call('terminal_read',**identity,cursor=0,wait_ms=1000)
                self.assertIn('READY 中文 😀 (73, 21)',first['text']);self.assertTrue(first['running'])
                # Attach/read/status creates no program, and each reader has its own cursor.
                reread=call('terminal_read',**identity,cursor=0,wait_ms=0)
                self.assertEqual(first['text'],reread['text']);self.assertEqual(session.child.pid,pid)
                self.assertEqual(len(call('terminal_list')['sessions']),1)
                sized=call('terminal_resize',**identity,rows=33,cols=101)
                self.assertEqual((sized['rows'],sized['cols']),(33,101))
                page=call('terminal_read',**identity,cursor=first['next_cursor'],wait_ms=1000)
                self.assertIn('SIZE (101, 33)',page['text'])
                call('terminal_write',**identity,text='你好 window 😀\n')
                cursor=0;output='';last=None
                for _ in range(300):
                    last=call('terminal_read',**identity,cursor=cursor,max_bytes=7,wait_ms=100)
                    output+=last['text'];cursor=last['next_cursor']
                    if last['output_complete'] and not last['has_more']:break
                self.assertTrue(last['output_complete']);self.assertEqual(last['exit_code'],7)
                self.assertEqual(last['evidence'],'bubblewrap-json-status')
                self.assertEqual(output.count('ECHO:你好 window 😀'),1)
                self.assertEqual(call('terminal_read',**identity,cursor=cursor)['text'],'')
                call('terminal_close',**identity)
                for operation in ('terminal_status','terminal_read','terminal_resize'):
                    with self.assertRaisesRegex(terminal.tools.ToolError,'closed'):
                        call(operation,**identity,**({'rows':24,'cols':80} if operation=='terminal_resize' else {}))
            finally:
                if not session.closed:
                    with session.lock:session.close()

if __name__=='__main__':unittest.main()
