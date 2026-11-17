"""Native task-bound shared mathematics, external seed reads and continuation."""
import hashlib,json,os,time,urllib.request
from pathlib import Path
from yohaku_workflow_gate import gate,digest
from yohaku_shared_math import Knowledge

def service(g=None):
    g=g or gate();return Knowledge(g.policy['knowledge_db'],g.policy['experiment_id'])

def actor_context(node,task_id,world):
    from yohaku_experiment_groups import Groups
    g=gate();group=Groups(world).group_for(node['node_id'])
    if str(Path(world).resolve())!=g.policy['world'] or group!=g.policy['group_id']:raise ValueError('Native actor is outside umbrella research group')
    with g.tx()as v:
        op=g.check_context(v,node.get('workflow'),node['node_id'])
        if op['task_id']!=task_id or op['profile']!=node['profile']:raise ValueError('Native tool provenance differs')
        team=next((t for t,nid in v['leaders'].items()if nid==node['node_id']),None)
    return {'experiment_id':g.policy['experiment_id'],'group_id':group,'team':team,'actor_node_id':node['node_id'],'task_id':task_id}

def seed_read(g,k,actor,args):
    index=json.loads(Path(g.policy['seed_index']).read_bytes())
    sources={s['fixed_source_url']:s for item in index['items']for s in item['sources']}
    source=sources.get(args['source_url'])
    if source is None:raise ValueError('Choose an exact fixed source URL from seed_index; arbitrary imports are not authorized')
    cache=Path(g.policy['source_cache'])/source['sha256']
    if not cache.exists():
        repo=source['fixed_source_url'].removeprefix('https://github.com/').split('/blob/',1)
        if len(repo)!=2:raise ValueError('Unsupported fixed seed URL')
        url='https://raw.githubusercontent.com/'+repo[0]+'/'+repo[1]
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Yohaku-native-seed-reader'}),timeout=45)as response:raw=response.read(5_000_001)
        if len(raw)>5_000_000 or hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('Fixed seed source bytes/hash differ; preserve and report')
        cache.parent.mkdir(parents=True,exist_ok=True);temp=cache.with_suffix('.partial-'+str(os.getpid()));temp.write_bytes(raw);temp.replace(cache)
        k.record({'actor_node_id':'HOST'},'external_seed_source_cached',{'source':source,'sha256':source['sha256'],'retrieval_at':time.time(),'native_run_id':g.policy['experiment_id']})
    raw=cache.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('Seed cache changed')
    body=raw.decode();offset=max(0,int(args.get('offset',0)));size=min(32768,max(1,int(args.get('max_chars',16000))))
    page=body[offset:offset+size]
    event=k.record(actor,'actual_read',{'kind':'external_seed_source_page','source':source,'offset':offset,'chars':len(page),'total_chars':len(body),'body_sha256':source['sha256'],'result_returned_is_not_adoption':True})
    return {'source':source,'text':page,'offset':offset,'next_offset':offset+len(page)if offset+len(page)<len(body)else None,'actual_read_event':event,'origin':'external_chatgpt_work','adoption_recorded':False}

