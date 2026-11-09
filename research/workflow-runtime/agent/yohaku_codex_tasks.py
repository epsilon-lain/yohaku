"""Host-owned independent Codex tasks bound one-to-one to existing Rust chat requests.

Business status/output/error live ONLY in the Loom chat object. Private records
hold ownership, process identity and cleanup evidence, never account credentials.
"""
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
VERSION='host-codex-tasks-collaboration-v2'
MODULE_REVISION=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
TERMINAL={'done','error','cancelled','unknown'}


def state_root():
    p=Path.home()/'.local/state/yohaku/model-tasks';p.mkdir(mode=0o700,parents=True,exist_ok=True)
    if p.is_symlink() or p.stat().st_uid!=os.getuid() or p.stat().st_mode&0o077:raise ValueError('Task state must be private and owned')
    return p


def atomic(path,value):
    fd,temp=tempfile.mkstemp(prefix='.task-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(value,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def task_path(task_id):
    if not isinstance(task_id,str) or not re.fullmatch(r'model-task-[0-9a-f]{32}',task_id):raise ValueError('Invalid task id; no process targeted')
    return state_root()/(task_id+'.json')


@contextlib.contextmanager
def locked(task_id):
    p=task_path(task_id)
    fd=os.open(str(p)+'.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:fcntl.flock(fd,fcntl.LOCK_EX);yield p
    finally:os.close(fd)


def read_record(task_id):
    p=task_path(task_id)
    if not p.is_file() or p.is_symlink():raise ValueError('Unknown task id; no process targeted')
    return json.loads(p.read_text())


def patch_record(task_id,**fields):
    with locked(task_id) as path:
        value=read_record(task_id);value.update(fields);atomic(path,value);return value


def identity(pid):
    try:
        s=(Path('/proc')/str(pid)/'stat').read_text().split(') ')[1].split()
        return {'pid':pid,'start':s[19],'state':s[0]}
    except (OSError,ValueError,IndexError):return None


def alive(record):
    current=identity(record.get('pid'))
    return bool(current and current['start']==record.get('start') and current['state']!='Z')


class Object:
    def __init__(self,world):
        self.world=Path(world).resolve(strict=True)
        source=self.world/'files/chat-runtime-20261025/requests.json.tex'
        # First use of a valid new world must initialize the same authoritative chat object.
        cursor=self.world
        for part in source.relative_to(self.world).parts:
            cursor=cursor/part
            if cursor.is_symlink():raise ValueError('World chat object path must not contain symlinks')
        gate=state_root()/('object-init-'+hashlib.sha256(str(self.world).encode()).hexdigest()+'.lock')
        with gate.open('a+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            if not source.exists():
                if source.with_suffix('').exists():raise ValueError('Untracked chat output exists; preserve it, explicit adoption required')
                from yohaku_agent import Workspace
                result=Workspace(self.world,ROOT/'bin/loom-linux-x86_64',ROOT/'bin/yohaku_chat_workspace').execute({'command':'create','directory':'files/chat-runtime-20261025','name':'requests.json','body':json.dumps({'format':'yohaku-chat-requests/1','next_request':1,'requests':[]})+'\n'})
                if result.get('sync_error') or result.get('loom',{}).get('ok') is False:raise ValueError('Chat source saved but Loom generation failed; no model started')
        if not source.is_file() or source.resolve()!=source:raise ValueError('World chat object source must exist without symlinks')
        if source.with_suffix('').is_symlink():raise ValueError('World chat output must not be a symlink')
        control=source.parent/'control'
        if control.is_symlink() or (control/'object.lock').is_symlink():raise ValueError('World chat control path must not use symlinks')
        # Execute only this reviewed host copy, never import executable code from the world.
        spec=importlib.util.spec_from_file_location('yohaku_host_chat_object',ROOT/'agent/yohaku_chat_object.py')
        self.adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.adapter)
        self.adapter.WORLD=self.world;self.adapter.WORKSPACE=ROOT/'bin/yohaku_chat_workspace'
        self.adapter.LOOM=ROOT/'bin/loom-linux-x86_64';self.adapter.MACROS=self.world/'macros'
    @contextlib.contextmanager
    def prepared(self):
        import shutil
        temp=self.adapter.prepare()
        try:yield temp
        finally:shutil.rmtree(temp,ignore_errors=True)
    def command(self,request):
        with self.prepared() as temp:return self.adapter.workspace(temp,request)
    def request(self,request_id):return self.command({'command':'chat_status','id':request_id})['request']


class Control:
    def __init__(self,world):self.object=Object(world)
    def call(self,name,args):
        # Existing adapter owns operation routing; it delegates only explicit host_* operations.
        op={'op':{'codex_task_start':'host_start','codex_task_status':'host_status','codex_task_cancel':'host_cancel'}[name],**args}
        self.object.adapter.HOST_TASK_CLIENT=self
        try:return self.object.adapter.execute(op,None)
        except RuntimeError as error:raise ValueError('Chat operation failed or outcome unknown; query by request_id before any new submission: '+str(error)[:600]) from None
    def dispatch(self,op):
        return {'host_start':self.start,'host_status':self.status,'host_cancel':self.cancel}[op['op']](op)
    def task_id_for(self,request_id):
        if not isinstance(request_id,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',request_id):raise ValueError('Invalid request_id')
        return 'model-task-'+hashlib.sha256((str(self.object.world)+'\0'+request_id).encode()).hexdigest()[:32]
    def owned(self,task_id):
        value=read_record(task_id)
        if value['world']!=str(self.object.world):raise ValueError('Task belongs to another world; no process targeted')
        return value
    def start(self,args,*,node_context=None):
        from yohaku_delegation import grant,mode
        if set(args)-{'op','request_id','prompt','mode','context_policy'}:raise ValueError('Unsupported delegation argument')
        policy=args.get('context_policy','world')
        if policy not in ('world','isolated_text','ai_node'):raise ValueError('Unsupported context policy')
        if (policy=='ai_node') != isinstance(node_context,dict):raise ValueError('AI node context requires trusted host dispatch')
        if policy=='isolated_text' and args.get('mode','read_only')!='read_only':raise ValueError('Isolated text tasks cannot grant execution')
        selected=mode(args.get('mode','read_only'))
        request_id=args['request_id']
        if not isinstance(request_id,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',request_id):raise ValueError('Use a unique ASCII request_id of 1..128 characters')
        tid=self.task_id_for(request_id)
        duplicate=False;accepted=True
        with locked(tid) as path:
            if path.exists():
                prior=self.owned(tid);original=self.object.request(request_id)
                if node_context!=prior.get('node_context') or policy!=prior.get('context_policy','world') or (policy in ('isolated_text','ai_node') and args.get('prompt',original['prompt'])!=original['prompt']):raise ValueError('Existing request has different immutable input/context; no replay')
                return {**self.status({'task_id':tid}),'duplicate':True,'started_new_process':False,'prompt_accepted':args.get('prompt',original['prompt'])==original['prompt'],'requested_mode_accepted':selected==self.owned(tid).get('authorization',grant())['mode']}
            authorization=grant(selected)
            if 'prompt' in args:
                submission=self.object.command({'command':'chat_submit','id':request_id,'prompt':args['prompt'],'kind':'independent-model','target':'independent-host-codex','context':None,'history':[],'config':{'delegation':authorization,'context_policy':policy,**({'node_context':node_context} if node_context else {})}})
                duplicate=bool(submission.get('duplicate'));accepted=submission['request']['prompt']==args['prompt']
            request=self.object.request(request_id)
            if request.get('kind')!='independent-model' or request.get('target')!='independent-host-codex':raise ValueError('Only explicitly submitted independent-model requests can be claimed; construction requests unchanged')
            original_grant=request.get('snapshot',{}).get('config',{}).get('delegation') or grant()
            if original_grant!=authorization:raise ValueError('Request has a different immutable delegation grant; use its original task/status, do not upgrade or replay')
            if request['status']!='queued':raise ValueError('Request is not queued and has no owned task binding; inspect it, do not replay')
            # Persist identity before claim or launch. A crash in this interval is unknown, never a retry permit.
            record={'task_id':tid,'world':str(self.object.world),'request_id':request_id,'version':VERSION,'pid':None,'start':None,'launch':'preparing','created':time.time(),'native':[],'authorization':authorization,'context_policy':policy,**({'node_context':node_context} if node_context else {})}
            atomic(path,record)
            if policy=='ai_node':
                from yohaku_experiment_groups import Groups
                groups=Groups(self.object.world)
                if not groups.before_start(node_context['node_id'],tid):
                    self.object.command({'command':'chat_stop','id':request_id,'by':'host-experiment-group'})
                    record.update(launch='queued_cancelled',receipt={'native':[],'native_cleanup_complete':True,'program_sessions':[],'queued_cancelled':True,'finished':time.time()});atomic(path,record)
                    return {**self.status({'task_id':tid}),'started_new_process':False,'stop_outcome':'queued_cancelled','cancel_confirmed':True}
            claim=self.object.command({'command':'chat_claim','id':request_id,'runner':tid,'target':'independent-host-codex'})
            if not claim.get('request'):
                record['launch']='claim_unknown';atomic(path,record);raise ValueError('Claim not obtained; task id reserved, inspect status; no automatic replay')
            record.update(token=claim['token'],launch='claimed');atomic(path,record)
            # No caller argv, config path, login or model override is accepted.
            try:
                log=(state_root()/(tid+'.log')).open('ab')
                try:child=subprocess.Popen([sys.executable,'-B',str(ROOT/'agent/yohaku_codex_tasks.py'),'run',tid],stdin=subprocess.DEVNULL,stdout=log,stderr=log,cwd=ROOT,start_new_session=True)
                finally:log.close()
                process=identity(child.pid)
                record.update(pid=child.pid,start=process['start'] if process else None,launch='spawned');atomic(path,record)
                if policy=='ai_node':groups.after_start(node_context['node_id'])
                threading.Thread(target=child.wait,daemon=True).start()
            except OSError:
                record['launch']='launch_failed';atomic(path,record)
                self.object.command({'command':'chat_update','id':request_id,'token':record['token'],'status':'unknown','error':'Host launch failed after claim; no model replay'})
                raise ValueError('Task launch failed after claim; reserved task must be inspected; no automatic retry') from None
        return {**self.status({'task_id':tid}),'duplicate':duplicate,'prompt_accepted':accepted,'started_new_process':True}
    def status(self,args):
        tid=args.get('task_id') or self.task_id_for(args.get('request_id'));record=self.owned(tid)
        if args.get('request_id') and args['request_id']!=record['request_id']:raise ValueError('Task/request binding mismatch')
        end=time.monotonic()+min(5000,max(0,args.get('wait_ms',0)))/1000
        while True:
            request=self.object.request(record['request_id'])
            if request['status'] in TERMINAL or time.monotonic()>=end:break
            time.sleep(.1);record=self.owned(tid)
        record=self.owned(tid)
        receipt=record.get('receipt');running=alive(record)
        reply=request.get('reply') or {};text=reply.get('text','') if isinstance(reply,dict) else ''
        if not isinstance(text,str):text=''
        cursor=max(0,args.get('cursor',0));limit=min(16384,max(1,args.get('max_chars',4096)));chunk=text[cursor:cursor+limit]
        uncertain=not running and not receipt and record.get('launch') not in ('preparing','claimed')
        return {'task_id':tid,'request_id':record['request_id'],'object':request.get('object'),'version':VERSION,
                'status':request['status'],'status_source':'Rust chat object','session_id':record.get('session_id'),'usage':record.get('usage'),'elapsed_seconds':record.get('elapsed_seconds'),'memory_versions':record.get('memory_versions',[]),'execution':'unknown' if uncertain else ('running' if running else 'ended' if receipt else record['launch']),
                'model_phase':record.get('model_phase'),'model_settings':record.get('model_settings'),'turn_settings':record.get('turn_settings'),'host_elapsed_seconds':(receipt or {}).get('host_elapsed_seconds'),'output':chunk,'next_cursor':cursor+len(chunk),'has_more':cursor+len(chunk)<len(text),
                'error':request.get('error'),'cancel':request.get('cancel'),'worker':request.get('worker'),'receipt':receipt,
                'replay_allowed':False,'construction_session_affected':False,'authorization':record.get('authorization',__import__('yohaku_delegation').grant()),'effective_capabilities':record.get('effective_capabilities'),'world_operations':record.get('world_operations',[]),'checks':record.get('checks',[]),'context_policy':record.get('context_policy','world'),'submitted_context':record.get('submitted_context'),'cancel_confirmed':request['status']=='cancelled' and bool((receipt or {}).get('native_cleanup_complete')),'output_cursor_unit':'unicode_scalars','output_complete':request['status'] in ('done','error','cancelled') and not uncertain}
    def cancel(self,args):
        tid=args['task_id'];signalled=False
        # Serialize against the prepare/claim/spawn interval so cancellation can
        # never leave an unobserved child launched after a successful receipt.
        with locked(tid):
            record=self.owned(tid);request=self.object.request(record['request_id'])
            terminal=request['status'] in TERMINAL
            if not terminal:self.object.command({'command':'chat_stop','id':record['request_id'],'by':'host-task-api'})
        # Only a process identity created by start() can receive this signal.
        record=self.owned(tid)
        if (not terminal or request['status']=='unknown') and alive(record) and record.get('model_phase') not in (None,'finished'):
            try:os.kill(record['pid'],signal.SIGTERM);signalled=True
            except ProcessLookupError:pass
        end=time.monotonic()+15
        while time.monotonic()<end:
            current=self.status({'task_id':tid})
            if current['status'] in TERMINAL and not alive(self.owned(tid)):
                receipt=current.get('receipt') or {}
                return {**current,'cancel_accepted':not terminal,'process_signalled':signalled,'cancel_confirmed':current['status']=='cancelled' and receipt.get('native_cleanup_complete') is True}
            time.sleep(.1)
        return {**self.status({'task_id':tid}),'cancel_accepted':not terminal,'process_signalled':signalled,'cancel_confirmed':False,'reason':'cleanup not confirmed within bounded wait; inspect task; do not replay'}


def run_task(tid):
    import yohaku_agent as agent
    import yohaku_codex as codex
    from yohaku_provider_transport import resolve_turn_config
    # start() holds this lock until the process binding is durable.
    with locked(tid) as path:record=read_record(tid)
    obj=Object(record['world']);request=obj.request(record['request_id']);children=[];stop=threading.Event();cancelled=False
    class Cancelled(Exception):pass
    def interrupt(*_):raise Cancelled('Independent model task cancelled')
    signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
    def monitor():
        heartbeat=time.monotonic()
        while not stop.wait(.2):
            try:
                current=obj.request(record['request_id'])
                if current['status']=='stopping':os.kill(os.getpid(),signal.SIGTERM);return
                if time.monotonic()-heartbeat>=30:
                    obj.command({'command':'chat_update','id':record['request_id'],'token':record['token'],'last_status':'independent host Codex task running'})
                    heartbeat=time.monotonic()
            except Exception:
                # A failed object read is not cancellation or success. Native completion still must commit.
                continue
    def emit(event):
        kind=event.get('event')
        fields={}
        if kind in ('model_settings','turn_settings'):fields[kind]=event
        if kind=='node_session':fields['session_id']=event['thread_id']
        if kind=='node_usage':fields.update(usage=event.get('usage'),elapsed_seconds=event.get('elapsed_seconds'))
        if kind=='status' and event.get('text','').startswith('Codex connected;'):fields['model_phase']='model_running'
        if fields:patch_record(tid,**fields)
    original=codex.launch
    def tracked(address,**kwargs):
        child=original(address,**kwargs);children.append(child)
        patch_record(tid,native=[identity(c.pid) for c in children if identity(c.pid)])
        return child
    codex.launch=tracked
    result=None;error=None;cleanup=[];execution=None
    monitor_thread=threading.Thread(target=monitor,daemon=True)
    try:
        if request['status']=='stopping':raise Cancelled('Stopped before launch')
        from yohaku_delegation import grant,validate,task_tools,TaskWorkspace,MODULE_REVISION
        authorization=validate(record.get('authorization') or grant())
        persisted=request.get('snapshot',{}).get('config',{}).get('delegation') or grant()
        if request.get('snapshot',{}).get('config',{}).get('context_policy','world')!=record.get('context_policy','world'):raise ValueError('Immutable context policy mismatch; no model turn started')
        if persisted!=authorization:raise ValueError('Request/task authorization mismatch; no model turn started')
        config=agent.read_config();config.update(protocol='codex-local',permissions=authorization['permissions'])
        if not config.get('codex_entry'):config['codex_entry']=os.environ.get('YOHAKU_CODEX_LINUX','')
        context={'root':str(obj.world),'page':'independent-host-model-task','draft':None,'dirty':False,'task_id':tid,'request_id':record['request_id']}
        initial={'config':config,'context':context,'history':[],'prompt':request['prompt']}
        initial['config']=resolve_turn_config(initial,ROOT)
        workspace=agent.Workspace(obj.world,ROOT/'bin/loom-linux-x86_64',ROOT/'bin/yohaku_workspace')
        execution=TaskWorkspace(workspace,authorization,tid,lambda **fields:patch_record(tid,**fields))
        tools=task_tools(execution.execute,context,authorization)
        effective={'authorization':authorization,'tool_names':sorted(t['name'] for t in tools.definitions),'native_control_profile':codex.CONTROL_PROFILE,'native_shell':False,'delegation_module_sha256':MODULE_REVISION,'tasks_module_sha256':globals()['MODULE_REVISION'],'agent_module_sha256':agent.WORKER_REVISION,'workspace_path':workspace.executable,'workspace_sha256':hashlib.sha256(Path(workspace.executable).read_bytes()).hexdigest()}
        patch_record(tid,effective_capabilities=effective)
        if record.get('context_policy')=='isolated_text':
            tools=agent.Tools(lambda request: (_ for _ in ()).throw(ValueError('Text-only task cannot access world tools')),lambda:{},{group:False for group in agent.GROUPS},native=True)
            tools.isolated_text=True;initial['history']=[];initial['context']={};initial['config']['max_tool_calls']=0
            initial['config']['reasoning_effort']='high'
            effective.update(tool_names=[],context_policy='isolated_text',world_bootstrap=False,history_injected=False);patch_record(tid,effective_capabilities=effective)
            patch_record(tid,submitted_context={'policy':'isolated_text','history':[],'world_context':{},'tools':[], 'base_instructions':codex.ISOLATED_TEXT_INSTRUCTIONS,'developer_instructions':codex.ISOLATED_TEXT_INSTRUCTIONS,'user_input':request['prompt'],'requested_model':'gpt-6.1-sol','requested_effort':'high'})
        if record.get('context_policy')=='ai_node':
            from yohaku_ai_nodes import task_tools as node_tools,validate_profile
            from yohaku_experiment_groups import Groups
            node=record['node_context']
            if node!=request.get('snapshot',{}).get('config',{}).get('node_context'):raise ValueError('Immutable node context mismatch')
            chosen=validate_profile(node['profile'])
            initial['config'].update(reasoning_effort=chosen['reasoning_effort'],turn_timeout=chosen['budget']['timeout_seconds'],max_tool_calls=chosen['budget']['max_tool_calls'])
            initial['context']={'root':str(obj.world),'page':'independent-ai-node','node_id':node['node_id'],'task_id':tid}
            tools=node_tools(workspace,initial['context'],node,tid)
            effective.update(tool_names=sorted(t['name'] for t in tools.definitions),context_policy='ai_node',world_bootstrap=False,history_injected=False,node_id=node['node_id'],requested_profile=chosen,project_scopes=node.get('project_scopes',[]),scoped_project_permissions={'read':True,'write':True,'run':True} if node.get('project_scopes') else {})
            group=Groups(obj.world).group_for(node['node_id'])
            if group:effective.update(experiment_group=group,experiment_budget=Groups(obj.world).status(group),experiment_controls_sha256=hashlib.sha256((ROOT/'agent/yohaku_experiment_groups.py').read_bytes()).hexdigest())
            patch_record(tid,effective_capabilities=effective)
        patch_record(tid,model_phase='connecting');monitor_thread.start()
        if record.get('context_policy')=='ai_node' and chosen['provider']=='adaption':
            import yohaku_adaption
            result=yohaku_adaption.run(initial,tools,emit)
        else:result=codex.run(initial,tools,emit)
    except (Exception,KeyboardInterrupt) as exc:
        error=str(exc)[:4096]
    finally:
        # Cancellation during cleanup cannot interrupt reaping owned native processes.
        signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
        stop.set()
        if monitor_thread.is_alive():monitor_thread.join(3)
        for child in children:
            if child.poll() is None:
                try:os.killpg(child.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    try:os.killpg(child.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    child.wait(timeout=3)
            cleanup.append({'pid':child.pid,'exit_code':child.returncode,'reaped':child.returncode is not None})
        for child in children:
            for pipe in (child.stdin,child.stdout,child.stderr):
                if pipe is not None and not pipe.closed:pipe.close()
        if execution is not None:session_cleanup=execution.cleanup()
        else:session_cleanup=[]
        codex.launch=original
    diagnostic_path=(result or {}).get('diagnostic_path')
    if not diagnostic_path and error:
        matched=re.search(r'diagnostic: ([^\s]+\.json)',error)
        if matched:diagnostic_path=matched.group(1)
    codex_evidence={}
    if diagnostic_path:
        location=Path(diagnostic_path)
        expected=Path.home()/'.local/state/yohaku/codex-diagnostics'
        if location.parent==expected and location.is_file() and not location.is_symlink():
            diagnostic=json.loads(location.read_text())
            codex_evidence={key:diagnostic.get(key) for key in ('thread_id','turn_id','effective_model','effective_turn_budget','status','failure_stage','submitted_context')}
            codex_evidence['diagnostic_path']=diagnostic_path
    receipt={'native':cleanup,'native_cleanup_complete':all(x['reaped'] for x in cleanup) and all(x['cleanup_confirmed'] for x in session_cleanup),'program_sessions':session_cleanup,'authorization':record.get('authorization'),'effective_capabilities':read_record(tid).get('effective_capabilities'),'runner_pid':os.getpid(),'codex':codex_evidence,'finished':time.time(),'host_elapsed_seconds':round(time.time()-record['created'],6),'version':VERSION}
    # Durable execution evidence precedes business commit; never re-run a model after an uncertain commit.
    previous_evidence=read_record(tid)
    patch_record(tid,receipt=receipt,model_phase='finished',pending_result=result,pending_error=error,**({'final_result':result,'usage':(result or {}).get('usage') or previous_evidence.get('usage'),'elapsed_seconds':(result or {}).get('elapsed_seconds') or previous_evidence.get('elapsed_seconds'),'submitted_context':(result or {}).get('submitted_context') or previous_evidence.get('submitted_context')} if record.get('context_policy')=='ai_node' else {}))
    current=obj.request(record['request_id']);cancelled=current['status']=='stopping'
    status='cancelled' if cancelled else 'done' if result is not None else 'error'
    reply=None if cancelled or result is None else {'text':result.get('text',''),'provenance':'independent-host-codex','task_id':tid,'diagnostic_path':result.get('diagnostic_path')}
    worker={'runner':tid,'task_id':tid,'pid':os.getpid(),'mode':'host-codex','child':receipt}
    try:
        final=obj.command({'command':'chat_update','id':record['request_id'],'token':record['token'],'status':status,'reply':reply,'error':'stop' if cancelled else error,'worker':worker,'cancel_result':'independent native process closed and reaped' if cancelled else None,'_respect_stop':True})
        patch_record(tid,commit_confirmed=True,pending_result=None,pending_error=None)
        if record.get('context_policy')=='ai_node':
            try:
                from yohaku_ai_nodes import Control as Nodes
                Nodes(obj.world,actor=record['node_context']['node_id']).node_status(record['node_context']['node_id'])
            except Exception as publication_error:patch_record(tid,node_publication_error=str(publication_error)[:500])
    except Exception as exc:
        patch_record(tid,commit_confirmed=False,commit_error=type(exc).__name__)
        # Leave durable result for inspection. Do not re-execute or invent a terminal state.
        return 2
    return 0


if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[1]!='run':raise SystemExit('Internal task runner only')
    raise SystemExit(run_task(sys.argv[2]))