#!/usr/bin/env python3
"""NEW EXTERNAL REVIEW, not native-round2 completion. Python stdlib only.

No uploaded research code is imported or executed. The only executed external
code is a complete SHA256/Git-blob-checked fixed official verifier checkout.
All 257 IDs are attempted at every forward expansion; own move interpreter,
own action table, own reduction, and an order-embedding inverse-destabilize.
Run: python independent_stable_verifier.py --official-checkout /path/to/official-checkout
"""
import argparse
import hashlib
import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

CAP = 5
START = ((-2, -1), (-2, -2, -1, -1, 2, 2, 1))
WITNESS = [7, 4, 12, 1, 12, 2, 5, 5, 16, 15]
EXPECTED = {
    'forward': ([1,14,160,1910,26426], '5036eb3bd6769068e0fa0f73ec2252fe6b932b85942c87ab474bf5dd7df73cd5'),
    'reverse': ([1,1,3,26,340,5710], 'a00fe597b1afe1a6ec3df7083fad09e30873d1ba7827b012c99988f13ffe60d3'),
}

def digest(b):
    return hashlib.sha256(b).hexdigest()

def compact(value):
    return json.dumps(value, separators=(',', ':')).encode('ascii')

def verify_official(directory):
    # Lock is shipped with this NEW review, not read from the checkout under test.
    provenance = json.loads((Path(__file__).parent/'official-source-lock.json').read_text())
    assert provenance['commit'] == 'a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e'
    receipts = []
    for row in provenance['files']:
        data = (directory/row['path']).read_bytes()
        assert digest(data) == row['sha256'], row['path']
        blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        assert blob == row['git_blob'], row['path']
        receipts.append(dict(path=row['path'], sha256=digest(data), git_blob=blob))
    assert len(receipts) == 30
    return receipts

def actions():
    # Independent representation: op, target slot, auxiliary slot/letter, sign.
    out = [('I',0,0,0), ('I',1,0,0), ('M',0,1,1), ('M',0,1,-1),
           ('M',1,0,1), ('M',1,0,-1)]
    out += [('C',i,g,0) for i in range(2) for g in (1,-1,2,-2)]
    out += [('S',0,0,0)] + [('D',i,0,0) for i in range(8)]
    out += [('I',i,0,0) for i in range(2,8)]
    out += [('M',i,j,sgn) for i in range(8) for j in range(8)
            if i != j and not (i < 2 and j < 2) for sgn in (1,-1)]
    out += [('C',i,sgn*g,0) for i in range(8) for g in range(1,9)
            if not (i < 2 and g < 3) for sgn in (1,-1)]
    assert len(out) == len(set(out)) == 257
    return out

ACTIONS = actions()
LOOKUP = {a:i for i,a in enumerate(ACTIONS)}

def inverse_id(mid):
    op,i,j,sgn = ACTIONS[mid]
    if op == 'I': return mid
    if op == 'M': return LOOKUP[(op,i,j,-sgn)]
    if op == 'C': return LOOKUP[(op,i,-j,sgn)]
    return None

def inv(word):
    return tuple(-a for a in word[::-1])

def reduced(word):
    # Repeated adjacent cancellation rather than author's official stack fold.
    word = list(word)
    p = 0
    while p+1 < len(word):
        if word[p] == -word[p+1]:
            del word[p:p+2]
            p = max(0, p-1)
        else:
            p += 1
    return tuple(word)

def own_apply(state, mid):
    op,i,j,sgn = ACTIONS[mid]
    k = len(state)
    if op == 'S': return state+((k+1,),) if k<8 else None
    if i>=k: return None
    if op == 'D':
        if len(state[i]) != 1 or state[i][0] < 1: return None
        g = state[i][0]
        rest = state[:i]+state[i+1:]
        if any(abs(a)==g for w in rest for a in w): return None
        labels = {a:b for b,a in enumerate([a for a in range(1,k+1) if a != g],1)}
        return tuple(tuple(labels[a] if a>0 else -labels[-a] for a in w) for w in rest)
    result = list(state)
    if op == 'I': result[i] = inv(state[i])
    elif op == 'M':
        if j>=k: return None
        result[i] = reduced(state[i]+(state[j] if sgn==1 else inv(state[j])))
    elif op == 'C':
        if abs(j)>k: return None
        result[i] = reduced((j,)+state[i]+(-j,))
    return tuple(result)

