"""Explicit immutable delegation grants and task-owned offline world checks."""
import hashlib,json,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='yohaku-delegation/1'
MODES={'read_only':{'read':True,'write':False,'run':False,'delete':False,'import':False},
       'development':{'read':True,'write':True,'run':True,'delete':False,'import':False}}
EXEC_TOOLS={'terminal_start','terminal_read','terminal_status','terminal_interrupt','terminal_close'}
MODULE_REVISION=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

def mode(value):
    if not isinstance(value,str) or value not in MODES:raise ValueError('Choose mode read_only or development; no task submitted')
    return value

def grant(selected='read_only',root=None):
    selected=mode(selected);policy_hash=None
    if selected=='development':
        path=Path(root or ROOT)/'config/collaboration.json'
        if not path.is_file() or path.resolve()!=path.absolute():raise ValueError('Trusted host collaboration policy is unavailable')
        stat=path.stat()
        if stat.st_uid!=os.getuid() or stat.st_mode&0o022:raise ValueError('Collaboration policy must be host-owned and not group/world writable')
        raw=path.read_bytes();policy=json.loads(raw)
        if set(policy)!={'format','development_enabled'} or policy.get('format')!=VERSION or policy.get('development_enabled') is not True:
            raise ValueError('Development delegation is not enabled by the host owner')
        policy_hash=hashlib.sha256(raw).hexdigest()
    return {'version':VERSION,'mode':selected,'permissions':dict(MODES[selected]),
            'execution_backend':'existing offline world terminal sandbox' if selected=='development' else 'none',
            'policy_sha256':policy_hash}

def validate(value):
    if not isinstance(value,dict) or value.get('version')!=VERSION:raise ValueError('Invalid persisted delegation grant')
    selected=mode(value.get('mode'))
    if value.get('permissions')!=MODES[selected]:raise ValueError('Persisted delegation permission mismatch; no model turn started')
    if selected=='development' and not isinstance(value.get('policy_sha256'),str):raise ValueError('Missing explicit host policy grant')
    return value

def task_tools(execute,context,authorization):
    import yohaku_agent as agent
    validate(authorization)
    tools=agent.Tools(execute,lambda:context,authorization['permissions'],native=False)
    if authorization['mode']=='development':
        tools.definitions.extend(t for t in agent.allowed_tools(authorization['permissions']) if t['name'] in EXEC_TOOLS)
    assert not any(t['name'].startswith(('codex_task_','codex_model_')) or t['name'] in ('run_tool','register_tool','inspect_tool','terminal_list','terminal_write') for t in tools.definitions)
    return tools

class TaskWorkspace:
    """Reuse Rust/Loom and the terminal service; only this task's program sessions."""
    def __init__(self,workspace,authorization,task_id,persist):
        self.workspace=workspace;self.root=Path(workspace.root);self.authorization=validate(authorization)
        self.task_id=task_id;self.persist=persist;self.sessions={};self.checks={};self.operations=[]
    def remember(self):self.persist(execution_sessions=self.sessions,checks=list(self.checks.values()),world_operations=self.operations[-128:])
    def execute(self,request):
        from yohaku_agent import ToolError
        command=request.get('command','')
        if command.startswith('terminal_'):
            if self.authorization['mode']!='development' or command not in EXEC_TOOLS:raise ToolError('Delegated execution is not authorized')
            import yohaku_terminal as terminal
            request=dict(request)
            if command=='terminal_start':
                if len(self.sessions)>=8:raise ToolError('Task program-session limit reached')
                if not isinstance(request.get('program'),str) or request.get('kind','program')!='program':raise ToolError('Delegated checks require an explicit program and kind=program')
                request['kind']='program'
            else:
                sid=request.get('session_id');owned=self.sessions.get(sid)
                if owned is None:raise ToolError('Session belongs to another task; no operation performed')
                request['service_instance']=owned['service_instance']
            try:response=terminal.call(self.root,request)
            except Exception as error:raise ToolError('Delegated terminal outcome unknown; inspect owned session; no replay: '+type(error).__name__) from error
            if not response.get('ok'):raise ToolError(response.get('error','Terminal outcome unknown; no replay'))
            result=response['result'];sid=result.get('session_id')
            if command=='terminal_start':
                if not sid or not result.get('service_instance'):raise ToolError('Program session ownership unconfirmed; no replay')
                self.sessions[sid]={'service_instance':result['service_instance'],'program':request['program']}
            if sid:
                entry={k:result[k] for k in ('session_id','service_instance','program','cwd','kind','state','running','exit_code','evidence','log_path','output_complete','closed') if k in result}
                entry['program']=self.sessions[sid]['program'];self.checks[sid]={**self.checks.get(sid,{}),**entry}
            self.remember();return result
        if command in ('tool_run','tool_status','tool_stop','tool_inspect'):raise ToolError('Registered host tool execution is not a delegated capability')
        result=self.workspace.execute(request)
        if command in ('create','save','sync','write_text'):
            document=result.get('document',{}) if isinstance(result,dict) else {}
            source=result.get('source') or document.get('source') or request.get('source') or request.get('path')
            if isinstance(source,str) and source.endswith('.tex'):
                path=self.root/source
                if path.resolve().is_relative_to(self.root) and path.is_file():
                    item={'command':command,'source':source,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                    # Rust generated path is validated by Loom; read it from this exact saved source.
                    doc=self.workspace.execute({'command':'read','source':source})
                    output=doc.get('routing',{}).get('output')
                    if isinstance(output,str):
                        target=self.root/output
                        if target.resolve().is_relative_to(self.root) and target.is_file():item.update(output=output,output_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
                    self.operations.append(item);self.remember()
        return result
    def cleanup(self):
        results=[]
        for sid in list(self.sessions):
            try:
                current=self.execute({'command':'terminal_status','session_id':sid})
                if not current.get('output_complete'):current=self.execute({'command':'terminal_close','session_id':sid})
                results.append({'session_id':sid,'complete':current.get('output_complete'),'exit_code':current.get('exit_code'),'cleanup_confirmed':current.get('output_complete') is True})
            except Exception as error:results.append({'session_id':sid,'cleanup_confirmed':False,'error_type':type(error).__name__})
        return results
