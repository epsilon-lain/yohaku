"""Codex app-server transport (Windows and Linux); world tools via Yohaku RPC.

No raw host shell or file-write tool is granted. Each session first verifies
Codex's read-only sandbox using real writes, then supplies dynamic world tools.
"""
import argparse
import hashlib
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
import yohaku_codex_diagnostics as diagnostics
import yohaku_codex_payloads as payloads

class CodexError(Exception):pass

class CodexTimeout(CodexError):pass

class CodexStopped(CodexError):pass

MAX_RESPONSE_BYTES=2*1024*1024
class CodexFrameError(CodexError):
    def __init__(self,category,line,offset=None):
        self.metadata={'category':category,'observed_bytes':len(line),'byte_limit':MAX_RESPONSE_BYTES,
                       'frame_sha256':hashlib.sha256(line).hexdigest(),'raw_frame_saved':False}
        if offset is not None:self.metadata['offset']=offset
        super().__init__('Codex bridge response parse failed: '+category+'; login status was not determined')

def parse_frame(line):
    if len(line)>MAX_RESPONSE_BYTES:raise CodexFrameError('oversized',line)
    try:text=line.decode('utf-8-sig')
    except UnicodeDecodeError as error:raise CodexFrameError('invalid_utf8',line,error.start) from None
    try:value=json.loads(text)
    except json.JSONDecodeError as error:raise CodexFrameError('invalid_json',line,error.pos) from None
    if not isinstance(value,dict):raise CodexFrameError('non_object',line)
    return value

def requested_effort(config,info,model):
    if info.get('provider')=='deepseek':return info['effort']
    row=next((m for m in info.get('model_details',[]) if m.get('id')==model),{})
    effort=info.get('selected_reasoning_effort') or os.environ.get('YOHAKU_CODEX_EFFORT') or config.get('reasoning_effort') or row.get('defaultReasoningEffort')
    if effort is None:return None
    supported={e.get('reasoningEffort') for e in row.get('supportedReasoningEfforts',[]) if isinstance(e,dict)}
    if effort not in supported:raise CodexError('Requested reasoning effort is absent from the actual model catalog; no fallback or model turn')
    return effort

BRIDGE_STAGES={'prepare-auth','compile-host','launch-app-server','native-started'}
HOOK_EVENTS=frozenset(('PreToolUse','PermissionRequest','PostToolUse','PreCompact','PostCompact',
    'SessionStart','SessionEnd','UserPromptSubmit','SubagentStart','SubagentStop','Stop','Interrupt','PreModelRequest','PostModelRequest'))

CONTROL_PROFILE='yohaku-control'
ISOLATED_TEXT_INSTRUCTIONS='You are an independent text-only role. Complete only the supplied role and task. No tools, files, other conversations or delegation are available.'

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

def read_account(connection):
    # The installed app-server can transiently fail routing discovery before
    # any thread or model turn exists. Retry only that read-only RPC, bounded.
    for attempt in range(3):
        try:
            return connection.request('account/read',{'refreshToken':False})
        except CodexError as error:
            if getattr(connection,'linux',False) and str(error)=='Codex account/read failed: workspace routing discovery unauthorized (401)' and not getattr(connection,'yohaku_auth_refresh_attempted',False):
                connection.yohaku_auth_refresh_attempted=True
                if connection.diagnostic is not None:
                    connection.diagnostic.data['auth_refresh']={'reason':'account/read routing 401 before any model thread','attempted_once':True,'interactive_login_started':False}
                    connection.diagnostic.save()
                return connection.request('account/read',{'refreshToken':True})
            if str(error) != 'Codex account/read failed: workspace routing discovery timed out' or attempt == 2:
                raise
            time.sleep(0.2)


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

