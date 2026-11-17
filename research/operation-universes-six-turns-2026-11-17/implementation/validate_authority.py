"""Zero-inference checks of the explicit new numeric authority."""
import copy,json,os,time
from continuation import BASE,activate,verify_parent,save,sha
p=activate();verify_parent()
from manage_native import verify_candidate
from yohaku_native_research_gate import NativeGate
from yohaku_workflow_gate import GateStopped,GateError
verify_candidate();checks=[];env=os.environ['YOHAKU_WORKFLOW_POLICY_SHA256']
f=BASE/'fixture';f.mkdir(exist_ok=True);q=copy.deepcopy(p);q['state_path']=str(f/'STATE.json');save(f/'POLICY.json',q)
os.environ['YOHAKU_WORKFLOW_POLICY_SHA256']=sha(f/'POLICY.json')
v=json.loads((BASE/'STATE.json').read_bytes());v['policy_sha256']=sha(f/'POLICY.json');save(f/'STATE.json',v)
try:
    g=NativeGate(f/'POLICY.json');good={'provider':'openai','model':'gpt-6.1-sol','reasoning_effort':'max','budget':{'timeout_seconds':900,'max_tool_calls':96}}
    assert g.status()['native_turns_remaining']==6 and g.status()['remaining_seconds']==5400
    assert g.cached_profile(good)==good;checks.append('six turns / 5400 seconds before first admission; Sol/max allowed')
    for key,value in [('model','gpt-6-astra'),('reasoning_effort','medium')]:
        bad=copy.deepcopy(good);bad[key]=value
        try:g.cached_profile(bad)
        except GateError:checks.append('denied '+key+'='+value)
        else:raise AssertionError('Weak model accepted')
    head=v['leaders']['theory'];low=copy.deepcopy(good);low['reasoning_effort']='high'
    try:g.reserve_start('main',None,head,'fixture-only','model-task-fixture',{'task':'fixture'},low,v['members'][head]['scopes'])
    except GateError:checks.append('host cannot directly dispatch original direction head')
    else:raise AssertionError('Host direction dispatch accepted')
    with g.tx()as state:
        state['turns']={str(i):{'state':'completed'}for i in range(6)}
    try:g.reserve_start('main',None,p['root_node_id'],'fixture-limit','model-task-fixture',{'task':'fixture'},good,v['members'][p['root_node_id']]['scopes'])
    except GateStopped:checks.append('seventh turn admission denied')
    else:raise AssertionError('Seventh turn accepted')
    with g.tx()as state:state['turns']={};state['first_send_at']=time.time()-5401
    try:g.ensure_admission_open()
    except GateStopped:checks.append('admission denied after 5400 seconds')
    else:raise AssertionError('Expired authority accepted')
finally:os.environ['YOHAKU_WORKFLOW_POLICY_SHA256']=env
verify_parent();save(BASE/'ENGINEERING-VALIDATION.json',{'passed':True,'checks':checks,'actual_model_requests':0,'fixture_is_not_research':True,'runtime_unchanged':True,'old_authorities_unchanged':True,'at':time.time()})
print(json.dumps({'passed':True,'checks':checks,'actual_model_requests':0}))
