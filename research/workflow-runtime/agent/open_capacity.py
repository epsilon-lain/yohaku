"""Host machine admission; independent of experimental run-count budgets."""
import json,os
from pathlib import Path
class CapacityBusy(RuntimeError):pass
def capacity():
    name=os.environ.get('YOHAKU_OPEN_CAPACITY_FILE')
    if not name:raise CapacityBusy('Machine capacity configuration absent; no node admitted')
    p=Path(name)
    if p.is_symlink()or not p.is_file():raise CapacityBusy('Machine capacity configuration unavailable')
    c=json.loads(p.read_bytes());c=c.get('capacity',c)
    reserve=int(c.get('reserve_memory_bytes',c.get('reserve_bytes',2*1024**3)));per=int(c.get('per_node_memory_bytes',c.get('estimated_active_node_bytes',1024**3)));cpu_per=int(c.get('cpus_per_node',c.get('cpu_per_active_node',2)))
    if min(per,cpu_per)<=0 or reserve<0:raise CapacityBusy('Invalid machine capacity configuration')
    available=next(int(s.split()[1])*1024 for s in Path('/proc/meminfo').read_text().splitlines()if s.startswith('MemAvailable:'))
    dynamic=max(0,min((os.cpu_count()or 1)//cpu_per,(available-reserve)//per))
    explicit=c.get('max_active_model_nodes')
    if explicit is not None:
        if type(explicit)is not int or explicit<0:raise CapacityBusy('Invalid machine admission ceiling')
        dynamic=min(dynamic,explicit)
    return dynamic
