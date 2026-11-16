"""Round2 preparation only: restore pinned sources and inspect official semantics."""
import importlib.util, json, sys
from pathlib import Path
sys.path.insert(0, "/project/round2-external")
from restore_resources import restore
info=restore("/output/fixed")
accept=Path(info["acceptance"])
sys.path.insert(0,str(accept))
import validate_candidate as acceptance
official=acceptance.Official(info["official"])
selected={cid:official.challenges[cid] for cid in acceptance.LOCKED_BASELINES}
verdicts={cid:official.verify(selected[cid],p) for cid,p in acceptance.LOCKED_BASELINES.items()}
v=Path(info["official"])/"competition/tools/verifier"
result=dict(preparation_only=True,resource_restore=info,limits=official.manifest["limits"],
    challenges=selected,baseline_verdicts=verdicts,
    sources={name:(v/name).read_text() for name in ["stable_core.py","core.py","submission.py","cli.py","specs.py","data/stable_move_spec.json"]})
Path("/output/r2-inspect.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:result[k]for k in ["preparation_only","resource_restore","limits","challenges","baseline_verdicts"]}))
print("STABLE_SOURCE_BEGIN\n"+result["sources"]["stable_core.py"]+"\nSTABLE_SOURCE_END")
