"""Codex app-server transport (Windows and Linux); world tools via Yohaku RPC.

No raw host shell or file-write tool is granted. Each session first verifies
Codex's read-only sandbox using real writes, then supplies dynamic world tools.
"""
import argparse
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time
from collections import deque

import yohaku_apps as apps
import yohaku_tools as local
import yohaku_codex_linux as linux

class CodexError(Exception):pass

class CodexTimeout(CodexError):pass

BRIDGE_STAGES={'prepare-auth','compile-host','launch-app-server','native-started'}
HOOK_EVENTS=frozenset(('PreToolUse','PermissionRequest','PostToolUse','PreCompact','PostCompact',
    'SessionStart','SessionEnd','UserPromptSubmit','SubagentStart','SubagentStop','Stop','Interrupt'))

CONTROL_PROFILE='yohaku-control'

def verify_profile_catalog(connection):
    # Never substitute :read-only: it permits broad host reads. Select only the
    # private profile written by the bridge, and require explicit availability.
    cursor=None;seen=set()
    for _ in range(20):
        params={'cwd':connection.info['cwd'],'limit':100}
        if cursor:params['cursor']=cursor
        response=connection.request('permissionProfile/list',params)
        entries=response.get('data')
        if not isinstance(entries,list):raise CodexError('Invalid Codex permission profile catalog')
        matches=[p for p in entries if isinstance(p,dict) and p.get('id')==CONTROL_PROFILE]
        if matches:
            if len(matches)!=1 or matches[0].get('allowed') is not True:
                raise CodexError('Codex does not allow the Yohaku control permission profile')
            return
        cursor=response.get('nextCursor')
        if cursor is None:break
        if not isinstance(cursor,str) or not cursor or cursor in seen:break
        seen.add(cursor)
    raise CodexError('Codex did not expose the Yohaku control permission profile; this version or host policy is unsupported')

def verify_config(config, platform="windows"):
    if not isinstance(config,dict) or not isinstance(config.get('features'),dict) or config['features'].get('shell_tool') is not False:
        raise CodexError('Codex did not confirm host shell tools are disabled')
    hooks=config.get('hooks')
    if hooks is not None:
        if not isinstance(hooks,dict):raise CodexError('Codex returned an unsupported hooks configuration')
        # HooksToml serializes default event arrays even when hooks={} on disk.
        # Accept only known empty defaults; preserve refusal of real/unknown hooks.
        for event,groups in hooks.items():
            if event=='state' and isinstance(groups,dict) and not groups:continue
            if event not in HOOK_EVENTS or not isinstance(groups,list):
                raise CodexError('Codex returned an unsupported hooks configuration; no model turn started')
            if groups:raise CodexError('Codex has configured '+event+' hooks; host tools are not allowed in this bridge')
    for key in ('mcp_servers','notify'):
        if config.get(key):raise CodexError('Codex has inherited '+key+'; host tools are not allowed in this bridge')
    if config.get('plugins') or config.get('features',{}).get('apps') is not False or config.get('features',{}).get('plugins') is not False:
        raise CodexError('Codex external apps/plugins must be disabled for the world bridge')
    if platform == 'windows':
        windows=config.get('windows')
        if not isinstance(windows,dict) or windows.get('sandbox')!='elevated':
            raise CodexError('Yohaku requires its explicitly selected elevated Windows sandbox; no model turn started')
    elif platform != 'linux':
        raise CodexError('Unsupported Codex host platform')

def native_executable(address):
    path=apps.address_path(address)
    if not apps.is_windows_path(path):raise CodexError('This connector expects an existing Windows Codex installation')
    if path.name.lower()=='codex.exe':candidates=[path]
    elif path.name.lower() in ('codex','codex.cmd','codex.ps1'):
        root=path.parent/'node_modules/@openai'
        candidates=[];examined=0
        for folder,dirs,files in os.walk(root,followlinks=False):
            examined+=1
            if examined>2000:break
            dirs[:]=[d for d in dirs if not (Path(folder)/d).is_symlink()]
            if 'codex.exe' in files:candidates.append(Path(folder)/'codex.exe')
    else:raise CodexError('Choose the Codex executable or its npm command')
    for candidate in sorted(candidates,key=lambda p:('x86_64' not in str(p),str(p))):
        if candidate.is_symlink() or not candidate.is_file():continue
        with candidate.open('rb') as stream:header=stream.read(2)
        if header==b'MZ':return candidate
    raise CodexError('Windows Codex native executable not found in the selected npm installation')

