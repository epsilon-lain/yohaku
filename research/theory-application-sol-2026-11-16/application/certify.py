"""Reproduce a complete unpruned radius-six meet-in-the-middle certificate.

Independent tuple-word move implementation is checked against the pinned
reference on every generated edge. No length/resource pruning or quotient is
used for the metric lower bound. Official limits apply separately to witnesses.
"""
from __future__ import annotations
import argparse,hashlib,json,signal,time
from pathlib import Path
from refine import HERE,TARGET,configure,source_arguments,dump,length,trajectory
GENS=(1,-1,2,-2)

class IncompleteEnumeration(RuntimeError):pass

class ResourceGuard:
    def __init__(self,max_seconds,max_states):
        self.max_seconds=max_seconds;self.max_states=max_states
        self.started=time.perf_counter();self.states=0
    def check(self):
        if self.states>self.max_states:raise IncompleteEnumeration('total_state_cap')
        if time.perf_counter()-self.started>self.max_seconds:raise IncompleteEnumeration('wall_clock_cap')
    def insert(self):
        if self.states>=self.max_states:raise IncompleteEnumeration('total_state_cap')
        self.states+=1;self.check()
    def report(self):return {'max_seconds':self.max_seconds,'max_total_states':self.max_states,'observed_states':self.states,'observed_seconds':time.perf_counter()-self.started}

def inv(w):return tuple(-x for x in reversed(w))
def reduce(w):
    out=[]
    for x in w:
        if out and out[-1]==-x:out.pop()
        else:out.append(x)
    return tuple(out)
def independent_apply(s,m):
    if m<2:
        a=list(s);a[m]=inv(a[m]);return tuple(a)
    i=(m-2)//2 if m<6 else (m-6)//4
    a=list(s)
    if m<6:a[i]=reduce(a[i]+(s[1-i] if m%2==0 else inv(s[1-i])))
    else:
        g=GENS[(m-6)%4];a[i]=reduce((g,)+a[i]+(-g,))
    return tuple(a)

def encode(s):
    code={-2:1,-1:2,1:3,2:4}
    return bytes([code[a] for a in s[0]]+[0]+[code[a] for a in s[1]])
def digest(states):
    h=hashlib.sha256()
    for s in sorted(map(encode,states)):
        h.update(len(s).to_bytes(4,'big'));h.update(s)
    return h.hexdigest()
def ball(source,depth,guard):
    seen={source:()};frontier=[source];sizes=[1];layerhash=[digest(frontier)]
    guard.insert()
    evals=0;peak=length(source);began=time.perf_counter()
    for k in range(depth):
        nxt=[]
        for s in frontier:
            for m in range(14):
                t=independent_apply(s,m)
                assert t==apply_move(s,m)
                evals+=1;peak=max(peak,length(t))
                if evals%4096==0:guard.check()
                if t not in seen:
                    guard.insert();seen[t]=seen[s]+(m,);nxt.append(t)
        frontier=nxt;sizes.append(len(nxt));layerhash.append(digest(nxt))
        print(json.dumps({'depth':k+1,'frontier':len(nxt),'elapsed':time.perf_counter()-began}),flush=True)
    return seen,{'radius':depth,'layer_sizes':sizes,'states':len(seen),'primitive_evaluations':evals,'official_crosscheck_evaluations':evals,'peak_total_length':peak,'pruning':False,'quotient':False,'layer_state_sha256':layerhash,'all_state_sha256':digest(seen),'digest_encoding':'state=[letter code for r0]+[0]+[letter code for r1], code(-2,-1,1,2)=(1,2,3,4); lexicographic sort states, each prefixed by 4-byte big-endian byte length','wall_seconds':time.perf_counter()-began}

def main():
    global apply_move,verify,INVERSE_MOVE
    parser=argparse.ArgumentParser(description=__doc__)
    source_arguments(parser)
    parser.add_argument('--max-seconds',type=float,default=30)
    parser.add_argument('--max-states',type=int,default=1600000)
    parser.add_argument('--output',type=Path,default=HERE/'distance_certificate_guarded.json')
    parser.add_argument('--refinement-results',type=Path,default=HERE/'refinement_results.json')
    args=parser.parse_args()
    guard=ResourceGuard(args.max_seconds,args.max_states)
    def timed_out(signum,frame):raise IncompleteEnumeration('wall_clock_alarm')
    signal.signal(signal.SIGALRM,timed_out)
    signal.setitimer(signal.ITIMER_REAL,args.max_seconds)
    provenance=configure(args.official_root,args.baseline_root)
    from verifier.core import apply_move,verify,INVERSE_MOVE
    prior=json.loads(args.refinement_results.read_text())
    manifest=json.loads((args.official_root/'competition/tools/verifier/data/manifest.json').read_text())
    c=next(c for c in manifest['challenges'] if c['challenge_id']=='ac-07445')
    assert prior['challenge']==c,'Refinement challenge does not match pinned official manifest'
    start=tuple(map(tuple,c['initial_relators']))
    witness=min((r['moves'] for r in prior['runs']),key=lambda p:(len(p),p))
    try:
        f,fmeta=ball(start,6,guard);b,bmeta=ball(TARGET,6,guard)
    except IncompleteEnumeration as error:
        signal.setitimer(signal.ITIMER_REAL,0)
        incomplete={'version':'application-distance-guarded-v1','status':'incomplete','reason':str(error),'resource_guard':guard.report(),'exact_AC_distance':None,'proof':None,'warning':'No lower bound follows from a partially generated empty intersection.'}
        dump(args.output,incomplete);print(json.dumps(incomplete),flush=True);return
    common=f.keys()&b.keys()
    if common:
        candidates=(f[s]+tuple(INVERSE_MOVE[m] for m in reversed(b[s])) for s in common)
        candidate=min(candidates,key=lambda p:(len(p),p))
        if (len(candidate),candidate)<(len(witness),tuple(witness)):witness=list(candidate)
        optimum=len(witness);excluded=optimum-1
        proof='The minimum length among all intersections of the two complete radius-six balls is the global distance if it is <=12: any shorter path also meets those balls. An official verified witness attains it.'
    else:
        excluded=12;optimum=13 if len(witness)==13 else None
        proof='Every path of length <=12 meets both complete radius-six balls. Their empty intersection excludes all such paths; the official verified length-13 witness proves distance exactly 13.'
    verdict=verify(c,witness,c['move_spec_version'],manifest['limits']);assert verdict['ok']
    signal.setitimer(signal.ITIMER_REAL,0)
    result={'version':'application-distance-guarded-v1','status':'complete','resource_guard':guard.report(),'provenance':provenance,'challenge':c,'forward_ball':fmeta,'target_ball':bmeta,'intersection_count':len(common),'excluded_move_lengths':{'minimum':0,'maximum':excluded},'exact_AC_distance':optimum,'witness':witness,'official_verification':verdict,'trajectory':trajectory(start,witness),'proof':proof,'scope':'One fixed ordinary AC instance; exact ordered target; no quotient or truncation; not Stable AC or a conjecture result.'}
    dump(args.output,result)
    print(json.dumps({k:result[k] for k in ['version','intersection_count','exact_AC_distance','official_verification']}),flush=True)
if __name__=='__main__':main()