def wrap_tools(tools,workspace,node,task_id):
    from yohaku_ai_nodes import definition
    from yohaku_experiment_groups import Groups
    g=gate();k=service(g);actor=actor_context(node,task_id,workspace.root)
    banned={'ai_workflow_request','ai_workflow_status','ai_workflow_snapshot_read','ai_workflow_report_use','ai_await_helper','ai_review_index','ai_review_read','ai_review_respond'}
    from yohaku_browser import NAMES as browser_names
    tools.definitions=[d for d in tools.definitions if d['name']not in banned|browser_names]
    for d in tools.definitions:
        d['description']=d['description'].split(' In this pilot,')[0]
        if d['name'] in ('ai_node_create','ai_node_dispatch'):
            for name in ('grant_id','work_key'):d['parameters']['properties'].pop(name,None)
        if d['name']=='ai_message_send':
            d['parameters']['properties'].pop('wake_authorizations',None)
            d['description']+=' Native research wake uses the recipient profile and stage admission; no historical grants. Pure messages never start a model.'
    s={'type':'string'};integer={'type':'integer','minimum':1};ref={'type':'object','properties':{'id':s,'revision':integer},'required':['id','revision'],'additionalProperties':False};refs={'type':'array','items':ref}
    extra=[
        definition('math_search','Search the common versioned mathematics index; summaries are not body reads.',{'query':s,'limit':integer,'offset':{'type':'integer','minimum':0}}),
        definition('math_read','Read the exact common mathematical entry and its provenance; records a body read, never adoption.',{'id':s,'revision':integer},('id',)),
        definition('math_publish','Publish definitions, proofs, counterexamples, code, computations, methods or failures for both directions immediately. Supply conditions and evidence. Publishing is not approval. Keep organization records in project files.',{**{key:s for key in ('request_id','id','title','summary','body','scope','conditions','claim_kind','author_status','evidence')},'related':refs,'supersedes':ref,'relation':{'type':'object','properties':{'premises':refs,'conclusions':refs,'relation_type':s,'basis':s},'required':['premises','conclusions','relation_type','basis'],'additionalProperties':False}},('request_id','title','summary','body','scope','conditions','claim_kind','author_status','evidence')),
        definition('math_challenge','Retain a challenge to an exact mathematical version.',{'id':s,'revision':integer,'reason':s,'evidence':s},('id','revision','reason','evidence')),
        definition('math_review','Record an independent review assertion after reading the exact body; an author cannot review its own entry.',{'id':s,'revision':integer,'decision':s,'evidence':s},('id','revision','decision','evidence')),
        definition('math_adopt','Record claimed use of an exact version, linked to a source/artifact. Actual later artifact evidence remains separate.',{'id':s,'revision':integer,'artifact':s,'explanation':s},('id','revision','artifact','explanation')),
        definition('math_lease','Optional expiring work lease; independent review bypasses duplication control.',{'mathematical_target':s,'purpose':s,'seconds':integer},('mathematical_target','purpose')),
        definition('seed_index','Read complete external-seed metadata with exact fixed source URLs and hashes. No body source read is inferred.',{'id':s}),
        definition('seed_read','Read a page of a fixed external seed proof/code/checkpoint. Exact URL must occur in seed_index; fetched bytes must match its pinned hash.',{'source_url':s,'offset':{'type':'integer','minimum':0},'max_chars':integer},('source_url',)),
        definition('research_team_bind','Umbrella lead binds its own native-created Max node as the user-requested theory/application direction lead. This does not dispatch or prescribe a workflow.',{'team':{'type':'string','enum':['theory','application']},'node_id':s},('team','node_id')),
        definition('research_resources','Read actual stage/model/resource bindings and remaining initial envelope; no new authorization.',{}),
        definition('research_continue','Queue your own explicitly chosen next work for yourself or a granted peer after its current task finishes. Host only consumes this request, preserving original actor/task provenance; no automatic next task.',{'request_id':s,'task':s,'node_id':s},('request_id','task')),
        definition('research_finish','Record your own decision to finish or sleep, reason and open questions; no other node is ended.',{'reason':s,'open_questions':s},('reason','open_questions'))]
    tools.definitions.extend(extra);extra_names={d['name']for d in extra}
    tools.node_system=g.policy['common_instructions'];original=tools.call
    versions={}
    def call(name,args):
        try:
            if name in ('ai_node_create','ai_node_dispatch','ai_message_send') and (name!='ai_message_send' or args.get('wake')):g.ensure_admission_open()
            if args.get('profile')is not None:g.cached_profile(args['profile'])
            if name in ('ai_node_dispatch','ai_node_status','ai_node_stop','ai_node_history','ai_node_memory_read','ai_node_memory_write','ai_node_compact','ai_message_send','ai_chat_create','research_continue'):
                targets=([args['node_id']]if args.get('node_id')else[])+args.get('wake',[])+args.get('participants',[])
                for target in targets:Groups(workspace.root).same_group(node['node_id'],target)
            if name=='research_team_bind':result={'ok':True,'result':g.bind_team(node['node_id'],node['workflow'],**args)}
            elif name=='research_resources':result={'ok':True,'result':g.status(node['node_id'],node['workflow'])}
            elif name=='seed_index':
                index=json.loads(Path(g.policy['seed_index']).read_bytes());items=[i for i in index['items']if not args.get('id') or i['id']==args['id']]
                k.record(actor,'seed_index_returned',{'ids':[i['id']for i in items],'index_sha256':g.policy['seed_index_sha256']});result={'ok':True,'result':{'items':items,'native_import_id':g.policy['seed_import_id'],'origin':'external_chatgpt_work'}}
            elif name=='seed_read':result={'ok':True,'result':seed_read(g,k,actor,args)}
            elif name in extra_names:result={'ok':True,'result':k.call(actor,name,args)}
            else:result=original(name,args)
        except Exception as exc:result={'ok':False,'error':str(exc),'error_type':type(exc).__name__,'replay_unknown_request':False}
        event=k.record(actor,'native_tool_completed',{'name':name,'arguments':args,'result':result})
        for scope in node['project_scopes']:
            for path in (Path(workspace.root)/scope['root']).rglob('*.tex'):
                if not path.is_file()or path.is_symlink():continue
                raw=path.read_bytes();revision=hashlib.sha256(raw).hexdigest();source=str(path.relative_to(workspace.root))
                if versions.get(source)==revision:continue
                dest=Path(g.policy['versions_dir'])/revision
                if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
                k.record(actor,'file_version_observed',{'source':source,'revision':revision,'archive':str(dest),'prior_revision':versions.get(source),'after_tool':name,'tool_event':event});versions[source]=revision
        return result
    tools.call=call
    k.record(actor,'worker_tools_bound',{'profile':node['profile'],'project_scopes':node['project_scopes'],'tools':[d['name']for d in tools.definitions],'shared_math':g.policy['knowledge_db'],'native_run_id':g.policy['experiment_id']})
    if g.policy.get('program_budget'):
        from mechanisms_host import wrap
        return wrap(tools,workspace,node,task_id)
    return tools
