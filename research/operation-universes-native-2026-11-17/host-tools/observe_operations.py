"""Round-scoped actual native start and private-literature read evidence."""
import json,os,signal,sys,time
from pathlib import Path
from launch_operations import BASE,STAGE,activate,verify_parent,save,sha

def observe():
    p=activate();verify_parent()
    from manage_native import snapshot
    data=snapshot(STAGE);allstatus,events,entries,state=data
    before=json.loads((BASE/'BEFORE.json').read_bytes());old=set(before['prior_task_ids']);tasks=[]
    for node in allstatus['nodes']:
        for t in node['tasks']:
            if t['task_id']not in old:tasks.append(dict(t,role=node['role']))
    ids={t['task_id']for t in tasks};new=[e for e in events if e['seq']>before['knowledge_prefix']]
    imported=json.loads((BASE/'IMPORT-RECEIPT.json').read_bytes());pages={p['id']:p for p in imported['page_entries']}
    reads=[]
    for e in new:
        if e['kind']!='math_body_read'or e['actor'].get('task_id')not in ids:continue
        eid=e['data']['id']
        completed=next((r for r in new if r['seq']>e['seq']and r['kind']=='native_tool_completed'and r['actor'].get('task_id')==e['actor']['task_id']and r['data']['name']=='math_read'and r['data']['arguments'].get('id')==eid),None)
        result=((completed or{}).get('data',{}).get('result')or{}).get('result')or{}
        body=result.get('body','')
        reads.append({'event_seq':e['seq'],'tool_event_seq':completed['seq']if completed else None,'node_id':e['actor']['actor_node_id'],'task_id':e['actor']['task_id'],'entry_id':eid,'revision':e['data']['revision'],'body_sha256':e['data']['body_sha256'],'tool_ok':bool(completed and completed['data']['result'].get('ok')),'returned_body_characters':len(body),'returned_body_sha256':__import__('hashlib').sha256(body.encode()).hexdigest()if body else None,'full_body_returned':bool(body and __import__('hashlib').sha256(body.encode()).hexdigest()==e['data']['body_sha256']),'kind':'primary_page'if eid in pages else'index_or_other','source_id':pages.get(eid,{}).get('source_id'),'page':pages.get(eid,{}).get('page'),'authoritative_files':pages.get(eid,{}).get('authoritative_files'),'adoption_is_separate':True})
    out={'observed_at':time.time(),'knowledge_prefix':allstatus['knowledge_event_prefix'],'same_live_stage':allstatus['native_run_id'],'policy_unchanged':sha(STAGE/'POLICY.json')==before['policy_sha256'],'gate_status':allstatus['gate_status'],'new_phase_created':False,'tasks':tasks,'literature_import':{k:imported[k]for k in('resource_id','revision','entry_count','import_event','user_instruction_event','actual_reads_prefilled','actual_adoption_prefilled','full_text_private')},'actual_reads':reads,'native_mathematics':[e for e in entries if e.get('source_task')in ids],'actual_adoptions':[e for e in new if e['kind']=='math_adopt'and e['actor'].get('task_id')in ids],'tool_failure_metadata':[{'seq':e['seq'],'node_id':e['actor'].get('actor_node_id'),'tool':e['data']['name'],'error':e['data']['result'].get('error')}for e in new if e['kind']=='native_tool_completed'and e['actor'].get('task_id')in ids and not e['data']['result'].get('ok')]}
    save(BASE/'CURRENT-PRIVATE.json',out)
    public={'observed_at':out['observed_at'],'knowledge_prefix':out['knowledge_prefix'],'same_live_stage':out['same_live_stage'],'policy_unchanged':out['policy_unchanged'],'gate_status':out['gate_status'],'new_phase_created':False,'tasks':[{k:t.get(k)for k in('node_id','role','node_request_id','task_id','submitted_by','status','output_complete','commit_confirmed','native_cleanup_complete','completed_real_research_receipt','requested_profile','native_thread_configuration','thread_id','turn_id','native_state','wire_write_completed','usage','error')}for t in tasks],'literature_import':out['literature_import'],'actual_reads':reads,'adoption_events':[{'seq':e['seq'],'node_id':e['actor']['actor_node_id'],'task_id':e['actor']['task_id'],'id':e['data']['id'],'revision':e['data']['revision'],'artifact':e['data'].get('artifact')}for e in out['actual_adoptions']],'native_math_versions':[{'id':e['id'],'revision':e['revision'],'title':e['title'],'summary':e['summary'],'body_sha256':e['body_sha256'],'source_task':e['source_task'],'author_node':e['author_node']}for e in out['native_mathematics']],'tool_failures':out['tool_failure_metadata'],'full_PDF_or_page_text_published':False}
    save(BASE/'START-AND-READ-RECEIPTS.json',public)
    return public

def resume_observer():
    p=activate()
    from yohaku_codex_tasks import identity
    r=json.loads((STAGE/'OBSERVER-IDLE-PAUSE.json').read_bytes());expected=r['identity'];actual=identity(expected['pid'])
    if not actual or actual['start']!=expected['start']:raise RuntimeError('Original observer identity differs')
    if actual['state']=='T':os.kill(actual['pid'],signal.SIGCONT)
    save(BASE/'OBSERVER-RESUMED.json',{'at':time.time(),'identity':identity(actual['pid']),'same_original_observer':True,'policy_or_deadline_modified':False,'model_workers_signalled':[]})
    print(json.dumps({'resumed_same_observer':True,'pid':actual['pid'],'new_model_started_by_resume':False}))

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('action',choices=['status','resume-observer']);args=a.parse_args()
    if args.action=='resume-observer':resume_observer()
    else:
        x=observe();print(json.dumps({'observed_at':x['observed_at'],'tasks':[{'node':t['node_id'],'id':t['task_id'],'status':t['status'],'turn':t['turn_id'],'native':t['native_thread_configuration']}for t in x['tasks']],'page_reads':[{'node':r['node_id'],'id':r['entry_id'],'page':r['page'],'full_body':r['full_body_returned'],'event':r['event_seq']}for r in x['actual_reads']if r['kind']=='primary_page'],'gate':x['gate_status']},ensure_ascii=False))
