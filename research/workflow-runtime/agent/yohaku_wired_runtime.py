"""Host-selected Wired backend; existing tool IDs, material paths and records stay stable."""
from pathlib import Path
import json
PACKAGE=Path(__file__).resolve().parents[1]
def selected_backend():
 path=PACKAGE/'runtime/WIRED-BACKEND.json'
 return json.loads(path.read_text()).get('backend','managed_playwright') if path.exists() else 'managed_playwright'
class Runtime:
 def __new__(cls,world):
  if selected_backend()=='normal_browser_extension':from yohaku_wired_bridge import Runtime as Backend
  else:from yohaku_browser_runtime import Runtime as Backend
  return Backend(world)