def launch(address,selection=None,node_key=None):
    if linux.is_linux_codex(address):
        return linux.launch(address,selection=selection,node_key=node_key)
    if selection is not None or node_key is not None:raise CodexError("AI node backend requires native Linux Codex")
    ps=apps.powershell_path()
    if ps is None:raise CodexError('WSL Windows interop is unavailable; launch Yohaku from the same WSL session')
    exe=native_executable(address)
    script=apps.windows_path(local.PACKAGE/'agent/yohaku_codex_host.ps1')
    if not (local.PACKAGE/'agent/yohaku_codex_host.ps1').is_file():
        raise CodexError('This Linux candidate does not package the Windows bridge; select native Linux Codex instead. Windows login was not checked')
    command=[str(ps),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',script,'-Executable',apps.windows_path(exe)]
    return subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=local.PACKAGE)

class Connection:
    def __init__(self,child,diagnostic=None):
        self.diagnostic=diagnostic
        def saved_payload(record):
            if diagnostic is not None:
                diagnostic.data.setdefault('payloads',[]).append(record)
                diagnostic.data['payloads']=diagnostic.data['payloads'][-32:]
                diagnostic.save()
        self.payloads=payloads.PayloadArchive(diagnostics.DIRECTORY,diagnostic.data['session_id'] if diagnostic is not None else None,saved_payload)
        self.stderr_capture=diagnostics.StderrCapture(getattr(child,"stderr",None))
        if diagnostic is not None:diagnostic.attach(child)
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
                value=self.payloads.receive(line,self.child.stdout) if len(line)>MAX_RESPONSE_BYTES else parse_frame(line)
                self._put(value)
        except CodexFrameError as error:
            self.response_failure={**error.metadata,'phase':self.phase,'platform':'linux' if self.linux else 'windows'}
            if self.diagnostic is not None:
                self.diagnostic.data['response_parse_failure']=self.response_failure
                self.diagnostic.save()
            self._put({'bridgeError':str(error)})
        except payloads.PayloadError as error:
            self._put({'bridgeError':str(error)})
        except (OSError,ValueError):self._put({'bridgeError':'Codex response stream I/O failed; login status was not determined'})
        finally:self._put({'bridgeError':'Codex connection closed; no further event received'})
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
            if isinstance(value,payloads.ArchivedFrame):
                try:value=value.load()
                except payloads.PayloadError as error:raise CodexError(str(error)) from error
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
        if self.diagnostic is not None:self.diagnostic.stage('codex_rpc/'+method)
        try:return self._request(method,params,timeout)
        finally:self.phase=previous
    def _request(self,method,params,timeout):
        self.sequence+=1;ident=self.sequence;self.send({'id':ident,'method':method,'params':params})
        deadline=time.monotonic()+timeout
        while True:
            if time.monotonic()>=deadline:raise self.timeout_error()
            value=self._receive(deadline-time.monotonic())
            if value.get('id')==ident and 'method' not in value:
                if 'error' in value:
                    if self.diagnostic is not None:self.diagnostic.rpc_error(method,value['error'])
                    raise CodexError('Codex '+method+' failed: '+str(value['error'].get('message','unsupported request'))[:600])
                if not isinstance(value.get('result'),dict):raise CodexError('Invalid Codex RPC result')
                return value['result']
            if 'id' in value and 'method' in value:
                if method=='turn/start' and value['method']=='item/tool/call':self.pending.append(value)
                else:self.deny(value)
            elif value.get('method','').startswith(('item/','turn/')) or value.get('method') in ('error','windowsSandbox/setupCompleted'):self.pending.append(value)
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
        deepseek=self.linux and self.info.get('provider')=='deepseek'
        if deepseek:
            config=self.request('config/read',{'includeLayers':False}).get('config',{})
            configured=config.get('model_providers',{}).get('deepseek',{})
            relay=self.child.yohaku_provider_relay
            if config.get('model_provider')!='deepseek' or config.get('model')!='deepseek-flash' or config.get('model_reasoning_effort')!='high' or configured.get('wire_api')!='responses' or configured.get('requires_openai_auth') is not False or configured.get('base_url')!=relay.base_url or configured.get('env_key')!=linux.provider.ENV_KEY or config.get('shell_environment_policy',{}).get('inherit')!='none':
                raise CodexError('DeepSeek runtime configuration was not confirmed; no model turn started')
        account=read_account(self)
        if deepseek and account.get('requiresOpenaiAuth') is not False:
            raise CodexError('DeepSeek unexpectedly requires an OpenAI login; no model turn started')
        if account.get('account') is None and account.get('requiresOpenaiAuth',True):
            if self.linux:
                raise CodexError('Linux Codex is not signed in to Yohaku private account storage. Run: python3 agent/yohaku_codex.py --entry /path/to/linux/codex login')
            raise CodexError('Windows Codex has no reusable login; sign in with your existing Codex first')
        models=[];cursor=None;seen=set()
        for _ in range(20):
            page=self.request('model/list',{'limit':100,**({'cursor':cursor} if cursor else {})})
            if not isinstance(page.get('data'),list):raise CodexError('Invalid Codex model catalog')
            models.extend(m for m in page['data'] if isinstance(m,dict))
            cursor=page.get('nextCursor')
            if cursor is None:break
            if not isinstance(cursor,str) or not cursor or cursor in seen:raise CodexError('Invalid Codex model catalog cursor')
            seen.add(cursor)
        else:raise CodexError('Codex model catalog exceeded bound')
        model=next((m for m in models if m.get('isDefault')),models[0] if models else {})
        if not isinstance(model.get('id'),str):raise CodexError('Codex returned no model catalog')
        result={'model':model['id'],'models':[m['id'] for m in models if isinstance(m.get('id'),str)],'auth_type':(account.get('account') or {}).get('type','provider')}
        self.model_details=models
        selected=self.info.get('selected_model')
        if selected:
            if selected not in result['models']:raise CodexError('Selected model is absent from the actual Codex catalog; no fallback')
            result['model']=selected
        if deepseek:
            if 'deepseek-flash' not in result['models']:raise CodexError('DeepSeek model missing from the installed Codex catalog')
            result.update(model='deepseek-flash',provider='deepseek',effort='high')
        return result

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
        forced=False
        if getattr(self.child,'yohaku_provider_relay',None) is not None:self.child.yohaku_provider_relay.recovery.cancel()
        self.closed.set()
        try:self.child.stdin.close()
        except (OSError,ValueError):pass
        try:self.child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            forced=True;self.child.kill();self.child.wait(timeout=3)
        self.child.stdout.close()
        self.stderr_capture.join()
        if self.diagnostic is not None:
            self.diagnostic.process_closed(self.child,self.stderr_capture,forced)
        if self.linux:
            linux.cleanup(self.child)
            if self.diagnostic is not None:
                self.diagnostic.data['auth_refresh_persistence']=getattr(self.child,'yohaku_auth_refresh_persistence',{'state':'unknown'})
                self.diagnostic.save()

