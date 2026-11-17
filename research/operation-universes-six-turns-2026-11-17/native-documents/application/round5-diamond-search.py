"""Round5: exact resource-monotone adjacent diamonds and two-edge cycles.
No radius balls, macro relabeling, literature pages, or ordinary shortest searches.
"""
import hashlib,json,os,subprocess,sys,time
from collections import deque
from pathlib import Path
sys.path.insert(0,"/project/round2-external")
from restore_resources import restore
OUT=Path("/output")
CFG=json.loads(Path("/project/round5-protocol.json").read_text())
class Guard(Exception):pass
def save(name,data):
 (OUT/name).write_text(json.dumps(data,indent=2)+"\n")
def resource(s):return sum(map(len,s))
def signature(trace):
 r=list(map(resource,trace))
 return dict(length=len(trace)-1,peak_total_relator_length=max(r),work=sum(r))
def main():
 restored=restore("/output/round5-fixed")
 sys.path.insert(0,restored["acceptance"])
 import validate_candidate as acc
 official=acc.Official(restored["official"])
 stable=sys.modules[official.specs.__package__+".stable_core"]
 ch=official.challenges[CFG["challenge"]];initial=tuple(map(tuple,ch["initial_relators"]))
 baseline=tuple(CFG["baseline"])
 assert list(baseline)==acc.LOCKED_BASELINES[CFG["challenge"]]
 initial_trace=[initial]
 for m in baseline:
  s,reason=stable.apply_move(initial_trace[-1],m)
  assert reason is None
  initial_trace.append(s)
 base_verdict=official.verify(ch,list(baseline))
 assert base_verdict["ok"]
 assert signature(initial_trace)==CFG["baseline_signature"]
 def checked(path,trace):
  v=official.verify(ch,list(path))
  if v["ok"]:
   s=signature(trace)
   assert all(v[k]==s[k] for k in s)
  return v
 checked(baseline,initial_trace)
 rows=[dict(path=baseline,trace=initial_trace,parent=None,certificate=None,verdict=base_verdict)]
 queue=deque([0]);seen={baseline:0};cache={}
 counts=dict(positions_checked=0,swap_attempts=0,swap_first_illegal=0,swap_second_illegal=0,
  unequal_exit=0,cost_increasing=0,endpoint_equal_swaps=0,resource_monotone_swaps=0,
  cycle_deletions=0,duplicate_paths=0,official_rejections=0,official_candidate_verifications=0,
  search_apply_calls=0,apply_cache_hits=0,processed_paths=0)
 best=0;guard=None;search_start=time.monotonic()
 def guard_check():
  if time.monotonic()-search_start>CFG["guard"]["search_wall_seconds"]:
   raise Guard("search_wall_seconds")
 def apply(s,m):
  guard_check();key=(s,m)
  if key in cache:
   counts["apply_cache_hits"]+=1
   return cache[key]
  if counts["search_apply_calls"]>=CFG["guard"]["max_search_apply_calls"]:
   raise Guard("max_search_apply_calls")
  counts["search_apply_calls"]+=1
  cache[key]=stable.apply_move(s,m)
  return cache[key]
 def quality(index):
  row=rows[index];v=row["verdict"]
  return (len(row["path"]),v["peak_total_relator_length"],v["work"],row["path"])
 def add(path,trace,parent,certificate):
  nonlocal best
  if path in seen:
   counts["duplicate_paths"]+=1
   return
  if len(rows)>=CFG["guard"]["max_paths"]:raise Guard("max_paths")
  counts["official_candidate_verifications"]+=1
  verdict=checked(path,trace)
  if not verdict["ok"]:
   counts["official_rejections"]+=1
   return
  before=signature(rows[parent]["trace"]);after=signature(trace)
  assert after["length"]<=before["length"]
  assert after["peak_total_relator_length"]<=before["peak_total_relator_length"]
  assert after["work"]<=before["work"]
  assert after["work"]-before["work"]==certificate["delta_work"]
  index=len(rows);seen[path]=index
  rows.append(dict(path=path,trace=trace,parent=parent,certificate=certificate,verdict=verdict))
  queue.append(index)
  if quality(index)<quality(best):best=index
 def checkpoint():
  save("round5-checkpoint.json",dict(paths_discovered=len(rows),queue_pending=len(queue),
   best_path=rows[best]["path"],best_verdict=rows[best]["verdict"],counts=counts,guard=guard,
   search_elapsed_seconds=time.monotonic()-search_start))
 try:
  while queue:
   guard_check()
   index=queue.popleft();row=rows[index];path=row["path"];trace=row["trace"]
   for i in range(len(path)-1):
    guard_check();counts["positions_checked"]+=1
    entry,old_middle,exit=trace[i:i+3]
    pair=path[i:i+2]
    if entry==exit:
     counts["cycle_deletions"]+=1
     new_path=path[:i]+path[i+2:]
     new_trace=trace[:i+1]+trace[i+3:]
     add(new_path,new_trace,index,dict(kind="delete_exact_two_cycle",offset=i,old_pair=pair,
      entry=entry,old_middle=old_middle,exit=exit,
      delta_work=-resource(old_middle)-resource(exit)))
    if pair[0]==pair[1]:continue
    counts["swap_attempts"]+=1
    middle,reason=apply(entry,pair[1])
    if reason is not None:
     counts["swap_first_illegal"]+=1;continue
    endpoint,reason=apply(middle,pair[0])
    if reason is not None:
     counts["swap_second_illegal"]+=1;continue
    if endpoint!=exit:
     counts["unequal_exit"]+=1;continue
    counts["endpoint_equal_swaps"]+=1
    delta=resource(middle)-resource(old_middle)
    if delta>0:
     counts["cost_increasing"]+=1;continue
    counts["resource_monotone_swaps"]+=1
    new_path=path[:i]+(pair[1],pair[0])+path[i+2:]
    new_trace=trace[:i+1]+[middle]+trace[i+2:]
    add(new_path,new_trace,index,dict(kind="adjacent_exact_diamond",offset=i,old_pair=pair,
     new_pair=(pair[1],pair[0]),entry=entry,old_middle=old_middle,new_middle=middle,exit=exit,
     delta_work=delta))
   counts["processed_paths"]+=1
   if counts["processed_paths"]%32==0:checkpoint()
 except Guard as e:guard=str(e)
 checkpoint()
 search_elapsed=time.monotonic()-search_start
 path=rows[best]["path"];trace=rows[best]["trace"]
 chain=[];j=best
 while rows[j]["parent"] is not None:
  chain.append(dict(node=j,parent=rows[j]["parent"],certificate=rows[j]["certificate"]))
  j=rows[j]["parent"]
 chain.reverse()
 candidate=dict(challenge_id=CFG["challenge"],tokens=list(path),macros={})
 acceptance=acc.validate(json.dumps(candidate).encode(),
  (Path(restored["acceptance"])/"baselines.json").read_bytes(),official)
 assert acceptance["official_verdict"]["ok"]
 save("round5-candidate.json",candidate)
 submission="\n".join(k+": "+json.dumps(list(path) if k==CFG["challenge"] else v)
  for k,v in acc.LOCKED_BASELINES.items())+"\n"
 (OUT/"round5-submission.txt").write_text(submission)
 env=dict(os.environ,PYTHONPATH=str(Path(restored["official"])/"competition/tools"))
 args=[sys.executable,"-B","-m","verifier","--manifest",
  str(Path(restored["official"])/"competition/tools/verifier/data/manifest.json"),
  "--submission",str(OUT/"round5-submission.txt"),"--pretty"]
 run=subprocess.run(args,cwd=restored["official"],env=env,capture_output=True,text=True,timeout=20)
 cli=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr)
 save("round5-cli.json",cli)
 assert run.returncode==0 and json.loads(run.stdout)["accepted"]
 summary=dict(paths_discovered=len(rows),processed_paths=counts["processed_paths"],
  queue_pending=len(queue),closure_complete=guard is None and not queue,guard=guard,
  baseline_signature=signature(initial_trace),current_signature=signature(trace),
  current_path=path,strict_primitive_improvement=len(path)<len(baseline),
  best_node=best,search_elapsed_seconds=search_elapsed,counts=counts,
  platform_upload=False)
 certificates=[dict(node=i,path=r["path"],parent=r["parent"],certificate=r["certificate"],
  verdict=r["verdict"]) for i,r in enumerate(rows)]
 save("round5-certificates.json",certificates)
 # Source metadata and relevant exact verifier code support convention inspection.
 import inspect
 stable_source=inspect.getsource(stable)
 source_lines=stable_source.splitlines()
 work_lines=[dict(line=i+1,text=line) for i,line in enumerate(source_lines)
  if "work" in line or "peak_total_relator_length" in line or "max_total" in line]
 stable_hash=hashlib.sha256(Path(stable.__file__).read_bytes()).hexdigest()
 assert stable_hash=="234b164c766bf7fd2e1bee7f7bfb3910319c5885e4250bf56520d2d2b0f46e9d"
 result=dict(summary=summary,protocol=CFG,restoration=restored,
  baseline_verdict=base_verdict,current_verdict=rows[best]["verdict"],
  baseline_trace=initial_trace,current_trace=trace,advantage_chain=chain,acceptance=acceptance,
  challenge=ch,stable_source_sha256=stable_hash,stable_resource_source_lines=work_lines,
  limitations="Only directed work-monotone adjacent swaps and exact two-cycle deletions from this one path. Same-author implementation, not independent reproduction. Official candidate and CLI replay do not prove search completeness beyond this transformation class. No speed/token benefit or global minimum claim.")
 save("round5-results.json",result)
 print(json.dumps(dict(summary=summary,cli=cli)),flush=True)
if __name__=="__main__":main()
