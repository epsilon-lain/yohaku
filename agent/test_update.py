"""Regression coverage for installing the metadata required by Develop."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PACKAGE=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('yohaku_update',PACKAGE/'apply_update.py')
update=importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)

def digest(data):return hashlib.sha256(data).hexdigest()

class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.bundle=self.base/'bundle';self.target=self.base/'installed'
        self.bundle.mkdir();self.target.mkdir()
        self.old_manifest=b'{"release":"previous"}\n';self.old_installer=b'# previous installer\n'
        for root in (self.bundle,self.target):(root/'Cargo.toml').write_bytes(b'[package]\n')
        (self.bundle/'apply_update.py').write_bytes((PACKAGE/'apply_update.py').read_bytes())
        (self.bundle/'runtime.py').write_bytes(b'# new runtime\n')
        (self.target/'runtime.py').write_bytes(b'# old runtime\n')
        manifest={'release':'test','project_checks':{'Cargo.toml':digest(b'[package]\n')},
                  'metadata_before_sha256s':{'apply_update.py':[digest(self.old_installer)],
                                            'update_manifest.json':[digest(self.old_manifest)]},
                  'files':[{'path':'runtime.py','sha256':digest(b'# new runtime\n'),
                            'before_sha256s':[digest(b'# old runtime\n')],'executable':False}]}
        (self.bundle/'update_manifest.json').write_text(json.dumps(manifest))
        (self.target/'world-note.txt').write_text('keep')
    def tearDown(self):self.temp.cleanup()
    def run_update(self,*args):
        with patch.object(update,'__file__',str(self.bundle/'apply_update.py')),patch.object(sys,'argv',['apply_update.py','--project',str(self.target),*args]),contextlib.redirect_stdout(io.StringIO()):
            update.main()
    def test_missing_metadata_is_installed_and_repeat_preserves_world(self):
        self.run_update()
        for name in ('runtime.py','apply_update.py','update_manifest.json'):
            self.assertEqual((self.target/name).read_bytes(),(self.bundle/name).read_bytes())
        self.run_update();self.assertEqual((self.target/'world-note.txt').read_text(),'keep')
    def test_known_previous_metadata_is_backed_up_and_replaced(self):
        (self.target/'apply_update.py').write_bytes(self.old_installer)
        (self.target/'update_manifest.json').write_bytes(self.old_manifest)
        self.run_update()
        backups=list(self.target.glob('loom-*'))
        self.assertEqual(len(backups),1)
        self.assertEqual((backups[0]/'apply_update.py').read_bytes(),self.old_installer)
        self.assertEqual((backups[0]/'update_manifest.json').read_bytes(),self.old_manifest)
    def test_preflight_leaves_missing_metadata_and_payload_unchanged(self):
        self.run_update('--check')
        self.assertFalse((self.target/'update_manifest.json').exists())
        self.assertFalse((self.target/'apply_update.py').exists())
        self.assertEqual((self.target/'runtime.py').read_bytes(),b'# old runtime\n')
    def test_unknown_metadata_and_symlinks_abort_before_writes(self):
        for name in ('apply_update.py','update_manifest.json'):
            p=self.target/name;p.write_text('human changes')
            with self.assertRaises(SystemExit):self.run_update()
            self.assertEqual(p.read_text(),'human changes');p.unlink()
            p.symlink_to(self.bundle/name)
            with self.assertRaises(SystemExit):self.run_update()
            p.unlink()
        self.assertEqual((self.target/'runtime.py').read_bytes(),b'# old runtime\n')
    def test_failed_metadata_replace_rolls_back_payload_and_installer(self):
        original=update.os.replace
        def replace(src,dst):
            if Path(dst)==self.target/'update_manifest.json':raise OSError('injected metadata write failure')
            return original(src,dst)
        with patch.object(update.os,'replace',side_effect=replace):
            with self.assertRaises(OSError):self.run_update()
        self.assertEqual((self.target/'runtime.py').read_bytes(),b'# old runtime\n')
        self.assertFalse((self.target/'apply_update.py').exists())
        self.assertFalse((self.target/'update_manifest.json').exists())

if __name__=='__main__':unittest.main()
