"""Native round3: pair-AND fibers, target auxiliary messages, coordinate queries.
General proof M-a85fc42f1e3e61a9@1; prior M-98718cbca95c0dc3@1.
Complete bounded enumeration is supporting evidence, not arbitrary-n proof.
"""
from collections import defaultdict
from functools import lru_cache
from itertools import combinations
from pathlib import Path
import hashlib
import json
import time

ROOT=Path(__file__).resolve().parent
FROZEN_BYTES=(ROOT/"round3-pair-freeze.json").read_bytes()
CFG=json.loads(FROZEN_BYTES)

def subsets(mask):
    s=mask
    while True:
        yield s
        if s==0:
            break
        s=(s-1)&mask

def observed(X,edges,H):
    F=0
    for e,(u,v) in enumerate(edges):
        if H&(1<<e) and X&(1<<u) and X&(1<<v):
            F|=1<<e
    return F

def structure(n,edges,H,F):
    P=0
    for e,(u,v) in enumerate(edges):
        if F&(1<<e):
            P|=(1<<u)|(1<<v)
    valid=(observed(P,edges,H)==F)
    Z=0
    for e,(u,v) in enumerate(edges):
        if H&(1<<e):
            if P&(1<<u): Z|=1<<v
            if P&(1<<v): Z|=1<<u
    Z &= ~P
    R=((1<<n)-1)&~(P|Z)
    return valid,P,Z,R

def query_solver(n,S,kind):
    labels=[(X&S) if kind=="pattern" else (X&S).bit_count() for X in range(1<<n)]
    one_masks=[sum(1<<X for X in range(1<<n) if X&(1<<i)) for i in range(n)]
    @lru_cache(None)
    def solve(C):
        xs=[X for X in range(1<<n) if C&(1<<X)]
        if len({labels[X] for X in xs})<=1:
            return 0
        best=n+1
        for one in one_masks:
            yes=C&one
            no=C&~one
            if yes and no:
                best=min(best,1+max(solve(yes),solve(no)))
        assert best<=n
        return best
    return solve

def analyze_graph(n,H):
    edges=list(combinations(range(n),2))
    full=(1<<n)-1
    fibers=defaultdict(list)
    for X in range(1<<n):
        fibers[observed(X,edges,H)].append(X)
    independent=fibers[0]
    i_table=[]
    alpha_table=[]
    for S in range(1<<n):
        projected=[I for I in independent if I&~S==0]
        i_table.append(len(projected))
        alpha_table.append(max(I.bit_count() for I in projected))
    b_pattern=[(a-1).bit_length() for a in i_table]
    b_weight=[a.bit_length() for a in alpha_table]
    max_patterns=[0]*(1<<n)
    max_weights=[0]*(1<<n)
    observed_cases=0
    target_fiber_cases=0
    codec_replays=0
    certificates=[]
    actual_query_calls=0
    worst_queries={kind:[0]*(1<<n) for kind in ("pattern","weight")}
    solvers={}
    if n<=CFG["query_dp_n_max"]:
        solvers={(S,kind):query_solver(n,S,kind)
                 for S in range(1<<n) for kind in ("pattern","weight")}
    for F in subsets(H):
        observed_cases+=1
        valid,P,Z,R=structure(n,edges,H,F)
        actual=fibers.get(F,[])
        assert valid==bool(actual),(n,H,F)
        if not valid:
            continue
        predicted=sorted(P|I for I in subsets(R) if observed(I,edges,H)==0)
        assert sorted(actual)==predicted,(n,H,F)
        assert len(actual)==i_table[R]
        C=sum(1<<X for X in actual)
        for S in range(1<<n):
            target_fiber_cases+=1
            A=R&S
            pats=sorted({X&S for X in actual})
            js=sorted(I for I in subsets(A) if observed(I,edges,H)==0)
            expected=sorted((P&S)|J for J in js)
            assert pats==expected and len(pats)==i_table[A]
            weights=sorted({(X&S).bit_count() for X in actual})
            expected_weights=list(range((P&S).bit_count(),(P&S).bit_count()+alpha_table[A]+1))
            assert weights==expected_weights
            assert (len(pats)==1)==(A==0)
            assert (len(weights)==1)==(A==0)
            max_patterns[S]=max(max_patterns[S],len(pats))
            max_weights[S]=max(max_weights[S],len(weights))
            ranks={p:i for i,p in enumerate(pats)}
            for X in actual:
                # An actual finite encoder/decoder replay, not just cardinality.
                msg=ranks[X&S]
                assert msg < (1<<b_pattern[S])
                assert pats[msg]==X&S
                wmsg=(X&S).bit_count()-(P&S).bit_count()
                assert wmsg < (1<<b_weight[S])
                assert wmsg+(P&S).bit_count()==(X&S).bit_count()
                codec_replays+=1
            if solvers:
                for kind in ("pattern","weight"):
                    queries=solvers[S,kind](C)
                    assert queries <= S.bit_count()
                    # Pointwise strengthening follows by the same singleton argument.
                    assert queries==A.bit_count()
                    if F==0:
                        assert queries==S.bit_count()
                    worst_queries[kind][S]=max(worst_queries[kind][S],queries)
                    actual_query_calls+=1
        certificates.append({"F":F,"P":P,"Z":Z,"R":R,"all_original_objects":actual})
    for S in range(1<<n):
        assert max_patterns[S]==i_table[S]
        assert max_weights[S]==alpha_table[S]+1
        if solvers:
            assert worst_queries["pattern"][S]==S.bit_count()
            assert worst_queries["weight"][S]==S.bit_count()
    return {"n":n,"H":H,"edge_index":edges,"object_count":1<<n,
        "output_subsets_examined":observed_cases,
        "realizable_outputs":len(certificates),
        "target_fiber_cases":target_fiber_cases,
        "codec_replays":codec_replays,"query_DP_instances":actual_query_calls,
        "independent_set_count_by_target":i_table,"alpha_by_target":alpha_table,
        "minimum_pattern_aux_bits":b_pattern,"minimum_weight_aux_bits":b_weight,
        "worst_coordinate_queries":worst_queries if solvers else None,
        "all_fibers":certificates}