def connect(address,diagnostic=None,selection=None,node_key=None):
    transient = {'Codex account/read failed: workspace routing discovery timed out',
                 'Codex account/read failed: workspace routing discovery failed'}
    for attempt in range(3):
        connection=Connection(launch(address,selection=selection,node_key=node_key) if selection is not None or node_key is not None else launch(address),diagnostic)
        try:return connection,connection.initialize()
        except BaseException as error:
            connection.close()
            if not isinstance(error,CodexError) or str(error) not in transient or attempt == 2:
                raise
            # Routing discovery can remain failed for one app-server lifetime.
            # No thread, turn or world operation has been started by connect.
            time.sleep(0.2)

TURN_TIMEOUT_DEFAULT=None
TURN_TIMEOUT_LONG=86400

def turn_timeout(config):
    from yohaku_provider_transport import turn_seconds
    try:return turn_seconds(config)
    except ValueError as error:raise CodexError(str(error)) from error


def timeout_error(seconds):
    return 'Codex turn exceeded '+str(seconds)+' seconds; completed file changes remain'

def turn_budget_status(seconds,started,source='worker input config'):
    elapsed=int(time.monotonic()-started)
    label=('unlimited; elapsed '+str(elapsed)+'s' if seconds is None else
           str(max(0,seconds-elapsed))+'s of '+str(seconds)+'s remain; elapsed '+str(elapsed)+'s')
    return 'time budget: '+label+'; source='+source+'; Stop remains available'

