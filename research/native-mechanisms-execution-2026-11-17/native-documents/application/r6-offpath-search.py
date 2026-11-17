"""Frozen R6 Stable off-path structural beam. No unmetered primitive interpreter.
Prepared only: execution requires the native task_submit budget argument bridge.
All official apply calls are metered by trusted runtime. Independent interpreter
uses @independent_step for EVERY primitive; it is a separate implementation but
same author, not an independent-author mathematical review.
"""
import hashlib,json,os,subprocess,sys,time
from collections import defaultdict,deque
from pathlib import Path
import meter
from meter import independent_step
sys.path.insert(0,"/project/round2-external")
from restore_resources import restore
OUT=Path("/output")
CFG=json.loads(Path("/project/r6-protocol.json").read_text())
def save(name,x): (OUT/name).write_text(json.dumps(x,indent=2)+"\n")
def size(s): return sum(map(len,s))
def inverse(w): return tuple(-a for a in reversed(w))
def reduce_independent(w):
 # Repeated adjacent-pair erasure, deliberately not the official stack reducer.
 z=list(w);j=0
 while j+1<len(z):
  if z[j]==-z[j+1]:
   del z[j:j+2];j=max(0,j-1)
  else:j+=1
 return tuple(z)
@independent_step
def independent_apply(s,m,table):
 if type(m) is not int or not 0<=m<len(table):raise ValueError("bad id")
 r=table[m];c=r["category"];k=len(s)
 if c=="stabilize":
  if k==8:raise ValueError("max rank")
  return s+((k+1,),)
 i=r["relator"]
 if i>=k:raise ValueError("relator rank")
 if c=="destabilize":
  if len(s[i])!=1 or s[i][0]<=0:raise ValueError("not positive singleton")
  g=s[i][0]
  if any(abs(a)==g for j,w in enumerate(s) if j!=i for a in w):raise ValueError("generator still used")
  return tuple(tuple((1 if a>0 else -1)*(abs(a)-(abs(a)>g)) for a in w) for j,w in enumerate(s) if j!=i)
 if c=="inversion":new=inverse(s[i])
 elif c=="multiplication":
  j=r["other"]
  if j>=k:raise ValueError("donor rank")
  donor=inverse(s[j]) if r["invert_other"] else s[j]
  new=reduce_independent(s[i]+donor)
 elif c=="conjugation":
  a=r["conjugator"]
  if abs(a)>k:raise ValueError("generator rank")
  new=reduce_independent((a,)+s[i]+(-a,))
 else:raise ValueError("unknown category")
 return s[:i]+(new,)+s[i+1:]
