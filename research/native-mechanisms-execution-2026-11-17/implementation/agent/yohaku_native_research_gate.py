"""Sol-only native research authority, independent of historical credit ledgers."""
import contextlib, hashlib, json, os, re, time
from pathlib import Path
from batch_budget_guard import locked, atomic
from yohaku_workflow_gate import GateError, GateStopped, digest

FORMAT='yohaku-native-two-team-sol/1'
TERMINAL={'done','error','cancelled','unknown'}

class NativeGate:
    native_stage=True
    mixed=False
    seed_stage=False
    autonomous=True
    continuation=False
    pooled=False
    def __init__(self,path):
        self.path=Path(path).resolve(strict=True)
        raw=self.path.read_bytes();self.sha=hashlib.sha256(raw).hexdigest();self.policy=json.loads(raw)
        p=self.policy;self.state=Path(p['state_path'])
        if self.sha!=os.environ.get('YOHAKU_WORKFLOW_POLICY_SHA256') or p['format']!=FORMAT:raise GateError('Native policy identity differs')
        world=Path(p['world']).resolve(strict=True)
        if self.path.is_relative_to(world) or self.state.resolve().is_relative_to(world):raise GateError('Authority cannot live in research world')
        if p['model']!='gpt-6.1-sol' or p['floor']!='high' or p['leader_effort']!='max' or p['fallback']!='forbidden':raise GateError('Native model authority differs')
    @contextlib.contextmanager
    def tx(self):
        with locked(self.state):
            if not self.state.is_file() or self.state.is_symlink():raise GateError('Original native state missing; reset forbidden')
            v=json.loads(self.state.read_bytes())
            if v['policy_sha256']!=self.sha:raise GateError('Native state pin differs')
            before=digest(v)
            try:yield v
            finally:
                if digest(v)!=before:atomic(self.state,v)
    def event(self,v,kind,**data):
        v['events'].append({'seq':len(v['events'])+1,'at':time.time(),'kind':kind,**data})
    def check(self,v):
        if Path(self.policy['stop_file']).exists() or v.get('shared_stop') or v['phase']!='open':raise GateStopped('New native admission stopped; original tasks are retained')
        if v.get('first_send_at') and time.time()>v['first_send_at']+self.policy['limits']['seconds']:raise GateStopped('Initial native observation envelope elapsed')
        if any(r['state']=='unknown' for r in v['turns'].values()):raise GateStopped('Original native outcome unknown; no new admission')
    @contextlib.contextmanager
    def admission_guard(self):
        with self.tx() as v:self.check(v);yield v
    def ensure_admission_open(self):
        with self.admission_guard():return {'admission_open':True}
    def cached_profile(self,value):
        if not isinstance(value,dict) or set(value)!={'provider','model','reasoning_effort','budget'}:raise GateError('Exact native profile fields required; fallback forbidden')
        if value['provider']!='openai' or value['model']!='gpt-6.1-sol' or value['reasoning_effort'] not in ('high','xhigh','max'):raise GateError('Only GPT-6.1 Sol High or above; no fallback')
        b=value['budget'];limit=self.policy['limits']
        if not isinstance(b,dict) or set(b)!={'timeout_seconds','max_tool_calls'} or type(b['timeout_seconds'])is not int or not 1<=b['timeout_seconds']<=limit['task_seconds'] or type(b['max_tool_calls'])is not int or not 1<=b['max_tool_calls']<=limit['task_tools']:raise GateError('Worker resource profile exceeds native envelope')
        raw=Path(self.policy['catalog_path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=self.policy['catalog_sha256']:raise GateError('Catalog cache identity differs')
        rows=json.loads(raw)['backends']
        if not any(r.get('configured') and r.get('login',{}).get('state')=='signed_in' and any(m['id']==value['model'] and value['reasoning_effort'] in m['executable_reasoning_efforts']for m in r['models'])for r in rows):raise GateError('Actual host catalog does not authorize requested profile')
        return json.loads(json.dumps(value))
    def validate_scopes(self,scopes,parent=None):
        allowed={s['project_id']:s for s in (self.policy['project_scopes'] if parent is None else parent)}
        if not isinstance(scopes,list) or not scopes or any(allowed.get(s.get('project_id'))!=s for s in scopes):raise GateError('Native project scope expansion denied')
    def reserve_helper(self,actor,binding,request_id,node_id,spec,grant_id=None,work_key=None):
        p=self.cached_profile(spec['profile'])
        if grant_id or work_key:raise GateError('Historical grant identities do not authorize native research')
        with self.admission_guard() as v:
            if actor=='main':
                if node_id!=self.policy['root_node_id'] or request_id!=self.policy['root_create_request']:raise GateError('Host may establish only the original native umbrella lead')
                ids=spec.get('project_ids',[])
                if p['reasoning_effort']!='max':raise GateError('Umbrella lead requires Max')
            else:
                self.check_context(v,binding,actor)
                ids=spec.get('project_ids',[s['project_id']for s in v['members'][actor]['scopes']])
                if re.search(r'负责人|组长|队长|leader|director|\blead\b',spec['role'],re.I) and p['reasoning_effort']!='max':raise GateError('Declared research lead requires Max')
            scopes=[s for s in self.policy['project_scopes']if s['project_id'] in ids]
            self.validate_scopes(scopes,None if actor=='main' else v['members'][actor]['scopes'])
            if len(scopes)!=len(set(ids)):raise GateError('Unknown project requested')
            if len(v['members'])>=self.policy['limits']['nodes']:raise GateStopped('Native node capacity envelope reached')
            if node_id in v['members']:raise GateError('Creation already reserved; query original ID')
            v['members'][node_id]={'state':'reserved','actor':actor,'request_id':request_id,'profile':p,'scopes':scopes,'spec':spec}
            self.event(v,'native_node_reserved',node_id=node_id,created_by=actor,profile=p,scopes=scopes)
    def registered_helper(self,actor,request_id,node_id):
        with self.tx() as v:
            m=v['members'][node_id]
            if m['actor']!=actor or m['request_id']!=request_id:raise GateError('Creation provenance differs')
            if m['state']!='registered':m['state']='registered';self.event(v,'native_node_registered',node_id=node_id,created_by=actor)
    def binding(self,op):return {k:op[k]for k in ('experiment_id','node_id','task_id','operation_id','policy_sha256')}
    def check_context(self,v,binding,node_id=None):
        op=v['starts'].get((binding or {}).get('operation_id'))
        if not op or self.binding(op)!=binding or (node_id is not None and op['node_id']!=node_id):raise GateError('Native task/node provenance differs')
        return op
    def reserve_start(self,actor,binding,node_id,request_id,task_id,spec,profile,scopes,grant_id=None,work_key=None,route='dispatch'):
        self.cached_profile(profile)
        if grant_id or work_key:raise GateError('Legacy grants cannot expand native authority')
        with self.admission_guard() as v:
            m=v['members'].get(node_id)
            if not m or m['state']!='registered':raise GateError('Native node not registered')
            if actor!='main':self.check_context(v,binding,actor)
            elif node_id!=self.policy['root_node_id']:raise GateError('Host only consumes explicit AI continuation requests through original actor binding')
            self.validate_scopes(scopes,None if actor=='main' else v['members'][actor]['scopes'])
            if scopes!=m['scopes']:raise GateError('Native dispatch scope differs from creation')
            leads={self.policy['root_node_id'],*v['leaders'].values()}
            declared_lead=bool(re.search(r'负责人|组长|队长|leader|director|\blead\b',m['spec']['role'],re.I))
            if (node_id in leads or declared_lead) and profile['reasoning_effort']!='max':raise GateError('Bound or declared research leader must remain Max on every dispatch')
            if any(op['node_id']==node_id and op['state'] not in ('done','error','cancelled')for op in v['starts'].values()):raise GateError('Node pending/unknown; query original ID')
            if len(v['starts'])>=self.policy['limits']['turns']:raise GateStopped('Native admitted-attempt envelope reached')
            active=sum(op['state']not in TERMINAL for op in v['starts'].values())
            if active>=self.policy['limits']['concurrent']:raise GateStopped('Native concurrency busy; request stays pending')
            oid=node_id+':'+request_id
            if oid in v['starts']:raise GateError('Native dispatch identity already reserved; no replay')
            op={'experiment_id':self.policy['experiment_id'],'node_id':node_id,'task_id':task_id,'operation_id':oid,'policy_sha256':self.sha,'state':'reserved','exact_input':spec,'profile':profile,'scopes':scopes,'submitted_by':actor,'source_binding':binding,'route':route,'at':time.time()}
            v['starts'][oid]=op;self.event(v,'native_dispatch_reserved',node_id=node_id,request_id=request_id,task_id=task_id,actor=actor,route=route)
            return self.binding(op)
    def execution_task(self,binding):
        with self.tx() as v:return self.check_context(v,binding)['exact_input']['task']
    def start_enter(self,binding,task_id,host_request_id):
        with self.admission_guard() as v:
            op=self.check_context(v,binding)
            if op['task_id']!=task_id or op['state']!='reserved':raise GateError('Native start already entered; no replay')
            op.update(state='entered',host_request_id=host_request_id);self.event(v,'native_worker_entered',task_id=task_id)
    def validate_start(self,binding,task_id):
        with self.admission_guard() as v:
            op=self.check_context(v,binding)
            if op['task_id']!=task_id or op['state']!='entered':raise GateError('No original entered native task')
    def verify_task_context(self,node_context,task_id):
        from yohaku_codex_tasks import read_record
        if read_record(task_id).get('node_context')!=node_context:raise GateError('Private native context differs')
        self.cached_profile(node_context['profile'])
        with self.admission_guard() as v:
            op=self.check_context(v,node_context.get('workflow'),node_context['node_id'])
            if op['state']!='entered' or op['task_id']!=task_id or op['profile']!=node_context['profile'] or op['scopes']!=node_context['project_scopes']:raise GateError('Native worker context mismatch')
        return node_context['workflow']
    def note_outcome(self,binding,status,evidence):
        with self.tx() as v:
            op=self.check_context(v,binding)
            if op['state'] in TERMINAL:
                if op['state']!=status:raise GateError('Original task terminal cannot change')
                return
            op.update(state=status,evidence=evidence,finished_at=time.time());self.event(v,'native_task_terminal',task_id=op['task_id'],status=status,evidence=evidence)
            if status!='done':v['shared_stop']={'reason':'Original native task failed; inspect before new admission','task_id':op['task_id'],'at':time.time(),'new_dispatch_allowed':False}
    def request_shared_stop(self,reason,evidence,**kwargs):
        with self.tx() as v:
            if not v.get('shared_stop'):v['shared_stop']={'reason':reason,'evidence':evidence,'at':time.time(),'new_dispatch_allowed':False};self.event(v,'native_admission_drained',stop=v['shared_stop'])
            return v['shared_stop']
    def shared_stop_status(self):
        with self.tx() as v:return v.get('shared_stop')
    def status(self,actor='main',binding=None):
        with self.tx() as v:
            if actor!='main':self.check_context(v,binding,actor)
            return {'experiment_id':self.policy['experiment_id'],'phase':v['phase'],'shared_stop':v.get('shared_stop'),'leaders':v['leaders'],'members':list(v['members']),'native_turns_reserved':len(v['turns']),'native_turns_remaining':self.policy['limits']['turns']-len(v['turns']),'remaining_seconds':max(0,self.policy['limits']['seconds']-(time.time()-v['first_send_at']))if v.get('first_send_at')else self.policy['limits']['seconds'],'provider_identity':'unknown; requested/native thread configuration separately recorded','provider_cost':'unknown','adaption_authority_used':False}
    def observe_tool(self,binding,name,args,result):
        with self.tx() as v:self.check_context(v,binding);self.event(v,'native_tool_return',task_id=binding['task_id'],name=name,arguments=args,result=result)
    def bind_team(self,actor,binding,team,node_id):
        if team not in ('theory','application') or actor!=self.policy['root_node_id']:raise GateError('Only native umbrella lead can bind the two user-requested directions')
        with self.admission_guard() as v:
            self.check_context(v,binding,actor);m=v['members'][node_id]
            if m['actor']!=actor or m['profile']['reasoning_effort']!='max' or not any(s['project_id']==self.policy['team_projects'][team]for s in m['scopes']):raise GateError('Direction lead needs native root provenance, Max and project scope')
            if team in v['leaders'] and v['leaders'][team]!=node_id:raise GateError('Direction already bound; preserve original provenance')
            v['leaders'][team]=node_id;self.event(v,'direction_bound_by_native_lead',actor=actor,team=team,node_id=node_id,source_task=binding['task_id'])
            return {'team':team,'node_id':node_id,'required_effort':'max','bound_by_native_task':binding['task_id']}
    def validate_wake(self,actor,binding,wake,authorizations):
        if not wake:return
        with self.admission_guard() as v:
            self.check_context(v,binding,actor)
            for nid in wake:
                if nid not in v['members']:raise GateError('Wake target outside native scope')
                self.validate_scopes(v['members'][nid]['scopes'],v['members'][actor]['scopes'])
                if any(op['node_id']==nid and op['state']not in ('done','error','cancelled')for op in v['starts'].values()):raise GateError('Wake target pending/unknown; query original task before saving a wake')
    def compose_wake(self,actor,binding,target,grant_id,work_key,conversation):
        self.validate_wake(actor,binding,[target],{})
        return json.dumps({'instruction':'Respond to the original peer message as your durable Yohaku node; choose your own next work.','conversation':conversation},ensure_ascii=False)
    def native_reserve(self,binding,identity,profile):
        self.cached_profile(profile)
        with self.admission_guard() as v:
            op=self.check_context(v,binding)
            if op['state']!='entered' or op['profile']!=profile or identity!=op['task_id']+':native:0' or identity in v['turns']:raise GateError('Native turn identity/profile reserved or mismatched')
            if len(v['turns'])>=self.policy['limits']['turns']:raise GateStopped('Native turn envelope reached')
            row={'identity':identity,'binding':binding,'profile':profile,'state':'reserved','reserved_at':time.time(),'tools':{}}
            v['turns'][identity]=row;self.event(v,'native_turn_reserved',identity=identity);return row
    def final_send(self,identity,value,expected_parameters_sha256):
        with self.admission_guard() as v:
            row=v['turns'].get(identity)
            if not row or row['state']!='reserved' or row.get('send_attempted'):raise GateError('Original native send pending/unknown/already attempted; no replay')
            op=self.check_context(v,row['binding']);p=value.get('params',{});profile=row['profile']
            self.cached_profile(profile);self.validate_scopes(op['scopes'])
            if op['state']!='entered' or value.get('method')!='turn/start' or set(p)!={'threadId','input','approvalPolicy','permissions','model','effort'} or digest(p)!=expected_parameters_sha256:raise GateError('Final native wire parameters differ from admitted original')
            if p['model']!=profile['model'] or p['effort']!=profile['reasoning_effort'] or p['permissions']!='yohaku-control' or p['approvalPolicy']!='never':raise GateError('Final native model/effort/permission downgrade denied')
            if op['node_id'] in {self.policy['root_node_id'],*v['leaders'].values()} and p['effort']!='max':raise GateError('Final leader Max floor violated')
            row.update(send_attempted=True,state='attempting',rpc_id=value.get('id'),thread_id=p['threadId'],payload_sha256=digest(value),send_attempted_at=time.time())
            if not v.get('first_send_at'):v['first_send_at']=time.time()
            self.event(v,'native_turn_start_pre_write_admitted',identity=identity,thread_id=p['threadId'],model=p['model'],effort=p['effort'],permissions=p['permissions'],rpc_id=value.get('id'))
            return dict(row)
    def native_event(self,identity,event,**evidence):
        with self.tx() as v:
            row=v['turns'][identity]
            if event=='usage':row['usage']=evidence;return
            if row['state'] in ('completed','failed','unknown','definitely_not_sent'):raise GateError('Original native terminal cannot be replaced')
            if event=='started' and row['state']!='attempting':raise GateError('No native send attempt for acknowledgment')
            row.update(state=event,last_evidence=evidence);self.event(v,'native_'+event,identity=identity,**evidence)
            if event=='unknown':v['shared_stop']={'reason':'Native outcome unknown; original ID retained','identity':identity,'at':time.time(),'new_dispatch_allowed':False}
    def native_tool_admit(self,identity,call_id,name,args):
        with self.tx() as v:
            row=v['turns'][identity]
            if row['state']!='started':raise GateError('Native task not active')
            fp=digest([name,args]);prior=row['tools'].get(call_id)
            if prior:
                if prior['fingerprint']!=fp:raise GateError('Tool request ID input conflict')
                return {'execute':False,'duplicate':True,'error':'Original tool call already reserved; no replay'}
            if len(row['tools'])>=self.policy['limits']['task_tools']:return {'execute':False,'error':'Per-task tool resource envelope reached'}
            row['tools'][call_id]={'name':name,'fingerprint':fp,'at':time.time()}
            return {'execute':True,'call_id':call_id}

def bind_native_config(config,root,profile):
    from yohaku_codex_linux import is_linux_codex
    client=json.loads((Path(root)/'runtime/CODEX-DEVELOPMENT.json').read_bytes());entry=Path(client['entry'])
    if not entry.is_file() or entry.is_symlink() or hashlib.sha256(entry.read_bytes()).hexdigest()!=client['entry_sha256'] or not is_linux_codex(str(entry)):raise GateError('Pinned native client dependency differs')
    from yohaku_workflow_gate import gate
    gate().cached_profile(profile)
    return dict(config,codex_entry=str(entry),protocol='codex-local',model=profile['model'],reasoning_effort=profile['reasoning_effort'],turn_timeout=profile['budget']['timeout_seconds'],max_tool_calls=profile['budget']['max_tool_calls'])