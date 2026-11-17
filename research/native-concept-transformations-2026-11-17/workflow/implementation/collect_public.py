"""Curate public scientific inputs/receipts; exclude chats, memories and accounts."""
import hashlib,json,os,re,shutil,time,zipfile
from pathlib import Path
from supplement import BASE,ORIGINAL,PHASE,REF,REVIEW_REF
ROUND='concept-transformations-user-20261117'
from prepare_native import save,sha
from aggregate import aggregate

YOH_PATH='research/native-concept-transformations-2026-11-17'
MATH_PATH='research/concept-transformations-2026-11-17'

def public_value(value):
    if isinstance(value,dict):return {k:public_value(v)for k,v in value.items()if k not in('token','host_path','diagnostic_path','auth_home','provider_file','authorization','native','process','pid','start','runner_pid')}
    if isinstance(value,list):return [public_value(v)for v in value]
    if isinstance(value,str):
        value=value.replace(str(ORIGINAL),'$ORIGINAL_RUN').replace(str(BASE),'$ROUND')
        return re.sub(r'/root/projects/yohaku[^\s"\n]*','[LOCAL_PATH]',value)
    return value

def copy_verified(source,target,expected=None):
    raw=Path(source).read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if expected and digest!=expected:raise RuntimeError('Native artifact/input changed: '+str(source))
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);return digest

