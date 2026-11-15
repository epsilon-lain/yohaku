"""Host validation after group completion; a different pi identity, no imports
from researcher/observer code or supplied baseline helper. Not a group action.
"""
from pathlib import Path
from fractions import Fraction
import hashlib,json,sys,time
sys.set_int_max_str_digits(0)
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
def h(b):return hashlib.sha256(b).hexdigest()
def gaussian(a,b):return(a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0])
def atan_bounds(z,S):
 lo=hi=k=0;power=S//z
 while power:
  term=power//(2*k+1)
  if k%2:lo-=term+1;hi-=term
  else:lo+=term;hi+=term+1
  power//=z*z;k+=1
 return lo-1,hi+1,k
def main():
 start=time.monotonic();z=(1,0)
 for _ in range(4):z=gaussian(z,(5,1))
 z=gaussian(z,(239,-1));assert z[0]==z[1]and z[0]>0
 assert 4*Fraction(5,26)-Fraction(1,239)>0
 assert Fraction(4,5)<1
 # 0<theta=4atan(1/5)-atan(1/239)<4/5<1<pi/2,
 # and tan(theta)=1, so pi=16atan(1/5)-4atan(1/239).
 S=10**30000;a,b,ka=atan_bounds(5,S);c,d,kb=atan_bounds(239,S)
 L,U=16*a-4*d,16*b-4*c;assert 3*S<L<U<4*S
 ln,ld,rn,rd=L,S,U,S;pm2,pm1,qm2,qm1=0,1,1,0;terms=[]
 for n in range(28422):
  an=ln//ld;assert an==rn//rd;terms.append(an)
  p,q=an*pm1+pm2,an*qm1+qm2
  assert p*qm1-pm1*q==(-1 if n%2==0 else 1)
  if n==28420:pt,qt=p,q
  if n==28421:qnext=q
  pm2,pm1,qm2,qm1=pm1,p,qm1,q
  lr,rr=ln-an*ld,rn-an*rd;assert lr>0 and rr>0
  ln,ld,rn,rd=rd,rr,ld,lr
 prior=max(terms[1:28421]);assert prior==20776 and terms[28421]==78629
 assert [i for i in range(1,28421)if terms[i]==prior]==[431]
 elo,ehi=qt*L-pt*S,qt*U-pt*S;assert 0<elo<ehi and 2*ehi<S
 vlo,vhi=qt*elo,qt*ehi;assert vhi*(prior+2)<S
 floor40=int('0000127178573727574566035844693935801274')
 assert floor40*S<vlo*10**40 and vhi*10**40<(floor40+1)*S
 for name,value in [('p28420',pt),('q28420',qt),('q28421',qnext)]:assert int((ROOT/'research_1'/f'{name}.txt').read_text())==value
 assert h(b''.join(b',%d'%x for x in terms))==json.loads((ROOT/'research_1/finite-minimum.json').read_text())['prefix_terms_sha256']
 rL,rU=L-3*S,U-3*S;threshold=U-3*S
 for k in range(1,15000):
  rL=10*rL%S;rU=10*rU%S;threshold//=10
  assert rU-rL==(U-L)*10**k and 0<rL<rU<S
  assert min(rL,S-rU)>threshold
 div=10**10;assert L//div==U//div
 prefix='3.'+str(L//div)[1:]+'\n';assert prefix==(ROOT/'research_2/pi_decimal_prefix.txt').read_text()
 report={'passed':True,'performed_by':'host after group; not attributed to Sol or researchers','pi_identity':'pi=16atan(1/5)-4atan(1/239)','shared_baseline_pi_identity':'pi=48atan(1/18)+32atan(1/57)-20atan(1/239)','independence_limit':'Different identity and standalone implementation; both use outward fixed-scale alternating-series bounds, not formal proof-assistant certification.','scale_digits':30000,'cf_prefix_terms':len(terms),'prior_max':prior,'next_partial_quotient':terms[28421],'p_q_boundaries_match':True,'finite_minimum_gap_passed':True,'decimal_power_range':[0,14999],'decimal_prefix_29990_matches':True,'enclosure_integer_width':U-L,'arctan_terms':{'5':ka,'239':kb},'elapsed_seconds':round(time.monotonic()-start,6),'original_runtime_calls':0}
 (ROOT/'host/INDEPENDENT-CHECK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
