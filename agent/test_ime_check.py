import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import yohaku_ime_check as check
import yohaku_dev_runtime as runtime

class DeploymentImeChecks(unittest.TestCase):
    def test_human_acceptance_requires_both_entries_and_restart(self):
        record={phase:{entry:{field:True for field in ['candidate_visible','chinese_committed','no_duplicate']} for entry in check.ENTRIES} for phase in check.PHASES}
        self.assertTrue(check.human_acceptance(record)['ok'])
        record['after_restart']['techne_codex']['candidate_visible']=False
        self.assertFalse(check.human_acceptance(record)['ok'])
        self.assertFalse(check.human_acceptance({'user_said_ok':True})['ok'])
    def test_old_graphics_errors_do_not_hide_new_popup_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'weston.log';p.write_text('rdp_allocate_shared_memory: Failed historical\n');s=p.stat();identity=(s.st_dev,s.st_ino);offset=s.st_size
            self.assertTrue(check.new_graphics_errors(p,identity,offset)['ok'])
            with p.open('a') as stream:stream.write('rdp_allocate_shared_memory: Failed new-popup\n')
            self.assertEqual(check.new_graphics_errors(p,identity,offset)['allocation_errors'],1)
            p.write_text('short');self.assertEqual(check.new_graphics_errors(p,identity,offset)['state'],'unknown_log_rotated_or_truncated')
    def test_event_counts_do_not_invent_nonempty_preedit_or_manual_acceptance(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'events.log';p.write_text('[IME EVENT] kind=Enabled chars=0 target=chat allowed=true\n[IME EVENT] kind=Preedit chars=0 target=chat allowed=true\n[IME EVENT] kind=Commit chars=2 target=chat allowed=true\n[IME EVENT] kind=Commit chars=5 target=nested allowed=true\n[IME EVENT] kind=Commit chars=3 target=chat allowed=false\n')
            r=check.event_summary(p);self.assertEqual(r['commit_characters'],2);self.assertEqual(r['nonempty_preedit_events'],0);self.assertNotIn('accepted',r)
    def test_failed_build_gate_does_not_install_candidate_bridge(self):
        with tempfile.TemporaryDirectory() as folder:
            project=Path(folder);(project/'Cargo.toml').write_text('[package]')
            with patch.object(runtime,'PROJECT',project),patch.dict(runtime.os.environ,{'YOHAKU_DEVELOPMENT':'1'}),patch.object(runtime.sys,'argv',['runtime','build']),patch.object(runtime,'run_command',side_effect=[0,2]) as run,patch.object(runtime.shutil,'copy2') as copy:
                self.assertEqual(runtime.main(),2)
                self.assertEqual(run.call_count,2)
                self.assertIn('yohaku_ime_check.py',str(run.call_args.args[0]))
                copy.assert_not_called()
    def test_loom_pair_rejects_stale_generated_output(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'source.tex';o=Path(folder)/'source';p.write_text('---\n## 正文\n`````text\nnew\n`````\n## AI 笔记\n');o.write_text('new\n');self.assertTrue(check.body_matches(p,o));o.write_text('old\n');self.assertFalse(check.body_matches(p,o))

if __name__=='__main__':unittest.main()
