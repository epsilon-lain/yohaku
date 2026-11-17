import json,sys
from pathlib import Path
from continuation import BASE,activate
p=activate();q=json.loads((BASE/'ROUND-PRIVATE.json').read_bytes());s=json.loads((BASE/'STARTUP-AND-PROGRESS.json').read_bytes())
out=dict(at=s['observed_at_asia_shanghai'],tasks=[{k:t.get(k)for k in('node_id','task_id','status','native_state','completed_real_research_receipt','error')}for t in s['tasks']],gate=s['gate_status'],math=[{k:e.get(k)for k in('id','revision','title','source_task','body_sha256')}for e in q['new_math']],queue=s['pending_queue'],failures=s['tool_failures'][-10:])
out['tools']=[dict(seq=e['seq'],node=e['actor'].get('actor_node_id'),tool=e['data']['name'],ok=e['data'].get('result',{}).get('ok'),args={k:v for k,v in e['data']['arguments'].items()if k not in('body','text','task','explanation')})for e in q['new_events']if e['kind']=='native_tool_completed'][-12:]
from mechanisms_host import rpc
out['program_budget']=rpc(p['program_budget']['socket'],dict(op='status'))
out['computations']=[dict(task_id=x.get('status',{}).get('task_id'),status=x.get('status',{}).get('status'),error=(x.get('status',{}).get('receipt')or{}).get('error'),artifacts=[{k:a.get(k)for k in('id','path','sha256','bytes')}for a in x.get('status',{}).get('artifacts',[])])for x in q['computations']]
if '--full'not in sys.argv:
    out=dict(at=out['at'],tasks=out['tasks'],turns=out['gate']['native_turns_reserved'],remaining=out['gate']['native_turns_remaining'],seconds=out['gate']['remaining_seconds'],stop=out['gate']['shared_stop'],math=out['math'],queue=out['queue'],latest_failures=out['failures'][-2:],recent_tools=[(r['seq'],r['node'],r['tool'],r['ok'])for r in out['tools']],program_budget={k:out['program_budget'][k]for k in('issued','reported','unresolved_leases')},computations=[{k:r[k]for k in('task_id','status','error')}for r in out['computations']])
print(json.dumps(out,ensure_ascii=False))
