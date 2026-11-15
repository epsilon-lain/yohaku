"""Observer finite-data re-extraction; shared baseline enclosure helper.
No independent pi formula is claimed. Writes only this observer directory.
"""
import sys
sys.dont_write_bytecode = True
sys.set_int_max_str_digits(0)
import importlib.util, json, hashlib, time
from pathlib import Path
start=time.monotonic()
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('baseline',root/'common/check_runB_independent.py')
b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
S=10**30000
bounds={x:b.inverse_atan_bounds(x,S) for x in (18,57,239)}
L=48*bounds[18][0]+32*bounds[57][0]-20*bounds[239][1]
U=48*bounds[18][1]+32*bounds[57][1]-20*bounds[239][0]
left=(L,S); right=(U,S)
p0,p1,q0,q1=0,1,1,0
terms=[]
for n in range(28422):
    a=left[0]//left[1]
    assert a==right[0]//right[1]
    terms.append(a)
    p,q=a*p1+p0,a*q1+q0
    if n==28420: pt,qt=p,q
    if n==28421: qnext=q
    p0,p1,q0,q1=p1,p,q1,q
    lr=left[0]-a*left[1]; rr=right[0]-a*right[1]
    assert lr>0 and rr>0
    left,right=(right[1],rr),(left[1],lr)
report=json.loads((root/'research_1/finite-minimum.json').read_text())
assert max(terms[1:28421])==report['prior_partial_quotient_max']==20776
assert terms[28421]==report['next_partial_quotient']==78629
assert qt==int((root/'research_1/q28420.txt').read_text())
assert qnext==int((root/'research_1/q28421.txt').read_text())
assert pt==int((root/'research_1/p28420.txt').read_text())
assert hashlib.sha256(b''.join(b',%d'%a for a in terms)).hexdigest()==report['prefix_terms_sha256']
assert 0<qt*L-pt*S<qt*U-pt*S<S//2
assert qt*(qt*U-pt*S)*20778<S
out={'check':'observer shared-helper re-extraction','all_assertions_passed':True,
 'prior_max':20776,'prior_max_indices':[i for i,a in enumerate(terms[1:28421],1) if a==20776],
 'next_a':78629,'p_q_and_boundary_files_match':True,'prefix_hash_matches':True,
 'target_upper_less_than_1_over_20778':True,
 'independence_limit':'Shares supplied baseline arctan helper; not an independent pi certification',
 'elapsed_seconds':round(time.monotonic()-start,3)}
Path(__file__).with_name('prefix_check.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