def launch(address):
    if linux.is_linux_codex(address):
        return linux.launch(address)
    ps=apps.powershell_path()
    if ps is None:raise CodexError('WSL Windows interop is unavailable; launch Yohaku from the same WSL session')
    exe=native_executable(address)
    script=apps.windows_path(local.PACKAGE/'agent/yohaku_codex_host.ps1')
    command=[str(ps),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',script,'-Executable',apps.windows_path(exe)]
    return subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,cwd=local.PACKAGE)

class Connection:
    def __init__(self,child):
        self.child=child;self.queue=queue.Queue(maxsize=64);self.sequence=0;self.info=None;self.pending=deque()
        self.linux=bool(getattr(child,'yohaku_linux',False))
        self.phase='Linux app-server startup' if self.linux else 'Windows bridge startup'
        self.bridge_stage='native-started' if self.linux else 'not reported'
        self.closed=threading.Event()
        threading.Thread(target=self._read,daemon=True).start()
    def _put(self,value):
        while not self.closed.is_set():
            try:self.queue.put(value,timeout=.2);return
            except queue.Full:pass
    def _read(self):
        try:
            while True:
                line=self.child.stdout.readline(2*1024*1024+1)
                if not line:break
                if len(line)>2*1024*1024:raise CodexError('Codex response exceeded 2 MiB')
                value=json.loads(line.decode('utf-8-sig'))
                if not isinstance(value,dict):raise CodexError('Invalid Codex response')
                self._put(value)
        except (ValueError,OSError,CodexError):self._put({'bridgeError':'Codex returned an invalid or oversized response'})
        finally:self._put({'bridgeError':'Codex connection closed; check existing Windows login and app-server support'})
    def send(self,value):
        try:self.child.stdin.write((json.dumps(value,ensure_ascii=False)+'\n').encode());self.child.stdin.flush()
        except (OSError,ValueError):raise CodexError('Codex connection is no longer available')
    def receive(self,timeout=30):
        if self.pending:return self.pending.popleft()
        return self._receive(timeout)
    def _receive(self,timeout=30):
        deadline=time.monotonic()+max(0,timeout)
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise self.timeout_error()
            try:value=self.queue.get(timeout=remaining)
            except queue.Empty:raise self.timeout_error()
            if value.get('bridgeError'):raise CodexError(value['bridgeError'])
            if 'yohakuStage' in value:
                stage=value['yohakuStage']
                if not isinstance(stage,str) or stage not in BRIDGE_STAGES:raise CodexError('Invalid Windows bridge stage')
                self.bridge_stage=stage
                continue
            return value
    def timeout_error(self):
        platform='Linux' if getattr(self,'linux',False) else 'Windows'
        return CodexTimeout('Codex timeout during '+self.phase+'; last '+platform+' bridge stage: '+self.bridge_stage)
    def request(self,method,params,timeout=30):
        previous=self.phase;self.phase='RPC '+method
        try:return self._request(method,params,timeout)
        finally:self.phase=previous
    def _request(self,method,params,timeout):
        self.sequence+=1;ident=self.sequence;self.send({'id':ident,'method':method,'params':params})
        deadline=time.monotonic()+timeout
        while True:
            if time.monotonic()>=deadline:raise self.timeout_error()
            value=self._receive(deadline-time.monotonic())
            if value.get('id')==ident and 'method' not in value:
                if 'error' in value:raise CodexError('Codex '+method+' failed: '+str(value['error'].get('message','unsupported request'))[:600])
                if not isinstance(value.get('result'),dict):raise CodexError('Invalid Codex RPC result')
                return value['result']
            if 'id' in value and 'method' in value:
                if method=='turn/start' and value['method']=='item/tool/call':self.pending.append(value)
                else:self.deny(value)
            elif value.get('method','').startswith(('item/','turn/')) or value.get('method')=='windowsSandbox/setupCompleted':self.pending.append(value)
            if len(self.pending)>256:raise CodexError('Too many queued Codex events')
    def deny(self,value):
        self.send({'id':value['id'],'error':{'code':-32601,'message':'Only Yohaku world tools are supported; no host approval or permission escalation'}})
    def initialize_transport(self):
        if self.linux:
            self.info=self.child.yohaku_info
            self.request('initialize',{'clientInfo':{'name':'yohaku','title':'Yohaku','version':'0.1.9.8'},'capabilities':{'experimentalApi':True}},timeout=45)
            self.send({'method':'initialized','params':{}})
            verify_config(self.request('config/read',{'includeLayers':False}).get('config'),platform='linux')
            verify_profile_catalog(self)
            return
        # A cold PowerShell/.NET bridge startup can take longer than an RPC.
        # Stage messages do not reset or extend this fixed startup deadline.
        first=self.receive(timeout=90)
        info=first.get('yohakuBridge',{})
        if info.get('version')!='1' or not all(isinstance(info.get(k),str) and info[k] for k in ('cwd','outside','readProbe')):raise CodexError('Missing Windows bridge handshake')
        self.info=info
        self.request('initialize',{'clientInfo':{'name':'yohaku','title':'Yohaku','version':'0.1.9.8'},'capabilities':{'experimentalApi':True}})
        self.send({'method':'initialized','params':{}})
        verify_config(self.request('config/read',{'includeLayers':False}).get('config'))
        verify_profile_catalog(self)

    def windows_readiness(self):
        status=self.request('windowsSandbox/readiness',None).get('status')
        if status not in ('ready','notConfigured','updateRequired'):
            raise CodexError('Codex returned an unsupported Windows sandbox readiness status')
        return status

    def setup_windows(self,timeout=180):
        self.initialize_transport()
        if self.windows_readiness()!='ready':
            result=self.request('windowsSandbox/setupStart',{'mode':'elevated','cwd':self.info['cwd']})
            if result.get('started') is not True:raise CodexError('Codex did not start Windows sandbox setup')
            previous=self.phase;self.phase='explicit Windows sandbox setup'
            deadline=time.monotonic()+timeout
            try:
                while True:
                    value=self.receive(deadline-time.monotonic())
                    if value.get('method')!='windowsSandbox/setupCompleted':continue
                    params=value.get('params',{})
                    if params.get('mode')!='elevated' or params.get('success') is not True:
                        raise CodexError('Windows sandbox setup did not complete; no model turn started')
                    break
            finally:self.phase=previous
            if self.windows_readiness()!='ready':raise CodexError('Windows sandbox is still not ready after setup')
        self.verify_boundaries()
        return {'text':'Windows sandbox setup and boundary check completed; no model task was sent'}

    def initialize(self):
        self.initialize_transport()
        if self.linux:
            linux.verify_boundaries(self)
        else:
            if self.windows_readiness()!='ready':
                raise CodexError('Yohaku Windows sandbox needs one-time setup or update. In WSL run: python3 agent/yohaku_codex.py --entry codex setup')
            self.verify_boundaries()
        account=self.request('account/read',{'refreshToken':False})
        if account.get('account') is None and account.get('requiresOpenaiAuth',True):
            if self.linux:
                raise CodexError('Linux Codex is not signed in to Yohaku private account storage. Run: python3 agent/yohaku_codex.py --entry /path/to/linux/codex login')
            raise CodexError('Windows Codex has no reusable login; sign in with your existing Codex first')
        models=self.request('model/list',{'limit':100}).get('data',[])
        model=next((m for m in models if m.get('isDefault')),models[0] if models else {})
        if not isinstance(model.get('id'),str):raise CodexError('Codex returned no model catalog')
        return {'model':model['id'],'models':[m['id'] for m in models if isinstance(m.get('id'),str)],'auth_type':(account.get('account') or {}).get('type','provider')}

    def verify_boundaries(self):
        info=self.info
        # Verify the actual native read-only execution policy before any model turn.
        paths=[info['cwd']+'\\write-probe',info['outside']]
        literal=lambda s:"'"+s.replace("'","''")+"'"
        readable=info['cwd']+'\\read-control'
        script="$ErrorActionPreference='Stop';try{if([IO.File]::ReadAllText("+literal(readable)+") -ne 'yohaku-readable-control'){exit 8}}catch{exit 8};$denied=0;foreach($p in @("+','.join(literal(p) for p in paths)+")){try{[IO.File]::WriteAllText($p,'probe')}catch{$denied++}};try{[IO.File]::ReadAllText("+literal(info['readProbe'])+")|Out-Null}catch{$denied++};if($denied -ne 3){exit 9};[Console]::WriteLine('YOHAKU_READ_ONLY_OK')"
        result=self.request('command/exec',{'command':['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',script],
            'cwd':info['cwd'],'permissionProfile':CONTROL_PROFILE,'timeoutMs':10000},timeout=25)
        if result.get('exitCode')!=0 or 'YOHAKU_READ_ONLY_OK' not in result.get('stdout',''):
            reason={8:'could not read the private control file',9:'did not enforce all read/write boundaries',124:'execution timed out'}.get(result.get('exitCode'),'execution did not return the verified result')
            raise CodexError('Windows Codex permission profile probe '+reason+'; no model turn started')
    def close(self):
        self.closed.set()
        try:self.child.stdin.close()
        except (OSError,ValueError):pass
        try:self.child.wait(timeout=5)
        except subprocess.TimeoutExpired:self.child.kill();self.child.wait(timeout=3)
        self.child.stdout.close()
        if self.linux:linux.cleanup(self.child)