def main():
    start=time.monotonic()
    all_rows=[]
    sizes=[]
    for n in CFG["graphs_n"]:
        edges=list(combinations(range(n),2))
        rows=[analyze_graph(n,H) for H in range(1<<len(edges))]
        all_rows.extend(rows)
        summary={"n":n,"graphs":len(rows)}
        for key in ["object_count","output_subsets_examined","realizable_outputs",
                    "target_fiber_cases","codec_replays","query_DP_instances"]:
            summary[key]=sum(r[key] for r in rows)
        sizes.append(summary)
        print(json.dumps(summary),flush=True)
    clique_rows=[r for r in all_rows if r["H"]==(1<<len(r["edge_index"]))-1]
    clique_examples=[]
    for r in clique_rows:
        n=r["n"]
        assert r["independent_set_count_by_target"][-1]==n+1
        assert r["minimum_pattern_aux_bits"][-1]==n.bit_length()
        assert r["minimum_weight_aux_bits"][-1]==1
        clique_examples.append({"n":n,"object_aux_bits":n.bit_length(),
            "weight_aux_bits":1,"proved_worst_coordinate_queries":n})
    result={"format":"native-round3-pair-inverse-results/1",
        "proof_dependency":{"id":"M-a85fc42f1e3e61a9","revision":1},
        "prior_dependency":{"id":"M-98718cbca95c0dc3","revision":1},
        "frozen_configuration":CFG,
        "freeze_sha256":hashlib.sha256(FROZEN_BYTES).hexdigest(),
        "code_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope":"all labelled graphs n1..5, all objects/output subsets/target subsets; adaptive query DP for every realizable fiber and target only n1..4",
        "same_author_methods_not_peer_review":True,
        "size_summaries":sizes,"clique_examples":clique_examples,"graphs":all_rows,
        "elapsed_seconds":time.monotonic()-start,"all_assertions_passed":True}
    Path("/output/round3-pair-inverse-results.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":"passed","clique_examples":clique_examples,
        "elapsed_seconds":result["elapsed_seconds"]}),flush=True)

if __name__=="__main__":
    main()
