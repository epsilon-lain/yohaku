"""Host adapter for the isolated mechanisms candidate; old runtime untouched."""
import contextvars,hashlib,json,os,socket,time
from pathlib import Path
SLOT=contextvars.ContextVar('mechanisms_program_slot',default=None)
def rpc(path,data):
    with socket.socket(socket.AF_UNIX)as s:
        s.settimeout(30);s.connect(path);s.sendall((json.dumps(data)+'\n').encode());raw=b''
        while not raw.endswith(b'\n'):
            p=s.recv(65536)
            if not p:raise RuntimeError('Program budget server unavailable; no unmetered fallback')
            raw+=p
    r=json.loads(raw)
    if not r['ok']:raise ValueError(r['error'])
    return r['result']
def budget_binding(world,project,action,request_id,snapshot,plan):
    slot=SLOT.get()
    if not slot:raise ValueError('This runtime requires task_submit.budget_allocation_id; allocate before execution')
    assert project['tasks'][action]['kind']=='python','This metered phase supports Python projects only; no unmetered fallback'
    from yohaku_project_tasks import digest
    tid='project-task-'+digest((str(Path(world).resolve())+'\0'+request_id).encode())[:32]
    r=rpc(slot['socket'],dict(op='bind',allocation=slot['allocation'],actor=slot['actor'],model_task=slot['model_task'],
        project=project['id'],task=tid,source_set=snapshot['source_set']))
    return dict(allocation=r['id'],search_cap=r['search_cap'],verification_cap=r['verification_cap'],socket=slot['socket'],
        deadline=slot['deadline'],guard_root=slot['guard_root'],guard_hashes=slot['guard_hashes'],
        source_set=snapshot['source_set'],task_id=tid,model_task=slot['model_task'],actor=slot['actor'])
