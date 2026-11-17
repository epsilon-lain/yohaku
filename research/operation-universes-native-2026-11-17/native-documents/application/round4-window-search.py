"""Round4 guarded exact-endpoint fragment conversion and actual local search."""
import json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,"/project/round2-external")
from restore_resources import restore
OUT=Path("/output");START=time.monotonic();CALLS=0
CFG=json.loads(Path("/project/round4-protocol.json").read_text())
class Guard(Exception):pass
def save(n,x):(OUT/n).write_text(json.dumps(x,indent=2)+"\n")
def main():
 global CALLS
 restored=restore("/output/round4-fixed")
 sys.path.insert(0,restored["acceptance"])
 import validate_candidate as acc
 official=acc.Official(restored["official"])
 stable=sys.modules[official.specs.__package__+".stable_core"]
 cid=CFG["challenge"];ch=official.challenges[cid];old=tuple(CFG["baseline"])
 assert list(old)==acc.LOCKED_BASELINES[cid]
 regressions={k:official.verify(official.challenges[k],v) for k,v in acc.LOCKED_BASELINES.items()}
 assert all(v["ok"] for v in regressions.values())
 def replay(path,source=None):
  s=tuple(map(tuple,ch["initial_relators"])) if source is None else source
  states=[s]
  for m in path:
   s,reason=stable.apply_move(s,m);assert reason is None
   states.append(s)
  return states
 trace=replay(old)
 c=CFG["conversion"];i=c["offset"];a=tuple(c["replacement"])
 assert tuple(c["old"])==old[i:i+len(a)]
 endpoint=replay(a,trace[i])[-1]
 assert endpoint==trace[i+len(a)]
 equal=old[:i]+a+old[i+len(a):]
 equal_verdict=official.verify(ch,list(equal));assert equal_verdict["ok"]
 certificate=dict(entry=trace[i],exit=endpoint,offset=i,old=list(old[i:i+len(a)]),
  replacement=list(a),expanded_old_length=len(a),expanded_new_length=len(a),
  full_path=list(equal),official_verdict=equal_verdict,
  guard="same exact ordered entry; rank2 legal IDs; full path resource replay")
 rows=stable.MOVE_TABLE
 choices={}
 for k in range(CFG["rank_cap"]+1):
  r=[x for x in rows if x["category"] not in ("stabilize","destabilize") and x["relator"]<k
   and (x["category"]!="multiplication" or x["other"]<k)
   and (x["category"]!="conjugation" or abs(x["conjugator"])<=k)]
  r += [x for x in rows if x["category"]=="destabilize" and x["relator"]<k]
  if k<CFG["rank_cap"]:r.append(rows[14])
  choices[k]=sorted(r,key=lambda x:x["id"])
 def call(s,m):
  global CALLS
  CALLS+=1
  if CALLS>CFG["max_wrapper_calls"]:raise Guard("global_call_cap")
  if CALLS%512==0 and time.monotonic()-START>CFG["wall_seconds"]:raise Guard("global_wall_cap")
  return stable.apply_move(s,m)
 def ball(source):
  before=CALLS;seen={source:()};layer=[source];sizes=[1];complete=True;guard=None
  try:
   for depth in range(CFG["bfs_radius"]):
    nxt=[]
    for s in layer:
     for row in choices[len(s)]:
      t,reason=call(s,row["id"])
      if reason is not None:continue
      if t not in seen:
       if len(seen)>=CFG["max_states_per_entry"]:raise Guard("entry_state_cap")
       seen[t]=seen[s]+(row["id"],);nxt.append(t)
    layer=nxt;sizes.append(len(layer))
  except Guard as e:complete=False;guard=str(e)
  return seen,dict(states=len(seen),layer_sizes=sizes,complete=complete,guard=guard,calls=CALLS-before)
 balls=[];windows=[];proposals=[];best=equal;global_guard=None
 for i in range(len(old)-1):
  seen,meta=ball(trace[i]);meta["entry_index"]=i;balls.append(meta)
  for length in CFG["window_lengths"]:
   j=i+length
   if j>len(old):continue
   bound=min(CFG["bfs_radius"],length-1);p=seen.get(trace[j])
   hit=p is not None and len(p)<=bound
   w=dict(i=i,j=j,old_length=length,strict_replacement_bound=bound,hit=hit,ball_complete=meta["complete"])
   if hit:
    path=old[:i]+p+old[j:];v=official.verify(ch,list(path))
    item=dict(window=w,replacement=list(p),full_path=list(path),verdict=v);proposals.append(item)
    if v["ok"] and len(path)<len(best):best=path
   windows.append(w)
  save("round4-checkpoint.json",dict(balls=balls,windows=windows,calls=CALLS))
  if meta["guard"] in ("global_call_cap","global_wall_cap"):
   global_guard=meta["guard"];break
 candidate=dict(challenge_id=cid,tokens=list(best),macros={})
 acceptance=acc.validate(json.dumps(candidate).encode(),(Path(restored["acceptance"])/"baselines.json").read_bytes(),official)
 assert acceptance["official_verdict"]["ok"]
 save("round4-candidate.json",candidate)
 submission="\n".join(k+": "+json.dumps(list(best) if k==cid else v) for k,v in acc.LOCKED_BASELINES.items())+"\n"
 (OUT/"round4-submission.txt").write_text(submission)
 env=dict(os.environ,PYTHONPATH=str(Path(restored["official"])/"competition/tools"))
 args=[sys.executable,"-B","-m","verifier","--manifest",str(Path(restored["official"])/"competition/tools/verifier/data/manifest.json"),
  "--submission",str(OUT/"round4-submission.txt"),"--pretty"]
 run=subprocess.run(args,cwd=restored["official"],env=env,capture_output=True,text=True,timeout=20)
 cli=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr)
 assert run.returncode==0 and json.loads(run.stdout)["accepted"]
 save("round4-cli.json",cli)
 summary=dict(entries_executed=len(balls),entries_planned=len(old)-1,windows_checked=len(windows),
  complete_balls=sum(x["complete"] for x in balls),guards=[dict(i=x["entry_index"],guard=x["guard"]) for x in balls if x["guard"]],
  global_guard=global_guard,short_endpoint_hits=len(proposals),accepted_short_proposals=sum(x["verdict"]["ok"] for x in proposals),
  wrapper_search_calls=CALLS,current_length=len(best),strict_improvement=len(best)<len(old),
  current_kind="strict_replacement" if len(best)<len(old) else "equal_length_certified_reordering",
  elapsed_seconds=time.monotonic()-START,platform_upload=False)
 result=dict(summary=summary,protocol=CFG,restoration=restored,regressions=regressions,certificate=certificate,
  balls=balls,windows=windows,proposals=proposals,current_trace=replay(best),acceptance=acceptance,
  limitations="radius3/rank3/one frozen path, not global lower bound; per-state representative not resource Pareto; wrapper calls exclude validation")
 save("round4-results.json",result)
 print(json.dumps(dict(summary=summary,certificate=certificate,cli=cli)),flush=True)
if __name__=="__main__":main()
