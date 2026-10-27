"""Published checkout portability: real Loom/CLI, synthetic world, no model or account."""
import hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import yohaku_dev as dev
import yohaku_host_update as update
import yohaku_codex_text_service as service
import yohaku_agent as agent
ROOT=Path(__file__).resolve().parents[1]
class ReleasePackageTests(unittest.TestCase):
 def test_portable_develop_candidate_prepares_and_checks_without_host_sync(self):
  with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'HOME':folder}):
   base=Path(folder);world=base/'world';service.setup(world)
   ws=agent.Workspace(world,ROOT/'bin/loom-linux-x86_64',ROOT/'bin/yohaku_workspace')
   original=dev.atomic
   def atomic(path,data):
    return original(base/'runtime-profile.json' if path==ROOT/dev.PROFILE else path,data)
   with patch.object(dev,'detect_runtime',return_value={'format':'yohaku-dev-runtime/1','toolchain':'/unused-fixture','registry':'/unused-fixture'}),patch.object(dev,'atomic',side_effect=atomic):
    dev.prepare(world,ws)
   bundle=world/dev.PROJECT
   before={n:update.sha(ROOT/n) for n in update.PAYLOAD}
   updater=update.Updater(world,ROOT);ready=updater.call({'action':'prepare_candidate'})
   self.assertEqual(ready['phase'],'candidate_ready')
   self.assertEqual(ready['candidate_files'],len(update.PAYLOAD))
   self.assertTrue(Path(ready['manifest_map_path']).is_file())
   plan=updater.call({'action':'check','id':'portable-package','manifest_sha256':ready['candidate_manifest_sha256']})
   self.assertEqual(plan['phase'],'prepared')
   self.assertEqual(plan['manifest'],ready['candidate_manifest_sha256'])
   self.assertEqual({n:update.sha(ROOT/n) for n in update.PAYLOAD},before)
   self.assertEqual(plan['files']['agent/yohaku_codex_text.py'],before['agent/yohaku_codex_text.py'])
   self.assertIn('save-feedback/2',(bundle/'agent/yohaku_codex_text.py').read_text())
   self.assertEqual(json.loads((world/'files/codex-text/UPDATE.json').read_text())['action'],'draft')
   for name in ('host-update','codex-text-service'):
    config=json.loads((ROOT/f'config/{name}.json').read_text())
    self.assertFalse(config['enabled_by_default']);self.assertFalse(config['launch_on_yohaku_start'])
if __name__=='__main__':unittest.main()
