## 自主选择与调整原因
用户目标保持严格原始步数改善不变。本节点在v1的完整负结果及08491精确10后，选择本范围；已见开发例，非盲测/宏双臂实验。root提醒的完整资源契约继续采用；没有新增协作者。
## 冻结配置
{
  "format": "native-round2-s07445-prefix3-deeper-bridge-preregistration/1",
  "user_goal_event": 482,
  "user_round": "native-compression-next-20261116-02",
  "autonomous_method": "after v1 negative and Stable08491 exact10 closure, test a deeper completion after the ORIGINAL sac07445 first3 moves",
  "user_goal_is_not_method": true,
  "targets": [
    "sac-08491",
    "sac-07445"
  ],
  "frozen_lengths": {
    "sac-08491": 10,
    "sac-07445": 15
  },
  "rank_cap": 8,
  "reverse": {
    "radius": 6,
    "max_states": 250000,
    "max_calls": 6000000,
    "seconds": 120
  },
  "primary": {
    "challenge": "sac-07445",
    "prefix_index": 3,
    "forward_radius": 5,
    "max_states": 350000,
    "max_calls": 6000000,
    "seconds": 120
  },
  "secondary": {
    "challenge": "sac-07445",
    "prefix_indices": [],
    "forward_radius": 3,
    "max_states_per_ball": 50000,
    "max_calls_per_ball": 750000,
    "seconds_per_ball": 20,
    "total_seconds": 240
  },
  "global": {
    "seconds": 300,
    "max_official_apply_calls": 12000000
  },
  "state_equality": "exact ordered freely reduced relators, no quotient",
  "resource_pruning": "none besides rank<=3; guards explicitly render balls incomplete; full candidates official replay",
  "old_prefix_dictionary": "all prefixes of both locked Stable routes; bound source/target determined by official replay",
  "dictionary_stored_primitive_ids": 175,
  "exposure": "same development routes; this deeper scope is a new explicitly frozen follow-up chosen after prior complete negative, not a hidden retune",
  "comparison": "fixed old15, seek prefix3 + new completion<=11, so total<=14; no global07445 optimality unless future full-source bound",
  "stop": "execute frozen budgets even if no improvement; retain negative and guard outcomes; no platform upload",
  "baselines": {
    "ac-07445": {
      "moves": [
        6,
        4,
        12,
        1,
        3,
        6,
        12,
        2,
        5,
        6,
        4,
        2,
        4
      ],
      "proved_minimum": 13,
      "source_commit": "9afa13603ab26d435d7b5729d057e9b7de9bf8bb",
      "source_sha256": "7544baaa6a188824b9e7538c8a9b6cc2710ccb576d74a8c0809f507bf3771a56",
      "source_url": "https://github.com/epsilon-lain/yohaku/blob/9afa13603ab26d435d7b5729d057e9b7de9bf8bb/research/theory-application-sol-2026-11-16/submission-latest.txt"
    },
    "ac-08491": {
      "moves": [
        7,
        4,
        12,
        12,
        3,
        1,
        5,
        5
      ],
      "proved_minimum": 8,
      "source_commit": "332c001bde009465a1420e4cf6b683ed2ff88cd9",
      "source_sha256": "0114c5aa4bdddd2fd9465c04a677fec7fa24bc60c06992d06a8df1a0318fc215",
      "source_url": "https://github.com/epsilon-lain/yohaku/blob/332c001bde009465a1420e4cf6b683ed2ff88cd9/research/native-theory-application-2026-11-16/data/ac-submission.txt"
    },
    "sac-07445": {
      "moves": [
        6,
        4,
        12,
        1,
        3,
        6,
        12,
        2,
        5,
        6,
        4,
        2,
        4,
        16,
        15
      ],
      "proved_minimum": null,
      "source_commit": "9afa13603ab26d435d7b5729d057e9b7de9bf8bb",
      "source_sha256": "7544baaa6a188824b9e7538c8a9b6cc2710ccb576d74a8c0809f507bf3771a56",
      "source_url": "https://github.com/epsilon-lain/yohaku/blob/9afa13603ab26d435d7b5729d057e9b7de9bf8bb/research/theory-application-sol-2026-11-16/submission-latest.txt"
    },
    "sac-08491": {
      "moves": [
        7,
        4,
        12,
        1,
        12,
        2,
        5,
        5,
        16,
        15
      ],
      "proved_minimum": null,
      "source_commit": "9afa13603ab26d435d7b5729d057e9b7de9bf8bb",
      "source_sha256": "7544baaa6a188824b9e7538c8a9b6cc2710ccb576d74a8c0809f507bf3771a56",
      "source_url": "https://github.com/epsilon-lain/yohaku/blob/9afa13603ab26d435d7b5729d057e9b7de9bf8bb/research/theory-application-sol-2026-11-16/submission-latest.txt"
    }
  }
}
## 完整原生源码
"""New real bounded Stable AC bridge search. Not package/self-test research.
Frozen rank<=8 graph; no quotient. All resulting full paths use pinned official validation.
"""
import hashlib, json, os, subprocess, sys, time
from collections import Counter
from pathlib import Path
sys.path.insert(0,"/project/round2-external")
from restore_resources import restore
OUT=Path("/output")
CFG=json.loads(Path("/project/round2_s07445_protocol.json").read_text())
STARTED=time.monotonic()
CALLS=0
class Guard(Exception): pass

