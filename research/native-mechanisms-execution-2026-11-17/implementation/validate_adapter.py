"""Exercise the actual base Tool validator with the extended submit schema."""
import contextlib,copy,json,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'candidate/agent'));sys.path.insert(0,str(BASE))
import yohaku_agent as agent,yohaku_workflow_gate as gates,yohaku_native_research_runtime as runtime
import mechanisms_host as host
class G:
    policy={'program_budget':{'socket':'fixture','guard_root':'fixture','guard_hashes':{}}}
    @contextlib.contextmanager
    def tx(self):yield {'first_send_at':time.time()}
class K:
    def record(self,*a):pass
gates.gate=lambda:G();runtime.service=lambda g:K();runtime.actor_context=lambda *a:dict(actor_node_id='fixture',task_id='fixture')
class P:
    def call(self,name,args):
        assert name=='task_submit'and args['budget_allocation_id']=='immutable-fixture-allocation'
        assert host.SLOT.get()['allocation']=='immutable-fixture-allocation'
        return {'base_validator_passed':True,'allocation_bound_context':True}
class W:root=BASE
t=agent.Tools(lambda a:None,lambda:{},{'read':True,'write':True,'run':True,'delete':False,'import':False},native=True)
t.host_world_root=str(BASE);t.project_control=P();t.codex_text_enabled=False
host.wrap(t,W(),{'node_id':'fixture'},'fixture')
result=t.call('task_submit',dict(project_id='fixture',action='frozen',request_id='same-original-request',budget_allocation_id='immutable-fixture-allocation'))
assert result['ok']and result['result']['base_validator_passed'],result
out=dict(passed=True,actual_model_requests=0,fixture_is_not_research=True,actual_base_validator_used=True,allocation_field_preserved=True,context_present_at_project_facade=True,at=time.time())
(BASE/'ADAPTER-VALIDATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