class Review:
    def __init__(self, official):
        self.official=official
        self.counts=Counter()
        self.started=time.monotonic()

    def apply(self, state, mid):
        self.counts['own_apply']+=1
        got=own_apply(state,mid)
        expected,reason=self.official.apply_move(state,mid)
        self.counts['official_apply']+=1
        assert got == expected and ((got is None)==(reason is not None)), (state,mid,got,expected,reason)
        return got

    def edges(self, state, reverse):
        if not reverse:
            for mid in range(257):
                t=self.apply(state,mid)
                if t is not None and len(t)<=CAP: yield t,mid
            return
        # Every preserving ID is tried, including all out-of-rank IDs.
        for mid in range(257):
            iid=inverse_id(mid)
            if iid is None: continue
            t=self.apply(state,iid)
            if t is not None:
                assert self.apply(t,mid)==state
                yield t,mid
        k=len(state)
        if k<CAP:
            # Different lift implementation: signed order embedding whose image
            # omits g. No cyclic, generator, relator or isomorphism quotient.
            for g in range(1,k+2):
                embedding=dict(enumerate([a for a in range(1,k+2) if a!=g],1))
                embedding.update({-a:-b for a,b in list(embedding.items())})
                lifted=tuple(tuple(embedding[a] for a in w) for w in state)
                for slot in range(k+1):
                    candidate=list(lifted)
                    candidate.insert(slot,(g,))
                    candidate=tuple(candidate)
                    assert self.apply(candidate,15+slot)==state
                    self.counts['inverse_destabilize_candidates']+=1
                    yield candidate,15+slot
        if k and state[-1]==(k,) and all(abs(a)!=k for w in state[:-1] for a in w):
            candidate=state[:-1]
            assert self.apply(candidate,14)==state
            yield candidate,14

    def ball(self, source, radius, reverse):
        seen={source:()}
        frontier=[source]
        sizes=[1]
        max_total=sum(map(len,source))
        before=self.counts.copy()
        for depth in range(radius):
            following=[]
            for state in frontier:
                assert time.monotonic()-self.started<90, 'external review time guard'
                for t,mid in self.edges(state,reverse):
                    max_total=max(max_total,sum(map(len,t)))
                    if t not in seen:
                        assert len(seen)<50000, 'external review state guard'
                        seen[t]=(mid,)+seen[state] if reverse else seen[state]+(mid,)
                        following.append(t)
            sizes.append(len(following))
            frontier=following
        meta=dict(radius=radius,complete=True,layers=sizes,states=len(seen),
                  state_sha256=digest(compact(sorted(seen))),
                  max_generated_total_length=max_total,counts=dict(self.counts-before),
                  ranks=dict(Counter(map(len,seen))))
        return seen,meta

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--official-checkout', '--official', dest='official', type=Path,
                        default=Path(__file__).parent.parent/'ac_official')
    parser.add_argument('--original-balls', type=Path)
    args=parser.parse_args()
    out=Path(__file__).resolve().parent
    official_receipts=verify_official(args.official)
    # Ignore any checkout-local bytecode cache: execute the checked .py bytes.
    fresh_cache=tempfile.TemporaryDirectory(prefix='stable-review-empty-cache-')
    sys.pycache_prefix=fresh_cache.name
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(args.official/'competition/tools'))
    from verifier import stable_core
    for mid,row in enumerate(stable_core.MOVE_TABLE):
        op,i,j,sgn=ACTIONS[mid]
        assert {'I':'inversion','M':'multiplication','C':'conjugation','S':'stabilize','D':'destabilize'}[op] == row['category']
        if op!='S': assert i==row['relator']
        if op=='M': assert j==row['other'] and (sgn==-1)==row['invert_other']
        if op=='C': assert j==row['conjugator']
        assert inverse_id(mid)==row['inverse']
    manifest=json.loads((args.official/'competition/tools/verifier/data/manifest.json').read_text())
    challenge=next(c for c in manifest['challenges'] if c['challenge_id']=='sac-08491')
    assert tuple(map(tuple,challenge['initial_relators']))==START
    assert challenge['target_relators']==[]
    assert challenge['instance_hash']=='sha256:757bc38cade1df7592589a7d7b45edbf4f793cbe05b09e538651aa28c9b8498c'
    review=Review(stable_core)
    forward,fm=review.ball(START,4,False)
    reverse,rm=review.ball((),5,True)
    for name,meta in [('forward',fm),('reverse',rm)]:
        assert (meta['layers'],meta['state_sha256'])==EXPECTED[name]
    intersection=forward.keys() & reverse.keys()
    assert not intersection
    trajectory=[START]
    for mid in WITNESS:
        trajectory.append(review.apply(trajectory[-1],mid))
    assert trajectory[-1]==()
    lengths=[sum(map(len,s)) for s in trajectory]
    official_verdict=stable_core.verify(challenge,WITNESS,'sac-r8-v1',manifest['limits'])
    assert official_verdict['ok'] and official_verdict['length']==10
    original_compare=None
    if args.original_balls:
        raw=args.original_balls.read_bytes()
        assert digest(raw)=='bc18a78605cf2a979179c096f32616e580b2f2483b1035f99795816d2cd722fb'
        original=json.loads(raw)
        original_compare={'artifact_sha256':digest(raw)}
        for name,new in [('forward',forward),('reverse',reverse)]:
            old={tuple(map(tuple,row['state'])):tuple(row['path' if name=='forward' else 'to_empty']) for row in original[name]}
            assert set(old)==set(new)
            assert all(len(old[s])==len(new[s]) for s in new)
            # Revalidate every original witness against own+official semantics.
            for state,path in old.items():
                replay=START if name=='forward' else state
                for mid in path: replay=review.apply(replay,mid)
                assert replay==(state if name=='forward' else ())
            original_compare[name]=dict(all_states_equal=True,all_distances_equal=True,all_original_paths_replayed=True,states=len(new))
    full=dict(forward=[{'state':s,'path':forward[s]} for s in sorted(forward)],
              reverse=[{'state':s,'to_empty':reverse[s]} for s in sorted(reverse)])
    ball_bytes=compact(full)+b'\n'
    (out/'external-rebuilt-balls.json').write_bytes(ball_bytes)
    result=dict(kind='NEW EXTERNAL INDEPENDENT REVIEW; NOT NATIVE TASK COMPLETION',
        status='passed',challenge=challenge,official_commit='a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e',
        official_files_checked=official_receipts,rank_cap=CAP,forward=fm,reverse=rm,
        intersection_size=len(intersection),all_257_ids_attempted_per_forward_expansion=True,
        independent_action_table=True,independent_reduction=True,quotient=False,
        resource_length_pruning=False,work_pruning=False,guards_triggered=False,
        original_ball_comparison=original_compare,
        witness=dict(moves=WITNESS,trajectory=trajectory,lengths=lengths,peak=max(lengths),work=sum(lengths),official_verdict=official_verdict),
        global_distance=10,rank_lemma='n>=2z+2; n<=9 implies z<=3 and peak rank<=5',
        all_calls=dict(review.counts),elapsed_seconds=time.monotonic()-review.started,
        rebuilt_balls_sha256=digest(ball_bytes),code_sha256=digest(Path(__file__).read_bytes()))
    (out/'external-review-results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:result[k] for k in ('status','kind','forward','reverse','intersection_size','global_distance','original_ball_comparison','elapsed_seconds')},ensure_ascii=False))

if __name__=='__main__': main()