def dump(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n")

def main():
    global CALLS
    restored=restore("/output/fixed")
    sys.path.insert(0,restored["acceptance"])
    import validate_candidate as acceptance
    official=acceptance.Official(restored["official"])
    stable=sys.modules[official.specs.__package__+".stable_core"]
    rank_cap=CFG["rank_cap"]
    def call(s,m):
        global CALLS
        CALLS+=1
        if CALLS>CFG["global"]["max_official_apply_calls"]:
            raise Guard("global_apply_budget")
        if CALLS%1024==0 and time.monotonic()-STARTED>CFG["global"]["seconds"]:
            raise Guard("global_wall_budget")
        return stable.apply_move(s,m)
    rows=stable.MOVE_TABLE
    normal={}
    forward={}
    for k in range(rank_cap+1):
        normal[k]=[r for r in rows if r["category"] not in ("stabilize","destabilize")
                   and r["relator"]<k and
                   (r["category"]!="multiplication" or r["other"]<k) and
                   (r["category"]!="conjugation" or abs(r["conjugator"])<=k)]
        forward[k]=normal[k]+[r for r in rows if r["category"]=="destabilize" and r["relator"]<k]
        if k<rank_cap:
            forward[k].append(rows[14])
        forward[k].sort(key=lambda r:r["id"])
    def next_edges(s):
        for row in forward[len(s)]:
            t,reason=call(s,row["id"])
            if reason is None:
                yield t,row["id"]
    def previous_edges(s):
        k=len(s)
        for row in normal[k]:
            prev,reason=call(s,row["inverse"])
            assert reason is None
            # Source/target checks remain explicit even for fixed inverse rows.
            check,reason=call(prev,row["id"])
            assert reason is None and check==s
            yield prev,row["id"]
        # All inverse destabilizations: independently choose inserted generator
        # label g and inserted relator position i. This is NOT a state quotient.
        if k<rank_cap:
            for g in range(1,k+2):
                shifted=tuple(tuple((1 if a>0 else -1)*(abs(a)+(abs(a)>=g)) for a in w) for w in s)
                for i in range(k+1):
                    prev=shifted[:i]+((g,),)+shifted[i:]
                    check,reason=call(prev,15+i)
                    assert reason is None and check==s
                    yield prev,15+i
        # The sole inverse of forward stabilization at this exact ordered state.
        if k and s[-1]==(k,) and all(abs(a)<k for w in s[:-1] for a in w):
            prev=s[:-1]
            check,reason=call(prev,14)
            assert reason is None and check==s
            yield prev,14
    def ball(source,radius,budget,reverse=False,label=""):
        start=time.monotonic()
        before=CALLS
        seen={source:()}
        layer=[source]
        sizes=[1]
        complete=True
        reason=None
        completed_layers=0
        peak=sum(map(len,source))
        def check():
            if CALLS-before>budget["max_calls"]:raise Guard("ball_apply_budget")
            if time.monotonic()-start>budget["seconds"]:raise Guard("ball_wall_budget")
        try:
            for depth in range(radius):
                nxt=[]
                for s in layer:
                    check()
                    edges=previous_edges(s) if reverse else next_edges(s)
                    for t,m in edges:
                        check()
                        peak=max(peak,sum(map(len,t)))
                        if t not in seen:
                            if len(seen)>=budget["max_states"]:raise Guard("ball_state_budget")
                            seen[t]=(m,)+seen[s] if reverse else seen[s]+(m,)
                            nxt.append(t)
                layer=nxt
                sizes.append(len(layer))
                completed_layers=depth+1
        except Guard as error:
            complete=False
            reason=str(error)
        meta=dict(label=label,radius=radius,reverse=reverse,states=len(seen),
                  completed_layers=completed_layers,completed_layer_sizes=sizes,
                  complete_radius=complete,guard_reason=reason,
                  official_apply_calls=CALLS-before,seconds=time.monotonic()-start,
                  maximum_generated_total_length=peak,rank_cap=rank_cap,
                  quotient=False,resource_length_pruning=False,states_sha256=hashlib.sha256(json.dumps(sorted(seen),separators=(",",":")).encode("ascii")).hexdigest())
        print(json.dumps(meta),flush=True)
        return seen,meta
    def trajectory(challenge,moves):
        state=tuple(map(tuple,challenge["initial_relators"]))
        states=[state]
        for m in moves:
            state,reason=stable.apply_move(state,m)
            assert reason is None
            states.append(state)
        lengths=[sum(map(len,s)) for s in states]
        return dict(states=states,lengths=lengths,peak=max(lengths),work=sum(lengths))
    locked=CFG["baselines"]
    baseline_verdicts={}
    starts={}
    old_traces={}
    best={}
    best_recipe={}
    accepted_proposals=[]
    for cid,entry in locked.items():
        challenge=official.challenges[cid]
        verdict=official.verify(challenge,entry["moves"])
        assert verdict["ok"]
        baseline_verdicts[cid]=verdict
        if cid.startswith("sac-"):
            starts[cid]=tuple(map(tuple,challenge["initial_relators"]))
            old_traces[cid]=trajectory(challenge,entry["moves"])
            best[cid]=tuple(entry["moves"])
            best_recipe[cid]=dict(kind="unchanged_locked_baseline")
    prefix_dictionary=[dict(name=cid+"-P"+str(i),challenge=cid,expanded=locked[cid]["moves"][:i],
        source=starts[cid],target=old_traces[cid]["states"][i])
        for cid in CFG["targets"] for i in range(1,len(locked[cid]["moves"])+1)]
    assert sum(len(x["expanded"])for x in prefix_dictionary)==CFG["dictionary_stored_primitive_ids"]
    dump("r2deep-prefix-dictionary.json",prefix_dictionary)
    def propose(cid,prefix,forward_seen,reverse_seen,label):
        common=forward_seen.keys() & reverse_seen.keys()
        candidates=sorted((len(prefix)+len(forward_seen[s])+len(reverse_seen[s]),
                           prefix+forward_seen[s]+reverse_seen[s],s) for s in common)
        hits=[]
        for length,path,junction in candidates:
            if length>=len(locked[cid]["moves"]):continue
            verdict=official.verify(official.challenges[cid],list(path))
            recipe=dict(label=label,prefix=prefix,bridge=forward_seen[junction],
                        completion=reverse_seen[junction],junction=junction,
                        proposed_length=length,official_verdict=verdict)
            accepted_proposals.append(recipe)
            if verdict["ok"]:
                hits.append(recipe)
                if (length,path)<(len(best[cid]),best[cid]):
                    best[cid]=path
                    best_recipe[cid]=recipe
                break
        return dict(label=label,intersections=len(common),strict_legal_hits=len(hits))
    rev,rm=ball((),CFG["reverse"]["radius"],CFG["reverse"],reverse=True,label="shared-empty-completion")
    p=CFG["primary"]
    fixed_prefix=tuple(locked[p["challenge"]]["moves"][:p["prefix_index"]])
    fixed_start=old_traces[p["challenge"]]["states"][p["prefix_index"]]
    f,fm=ball(fixed_start,p["forward_radius"],p,label="sac07445-locked-prefix3-forward5")
    primary_join=propose(p["challenge"],fixed_prefix,f,rev,"prefix3-plus5plus6")
    # A directed rank-capped graph statement, only when BOTH balls completed.
    negative_complete=(rm["complete_radius"] and fm["complete_radius"] and
                       not(f.keys() & rev.keys()))
    secondary=[]
    secondary_start=time.monotonic()
    sec=CFG["secondary"]
    cid=sec["challenge"]
    for i in sec["prefix_indices"]:
        if time.monotonic()-secondary_start>sec["total_seconds"]:
            secondary.append(dict(prefix_index=i,executed=False,reason="secondary_global_wall_budget"))
            continue
        budget=dict(max_states=sec["max_states_per_ball"],max_calls=sec["max_calls_per_ball"],seconds=sec["seconds_per_ball"])
        # Prefix is from the ORIGINAL locked path, never adaptively updated.
        prefix=tuple(locked[cid]["moves"][:i])
        source=old_traces[cid]["states"][i]
        radius=min(sec["forward_radius"],len(locked[cid]["moves"])-1-i)
        seen,meta=ball(source,radius,budget,label="sac07445-prefix-"+str(i))
        join=propose(cid,prefix,seen,rev,"secondary-prefix-"+str(i))
        secondary.append(dict(prefix_index=i,executed=True,forward=meta,join=join))
    # External acceptance expands each full recipe and replays ALL intermediate
    # states/resource limits with exactly the same fixed official implementation.
    registry=(Path(restored["acceptance"])/"baselines.json").read_bytes()
    candidate_results={}
    for cid in CFG["targets"]:
        recipe=best_recipe[cid]
        path=list(best[cid])
        # Literal candidate is also the submit-ready primitive expansion.
        candidate=dict(challenge_id=cid,tokens=path,macros={})
        raw=json.dumps(candidate,separators=(",",":")).encode()
        result=acceptance.validate(raw,registry,official)
        assert result["official_verdict"]["ok"]
        assert result["lengths"]["expanded_primitive_length"]==len(path)
        candidate_results[cid]=dict(candidate=candidate,acceptance=result,
                                  recipe=recipe,trajectory=trajectory(official.challenges[cid],path))
    # Actual pinned official submission parser and CLI, not just a custom replay.
    submission="\n".join(cid+": "+json.dumps(list(best[cid]) if cid in best else entry["moves"])
                         for cid,entry in locked.items())+"\n"
    (OUT/"r2deep-submission.txt").write_text(submission)
    env=dict(os.environ,PYTHONPATH=str(Path(restored["official"])/"competition/tools"))
    args=[sys.executable,"-B","-m","verifier","--manifest",
          str(Path(restored["official"])/"competition/tools/verifier/data/manifest.json"),
          "--submission",str(OUT/"r2deep-submission.txt"),"--pretty"]
    run=subprocess.run(args,cwd=restored["official"],env=env,capture_output=True,text=True,timeout=30)
    cli=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr)
    try:cli["parsed_verdict"]=json.loads(run.stdout)
    except json.JSONDecodeError:cli["parsed_verdict"]=None
    assert run.returncode==0 and cli["parsed_verdict"]["accepted"]
    dump("r2deep-official-cli.json",cli)
    result=dict(format="native-round2-stable-prefix-bridge-results/1",status="completed_frozen_experiment",
        protocol=CFG,restore_receipt=restored,source_fingerprints=official.fingerprints,
        baseline_official_verdicts=baseline_verdicts,
        reverse_ball=rm,primary_forward=fm,primary_join=primary_join,
        no_completion_le11_after_locked_prefix3_if_complete=negative_complete,
        conditional_negative_scope="Full official rank<=8 graph, but source is the frozen prefix3 endpoint. Empty complete5/6 intersection only excludes a <=11 completion after that fixed prefix; not all <=14 paths from original source.",
        secondary=secondary,strict_proposals=accepted_proposals,candidates=candidate_results,
        strict_improvements={cid:len(best[cid]) for cid in best if len(best[cid])<len(locked[cid]["moves"])},
        best_lengths={cid:len(p)for cid,p in best.items()},
        official_apply_calls_search=CALLS,elapsed_seconds=time.monotonic()-STARTED,
        dictionary_build_cost=dict(stored_primitive_ids=175,reverse_build_calls=rm["official_apply_calls"]),
        causal_macro_gain_comparison=False,held_out_evaluation=False,platform_upload=False,
        actual_adopted_math=[{"id":"external/native-compression-next-20261116-02-resources","revision":1},
                            {"id":"M-5606eba96406db45","revision":1}],
        limitations="Fixed development instances, rank cap3, explicit ball/time/call/state guards, no leaderboard query. Token/work gains are not step gains.")
    dump("r2deep-search-results.json",result)
    print(json.dumps({k:result[k]for k in ["status","best_lengths","strict_improvements",
        "official_apply_calls_search","elapsed_seconds","no_completion_le11_after_locked_prefix3_if_complete"]}),flush=True)
    print(json.dumps(dict(official_cli_returncode=run.returncode,
        official_cli_verdict=cli["parsed_verdict"])),flush=True)

if __name__=="__main__":main()

