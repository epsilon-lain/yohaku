"""Read-only runtime/official-source fixture. No primitive application."""
import inspect,json,sys,hashlib
from pathlib import Path
sys.path.insert(0,"/project/round2-external")
from restore_resources import restore
import meter
r=restore("/output/r6-fixture-fixed")
sys.path.insert(0,r["acceptance"])
import validate_candidate as acc
o=acc.Official(r["official"])
s=sys.modules[o.specs.__package__+".stable_core"]
out=dict(preparation_only=True,restoration=r,meter_source=inspect.getsource(meter),stable_source=Path(s.__file__).read_text(),stable_sha256=hashlib.sha256(Path(s.__file__).read_bytes()).hexdigest(),sample_rows=s.MOVE_TABLE[:18])
Path("/output/r6-runtime-fixture.json").write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(dict(preparation_only=True,meter_names=[x for x in dir(meter) if not x.startswith("_")],stable_sha256=out["stable_sha256"])))
