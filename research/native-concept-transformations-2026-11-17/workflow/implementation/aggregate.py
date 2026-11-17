"""Keep both native phases of one user supplement separate and inspectable."""
import json
from supplement import BASE,save
from observe import observe
FIRST=BASE.parent/'native-concept-transformations-20261117-01'
SECOND=BASE.parent/'native-concept-transformations-20261117-02'

def aggregate():
    current,data=observe();first=json.loads((FIRST/'ROUND-STATUS.json').read_bytes());second=json.loads((SECOND/'ROUND-STATUS.json').read_bytes())
    phases=[first,second,current]
    all_events=[e for e in data[1]if e['seq']>first['baseline_knowledge_prefix']]
    out=dict(current)
    out['round_id']='concept-transformations-user-20261117'
    out['native_phases']=[{'phase':phase['round_id'],'gate':phase['resource_status'],'status':'current recovery'if phase is current else'closed to new admission; stop and responsibility retained','tasks':[t['task_id']for t in phase['tasks']]}for phase in phases]
    out['tasks']=[t for phase in phases for t in phase['tasks']]
    out['project_receipts']=[r for phase in phases for r in phase['project_receipts']]
    out['baseline_knowledge_prefix']=first['baseline_knowledge_prefix']
    out['new_nodes']=list({n['node_id']:n for phase in phases for n in phase['new_nodes']}.values())
    entries={}
    for e in[e for phase in phases for e in phase['new_math_entries']]:
        key=(e['id'],e['revision'])
        if key in entries and entries[key]['body_sha256']!=e['body_sha256']:raise RuntimeError('Immutable mathematical version conflict')
        entries[key]=e
    out['new_math_entries']=list(entries.values())
    out['adoption_claims']=[e for e in all_events if e['kind']=='math_adopt']
    out['ai_continuation_requests']=[e for e in all_events if e['kind']=='continuation_requested']
    out['consumed_ai_continuations']=[e for e in all_events if e['kind']=='explicit_ai_continuation_consumed']
    out['tool_failures_retained']=[e for e in all_events if e['kind']=='native_tool_completed'and not e['data']['result'].get('ok')]
    out['original_policy_sha256']=first['original_policy_sha256']
    out['all_predecessor_states_and_stops_preserved']=True
    out['user_authority_new_turns_total']=12
    out['user_authority_turns_reserved']=sum(phase['resource_status']['native_turns_reserved']for phase in phases)
    assert out['user_authority_turns_reserved']<=12
    out['original_first_phase_error_retained']=True
    save(BASE/'USER-ROUND-STATUS.json',out);save(BASE/'USER-ROUND-EVENTS.json',all_events)
    return out,all_events

if __name__=='__main__':
    out,_=aggregate();print(json.dumps({'classification':out['classification'],'tasks':len(out['tasks']),'projects':len(out['project_receipts']),'math_versions':len(out['new_math_entries']),'reserved':out['user_authority_turns_reserved'],'ceiling':12}))
