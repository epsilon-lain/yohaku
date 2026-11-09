"""Private, identity-bound browser lifecycle; ordinary tools remain offline."""
import contextlib,fcntl,hashlib,json,os,secrets,signal,socket,stat,subprocess,sys,time,uuid
from pathlib import Path
PACKAGE=Path(__file__).resolve().parents[1]

class BrowserError(ValueError):
 def __init__(self,message,kind='browser_error',**details):super().__init__(message);self.kind=kind;self.details=details
 def to_dict(self):return {'ok':False,'error':str(self),'kind':self.kind,'replay_allowed':False,**self.details}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def atomic(path,value):
 path=Path(path);tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.pending');fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w') as f:json.dump(value,f,ensure_ascii=False);f.write('\n');f.flush();os.fsync(f.fileno())
 tmp.replace(path)
def private_dir(path):
 path=Path(path)
 current=Path(path.anchor)
 for part in path.parts[1:]:
  current/=part
  if current.is_symlink():raise BrowserError('Private browser directories cannot use symlinks','unsafe_runtime')
 path.mkdir(mode=0o700,parents=True,exist_ok=True)
 st=path.stat()
 if st.st_uid!=os.getuid() or not stat.S_ISDIR(st.st_mode):raise BrowserError('Private browser directory owner mismatch','unsafe_runtime')
 path.chmod(0o700);return path
def process(pid):
 try:
  p=Path('/proc')/str(pid);tail=(p/'stat').read_text().rpartition(')')[2].split();args=(p/'cmdline').read_bytes().decode().split('\0');return {'pid':pid,'start':tail[19],'state':tail[0],'argv':[a for a in args if a]}
 except (OSError,IndexError):return None
def alive(record):
 p=process(record.get('pid')) if record else None
 return bool(p and p['start']==record.get('start') and p['state'] not in ('Z','X'))
def binding(world):
 from yohaku_candidate import alive as candidate_alive,identity,selected_environment
 ready=load(PACKAGE/'runtime/LATEST.json');host=ready.get('host') or {};world=Path(world).resolve(strict=True)
 if ready.get('world')!=str(world) or not candidate_alive(host):raise BrowserError('The bound candidate is not running; use its original launcher','candidate_not_running')
 current=identity(host['pid']);env=selected_environment(host['pid'])
 if not current.get('identity_confirmed') or current.get('exe')!=str(PACKAGE/'bin/yohaku_compositor') or current.get('start')!=host.get('start') or current['executable']['sha256']!=sha(PACKAGE/'bin/yohaku_compositor'):raise BrowserError('Candidate identity mismatch; no browser started','candidate_identity_mismatch')
 if env.get('YOHAKU_WORKSPACE')!=str(world) or env.get('HOME')!=ready['state_home']:raise BrowserError('Candidate world/HOME binding mismatch','candidate_identity_mismatch')
 endpoint=Path(env['XDG_RUNTIME_DIR'])/'yohaku-0'
 if not endpoint.exists() or not stat.S_ISSOCK(endpoint.stat().st_mode):raise BrowserError('Candidate Wayland socket unavailable','candidate_not_ready')
 return ready,env,endpoint