def connect(address):
    connection=Connection(launch(address))
    try:return connection,connection.initialize()
    except BaseException:connection.close();raise

def wait_for_turn_event(connection,deadline,emit):
    # A quiet model stream is not a failed turn. Keep the existing total limit.
    # Never resend a turn or tool call: saved work must not be executed twice.
    while True:
        remaining=deadline-time.monotonic()
        if remaining<=0:raise CodexError('Codex turn exceeded 900 seconds; completed file changes remain')
        try:return connection.receive(min(60,remaining))
        except CodexTimeout:
            if time.monotonic()>=deadline:
                raise CodexError('Codex turn exceeded 900 seconds; completed file changes remain')
            if connection.child.poll() is not None:
                raise CodexError('Codex process exited while waiting; completed file changes remain')
            emit({'event':'status','text':'Waiting for Codex events; no completion received. Stop remains available.'})

def dynamic_definitions(tools):
    return [{'type':'function','name':'yohaku_'+tool['name'],'description':tool['description'],'inputSchema':tool['parameters']} for tool in tools.definitions if tool['name']!='import_document']

def run(initial,tools,emit):
    import yohaku_agent as agent
    address=initial['config'].get('codex_entry','')
    connection,info=connect(address);count=0;text=[];seen=set();replies={}
    old={n:signal.getsignal(n) for n in (signal.SIGTERM,signal.SIGINT)}
    def stop(*_):raise CodexError('Codex turn stopped')
    for n in old:signal.signal(n,stop)
    try:
        model=initial['config'].get('model') or info['model']
        if model not in info['models']:raise CodexError('Selected model is not in this installed Codex catalog; reconnect or select a listed model')
        definitions=dynamic_definitions(tools)
        thread=connection.request('thread/start',{'cwd':connection.info['cwd'],'model':model,'approvalPolicy':'never','permissions':CONTROL_PROFILE,
            'ephemeral':True,'dynamicTools':definitions,'developerInstructions':agent.SYSTEM+'\nUse yohaku_ tools for all world operations. Native paths belong to an empty read-only control workspace. Do not use host shell, native file edits, MCP, or external imports.'})
        thread_id=thread.get('thread',{}).get('id')
        if not isinstance(thread_id,str):raise CodexError('Missing Codex thread id')
        active=thread.get('activePermissionProfile')
        if not isinstance(active,dict) or active.get('id')!=CONTROL_PROFILE:
            raise CodexError('Codex thread did not confirm the Yohaku control permission profile; no model turn started')
        verify_config(connection.request('config/read',{'includeLayers':False,'cwd':connection.info['cwd']}).get('config'),
                      platform='linux' if connection.linux else 'windows')
        history=initial.get('history',[])
        if not isinstance(history,list):history=[]
        history=[m for m in history[-8:] if isinstance(m,dict) and m.get('role') in ('user','assistant') and isinstance(m.get('content'),str)]
        prompt=json.dumps({'recent_conversation':history,'context':initial.get('context',{}),'request':initial['prompt']},ensure_ascii=False)
        turn=connection.request('turn/start',{'threadId':thread_id,'input':[{'type':'text','text':prompt}],
            'approvalPolicy':'never','permissions':CONTROL_PROFILE,'model':model})
        turn_id=turn.get('turn',{}).get('id');deadline=time.monotonic()+900
        connection.phase='waiting for model turn events'
        emit({'event':'status','text':'Codex connected; model='+model+'; editing through Yohaku world tools'})
        while True:
            value=wait_for_turn_event(connection,deadline,emit)
            if time.monotonic()>deadline:raise CodexError('Codex turn exceeded 900 seconds; completed file changes remain')
            method=value.get('method','');params=value.get('params',{})
            if method=='item/tool/call' and 'id' in value:
                if params.get('threadId')!=thread_id:
                    connection.deny(value);continue
                if value['id'] in replies:
                    connection.send(replies[value['id']]);continue
                name=params.get('tool','');args=params.get('arguments',{})
                if name not in {d['name'] for d in definitions}:result={'ok':False,'error':'Unsupported tool'}
                elif count>=100:raise CodexError('Codex tool-call limit reached')
                else:
                    if isinstance(args,str):
                        try:args=json.loads(args)
                        except ValueError:args=None
                    result=tools.call(name[len('yohaku_'):],args);count+=1
                    emit({'event':'tool_result','name':name,'result':result})
                reply={'id':value['id'],'result':{'contentItems':[{'type':'inputText','text':json.dumps(result,ensure_ascii=False)}],'success':result.get('ok') is True}}
                replies[value['id']]=reply;connection.send(reply)
            elif 'id' in value and 'method' in value:connection.deny(value)
            elif method=='item/completed':
                item=params.get('item',{})
                if item.get('type')=='agentMessage' and item.get('id') not in seen:
                    seen.add(item.get('id'));message=item.get('text','')
                    if sum(len(v) for v in text)+len(message)>1024*1024:raise CodexError('Codex message limit reached')
                    if message:text.append(message);emit({'event':'assistant','text':message})
            elif method=='turn/completed':
                completed=params.get('turn',{})
                if params.get('threadId')!=thread_id or (turn_id and completed.get('id')!=turn_id):continue
                if completed.get('status')!='completed':raise CodexError('Codex turn '+str(completed.get('status'))+'; completed file changes remain')
                final='\n'.join(text)
                return {'text':final,'history':history+[{'role':'user','content':initial['prompt']},{'role':'assistant','content':final}], 'tool_calls':count}
    finally:
        connection.close()
        for n,handler in old.items():signal.signal(n,handler)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--entry',required=True);parser.add_argument('mode',choices=['probe','setup','login']);args=parser.parse_args()
    try:
        if args.mode=='login':
            if not linux.is_linux_codex(args.entry):
                raise CodexError('The login command supports native Linux Codex only')
            return linux.login(args.entry)
        if args.mode=='setup':
            if linux.is_linux_codex(args.entry):
                raise CodexError('Linux Codex does not need Windows sandbox setup')
            print('Explicit Windows sandbox setup: approve the Windows administrator prompt if it appears. This may provision sandbox accounts/firewall rules; no model task will be sent.',flush=True)
            connection=Connection(launch(args.entry))
            try:result=connection.setup_windows()
            finally:connection.close()
            print(result['text'],flush=True)
            return 0
        connection,info=connect(args.entry);connection.close()
        print(json.dumps({'event':'codex','config':{'protocol':'codex-local','codex_entry':str(apps.address_path(args.entry)),'model':info['model']},'text':'Codex connection and read-only sandbox verified; ready for Chat'},ensure_ascii=False),flush=True)
    except (CodexError,local.ToolError,OSError,ValueError,subprocess.SubprocessError) as error:
        print(json.dumps({'event':'error','text':str(error)},ensure_ascii=False),flush=True);return 1
    return 0

if __name__=='__main__':sys.exit(main())