class Guard(Exception):pass
def main():
 restored=restore("/output/r6-fixed")
 sys.path.insert(0,restored["acceptance"])
 import validate_candidate as acc
 official=acc.Official(restored["official"])
 stable=sys.modules[official.specs.__package__+".stable_core"]
 sha=hashlib.sha256(Path(stable.__file__).read_bytes()).hexdigest()
 assert sha=="234b164c766bf7fd2e1bee7f7bfb3910319c5885e4250bf56520d2d2b0f46e9d"
 table=stable.MOVE_TABLE
 ch=official.challenges[CFG["challenge"]]
 initial=tuple(map(tuple,ch["initial_relators"]))
 baseline=tuple(CFG["baseline"]);best=baseline;winner=None
 normal={};forward={}
 for k in range(CFG["rank_cap"]+1):
  normal[k]=[r for r in table if r["category"] not in ("stabilize","destabilize") and r["relator"]<k and (r["category"]!="multiplication" or r["other"]<k) and (r["category"]!="conjugation" or abs(r["conjugator"])<=k)]
  forward[k]=normal[k]+[r for r in table if r["category"]=="destabilize" and r["relator"]<k]
  if k<CFG["rank_cap"]:forward[k].append(table[14])
  forward[k].sort(key=lambda r:r["id"])
 counts=dict(search_apply_calls=0,reverse_apply_calls=0,forward_apply_calls=0,joins=0,candidate_checks=0,illegal=0,length_pruned=0,beam_discard_events=0)
 started=time.monotonic();guard=None;layers=[];reverse_meta={}
 def call(s,m,phase):
  if counts["search_apply_calls"]>=CFG["guards"]["search_apply_calls"]:raise Guard("search_apply_calls")
  if time.monotonic()-started>CFG["guards"]["search_wall_seconds"]:raise Guard("search_wall_seconds")
  counts["search_apply_calls"]+=1;counts[phase+"_apply_calls"]+=1
  return stable.apply_move(s,m)
 def previous(s):
  k=len(s)
  for r in normal[k]:
   t,err=call(s,r["inverse"],"reverse")
   assert err is None
   yield t,r["id"]
  if k<CFG["rank_cap"]:
   # All (generator-label, ordered-relator-position) insertions are distinct
   # candidates; do not quotient by names or permutations.
   for g in range(1,k+2):
    shifted=tuple(tuple((1 if a>0 else -1)*(abs(a)+(abs(a)>=g)) for a in w) for w in s)
    for i in range(k+1):
     t=shifted[:i]+((g,),)+shifted[i:]
     check,err=call(t,15+i,"reverse");assert err is None and check==s
     yield t,15+i
  if k and s[-1]==(k,) and all(abs(a)<k for w in s[:-1] for a in w):
   t=s[:-1];check,err=call(t,14,"reverse");assert err is None and check==s
   yield t,14
 def verification_context():
  v=meter.verification
  return v() if callable(v) else v
 def replay(path):
  with verification_context():
   states=[initial]
   for m in path:
    t,err=stable.apply_move(states[-1],m)
    assert err is None;states.append(t)
   verdict=official.verify(ch,list(path))
  assert verdict["ok"]
  indep=[initial]
  for m,t in zip(path,states[1:]):
   u=independent_apply(indep[-1],m,table);assert u==t;indep.append(u)
  lengths=list(map(size,indep))
  assert indep[-1]==() and len(path)<=100000 and max(lengths)<=10000 and sum(lengths)<=5000000 and all(len(s)<=8 for s in indep)
  assert (len(path),max(lengths),sum(lengths))==tuple(verdict[k] for k in ("length","peak_total_relator_length","work"))
  return dict(path=path,trace=states,independent_trace=indep,verdict=verdict)
 baseline_check=replay(baseline)
 assert all(baseline_check["verdict"][k]==v for k,v in CFG["baseline_signature"].items())
 reverse={():()};front=[()];reverse_sizes=[1]
 def checkpoint():
  save("r6-checkpoint.json",dict(counts=counts,layers=layers,reverse_meta=reverse_meta,best=best,guard=guard,winner=winner))
 def phi(s):
  k=len(s)
  return tuple(tuple(sum((1 if a>0 else -1) for a in w if abs(a)==g) for g in range(1,k+1)) for w in s)
 def deletable(s):
  return sum(len(w)==1 and w[0]>0 and not any(abs(a)==w[0] for j,v in enumerate(s) if j!=i for a in v) for i,w in enumerate(s))
 def key(s):return (phi(s),tuple(w[0] if len(w)==1 else 0 for w in s))
 def score(s,record):return (-deletable(s),size(s),sum(abs(a) for row in phi(s) for a in row),record[1],record[0])
 try:
  for d in range(CFG["reverse_radius"]):
   nxt=[]
   for s in front:
    for t,m in previous(s):
     if size(t)>CFG["max_generated_total_length"]:counts["length_pruned"]+=1;continue
     if t not in reverse:
      if len(reverse)>=CFG["guards"]["reverse_states"]:raise Guard("reverse_states")
      reverse[t]=(m,)+reverse[s];nxt.append(t)
   front=nxt;reverse_sizes.append(len(front))
  reverse_meta=dict(states=len(reverse),layer_sizes=reverse_sizes,complete_bounded_radius=True,rank_cap=CFG["rank_cap"],length_cap=CFG["max_generated_total_length"])
  beam={initial:((),size(initial))}
  for d in range(1,CFG["forward_depth"]+1):
   candidates={}
   for s,(prefix,work) in sorted(beam.items()):
    for r in forward[len(s)]:
     t,err=call(s,r["id"],"forward")
     if err is not None:counts["illegal"]+=1;continue
     if size(t)>CFG["max_generated_total_length"]:counts["length_pruned"]+=1;continue
     p=prefix+(r["id"],);rec=(p,work+size(t))
     if t in reverse and len(p)+len(reverse[t])<len(best):
      counts["joins"]+=1
      if counts["candidate_checks"]>=CFG["guards"]["candidate_verifications"]:raise Guard("candidate_verifications")
      counts["candidate_checks"]+=1
      candidate=replay(p+reverse[t]);best=p+reverse[t];winner=candidate
      break
     if t not in candidates or (rec[1],rec[0])<(candidates[t][1],candidates[t][0]):candidates[t]=rec
    if winner is not None:break
   if winner is not None:break
   selected={};rank_counts={};bucket_counts={}
   for k in range(CFG["rank_cap"]+1):
    buckets=defaultdict(list)
    for s,rec in candidates.items():
     if len(s)==k:buckets[key(s)].append((score(s,rec),s,rec))
    queues=[]
    for group in buckets.values():
     group.sort();queues.append(deque(group))
    queues.sort(key=lambda q:q[0][0])
    taken=0
    while queues and taken<CFG["beam_width_per_rank"]:
     nextq=[]
     for q in queues:
      if taken>=CFG["beam_width_per_rank"]:break
      _,s,rec=q.popleft();selected[s]=rec;taken+=1
      if q:nextq.append(q)
     queues=nextq
    rank_counts[k]=taken;bucket_counts[k]=len(buckets)
   discard=len(candidates)-len(selected);counts["beam_discard_events"]+=discard
   layers.append(dict(depth=d,candidates=len(candidates),retained=len(selected),discarded=discard,rank_counts=rank_counts,buckets=bucket_counts))
   beam=selected;checkpoint()
   if not beam:break
 except Guard as e:guard=str(e)
 if not reverse_meta:reverse_meta=dict(states=len(reverse),layer_sizes=reverse_sizes,complete_bounded_radius=False)
 checkpoint()
 final_check=winner if winner is not None else baseline_check
 # Freeze complete candidate before the actual official CLI invocation.
 save("r6-candidate.json",dict(challenge_id=CFG["challenge"],tokens=best,macros={}))
 save("r6-full-path.json",final_check)
 submission="\n".join(cid+": "+json.dumps(list(best) if cid==CFG["challenge"] else path) for cid,path in acc.LOCKED_BASELINES.items())+"\n"
 (OUT/"r6-submission.txt").write_text(submission)
 env=dict(os.environ,PYTHONPATH=str(Path(restored["official"])/"competition/tools")+os.pathsep+os.environ.get("PYTHONPATH",""))
 cmd=[sys.executable,"-B","-m","verifier","--manifest",str(Path(restored["official"])/"competition/tools/verifier/data/manifest.json"),"--submission",str(OUT/"r6-submission.txt"),"--pretty"]
 run=subprocess.run(cmd,cwd=restored["official"],env=env,capture_output=True,text=True,timeout=20)
 cli=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr);save("r6-cli.json",cli)
 assert run.returncode==0 and json.loads(run.stdout)["accepted"]
 reverse_rows=[dict(state=s,completion=reverse[s]) for s in sorted(reverse)]
 save("r6-reverse.json",reverse_rows)
 summary=dict(best_length=len(best),strict_improvement=len(best)<15,winner=winner is not None,guard=guard,reverse=reverse_meta,layers=layers,counts=counts,elapsed_seconds=time.monotonic()-started,global_complete=False,platform_upload=False)
 save("r6-results.json",dict(summary=summary,protocol=CFG,restoration=restored,stable_source_sha256=sha,final_path_artifact="r6-full-path.json",limitations="Finite deterministic beam; dropping any state defeats exhaustive negative conclusions. Rank<=3 and total-length<=96 are additional search restrictions. Independent interpreter is same-author, not independent-author review. Native trusted ledger, not wrapper counts, governs total charges including verification and Python CLI subprocess. No improvement is not 15-minimality."))
 print(json.dumps(summary),flush=True)
if __name__=="__main__":main()