def collect():
    status,events=aggregate();stamp=str(int(time.time()*1000));root=BASE/'public-staging'/('prefix-'+str(status['knowledge_event_prefix'])+'-'+stamp);root.mkdir(parents=True)
    yoh=root/'yohaku';math=root/'math';yoh.mkdir();math.mkdir()
    # No raw node memories, conversation transcripts, task prompts or auth files.
    models=[]
    for t in status['tasks']:
        models.append({key:public_value(t.get(key))for key in('original_node_id','native_node_role','task_id','node_request_id','dispatch_origin','status','output_complete','commit_confirmed','native_cleanup_complete','completed_real_research_receipt','requested_profile','native_thread_configuration','usage','final_text_sha256')})
    save(yoh/'evidence/model-task-receipts.json',{'round_id':ROUND,'observed_at':status['observed_at'],'knowledge_event_prefix':status['knowledge_event_prefix'],'gate_event_prefix':status['gate_event_prefix'],'receipts':models,'supplier_actual_identity':'unknown','supplier_actual_debit':'unknown','raw_chats_and_private_runtime_not_published':True})
    source_manifest=[];artifact_index=[]
    for item in status['project_receipts']:
        record=item.get('private_record');s=item.get('status',{});tid=s.get('task_id')
        if not record or not tid:continue
        snapshot=record['snapshot'];files=[];snapshot_root=Path(snapshot['path'])
        for f in snapshot['files']:
            if f['role']!='generated':continue
            name=f['path']
            if any(x in name.lower()for x in('memory','user-goal','handoff')):raise RuntimeError('Unexpected private file in executable snapshot: '+name)
            digest=copy_verified(snapshot_root/name,yoh/'blobs'/f['sha256'],f['sha256']);files.append({k:f[k]for k in('path','sha256','bytes','source','source_revision')if k in f})
        task=record['project']['tasks'][record['action']]
        snap={'task_id':tid,'native_submit':item['native_submit'],'project_id':record['project_id'],'action':record['action'],'source_set':snapshot['source_set'],'snapshot_id':snapshot['id'],'manifest_revision':snapshot['manifest_revision'],'task':task,'files':files}
        save(yoh/'snapshots'/(tid+'.json'),snap);source_manifest.append(snap)
        rec={'native_submit':item['native_submit'],'task_id':tid,'status':s.get('status'),'source_set':snapshot['source_set'],'snapshot_id':snapshot['id'],'native_receipt':public_value(s.get('receipt')),'artifacts':[]}
        for a in(record.get('receipt')or{}).get('artifacts',[]):
            relative='evidence/'+tid+'/'+a['path'];copy_verified(a['host_path'],yoh/relative,a['sha256'])
            meta={k:a[k]for k in('id','path','sha256','bytes','source_set','snapshot_id')if k in a};meta['public_path']=relative;rec['artifacts'].append(meta);artifact_index.append(dict(meta,task_id=tid,project_id=record['project_id']))
        logs=Path(status['tasks'][0]['trace_path']).parent.parent/'project-tasks/logs'
        for stream in('stdout','stderr'):
            path=logs/(tid+'.'+stream)
            if path.is_file():
                text=path.read_text(errors='replace');target=yoh/'evidence'/tid/(stream+'.txt');target.parent.mkdir(parents=True,exist_ok=True);target.write_text(public_value(text));rec[stream+'_original_sha256']=sha(path)
        save(yoh/'evidence'/tid/'receipt.json',rec)
    save(yoh/'evidence/source-snapshot-index.json',source_manifest);save(yoh/'evidence/artifact-index.json',artifact_index)
    # Preserve all exact published mathematical versions from this round.
    latest={}
    for entry in status['new_math_entries']:
        name=entry['id']+'-v'+str(entry['revision'])+'.md';body=entry['body']
        (yoh/'mathematics').mkdir(exist_ok=True);(yoh/'mathematics'/name).write_text(body+'\n')
        (math/'versions').mkdir(exist_ok=True);(math/'versions'/name).write_text(body+'\n')
        if entry['id']not in latest or latest[entry['id']]['revision']<entry['revision']:latest[entry['id']]=entry
    metadata=[{k:e.get(k)for k in('id','revision','title','summary','scope','conditions','claim_kind','author_status','independent_review_status','source_task','author_node','body_sha256')}for e in status['new_math_entries']]
    save(yoh/'mathematics/INDEX.json',metadata);save(math/'INDEX.json',metadata)
    workflow=[]
    for e in events:
        if e['kind']=='native_tool_completed'and e['data']['name']in('ai_node_create','ai_node_dispatch','ai_chat_create','ai_message_send','ai_messages','research_continue','research_finish'):
            args=e['data']['arguments'];workflow.append({'event_seq':e['seq'],'actor_node_id':e['actor']['actor_node_id'],'source_task':e['actor']['task_id'],'tool':e['data']['name'],'ok':e['data']['result'].get('ok'),'target_node_id':args.get('node_id'),'chat_id':args.get('chat_id'),'request_id':args.get('request_id'),'raw_text_not_published':True})
    adoption=[public_value(e)for e in events if e['kind']in('math_adopt','math_review','math_body_read','continuation_requested','explicit_ai_continuation_consumed')]
    # Continuation body and reply transcripts remain private; keep identity/hash.
    for e in adoption:
        if e['kind']in('continuation_requested','explicit_ai_continuation_consumed'):
            e['data']={'original_event_data_sha256':hashlib.sha256(json.dumps(e['data'],ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'scope':'AI-requested continuation identity is recorded in native logs; raw task text private'}
    save(yoh/'workflow/observed-operations.json',workflow);save(yoh/'workflow/reads-adoptions-reviews.json',adoption)
    proof_meta={'round_id':ROUND,'original_nodes_preserved':True,'new_user_supplement':True,'theory_independent_of_competition_improvement':True,'native_user_request_id':'user-concept-transformations-20261117-v1','user_instruction_event':968,'old_policy_sha256':status['original_policy_sha256'],'old_policy_unchanged':status['old_policy_unchanged'],'old_budget_reset':False,'package_commit':REF,'external_review_commit':REVIEW_REF,'official_commit':'a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e','knowledge_event_window':[status['baseline_knowledge_prefix']+1,status['knowledge_event_prefix']],'gate_event_prefix':status['gate_event_prefix'],'raw_private_runtime_archive':'retained on the user host, not published','external_resources':json.loads((BASE/'IMPORT.json').read_bytes()),'contributors':[{'node_id':n['node_id'],'role':n['role'],'model':n['profile']['model'],'effort':n['profile']['reasoning_effort']}for n in status['new_nodes']],'host_work':'Independent delta-stage bridge, source import, original-ID status and cleanup verification, handoff, observation and public curation; not attributed to native AI mathematics'}
    save(yoh/'PROVENANCE.json',proof_meta);save(math/'PROVENANCE.json',proof_meta)
    # Scientific programs/configurations can be read directly as well as via blobs.
    world=ORIGINAL/'run/world/files'
    for team in('theory','application'):
        for path in(world/team).glob('*'):
            if not path.is_file()or path.name.endswith('.tex')or not('round3'in path.name):continue
            if path.suffix=='.py'or path.suffix=='.json':copy_verified(path,yoh/'code'/team/path.name)
    copy_verified(BASE/'public_reproduce.py',yoh/'reproduce.py')
    for name in('ENGINEERING-VALIDATION.json','PARENT-TURN-QUERY.json'):
        copy_verified(BASE/name,yoh/'provenance'/name)
    index={'root':str(root),'yohaku':str(yoh),'math':str(math),'yohaku_repo_path':YOH_PATH,'math_repo_path':MATH_PATH,'knowledge_event_prefix':status['knowledge_event_prefix'],'classification':status['classification'],'artifacts':artifact_index,'mathematical_entries':[{k:e[k]for k in('id','revision','title','summary')}for e in latest.values()],'native_tasks':models,'collected_at':time.time(),'publication_not_yet_performed':True}
    save(BASE/'PUBLIC-STAGING.json',index)
    print(json.dumps({'staging':str(root),'classification':status['classification'],'artifacts':len(artifact_index),'snapshots':len(source_manifest),'math_entries':len(latest),'files':sum(p.is_file()for p in root.rglob('*'))},ensure_ascii=False))

if __name__=='__main__':collect()
