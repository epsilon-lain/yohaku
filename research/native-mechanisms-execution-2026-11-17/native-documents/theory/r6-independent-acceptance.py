"""Independent-author fixed-certificate acceptance. No search.
The primitive interpreter is newly authored here: a literal rank2 catalogue,
divide-and-conquer word normal form, explicit Stable insertion/deletion with
real relabelling. It does not call/copy official or application primitive code.
Every interpreted primitive, including fixed guard probes, is metered.
"""
import json,hashlib,os,sys,subprocess,inspect
from pathlib import Path
import meter
from meter import independent_step
sys.path.insert(0,"/project/round2-external")
from restore_resources import restore

OUT=Path("/output")
CFG=json.loads(Path("/project/r6-independent-freeze.json").read_text())
COUNT={"official":0,"independent":0}
CAT=(("I",0),("I",1),("M",0,1,1),("M",0,1,-1),
     ("M",1,0,1),("M",1,0,-1),
     ("C",0,1),("C",0,-1),("C",0,2),("C",0,-2),
     ("C",1,1),("C",1,-1),("C",1,2),("C",1,-2))
def save(n,x):
    (OUT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n")
def state(x):return tuple(tuple(w) for w in x)
def inverse(w):return tuple(-q for q in w[::-1])
def normal(w):
    # Divide in two, normalize halves, then cancel only their joining boundary.
    if len(w)<2:return tuple(w)
    m=len(w)//2
    a,b=normal(w[:m]),normal(w[m:])
    n=0
    while n<min(len(a),len(b)) and a[-1-n]==-b[n]:n+=1
    return a[:len(a)-n]+b[n:]
def well_formed(s,stable_mode):
    assert type(s) is tuple and (len(s)<=8 if stable_mode else len(s)==2)
    for w in s:
        assert type(w) is tuple
        assert all(type(q) is int and q and abs(q)<=len(s) for q in w)
        assert all(a!=-b for a,b in zip(w,w[1:]))
@independent_step
def primitive(s,m,stable_mode):
    COUNT["independent"]+=1
    well_formed(s,stable_mode)
    if type(m) is not int:raise ValueError("integer primitive id required")
    if 0<=m<14:
        op=CAT[m];i=op[1]
        if i>=len(s):raise ValueError("absent relator")
        if op[0]=="I":w=inverse(s[i])
        elif op[0]=="M":
            j,sign=op[2:]
            if j>=len(s):raise ValueError("absent donor")
            donor=s[j] if sign==1 else inverse(s[j])
            w=normal(s[i]+donor)
        else:
            c=op[2]
            if abs(c)>len(s):raise ValueError("absent generator")
            w=normal((c,)+s[i]+(-c,))
        result=tuple(w if p==i else old for p,old in enumerate(s))
    elif stable_mode and m==14:
        if len(s)>=8:raise ValueError("rank cap")
        result=s+((len(s)+1,),)
    elif stable_mode and 15<=m<23:
        i=m-15
        if i>=len(s):raise ValueError("absent deletion slot")
        if len(s[i])!=1 or s[i][0]<1:raise ValueError("positive singleton required")
        g=s[i][0]
        if any(abs(q)==g for p,w in enumerate(s) if p!=i for q in w):
            raise ValueError("deleted generator occurs elsewhere")
        rename={q:(q if q<g else q-1) for q in range(1,len(s)+1) if q!=g}
        result=tuple(tuple(rename[q] if q>0 else -rename[-q] for q in w)
                     for p,w in enumerate(s) if p!=i)
    else:raise ValueError("outside frozen interpreter catalogue")
    well_formed(result,stable_mode)
    return result
def official_step(module,s,m):
    COUNT["official"]+=1
    out=module.apply_move(s,m)
    # Fixed ordinary core returns a state; Stable core returns (state,error).
    if isinstance(out,tuple) and len(out)==2 and (out[1] is None or isinstance(out[1],str)):
        out,err=out
        if err is not None:raise ValueError(err)
    if out is None:raise ValueError("official rejected primitive")
    return state(out)
def check(initial,moves,module,stable_mode):
    assert all(type(m) is int for m in moves)
    assert len(moves)<=CFG["limits"]["max_actions"]
    a=b=initial;aa=[a];bb=[b]
    well_formed(a,stable_mode)
    for m in moves:
        a=official_step(module,a,m)
        b=primitive(b,m,stable_mode)
        assert a==b,("step mismatch",len(aa),m,a,b)
        aa.append(a);bb.append(b)
    lengths=[sum(len(w) for w in s) for s in bb]
    assert max(lengths)<=CFG["limits"]["max_total_length"]
    assert sum(lengths)<=CFG["limits"]["max_work"]
    assert all(len(s)<=CFG["limits"]["max_rank"] for s in bb)
    return {"actions":moves,"official_trace":aa,"independent_trace":bb,
            "lengths":lengths,"ranks":[len(s) for s in bb],
            "signature":[len(moves),sum(lengths),max(lengths)],
            "every_state_equal":True}
def main():
    restored=restore("/output/r6-independent-fixed")
    sys.path.insert(0,restored["acceptance"])
    import validate_candidate as acc
    official=acc.Official(restored["official"])
    package=official.specs.__package__
    core=sys.modules[package+".core"]
    stable=sys.modules[package+".stable_core"]
    assert acc.LOCKED_BASELINES==CFG["baselines"]
    root=Path(restored["official"])
    file_hashes={}
    for row in json.loads(Path("/project/r6-official-source-lock.json").read_text())["files"]:
        q=root/row["path"];h=hashlib.sha256(q.read_bytes()).hexdigest()
        assert h==row["sha256"],row["path"]
        file_hashes[row["path"]]=h
    save("r6-independent-official-source.json",{
         "commit":CFG["official_commit"],"file_hashes":file_hashes,
         "core_apply_move":inspect.getsource(core.apply_move),
         "stable_apply_move":inspect.getsource(stable.apply_move),
         "ordinary_catalogue":getattr(core,"MOVE_TABLE",None),
         "stable_first23":stable.MOVE_TABLE[:23]})
    paths={}
    with meter.verification():
        for cid,moves in CFG["baselines"].items():
            ch=official.challenges[cid];isstable=cid.startswith("sac-")
            module=stable if isstable else core
            result=check(state(ch["initial_relators"]),moves,module,isstable)
            expected_goal=() if isstable else state(ch["target_relators"])
            assert result["independent_trace"][-1]==expected_goal
            verdict=official.verify(ch,moves)
            assert verdict["ok"]
            assert result["signature"]==[verdict["length"],verdict["work"],verdict["peak_total_relator_length"]]
            assert result["signature"]==CFG["expected"][cid]
            result.update(challenge_id=cid,move_spec_version=ch["move_spec_version"],
                          module_file_sha256=file_hashes["competition/tools/verifier/"+("stable_core.py" if isstable else "core.py")],
                          verdict=verdict,goal_exact=True)
            paths[cid]=result
        assert paths["sac-07445"]["official_trace"]==[state(s) for s in CFG["prior"]["trace"]]
        save("r6-independent-paths.json",paths)
        synthetic=check(state(CFG["theory"]["initial"]),CFG["theory"]["actions"],stable,True)
        assert synthetic["independent_trace"][-1]==()
        assert synthetic["signature"]==CFG["theory"]["expected"]
        assert synthetic["lengths"]==CFG["theory"]["expected_lengths"]
        synthetic["not_competition_instance"]=True
        save("r6-independent-theory-certificate.json",synthetic)
        # Fixed unit guard probes only. No search, enumeration or new candidate.
        probes=[]
        good=[(((1,),(2,)),[14,17],((1,),(2,))),
              (((3,-1),(2,),(1,)),[16],((2,-1),(1,))),
              (((2,),(1,)),[16],((1,),))]
        for initial,moves,expected in good:
            r=check(initial,moves,stable,True)
            assert r["independent_trace"][-1]==expected
            probes.append(r)
        bad=[(((1,2,-1),(2,)),16),(((1,),(-2,)),16)]
        for s,m in bad:
            official_bad=independent_bad=False
            try:official_step(stable,s,m)
            except ValueError:official_bad=True
            try:primitive(s,m,True)
            except ValueError:independent_bad=True
            assert official_bad and independent_bad
            probes.append({"initial":s,"action":m,"both_reject":True})
        save("r6-independent-probes.json",probes)
        submission="".join(cid+": "+json.dumps(moves)+"\n" for cid,moves in CFG["baselines"].items())
        (OUT/"r6-independent-submission.txt").write_text(submission)
        env=os.environ.copy()
        env["PYTHONPATH"]=str(root/"competition/tools")+os.pathsep+env.get("PYTHONPATH","")
        argv=[sys.executable,"-B","-m","verifier","--manifest",
              str(root/"competition/tools/verifier/data/manifest.json"),
              "--submission",str(OUT/"r6-independent-submission.txt"),"--pretty"]
        cli=subprocess.run(argv,cwd=root,env=env,capture_output=True,text=True,timeout=20)
        cli_record={"returncode":cli.returncode,"stdout":cli.stdout,"stderr":cli.stderr,
                    "argv":argv,"python_only":True,"trusted_pythonpath_preserved":True}
        save("r6-independent-cli.json",cli_record)
        assert cli.returncode==0 and json.loads(cli.stdout)["accepted"]
        assert [(r["challenge_id"],r["length"],r["work"]) for r in json.loads(cli.stdout)["results"]]==[(c,len(m),CFG["expected"][c][1]) for c,m in CFG["baselines"].items()]
    summary={"format":"r6-independent-author-acceptance/1","status":"passed",
             "official_commit":CFG["official_commit"],"restoration":restored,
             "signatures":{c:p["signature"] for c,p in paths.items()},
             "prior_export_full_trace_equal":True,"cli_accepted":True,
             "theory_synthetic_signature":synthetic["signature"],"fixed_guard_probes":5,
             "local_direct_calls":COUNT,"search":0,"all_primitive_interpretations_decorated":True,
             "limits_checked":CFG["limits"],"platform_upload":False,
             "scope":"Independent fixed-path replay and guards only, not reproduction of search counts/reverse dictionary, no Stable shortestness."}
    save("r6-independent-results.json",summary)
    print(json.dumps(summary),flush=True)
if __name__=="__main__":main()
