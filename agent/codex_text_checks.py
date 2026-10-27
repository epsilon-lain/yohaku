"""Reproducible offline checks; no credentials, network, or real model calls."""
import hashlib,json,sys,unittest
from yohaku_codex_text import VERSION,FEEDBACK_VERSION
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
files=['yohaku_codex_text.py','yohaku_agent.py','test_codex_text.py','test_codex_text_integration.py','yohaku_codex_tasks.py']
print(json.dumps({'version':VERSION,'feedback_version':FEEDBACK_VERSION,'scope':'offline controlled transport + real Rust/Loom, NOT real DeepSeek or Codex','code_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}}),flush=True)
suite=unittest.defaultTestLoader.loadTestsFromNames(['test_codex_text','test_codex_text_integration','test_coordinates','test_edit_continuation','test_codex_tasks'])
result=unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
