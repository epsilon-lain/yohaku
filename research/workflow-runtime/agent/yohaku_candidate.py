"""Independent Linux Yohaku candidate. No updater, text service or IME service start."""
import argparse,ctypes,ctypes.util,fcntl,hashlib,json,os,signal,subprocess,sys,tempfile,time
from pathlib import Path
from yohaku_launcher import launch_environment
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix(p.suffix+'.pending');q.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');q.replace(p)
def identity(pid):
 from yohaku_project_ui import _process_identity
 return _process_identity(pid)
def alive(record):
 try:
  tail=(Path('/proc')/str(record['pid'])/'stat').read_text().rpartition(')')[2].split()
 except FileNotFoundError:return False
 except OSError as e:raise RuntimeError('Candidate liveness unknown; no launch or stop: '+type(e).__name__)
 if len(tail)<20:raise RuntimeError('Candidate process stat incomplete')
 return tail[19]==record.get('start') and tail[0] not in ('Z','X','x')

def process_namespace():
 return os.readlink('/proc/self/ns/pid')

def boot_identity():
 return {'id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'started':int(next(l.split()[1] for l in Path('/proc/stat').read_text().splitlines() if l.startswith('btime ')))}

def root_init_after(host,namespace):
 # WSL can restart one distribution/PID namespace without rebooting its VM.
 # Accept only an observed Arch systemd root init newer than the old host.
 previous=host.get('start') if isinstance(host,dict) else None
 if not isinstance(previous,str) or not previous.isascii() or not previous.isdecimal():return None
 try:
  executable=os.readlink('/proc/1/exe');init_namespace=os.readlink('/proc/1/ns/pid');stat=Path('/proc/1/stat').read_text()
 except OSError:return None
 fields=stat.rpartition(')')[2].split()
 if executable!='/usr/lib/systemd/systemd' or init_namespace!=namespace or stat.partition(' ')[0]!='1' or len(fields)<20 or fields[1]!='0':return None
 started=fields[19]
 if not started.isascii() or not started.isdecimal() or int(started)<=int(previous):return None
 return {'pid':1,'parent_pid':0,'exe':executable,'start':started,'pid_namespace':init_namespace,'previous_host_start':previous,'reason':'Recorded host predates the current same-namespace Arch root systemd init'}
def selected_environment(pid):
 fields=dict(v.split('=',1) for v in (Path('/proc')/str(pid)/'environ').read_bytes().decode().split('\0') if '=' in v)
 keys=('HOME','YOHAKU_WORKSPACE','YOHAKU_CODEX_LINUX','YOHAKU_CODEX_AUTH_HOME','YOHAKU_CODEX_PROVIDER_FILE','YOHAKU_CODEX_EFFORT','YOHAKU_NO_MODEL_REQUESTS','YOHAKU_LAUNCH_ID','XDG_RUNTIME_DIR','DISPLAY')
 return {k:fields.get(k) for k in keys}

def validate_development(development):
 # This file binds the dedicated native executable/login and legacy bootstrap
 # defaults. The private provider selection is the authority for future turns.
 if set(development)!={'format','entry','auth_home','provider_file','model','effort'} or development['format']!='yohaku-codex-development/1':raise RuntimeError('Invalid explicit Codex development profile')
 if any(not isinstance(development.get(k),str) or not development[k] for k in ('entry','auth_home','provider_file','model','effort')):raise RuntimeError('Incomplete native Codex binding')
def verify_instance(host,world,home,development,prior=None):
 if not alive(host):raise RuntimeError('Candidate identity ended or reused; no process targeted')
 now=identity(host['pid']);expected=ROOT/'bin/yohaku_compositor'
 if not now.get('identity_confirmed') or now.get('start')!=host.get('start') or now.get('exe')!=str(expected) or now.get('cwd')!=str(ROOT) or now.get('argv')!=[str(expected)] or now.get('executable',{}).get('sha256')!=host.get('executable',{}).get('sha256') or now['executable']['sha256']!=sha(expected):raise RuntimeError('Candidate executable/cwd/argv identity mismatch; no duplicate or signal')
 env=selected_environment(host['pid'])
 if env.get('HOME')!=str(home) or env.get('YOHAKU_WORKSPACE')!=str(world):raise RuntimeError('Candidate world/HOME mismatch; no duplicate or signal')
 if development:
  pairs={'YOHAKU_CODEX_LINUX':development['entry'],'YOHAKU_CODEX_AUTH_HOME':development['auth_home'],'YOHAKU_CODEX_PROVIDER_FILE':development['provider_file'],'YOHAKU_CODEX_EFFORT':development['effort']}
  if any(env.get(k)!=v for k,v in pairs.items()) or env.get('YOHAKU_NO_MODEL_REQUESTS'):raise RuntimeError('Active candidate is not bound to the expected native Linux Codex profile; no automatic replacement')
 if prior and prior.get('launch_id') and env.get('YOHAKU_LAUNCH_ID')!=prior['launch_id']:raise RuntimeError('Launch token mismatch; preserve unknown state')
 if prior and prior.get('environment',{}).get('XDG_RUNTIME_DIR') and env.get('XDG_RUNTIME_DIR')!=prior['environment']['XDG_RUNTIME_DIR']:raise RuntimeError('Runtime binding differs; preserve unknown state')
 return now,env

def reconcile_previous(old,world,home,development):
 # Called only under launch.lock. No signal, task query, preparation or model call.
 if old.get('world') and (old['world']!=str(world) or old.get('state_home')!=str(home)):raise RuntimeError('Recorded candidate belongs to another world/HOME; preserve it')
 boot=boot_identity();boot_changed=bool(old.get('boot_id') and old['boot_id']!=boot['id']);namespace=process_namespace()
 # Unknown namespaces remain unsafe without a changed boot or strict evidence
 # that a new Arch root init began after the previously recorded process.
 root_init=None
 if old.get('pid_namespace') and old['pid_namespace']!=namespace and not boot_changed:
  if old.get('boot_id')==boot['id']:root_init=root_init_after(old.get('host'),namespace)
  if root_init is None:raise RuntimeError('Candidate PID namespace differs; host process visibility is unavailable; preserve record and use the host launch entry')
 host=old.get('host');evidence={'boot':boot,'original_status':old.get('status'),'original_host':host,'boot_changed':boot_changed,'pid_namespace':namespace,'previous_pid_namespace':old.get('pid_namespace')}
 if root_init:evidence['root_init_restart']=root_init
 if host and not boot_changed and not root_init and alive(host):
  now,env=verify_instance(host,world,home,development,old);return 'active',dict(old,host=now),dict(evidence,environment=env)
 matches=[]
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:exe=os.readlink(proc/'exe')
  except FileNotFoundError:continue
  except PermissionError:raise RuntimeError('Cannot inspect all process identities; previous launch remains unknown')
  except OSError:continue
  if exe!=str(ROOT/'bin/yohaku_compositor'):continue
  now=identity(int(proc.name))
  if not now.get('identity_confirmed'):raise RuntimeError('Unconfirmed candidate process exists; no duplicate launch')
  if not alive(now):continue
  now,env=verify_instance(now,world,home,development)
  matches.append((now,env))
 evidence['matching_processes']=[v[0] for v in matches]
 if len(matches)>1:raise RuntimeError('Multiple matching candidates; preserve all and do not launch')
 if matches:
  now,env=matches[0];nonce=old.get('launch_id');runtime=old.get('environment',{}).get('XDG_RUNTIME_DIR')
  if not ((nonce and env.get('YOHAKU_LAUNCH_ID')==nonce) or (runtime and env.get('XDG_RUNTIME_DIR')==runtime)):raise RuntimeError('A candidate exists but cannot be correlated with the unknown launch; no duplicate')
  return 'active',dict(old,host=now),dict(evidence,environment=env,reason='recovered exact launch binding')
 if host:evidence['reason']=(root_init['reason']+'; complete candidate scan found no replacement') if root_init else 'Recorded process identity ended; complete candidate scan found no replacement'
 else:
  dispatched=old.get('dispatched_ns')
  if dispatched is None:
   try:dispatched=int(Path(old['scene']).name.removeprefix('launch-'))
   except (KeyError,ValueError):dispatched=None
  if old.get('status') in ('dispatching','unknown') and not ((old.get('boot_id') and old['boot_id']!=boot['id']) or (dispatched and dispatched//1000000000<boot['started'])):raise RuntimeError('Unbound dispatch has insufficient end evidence; preserve unknown state')
  evidence['reason']='Unbound launch predates the current boot; complete candidate scan is empty'
 return 'ended',dict(old,status='ended',reconciled_ns=time.time_ns()),evidence

def mapped_windows(pid,display):
 # Read-only X11 evidence. Match _NET_WM_PID, never a title alone.
 lib=ctypes.CDLL(ctypes.util.find_library('X11') or 'libX11.so.6');P=ctypes.c_void_p;U=ctypes.c_ulong;I=ctypes.c_int
 class Attr(ctypes.Structure):
  _fields_=[('x',I),('y',I),('width',I),('height',I),('border',I),('depth',I),('visual',P),('root',U),('klass',I),('bit',I),('gravity',I),('backing',I),('planes',U),('pixel',U),('save',I),('colormap',U),('installed',I),('map_state',I),('all_events',ctypes.c_long),('own_events',ctypes.c_long),('propagate',ctypes.c_long),('override',I),('screen',P)]
 lib.XOpenDisplay.argtypes=[ctypes.c_char_p];lib.XOpenDisplay.restype=P;lib.XCloseDisplay.argtypes=[P];lib.XDefaultRootWindow.argtypes=[P];lib.XDefaultRootWindow.restype=U;lib.XInternAtom.argtypes=[P,ctypes.c_char_p,I];lib.XInternAtom.restype=U
 lib.XQueryTree.argtypes=[P,U,ctypes.POINTER(U),ctypes.POINTER(U),ctypes.POINTER(ctypes.POINTER(U)),ctypes.POINTER(ctypes.c_uint)];lib.XFree.argtypes=[P]
 lib.XGetWindowProperty.argtypes=[P,U,U,ctypes.c_long,ctypes.c_long,I,U,ctypes.POINTER(U),ctypes.POINTER(I),ctypes.POINTER(U),ctypes.POINTER(U),ctypes.POINTER(P)]
 lib.XGetWindowAttributes.argtypes=[P,U,ctypes.POINTER(Attr)];lib.XFetchName.argtypes=[P,U,ctypes.POINTER(P)]
 handler=ctypes.CFUNCTYPE(I,P,P)(lambda *_:0);lib.XSetErrorHandler.argtypes=[P];lib.XSetErrorHandler.restype=P;prior=lib.XSetErrorHandler(ctypes.cast(handler,P))
 d=lib.XOpenDisplay(display.encode())
 if not d:lib.XSetErrorHandler(prior);return []
 try:
  atom=lib.XInternAtom(d,b'_NET_WM_PID',1);pending=[int(lib.XDefaultRootWindow(d))];seen=set();found=[]
  while pending and len(seen)<4096:
   window=pending.pop()
   if window in seen:continue
   seen.add(window);typ=U();fmt=I();n=U();after=U();data=P()
   lib.XGetWindowProperty(d,window,atom,0,1,0,0,ctypes.byref(typ),ctypes.byref(fmt),ctypes.byref(n),ctypes.byref(after),ctypes.byref(data))
   owner=int(ctypes.cast(data,ctypes.POINTER(U))[0]) if data.value and n.value and fmt.value==32 else None
   if data.value:lib.XFree(data)
   if owner==pid:
    attr=Attr();name=P();title=''
    if lib.XFetchName(d,window,ctypes.byref(name)) and name.value:title=ctypes.string_at(name).decode('utf-8','replace');lib.XFree(name)
    if lib.XGetWindowAttributes(d,window,ctypes.byref(attr)) and attr.map_state==2:found.append({'id':window,'pid':pid,'title':title,'width':attr.width,'height':attr.height,'mapped':True,'display':display})
   rr=U();parent=U();children=ctypes.POINTER(U)();count=ctypes.c_uint()
   if lib.XQueryTree(d,window,ctypes.byref(rr),ctypes.byref(parent),ctypes.byref(children),ctypes.byref(count)) and children:pending.extend(int(children[i]) for i in range(count.value));lib.XFree(children)
  return found
 finally:lib.XCloseDisplay(d);lib.XSetErrorHandler(prior)

def runtime_ready(host,env):
 import socket,stat
 endpoint=Path(env['XDG_RUNTIME_DIR'])/'yohaku-0';windows=mapped_windows(host['pid'],env['DISPLAY'])
 if not windows or not endpoint.exists() or not stat.S_ISSOCK(endpoint.stat().st_mode):return None
 with socket.socket(socket.AF_UNIX) as client:
  client.settimeout(1)
  try:client.connect(str(endpoint))
  except OSError:return None
 return {'method':'verified native process + mapped X11 window + accepting owned Wayland socket','windows':windows,'socket':str(endpoint),'task_log_drain_required':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--world',type=Path,required=True);p.add_argument('--state-home',type=Path,required=True);p.add_argument('--resume-request');p.add_argument('--audit',action='store_true');p.add_argument('--stop',action='store_true');p.add_argument('--codex-development',action='store_true',default=(ROOT/'runtime/CODEX-DEVELOPMENT.json').is_file());a=p.parse_args()
 if sys.platform!='linux':raise RuntimeError('Linux only')
 manifest=json.loads((ROOT/'CANDIDATE.json').read_bytes());history=ROOT/'runtime';history.mkdir(exist_ok=True)
 launch_lock=(history/'launch.lock').open('a+b')
 fcntl.flock(launch_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 latest=history/'LATEST.json';world=a.world.resolve(strict=True);home=a.state_home.resolve(strict=True)
 development=json.loads((history/'CODEX-DEVELOPMENT.json').read_bytes()) if a.codex_development else None
 if development:validate_development(development)
 if latest.exists():
  old=json.loads(latest.read_bytes());state,reconciled,evidence=reconcile_previous(old,world,home,development)
  if state=='active':
   if a.stop:
    expected=reconciled['host'];fd=os.pidfd_open(expected['pid'],0)
    try:
     verify_instance(expected,world,home,development,reconciled);signal.pidfd_send_signal(fd,signal.SIGTERM,None,0)
    finally:os.close(fd)
    deadline=time.monotonic()+5
    while alive(expected) and time.monotonic()<deadline:time.sleep(.1)
    stopped=not alive(expected);save(history/('STOP-'+str(time.time_ns())+'.json'),{'signal':'SIGTERM','identity':expected,'confirmed_stopped':stopped,'tasks_cancelled':False});print(json.dumps({'status':'candidate_stopped' if stopped else 'stop_unconfirmed','confirmed_stopped':stopped,'host':expected}));return
   ready=runtime_ready(reconciled['host'],evidence['environment'])
   if (old.get('status')!='ready' or not old.get('pid_namespace')) and ready:
    save(history/('RECOVERY-'+str(time.time_ns())+'.json'),{'before':old,'evidence':evidence,'readiness':ready,'new_process_started':False})
    reconciled.update(status='ready',readiness=ready,boot_id=boot_identity()['id'],pid_namespace=process_namespace());save(latest,reconciled)
   print(json.dumps({'status':'already_running' if ready else 'already_running_readiness_pending','record':str(latest),'host':reconciled['host'],'world':str(world),'state_home':str(home),'readiness':ready,'codex_development':development,'model_requests':0,'new_process_started':False}));return
  # Archive the unknown state and evidence, never delete or rewrite its original scene.
  save(history/('RECOVERY-'+str(time.time_ns())+'.json'),{'before':old,'evidence':evidence,'after':reconciled,'new_process_started':False});save(latest,reconciled)
 if a.stop:
  print(json.dumps({'status':'already_stopped','confirmed_stopped':True,'process_signalled':False}));return
 mutable_config={}
 for item in manifest['files']:
  file=ROOT/item['path']
  if a.codex_development and item['path']=='config/ai.json' and not file.is_symlink():
   config=json.loads(file.read_bytes())
   if not isinstance(config,dict):raise RuntimeError('Invalid existing mutable UI configuration')
   mutable_config={'path':item['path'],'observed_sha256':sha(file),'sealed_sha256':item['sha256'],'preserved':True}
   continue
  if file.is_symlink() or sha(file)!=item['sha256']:raise RuntimeError('Candidate drift: '+item['path'])
 world=a.world.resolve(strict=True);home=a.state_home.resolve(strict=True)
 if not (home/'.local/state/yohaku/project-tasks/records').is_dir():raise RuntimeError('Explicit original task home required; no default HOME fallback')
 env,backend=launch_environment('x11')
 lib=ctypes.CDLL(ctypes.util.find_library('X11') or 'libX11.so.6');lib.XOpenDisplay.argtypes=[ctypes.c_char_p];lib.XOpenDisplay.restype=ctypes.c_void_p;lib.XCloseDisplay.argtypes=[ctypes.c_void_p]
 display=lib.XOpenDisplay(env['DISPLAY'].encode())
 if not display:raise RuntimeError('X11 unavailable; no service restarted and no launch')
 lib.XCloseDisplay(display)
 private=Path(tempfile.mkdtemp(prefix='yh-int-'));private.chmod(0o700)
 env.update(HOME=str(home),YOHAKU_WORKSPACE=str(world),YOHAKU_LOOM=str(ROOT/'bin/loom-linux-x86_64'),XDG_RUNTIME_DIR=str(private),WINIT_UNIX_BACKEND='x11',LIBGL_ALWAYS_SOFTWARE='1',YOHAKU_PROJECT_VIEW='1',YOHAKU_NO_MODEL_REQUESTS='1',PYTHONDONTWRITEBYTECODE='1')
 development=None
 if a.codex_development:
  from yohaku_codex_linux import is_linux_codex,_auth_home
  from yohaku_codex_provider import load as provider_load
  development=json.loads((ROOT/'runtime/CODEX-DEVELOPMENT.json').read_bytes())
  validate_development(development)
  if not is_linux_codex(development['entry']):raise RuntimeError('Requested native executable differs; no fallback')
  bindings={'YOHAKU_CODEX_LINUX':development['entry'],'YOHAKU_CODEX_AUTH_HOME':development['auth_home'],'YOHAKU_CODEX_PROVIDER_FILE':development['provider_file'],'YOHAKU_CODEX_EFFORT':development['effort']}
  # Validate the dedicated private stores with the exact environment inherited by workers.
  saved={key:os.environ.get(key) for key in bindings}
  try:
   os.environ.update(bindings);_auth_home();selected=provider_load()
   # Read/validate the current authorized selection without overwriting it with
   # offline acceptance values or the launch profile's historical defaults.
   if selected.get('active') not in ('openai','deepseek'):raise RuntimeError('Invalid dedicated provider selection; no fallback')
  finally:
   for key,value in saved.items():
    if value is None:os.environ.pop(key,None)
    else:os.environ[key]=value
  env.update(bindings);env.pop('YOHAKU_NO_MODEL_REQUESTS',None)
 if a.resume_request:env['YOHAKU_PROJECT_RESUME_REQUEST']=a.resume_request
 if a.audit:env['YOHAKU_PROJECT_RPC_AUDIT']='1'
 dispatched=time.time_ns();scene=history/('launch-'+str(dispatched));scene.mkdir(mode=0o700);launch_id=hashlib.sha256((str(ROOT)+str(dispatched)).encode()).hexdigest()[:32];env['YOHAKU_LAUNCH_ID']=launch_id;boot=boot_identity()
 save(latest,{'status':'dispatching','pid_namespace':process_namespace(),'scene':str(scene),'world':str(world),'state_home':str(home),'boot_id':boot['id'],'dispatched_ns':dispatched,'launch_id':launch_id,'environment':{'XDG_RUNTIME_DIR':str(private)},'automatic_retry':False})
 log=(scene/'host.log').open('wb')
 child=subprocess.Popen([str(ROOT/'bin/yohaku_compositor')],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);log.close()
 record={'status':'starting','pid_namespace':process_namespace(),'boot_id':boot['id'],'dispatched_ns':dispatched,'launch_id':launch_id,'scene':str(scene),'host':identity(child.pid),'world':str(world),'state_home':str(home),'resume_request_id':a.resume_request,'source_set':manifest['source_set'],'candidate_manifest_sha256':sha(ROOT/'CANDIDATE.json'),'environment':{k:env.get(k) for k in ('DISPLAY','XMODIFIERS','GTK_IM_MODULE','QT_IM_MODULE','XDG_RUNTIME_DIR')},'model_requests_disabled':not a.codex_development,'codex_development':development,'preserved_mutable_configuration':mutable_config,'services_started':False,'formal_package_updated':False}
 save(latest,record);save(scene/'LAUNCH.json',record)
 if not record['host'].get('identity_confirmed'):
  record['status']='unknown';save(latest,record);raise RuntimeError('Spawned host identity unknown; retain process, do not relaunch')
 deadline=time.monotonic()+60
 while time.monotonic()<deadline:
  text=(scene/'host.log').read_text(errors='replace')
  if child.poll() is not None:
   record.update(status='failed',exit_code=child.returncode);save(latest,record);save(scene/'RESULT.json',record);raise RuntimeError('Candidate exited; full log preserved: '+str(scene/'host.log'))
  ready=runtime_ready(record['host'],env)
  if ready and (not a.audit or ('[NATIVE PROJECT FRAME]' in text and '[NATIVE PROJECT TOOLS]' in text)):
   current=identity(child.pid);expected=next(row['sha256'] for row in manifest['files'] if row['path']=='bin/yohaku_compositor')
   if not current.get('identity_confirmed') or current.get('executable',{}).get('sha256')!=expected:
    record['status']='unknown';save(latest,record);raise RuntimeError('Loaded host ELF not confirmed; preserve launch')
   record.update(status='ready',host=current,readiness=ready);save(latest,record);save(scene/'READY.json',record);print(json.dumps({'status':'integration_candidate_ready','scene':str(scene),'host':record['host'],'model_requests':0,'formal_host_updated':False}),flush=True);return
  time.sleep(.2)
 record.update(status='unknown');save(latest,record);save(scene/'RESULT.json',record);raise RuntimeError('Candidate readiness unknown; retain process and log, do not relaunch')
if __name__=='__main__':main()
