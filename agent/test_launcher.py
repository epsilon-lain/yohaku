import io,os,sys,time,unittest
from unittest.mock import patch
import yohaku_launcher as l
from pathlib import Path

class LaunchTests(unittest.TestCase):
    def test_x11_only_changes_host_display_selection(self):
        original={'DISPLAY':':0','WAYLAND_DISPLAY':'wayland-0','WAYLAND_SOCKET':'4','XDG_RUNTIME_DIR':'/run/user/1000','PATH':'/usr/bin'}
        with patch.dict(os.environ,original,clear=True):
            env,backend=l.launch_environment('x11')
            self.assertEqual(backend,'x11');self.assertNotIn('WAYLAND_DISPLAY',env);self.assertNotIn('WAYLAND_SOCKET',env)
            self.assertEqual(env['XDG_RUNTIME_DIR'],original['XDG_RUNTIME_DIR']);self.assertEqual(dict(os.environ),original)
    def test_native_preserves_selection_and_missing_display_fails(self):
        with patch.dict(os.environ,{'WAYLAND_DISPLAY':'wayland-0'},clear=True):
            self.assertEqual(l.launch_environment('native')[0]['WAYLAND_DISPLAY'],'wayland-0')
            with self.assertRaises(ValueError):l.launch_environment('x11')
    def test_normal_output_and_build_exit_code(self):
        output=io.BytesIO();code=l.supervise([sys.executable,'-c','print("build failed");raise SystemExit(101)'],Path.cwd(),output)
        self.assertEqual(code,101);self.assertEqual(output.getvalue(),b'build failed\n')
    def test_disconnection_is_bounded_and_process_terminated(self):
        message=next(iter(l.DISPLAY_ERRORS)).decode();output=io.BytesIO();started=time.monotonic()
        code=l.supervise([sys.executable,'-u','-c',f'import signal;signal.signal(signal.SIGTERM,signal.SIG_IGN)\nwhile True: print({message!r},flush=True)'],Path.cwd(),output)
        self.assertEqual(code,70);self.assertEqual(output.getvalue().count(message.encode()),4);self.assertLess(time.monotonic()-started,4)

if __name__=='__main__':unittest.main()