def wait_for_turn_event(connection,deadline,emit,seconds,started,source='worker input config'):
    # Polling and per-RPC timeouts do not impose or reset a whole-turn limit.
    while True:
        remaining=None if deadline is None else deadline-time.monotonic()
        if remaining is not None and remaining<=0:raise CodexError(timeout_error(seconds))
        try:return connection.receive(60 if remaining is None else min(60,remaining))
        except CodexTimeout:
            if deadline is not None and time.monotonic()>=deadline:raise CodexError(timeout_error(seconds))
            if connection.child.poll() is not None:
                raise CodexError('Codex process exited while waiting; completed file changes remain')
            emit({'event':'status','text':turn_budget_status(seconds,started,source)})


def dynamic_definitions(tools):
    return [{'type':'function','name':'yohaku_'+tool['name'],'description':tool['description'],'inputSchema':tool['parameters']} for tool in tools.definitions if tool['name']!='import_document']

def native_tools_sha256(definitions):
    # Native persistent threads retain the dynamic catalog installed at start.
    # Canonicalize the definitions rather than resuming a thread with old tools.
    catalog={'format':'yohaku-native-tools/1','tools':sorted(definitions,key=lambda tool:tool['name'])}
    return hashlib.sha256(json.dumps(catalog,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def run(initial,tools,emit):
    diagnostic=diagnostics.TurnDiagnostics(initial)
    try:
        result=_run(initial,tools,emit,diagnostic)
        diagnostic.finish('completed')
        result['diagnostic_path']=diagnostic.location()
        return result
    except Exception as error:
        diagnostic.fail(error)
        raise CodexError(diagnostic.failure_message()) from error
    finally:
        diagnostic.save()


def _run(initial,tools,emit,diagnostic):
    import yohaku_agent as agent
    diagnostic.stage('call_budget')
    budget=turn_timeout(initial['config'])
    from yohaku_provider_transport import turn_policy
    policy=turn_policy(initial['config'])
    import hashlib
    identity={'version':'codex-unlimited-20261024-v1','worker_path':__file__,
              'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),**policy}
    diagnostic.data['effective_turn_budget']=identity
    diagnostic.save()
    emit({'event':'turn_settings',**identity})
    emit({'event':'status','text':turn_budget_status(budget,time.monotonic(),policy['source'])})
    max_tool_calls=agent.optional_count(initial['config'], 'max_tool_calls')
    if agent.optional_count(initial['config'], 'max_rounds') is not None:
        raise CodexError('Codex-local cannot enforce max_rounds; use max_tool_calls or a direct provider protocol; no model turn started')
    address=initial['config'].get('codex_entry','')
    tools.protocol='codex-local'
    tools.enable_model_management(dict(initial['config'],protocol='codex-local'))
    diagnostic.stage('world_bootstrap')
    isolated=bool(getattr(tools,'isolated_text',False))
    node=getattr(tools,'node_context',None)
    node_started=time.monotonic();usage=None;usage_baseline=(node or {}).get('usage_baseline') or {}
    node_event=getattr(tools,'node_event',lambda event:None)
    context={} if isolated else initial.get('context',{}) if node else tools.bootstrap(initial.get('context',{}))
    diagnostic.stage('connect')
    if node:
        selection=linux.provider.load();selection=dict(selection,active=node['profile']['provider'])
        if selection['active']=='openai':selection.update(openai_model=node['profile']['model'],openai_reasoning_effort=node['profile']['reasoning_effort'])
        connection,info=connect(address,diagnostic,selection=selection,node_key=node['world_key']+'/'+node['node_id'])
    else:connection,info=connect(address,diagnostic)
    count=0;text=[];seen=set();replies={};output_progress=payloads.OutputProgress()
    old={n:signal.getsignal(n) for n in (signal.SIGTERM,signal.SIGINT)}
    def stop(*_):raise CodexStopped('Codex turn stopped')
    for n in old:signal.signal(n,stop)
    try:
        if info.get('provider')=='deepseek':connection.child.yohaku_provider_relay.configure_recovery(initial['config'],emit)
        model=info['model'] if info.get('provider')=='deepseek' else connection.info.get('selected_model') or initial['config'].get('model') or info['model']
        effective_provider=connection.info.get('provider',info.get('provider','openai'))
        effort=node['profile']['reasoning_effort'] if node else requested_effort(initial['config'],dict(info,selected_reasoning_effort=connection.info.get('selected_reasoning_effort'),model_details=getattr(connection,'model_details',[])),model)
        if node:
            actual=next((m for m in connection.model_details if m.get('id')==model),{})
            supported={e.get('reasoningEffort') for e in actual.get('supportedReasoningEfforts',[])}
            if model!=node['profile']['model'] or effective_provider!=node['profile']['provider'] or effort not in supported or (effective_provider=='deepseek' and effort!='high'):raise CodexError('Node selected configuration not confirmed; no model fallback')
        if isolated and (effective_provider!='openai' or model!='gpt-6.1-sol' or effort!='high'):raise CodexError('Isolated role requires actual GPT-6.1 Sol/high; no model turn started')
        tools.model_control.bind(effective_provider,model, 'host private codex-provider.json' if effective_provider=='deepseek' or connection.info.get('selected_model') else 'Codex turn config model')
        effective_model={'provider':effective_provider,'model':model,'selection_source':tools.model_control.runtime['source'],'scope':'codex-local only; ordinary AI unchanged','reasoning_effort':effort}
        diagnostic.data['effective_model']=effective_model
        diagnostic.save()
        emit({'event':'model_settings',**effective_model})
        if model not in info['models']:raise CodexError('Selected model is not in this installed Codex catalog; reconnect or select a listed model')
        definitions=[] if isolated else dynamic_definitions(tools)
        tools_sha256=native_tools_sha256(definitions)
        previous_sha256=(node or {}).get('native_tools_sha256')
        resume=bool(node and node.get('session_id') and previous_sha256==tools_sha256)
        thread_method='thread/resume' if resume else 'thread/start'
        catalog_transition=None
        if node:
            reason='catalog_matches' if resume else 'new_node_session' if not node.get('session_id') else 'unknown_tool_catalog' if not previous_sha256 else 'changed_tool_catalog'
            catalog_transition={'native_tools_sha256':tools_sha256,'previous_sha256':previous_sha256,'previous_session_id':node.get('session_id'),'method':thread_method,'reason':reason}
            diagnostic.data['native_tool_catalog']=catalog_transition
            diagnostic.save()
            node_event({'event':'native_tool_catalog',**catalog_transition})
            emit({'event':'native_tool_catalog',**catalog_transition})
            # A newly started native thread has its own cumulative token usage.
            if not resume:usage_baseline={}
        diagnostic.stage(thread_method)
        instructions=tools.node_system if node else ISOLATED_TEXT_INSTRUCTIONS if isolated else agent.SYSTEM+'\nUse yohaku_ tools for all world operations. Native paths belong to an empty read-only control workspace. Do not use host shell, native file edits, MCP, or external imports.'
        params={'cwd':connection.info['cwd'],'model':model,'approvalPolicy':'never','permissions':CONTROL_PROFILE,
                **({'config':{'model_reasoning_effort':effort}} if effort else {}),'developerInstructions':instructions}
        if node or isolated:params['baseInstructions']=instructions
        if thread_method=='thread/resume':params.update(threadId=node['session_id'],excludeTurns=True)
        else:params.update(ephemeral=not bool(node),dynamicTools=definitions)
        thread=connection.request(thread_method,params)
        if (isolated or node) and thread.get('instructionSources'):raise CodexError('Independent session unexpectedly loaded instruction files; no turn started')
        diagnostic.data['context_policy']='isolated_text' if isolated else 'ai_node' if node else 'world'
        confirmed_model=thread.get('model')
        confirmed_provider=thread.get('modelProvider')
        if isinstance(confirmed_model,str) and confirmed_model!=model:
            raise CodexError('Codex thread/start returned a different model; no model turn started')
        if effective_provider=='openai' and isinstance(confirmed_provider,str) and confirmed_provider!='openai':
            raise CodexError('Codex thread/start returned a different provider; no model turn started')
        confirmed_effort=thread.get('reasoningEffort')
        if effort is not None and confirmed_effort!=effort:
            raise CodexError('Codex thread/start did not confirm requested reasoning effort; no model turn started')
        effective_model.update(thread_start_model=confirmed_model,thread_start_provider=confirmed_provider,thread_start_effort=confirmed_effort)
        diagnostic.save()
        thread_id=thread.get('thread',{}).get('id')
        if not isinstance(thread_id,str):raise CodexError('Missing Codex thread id')
        diagnostic.identify(thread_id,None)
        if node:
            if resume and thread_id!=node['session_id']:raise CodexError('Native thread resume identity mismatch')
            emit({'event':'node_session','thread_id':thread_id,'method':thread_method})
            node_event({'event':'native_thread','method':thread_method,'response':thread,'native_tool_catalog':catalog_transition})
        active=thread.get('activePermissionProfile')
        if not isinstance(active,dict) or active.get('id')!=CONTROL_PROFILE:
            raise CodexError('Codex thread did not confirm the Yohaku control permission profile; no model turn started')
        diagnostic.stage('config/read')
        verify_config(connection.request('config/read',{'includeLayers':False,'cwd':connection.info['cwd']}).get('config'),
                      platform='linux' if connection.linux else 'windows')
        from yohaku_ai_context import assemble,snapshot as input_snapshot
        prompt,history,segment,continuation,discarded_history=assemble(initial,context,node,isolated)
        if node:
            submitted={'base_instructions':instructions,'developer_instructions':instructions,'user_input':prompt,'tools':definitions,'history':history,'world_context':context,'context_segment':segment,'node_id':node['node_id'],'memory_origin':node['memory_origin'],'native_resume':thread_method=='thread/resume','instruction_sources':thread.get('instructionSources',[])}
            node_event({'event':'submitted_context',**submitted})
        if isolated:diagnostic.data['submitted_context']={'base_instructions':ISOLATED_TEXT_INSTRUCTIONS,'developer_instructions':ISOLATED_TEXT_INSTRUCTIONS,'user_input':prompt,'history':[],'world_context':{},'tools':[],'instruction_sources':thread.get('instructionSources',[])}
        diagnostic.protect(prompt)
        diagnostic.stage('turn/start')
        turn_parameters={'threadId':thread_id,'input':[{'type':'text','text':prompt}],
            'approvalPolicy':'never','permissions':CONTROL_PROFILE,'model':model,
            **({'effort':effort} if effort else {})}
        observed_input=input_snapshot(thread_method,dict(params if isinstance(params,dict) else {}),turn_parameters,segment,discarded_history)
        node_event({'event':'host_input_snapshot','snapshot':observed_input})
        diagnostic.data['host_input_layer']=observed_input['layer'];diagnostic.data['context_segment']=segment;diagnostic.save()
        turn=connection.request('turn/start',turn_parameters)
        turn_id=turn.get('turn',{}).get('id');started=time.monotonic();deadline=None if budget is None else started+budget
        if info.get('provider')=='deepseek':connection.child.yohaku_provider_relay.recovery.set_budget(budget)
        diagnostic.identify(thread_id,turn_id)
        diagnostic.stage('waiting_for_turn')
        connection.phase='waiting for model turn events'
        emit({'event':'status','text':'Codex connected; provider='+effective_provider+'; model='+model+'; source='+tools.model_control.runtime['source']+'; editing through Yohaku world tools'})
        emit({'event':'status','text':turn_budget_status(budget,started,policy['source'])})
        while True:
            value=wait_for_turn_event(connection,deadline,emit,budget,started,policy['source'])
            if deadline is not None and time.monotonic()>deadline:raise CodexError(timeout_error(budget))
            method=value.get('method','');params=value.get('params',{})
            diagnostic.observe(value)
            node_event({'event':'native_event','value':value})
            if method=='thread/tokenUsage/updated' and params.get('threadId')==thread_id:
                report=params.get('tokenUsage') or {};totals=report.get('total') or {}
                usage={'source':'thread/tokenUsage/updated','raw':report,'turn_id':params.get('turnId'),'baseline':usage_baseline,**{out:totals.get(inp,0)-usage_baseline.get(inp,0) for out,inp in [('input_tokens','inputTokens'),('output_tokens','outputTokens'),('total_tokens','totalTokens'),('cached_input_tokens','cachedInputTokens'),('reasoning_output_tokens','reasoningOutputTokens')]}}
                diagnostic.data['usage']=usage;diagnostic.save()
                emit({'event':'node_usage','usage':usage,'elapsed_seconds':round(time.monotonic()-node_started,6)})
            if node and method=='model/rerouted':raise CodexError('Selected model was rerouted; actual routing event retained, no fallback accepted')
            if method=='item/tool/call' and 'id' in value:
                if params.get('threadId')!=thread_id or (params.get('turnId') is not None and params['turnId']!=turn_id):
                    connection.deny(value);continue
                if value['id'] in replies:
                    connection.send(replies[value['id']]);continue
                name=params.get('tool','');args=params.get('arguments',{})
                diagnostic.tool_start(value['id'],name)
                if name not in {d['name'] for d in definitions}:result={'ok':False,'error':'Unsupported tool'}
                elif max_tool_calls is not None and count>=max_tool_calls:
                    raise CodexError('Codex tool-call limit reached (explicit max_tool_calls='+str(max_tool_calls)+'); completed file changes remain')
                else:
                    if isinstance(args,str):
                        try:args=json.loads(args)
                        except ValueError:args=None
                    if info.get('provider')=='deepseek':
                        guard=connection.child.yohaku_provider_relay.recovery.tool_guard
                        result=guard.execute(name[len('yohaku_'):],args,lambda:tools.call(name[len('yohaku_'):],args))
                    else:result=tools.call(name[len('yohaku_'):],args)
                    count+=1
                    node_event({'event':'tool_result','tool':name,'arguments':args,'result':result})
                    connection.payloads.audit(value['id'],name[len('yohaku_'):],args,result)
                    result=output_progress.observe(name[len('yohaku_'):],args,result)
                    result=connection.payloads.compact(result,args)
                    emit({'event':'tool_result','name':name,'result':result})
                diagnostic.stage('tool_result_serialization')
                diagnostic.tool_executed(result)
                reply={'id':value['id'],'result':{'contentItems':[{'type':'inputText','text':json.dumps(result,ensure_ascii=False)}],'success':result.get('ok') is True}}
                diagnostic.stage('tool_result_return')
                replies[value['id']]=reply
                try:connection.send(reply)
                except (OSError,CodexError) as error:
                    raise CodexError('Tool executed; result delivery unknown; inspect saved state; do not replay') from error
                diagnostic.tool_sent()
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
                if completed.get('status')!='completed':raise CodexError(diagnostic.turn_failure(completed))
                final='\n'.join(text)
                result={'text':final,'history':history+[{'role':'user','content':initial['prompt'],'context_segment':segment},{'role':'assistant','content':final,'context_segment':segment}], 'tool_calls':count,'usage':usage,'elapsed_seconds':round(time.monotonic()-node_started,6),'session_id':thread_id,'actual_profile':effective_model}
                if node:
                    result.update(submitted_context=submitted,native_tools_sha256=tools_sha256,native_tool_catalog=catalog_transition)
                    node_event({'event':'final_reply','result':result})
                if info.get('provider')=='deepseek':
                    evidence=connection.child.yohaku_provider_relay.evidence()
                    result['provider_evidence']=evidence
                return result
    finally:
        try:
            if info.get('provider')=='deepseek':
                emit({'event':'provider_evidence','provider':'deepseek','requests':connection.child.yohaku_provider_relay.evidence()})
        finally:connection.close()
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