"""Bounded authority tests; block before native write, never start inference."""
import copy,json,os,time
from supplement import BASE,ORIGINAL,activate,verify_parent,save,sha

p=activate();from yohaku_native_research_gate import NativeGate
from yohaku_workflow_gate import GateError,GateStopped,digest
from yohaku_native_research_lease import NativeLease
from batch_budget_guard import atomic
from manage_native import verify_candidate
verify_candidate();baseline=verify_parent();checks=[]
fixture=BASE/'bridge-fixture';fixture.mkdir(exist_ok=False)
policy=copy.deepcopy(p);policy.update(experiment_id=p['experiment_id']+'-zero-inference-fixture',state_path=str(fixture/'STATE.json'),stop_file=str(fixture/'DRAIN'),preflight_only=True)
save(fixture/'POLICY.json',policy);state=copy.deepcopy(json.loads((BASE/'STATE.json').read_bytes()));state['policy_sha256']=sha(fixture/'POLICY.json');save(fixture/'STATE.json',state)
os.environ['YOHAKU_WORKFLOW_POLICY_SHA256']=sha(fixture/'POLICY.json');g=NativeGate(fixture/'POLICY.json')
profile={'provider':'openai','model':'gpt-6.1-sol','reasoning_effort':'max','budget':{'timeout_seconds':900,'max_tool_calls':96}}
def rejected(label,call):
    try:call()
    except (GateError,GateStopped):checks.append({'check':label,'passed':True});return
    raise AssertionError(label+' unexpectedly allowed')
assert set(state['members'])==set(baseline['original_state']['members']);checks.append({'check':'same original nodes and direction bindings','passed':True})
assert p['limits']['turns']+p['lineage']['previous_delta_turns_reserved']==p['lineage']['total_user_supplement_turn_ceiling']
assert state['first_send_at']+p['limits']['seconds']==p['lineage']['deadline_inherited_exactly']
checks.append({'check':'recovery carries remaining turn budget and exact original deadline; no renewal','passed':True})
for model,effort in [('gpt-6-astra','max'),('gpt-6.1-sol','medium')]:rejected('deny '+model+'/'+effort,lambda:g.cached_profile(dict(profile,model=model,reasoning_effort=effort)))
spec={'task':'offline bridge fixture; no research or model execution','profile':profile}
rejected('heads cannot be high',lambda:g.reserve_start('main',None,p['root_node_id'],'fixture-head-high','fixture-high',spec,dict(profile,reasoning_effort='high'),p['project_scopes']))
rejected('host cannot dispatch direction directly',lambda:g.reserve_start('main',None,state['leaders']['theory'],'fixture-host-direction','fixture-direction',spec,profile,next(iter(state['members'].values()))['scopes']))
binding=g.reserve_start('main',None,p['root_node_id'],'fixture-user-root','fixture-root',spec,profile,p['project_scopes'])
rejected('unknown old task binding cannot authorize new work',lambda:g.execution_task(next(iter(baseline['original_state']['starts'].values()))))
g.start_enter(binding,'fixture-root','fixture-host-request')
identity='fixture-root:native:0';g.native_reserve(binding,identity,profile)
rejected('no duplicate native reservation',lambda:g.native_reserve(binding,identity,profile))
lease=NativeLease.__new__(NativeLease);lease.gate=g;lease.identity=identity;lease.data={'send_attempted':False,'events':[]};lease.atomic=atomic;lease.path=fixture/'native-turn.json'
parameters={'threadId':'fixture-thread-never-sent','input':[],'approvalPolicy':'never','permissions':'yohaku-control','model':'gpt-6.1-sol','effort':'max'}
lease.permit_send(parameters['threadId'],parameters)
try:lease.attempting({'id':1,'method':'turn/start','params':parameters})
except ValueError as exc:
    assert 'NATIVE_PREFLIGHT_ZERO_INFERENCE'in str(exc);checks.append({'check':'unchanged NativeLease actual pre-write fixture block','passed':True})
else:raise AssertionError('Zero-inference block did not fire')
rejected('no replay after prewrite reservation',lambda:g.final_send(identity,{'id':2,'method':'turn/start','params':parameters},digest(parameters)))
g.request_shared_stop('fixture stop',{'offline':True});rejected('stage stop blocks new admission',g.ensure_admission_open)
from observe import inspect_project
class UnstartedProject:
    def status(self,**args):raise ValueError('No task with this identity; no process targeted')
    def _owned(self,*args):raise AssertionError('An unstarted task has no record to read')
before_state=(fixture/'STATE.json').read_bytes()
row={'request_id':'fixture-preflight-not-started','model_task_id':'fixture-root','node_id':p['root_node_id']}
observation=inspect_project(UnstartedProject(),row)
assert observation['request_not_replayed']and observation['native_submit']==row and'No task'in observation['inspection_error']
assert (fixture/'STATE.json').read_bytes()==before_state
checks.append({'check':'unstarted project observation retains original ID without mutating gate or replaying request','passed':True})
from observe import continuation_profile
legacy={'provider':'openai','model':'gpt-6.1-sol','reasoning_effort':'max','budget':{'timeout_seconds':1800,'max_tool_calls':128}}
chosen=continuation_profile({'profile':legacy,'tasks':[]},p['limits'])
assert chosen['model']==legacy['model']and chosen['reasoning_effort']==legacy['reasoning_effort']
assert chosen['budget']=={'timeout_seconds':900,'max_tool_calls':96}
g.cached_profile(chosen)
checks.append({'check':'AI continuation explicitly retains Sol/Max and clamps legacy1800/128 resources to900/96','passed':True})
verify_parent()
save(BASE/'ENGINEERING-VALIDATION.json',{'passed':True,'checks':checks,'actual_model_requests':0,'native_pipe_writes':0,'new_real_node_or_task_created':False,'fixture_is_not_research':True,'candidate_runtime_unchanged_and_original_seal_verified':True,'parent_policy_state_and_stop_unchanged':True,'at':time.time()})
print(json.dumps({'passed':True,'checks':len(checks),'actual_model_requests':0,'parent_unchanged':True}))