class Runtime:
 def __init__(self,world):
  self.world=Path(world).resolve(strict=True);ready=load(PACKAGE/'runtime/LATEST.json')
  if ready.get('world')!=str(self.world):raise BrowserError('Browser requires the current native world binding','native_world_required')
  self.key=hashlib.sha256(str(self.world).encode()).hexdigest()[:20]
  self.base=private_dir(Path(ready['state_home'])/'.local/state/yohaku/browser'/self.key)
  self.spool=private_dir(self.base/'spool');self.profile=private_dir(self.base/'profile');self.config_path=self.base/'runtime.json';self.record_path=self.base/'process.json';self.lock_path=self.base/'service.lock'
  self.recipe_state_dir=private_dir(self.base/'recipes')
  self.socket_dir=private_dir(Path('/tmp')/('yohaku-browser-'+str(os.getuid())+'-'+self.key));self.socket_path=self.socket_dir/'rpc.sock'
 @contextlib.contextmanager
 def locked(self):
  fd=os.open(self.lock_path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'a+b') as f:fcntl.flock(f,fcntl.LOCK_EX);yield
 def _rpc(self,operation,args=None,actor='main',request_id=None,timeout=65):
  try:config=load(self.config_path)
  except (OSError,ValueError):raise BrowserError('Browser has not been started','browser_not_running') from None
  ident=uuid.uuid4().hex;request_id=request_id or ('browser-'+uuid.uuid4().hex)
  envelope={'id':ident,'secret':config['secret'],'actor':actor,'operation':operation,'args':args or {},'request_id':request_id}
  dispatched=False
  try:
   with socket.socket(socket.AF_UNIX) as client:
    client.settimeout(timeout);client.connect(str(self.socket_path));client.sendall((json.dumps(envelope,ensure_ascii=False)+'\n').encode());dispatched=True
    data=bytearray()
    while b'\n' not in data:
     chunk=client.recv(65536)
     if not chunk:raise OSError('Browser disconnected')
     data.extend(chunk)
     if len(data)>2*1024*1024:raise OSError('Browser result exceeded transport bound')
    reply=json.loads(data[:data.index(10)])
   if reply.get('id')!=ident:raise OSError('Browser response identity mismatch')
  except (OSError,ValueError) as error:
   raise BrowserError('Browser response unavailable after dispatch; query the original operation; do not replay' if dispatched else 'Browser service unavailable; query status and restore explicitly','outcome_unknown' if dispatched else 'browser_not_running',request_id=request_id,dispatched=dispatched) from None
  if not reply.get('ok'):raise BrowserError(reply.get('error','Browser operation failed'),reply.get('kind','browser_error'),request_id=request_id,**(reply.get('details') or {}))
  result=reply['result']
  if isinstance(result,dict):result=dict(result,request_id=request_id,**({'duplicate':True} if reply.get('duplicate') else {}))
  return result
 def status(self,actor='main'):
  record=load(self.record_path) if self.record_path.exists() else None
  if not alive(record):return {'state':'stopped','persistent_profile':True,'profile_preserved':True,'starts_browser':False}
  try:return self._rpc('status',actor=actor,timeout=3)
  except BrowserError as error:return {'state':'unresponsive','persistent_profile':True,'starts_browser':False,'error':str(error),'kind':error.kind}
 def start(self,actor='main'):
  with self.locked():
   ready,env,endpoint=binding(self.world);record=load(self.record_path) if self.record_path.exists() else None
   if alive(record):
    old_config=load(self.config_path)
    if old_config.get('candidate_start')==ready['host']['start'] and old_config.get('candidate_pid')==ready['host']['pid']:
     status=self.status(actor)
     if status.get('state')=='running':return status
     if status.get('state')=='starting':return self._wait(actor,record)
    self._close_locked(record)
   # A stale socket is unlinked only after proving the recorded process ended.
   if self.socket_path.exists():
    st=self.socket_path.lstat()
    if not stat.S_ISSOCK(st.st_mode) or st.st_uid!=os.getuid():raise BrowserError('Unexpected browser socket path; preserve it','unsafe_runtime')
    self.socket_path.unlink()
   manifest=load(PACKAGE/'runtime/BROWSER-RUNTIME.json')
   if not Path(manifest['chromium_executable']).is_file():raise BrowserError('Installed browser executable missing','browser_unavailable')
   log=self.base/('service-'+str(time.time_ns())+'.log');config={'socket':str(self.socket_path),'secret':secrets.token_hex(32),'profile':str(self.profile),'spool':str(self.spool),'playwright_module':manifest['playwright_module'],'executable_wrapper':str(PACKAGE/'agent/yohaku_browser_exec.py'),'chromium_executable':manifest['chromium_executable'],'browser_bundle':manifest['browser_bundle'],'library_dir':manifest.get('library_dir'),'candidate_pid':ready['host']['pid'],'candidate_start':ready['host']['start'],'world':str(self.world),'candidate_socket':str(endpoint),'scratch':str(private_dir(self.base/'sandbox-world')),'env':{'PATH':'/usr/bin:/bin','HOME':str(private_dir(self.base/'controller-home')),'LANG':'C.UTF-8','PLAYWRIGHT_BROWSERS_PATH':str(Path(manifest['browser_bundle']).parents[1]),'YOHAKU_BROWSER_RUNTIME_CONFIG':str(self.config_path)}}
   config['synthetic_dns_validation']=manifest.get('synthetic_dns_validation') is True
   for name in ('files','.yohaku','tools/state/browser'):(Path(config['scratch'])/name).mkdir(mode=0o700,parents=True,exist_ok=True)
   registry=Path(config['scratch'])/'.yohaku/files.json'
   if not registry.exists():atomic(registry,{'format':'yohaku-workspace/0.1','files':[]})
   atomic(self.config_path,config)
   with log.open('wb') as output:child=subprocess.Popen(['/usr/bin/node',str(PACKAGE/'agent/yohaku_browser_server.mjs'),str(self.config_path)],cwd=PACKAGE,env=config['env'],stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
   record=process(child.pid)
   if not record:raise BrowserError('Browser service launch identity unknown; inspect status before restoring','outcome_unknown')
   record.update(log=str(log),world=str(self.world),candidate_pid=ready['host']['pid'],candidate_start=ready['host']['start']);atomic(self.record_path,record)
   return self._wait(actor,record)
 def _wait(self,actor,record):
  deadline=time.monotonic()+55;last={}
  while time.monotonic()<deadline:
   if not alive(record):break
   try:
    last=self._rpc('status',actor=actor,timeout=3)
    if last.get('state')=='running':return last
    if last.get('state')=='failed':break
   except BrowserError:pass
   time.sleep(.2)
  error=(last.get('last_error') or {}).get('error','Browser launch failed or timed out; inspect browser status')
  raise BrowserError(error,'browser_launch_failed',state=last.get('state','ended'),profile_preserved=True)
 def call(self,operation,args=None,actor='main',request_id=None):return self._rpc(operation,args,actor,request_id)
 def _close_locked(self,record):
  if not alive(record):return
  if str(PACKAGE/'agent/yohaku_browser_server.mjs') not in record.get('argv',[]):raise BrowserError('Unrecognized browser process; no signal sent','unsafe_runtime')
  try:self._rpc('close',actor='main',timeout=5)
  except BrowserError:pass
  deadline=time.monotonic()+5
  while alive(record) and time.monotonic()<deadline:time.sleep(.1)
  if alive(record):
   fd=os.pidfd_open(record['pid'],0)
   try:
    if alive(record):signal.pidfd_send_signal(fd,signal.SIGTERM,None,0)
   finally:os.close(fd)
   deadline=time.monotonic()+3
   while alive(record) and time.monotonic()<deadline:time.sleep(.1)
  if alive(record):raise BrowserError('Browser close not confirmed; profile retained; no second process started','close_unconfirmed')
 def close(self,actor='main'):
  if actor!='main':raise BrowserError('Only main may close the whole browser; close your own page_id','page_not_authorized')
  with self.locked():self._close_locked(load(self.record_path) if self.record_path.exists() else None)
  return {'state':'stopped','profile_preserved':True}

def techne(root,socket_path=None):
 from yohaku_tools import emit
 from yohaku_wired_runtime import Runtime as WiredRuntime,selected_backend
 runtime=WiredRuntime(root);binding(root);result=runtime.start('main');normal=selected_backend()=='normal_browser_extension'
 if normal:runtime.open_viewer()
 emit('running',tool='yohaku-browser',wayland=not normal,text='Wired — normal browser extension; user owns login; connect the extension first' if normal else 'Wired — managed Chromium; Google federation not passed; normal browser is the supported manual login route',browser=result)
 stopped=False
 def stop(*args):
  nonlocal stopped
  stopped=True
  try:runtime.close()
  except BrowserError as error:emit('log',text=str(error),channel='stderr')
 for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,stop)
 while not stopped:
  state=runtime.status()
  if state.get('state') in ('stopped','closed','failed'):break
  time.sleep(.5)
 emit('exit',code=0,text='Wired connection ended; browser profile retained');return 0
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['techne']);p.add_argument('--root',required=True);a=p.parse_args();raise SystemExit(techne(a.root))