def guard_mounts(binding):
    root=Path(binding['guard_root'])
    for name,expected in binding['guard_hashes'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,'Immutable meter changed'
    assert Path(binding['socket']).is_socket()
    return ['--ro-bind',str(root),'/budget-runtime','--ro-bind',binding['socket'],'/budget.sock']
def receipt(binding):
    guard_mounts(binding)
    r=rpc(binding['socket'],dict(op='status'))
    return dict(binding=binding,shared=r,actual_calls_separate_from_nonrefundable_issued_leases=True)

def wrap(tools,workspace,node,task_id):
    from yohaku_ai_nodes import definition,Control
    from yohaku_workflow_gate import gate
    from yohaku_native_research_runtime import service,actor_context
    g=gate();p=g.policy;cfg=p['program_budget'];k=service(g);actor=actor_context(node,task_id,workspace.root)
    s={'type':'string'};count={'type':'integer','minimum':0}
    for d in tools.definitions:
        if d['name']=='task_submit':
            d['parameters']['properties']['budget_allocation_id']=s
            d['parameters']['required'].append('budget_allocation_id')
            d['description']+=' This phase requires a host-authorized per-producer program budget allocation. All Python subprocesses are metered; failed/retried producers keep their charges.'
    extra=[
        definition('program_budget_allocate','Reserve a share of the ONE stage-wide 2000000 search / 50000 verification apply cap before a producer. New team/retry never resets it. Bind once to one immutable source_set/producer. Allot zero search/verification for pure math with no moves.',
            dict(request_id=s,project_id=s,node_id=s,search_apply=count,verification_apply=count,purpose=s),('request_id','project_id','search_apply','verification_apply','purpose')),
        definition('program_budget_status','Read actual reported calls, conservative issued leases, allocations, unresolved liabilities and remaining shared ceilings. This is not new authority.',{}),
        definition('mechanism_sources_index','Search fixed external source metadata before reading bodies. External cloud results remain external. No body read or adoption is inferred.',dict(query=s,offset=count,limit={'type':'integer','minimum':1})),
        definition('mechanism_source_read','Read a precise page of one fixed hash source; optionally import its complete body as an authoritative .tex into one granted project for code execution. Returns exact common-entry ID and revision; body reads/adoption separate.',
            dict(origin={'type':'string','enum':['workflow','math']},path=s,project_id=s,offset=count,max_chars={'type':'integer','minimum':1}),('origin','path'))]
    tools.definitions.extend(extra);original=tools.call
    def call(name,args):
        if name not in {d['name']for d in extra}and name not in('task_submit','research_resources'):return original(name,args)
        try:
            if name=='program_budget_allocate':
                g.ensure_admission_open();nid=args.get('node_id')or node['node_id']
                with g.tx()as v:
                    assert nid in v['members'];g.validate_scopes(v['members'][nid]['scopes'],v['members'][node['node_id']]['scopes'])
                r=rpc(cfg['socket'],dict(op='allocate',actor=node['node_id'],model_task=task_id,request_id=args['request_id'],
                    node=nid,project=args['project_id'],search=args['search_apply'],verification=args['verification_apply'],purpose=args['purpose']))
                result={'ok':True,'result':r}
            elif name=='program_budget_status':result={'ok':True,'result':rpc(cfg['socket'],dict(op='status'))}
            elif name=='research_resources':
                result=original(name,args)
                with g.tx()as v:
                    op=g.check_context(v,node['workflow']);turn=next((t for t in v['turns'].values()if t['binding']['task_id']==task_id),{})
                start=turn.get('send_attempted_at')or op['at'];elapsed=time.time()-start
                result['result']['this_task_elapsed_seconds']=elapsed;result['result']['this_task_seconds_remaining']=max(0,node['profile']['budget']['timeout_seconds']-elapsed)
                result['result']['program_budget']=rpc(cfg['socket'],dict(op='status'))
                return result
            elif name=='task_submit':
                allocation=args['budget_allocation_id'];plain={key:value for key,value in args.items()if key!='budget_allocation_id'}
                with g.tx()as v:deadline=v['first_send_at']+5400
                token=SLOT.set(dict(allocation=allocation,actor=node['node_id'],model_task=task_id,socket=cfg['socket'],
                    deadline=deadline,guard_root=cfg['guard_root'],guard_hashes=cfg['guard_hashes']))
                # The extended definition is shared with the base validator.
                # Keep the allocation argument through validation; Project/Task
                # reads only its existing named fields and the host SLOT binds it.
                try:result=original(name,args)
                finally:SLOT.reset(token)
                return result
            else:
                catalog=json.loads(Path(p['mechanism_catalog']).read_bytes());rows=catalog['files']
                if name=='mechanism_sources_index':
                    q=args.get('query','').casefold();rows=[r for r in rows if q in(r['origin']+'/'+r['path']).casefold()];offset=args.get('offset',0);limit=min(40,args.get('limit',12));result={'ok':True,'result':dict(total=len(rows),files=rows[offset:offset+limit],next_offset=offset+limit if offset+limit<len(rows)else None,bodies_read=False)}
                else:
                    row=next(r for r in rows if r['origin']==args['origin']and r['path']==args['path']);raw=Path(row['local']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];body=raw.decode()
                    pid=args.get('project_id');authorities=[]
                    if pid:
                        scope=next(s for s in node['project_scopes']if s['project_id']==pid);source=scope['root']+'/r6-inputs/'+row['origin']+'/'+row['path']+'.tex'
                        ctrl=Control(workspace.root);target=Path(workspace.root)/source
                        if target.exists():back=ctrl.read(source);assert back['body']==body
                        else:back=ctrl.write(source,body,node=dict(id='r6-'+hashlib.sha256(source.encode()).hexdigest()[:24],name=row['path'],description='Fixed external cloud source; not native result',entry=False))
                        assert back['valid'];authorities.append(dict(source=source,revision=back['revision']))
                    eid='external/mechanisms-20261117/source/'+row['origin']+'/'+row['path']
                    with k.tx()as db:
                        found=db.execute('SELECT value FROM entries WHERE id=?AND revision=1',(eid,)).fetchone()
                        if not found:
                            entry=dict(id=eid,revision=1,title=row['origin']+'/'+row['path'],summary='Fixed external cloud source, read body only when needed',body=body,scope='external mechanisms source',conditions='Keep hash/source and native adoption separate',claim_kind='external_source',author_status='External cloud author, not a native discovery',independent_review_status='fixed source bytes verified, not new peer review',source_group='EXTERNAL',source_task=None,author_node='EXTERNAL_SOURCE',body_sha256=row['sha256'],at=time.time(),source=row,authoritative_files=authorities)
                            db.execute('INSERT INTO entries VALUES(?,?,?)',(eid,1,json.dumps(entry,ensure_ascii=False)))
                    offset=args.get('offset',0);size=min(60000,args.get('max_chars',12000));page=body[offset:offset+size]
                    result={'ok':True,'result':dict(id=eid,revision=1,source=row,authoritative_files=authorities,body_sha256=row['sha256'],text=page,offset=offset,total_characters=len(body),next_offset=offset+len(page)if offset+len(page)<len(body)else None,adoption_recorded=False)}
        except Exception as exc:result={'ok':False,'error':str(exc)or type(exc).__name__,'error_type':type(exc).__name__,'replay_unknown_request':False}
        k.record(actor,'native_tool_completed',dict(name=name,arguments=args,result=result));return result
    tools.call=call
    return tools
