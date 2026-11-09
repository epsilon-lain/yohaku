"""Fixed new-worker module deployment. Existing UI/tasks/terminals and pending controls stay untouched."""
import ast,contextlib,fcntl,hashlib,json,re,subprocess,sys,time
from pathlib import Path
from yohaku_host_update import safe,put,record,sha
VERSION='yohaku-collaboration-update/1'
PAYLOAD=('config/collaboration.json','agent/yohaku_delegation.py','agent/yohaku_provider_diagnostics.py','agent/yohaku_codex_tasks.py','agent/yohaku_agent.py','agent/test_delegation.py','agent/test_provider_diagnostics.py','agent/test_agent.py','agent/test_codex_tasks.py','agent/test_codex_text_integration.py')
DEPENDENCIES=('agent/yohaku_codex.py','agent/yohaku_codex_linux.py','agent/yohaku_codex_models.py','agent/yohaku_codex_provider.py','agent/yohaku_provider_transport.py','agent/yohaku_terminal.py','agent/yohaku_tools.py','agent/yohaku_apps.py','agent/yohaku_coordinates.py','agent/yohaku_entries.py','agent/yohaku_chat_object.py','agent/yohaku_codex_diagnostics.py','bin/yohaku_workspace','bin/yohaku_chat_workspace','bin/loom-linux-x86_64')
MANIFEST='config/collaboration-update.json'
MODULES=('yohaku_delegation','yohaku_provider_diagnostics','yohaku_codex_tasks','yohaku_agent')
class CollaborationUpdate:
 def __init__(self,shared):
  self.shared=shared;self.root=shared.root;self.world=shared.world;self.bundle=shared.bundle
  self.state=shared.state/'collaboration';self.state.mkdir(mode=0o700,exist_ok=True)
 @contextlib.contextmanager
 def locked(self):
  with (self.state/'lock').open('a') as f:fcntl.flock(f,fcntl.LOCK_EX);yield
 def probe(self):
  code=chr(10).join(['import sys,json,hashlib,importlib', 'from pathlib import Path', 'sys.path.insert(0,sys.argv[1])', 'result={}', 'for name in json.loads(sys.argv[2]):', ' m=importlib.import_module(name);p=Path(m.__file__)', ' result[name]={"path":str(p),"sha256":getattr(m,"WORKER_REVISION",getattr(m,"MODULE_REVISION",hashlib.sha256(p.read_bytes()).hexdigest()))}', 'print(json.dumps(result))'])
  value=subprocess.run([sys.executable,'-B','-c',code,str(self.root/'agent'),json.dumps(MODULES)],capture_output=True,text=True,timeout=20)
  if value.returncode:raise ValueError('Fresh collaboration import probe failed: '+value.stderr[-1200:])
  return json.loads(value.stdout)
 def prepare_candidate(self):
  from yohaku_agent import Workspace
  ws=Workspace(self.world,self.root/'bin/loom-linux-x86_64',self.root/'bin/yohaku_workspace');files={};sources={}
  for n in PAYLOAD:
   path=safe(self.bundle,n);source=safe(self.bundle,n+'.tex');root,route=self.shared.bundle_root_for(source,path)
   data,source_hash,_,_=self.shared.bundle_sync(n+'.tex',route,root)
   if n.endswith('.py'):ast.parse(data,filename=n)
   files[n]=hashlib.sha256(data).hexdigest();sources[n]=source_hash
  dependencies={n:sha(safe(self.root,n)) for n in DEPENDENCIES}
  if None in dependencies.values():raise ValueError('Missing installed collaboration dependency')
  m={'format':VERSION,'load_policy':'new-worker-only','files':files,'sources':sources,'dependencies':dependencies}
  source='files/yohaku-default/'+MANIFEST+'.tex';body=json.dumps(m,ensure_ascii=False,indent=2)+'\n'
  if (self.world/source).exists():
   old=ws.execute({'command':'read','source':source});ws.execute({'command':'save','source':source,'expected':old['text'],'body_only':True,'text':body})
  else:ws.execute({'command':'create','directory':'files/yohaku-default/config','name':'collaboration-update.json','body':body})
  return {'version':VERSION,'phase':'candidate_ready','scope':'collaboration','candidate_manifest_sha256':sha(safe(self.bundle,MANIFEST)),'candidate_manifest_path':'files/yohaku-default/'+MANIFEST,'candidate_files':len(files),'load_policy':'new-worker-only'}
 def load(self,ident):
  dest=self.state/ident;p=json.loads((dest/'plan.json').read_text())
  if p.get('world')!=str(self.world) or set(p.get('files',{}))!=set(PAYLOAD):raise ValueError('Wrong world/fixed collaboration payload')
  return dest,p
 def prepare(self,ident,digest):
  dest=self.state/ident
  if dest.exists():return self.load(ident)[1]
  path=safe(self.bundle,MANIFEST)
  if sha(path)!=digest:raise ValueError('Collaboration candidate manifest hash mismatch')
  m=json.loads(path.read_text())
  if m.get('format')!=VERSION or m.get('load_policy')!='new-worker-only' or set(m.get('files',{}))!=set(PAYLOAD) or set(m.get('dependencies',{}))!=set(DEPENDENCIES):raise ValueError('Wrong fixed collaboration manifest')
  for n,h in m['dependencies'].items():
   if sha(safe(self.root,n))!=h:raise ValueError('Installed dependency changed: '+n)
  blobs={};sources={}
  for n in PAYLOAD:
   data=safe(self.bundle,n).read_bytes()
   if hashlib.sha256(data).hexdigest()!=m['files'][n] or sha(safe(self.bundle,n+'.tex'))!=m['sources'].get(n):raise ValueError('Candidate source/output changed: '+n)
   if n.endswith('.py'):ast.parse(data,filename=n)
   blobs[n]=data;sources[n]=self.shared.source_blob(n,data)
  dest.mkdir(mode=0o700)
  p={'version':VERSION,'scope':'collaboration','id':ident,'world':str(self.world),'manifest':digest,'phase':'prepared','load_policy':'new-worker-only','files':m['files'],'before':{},'modes':{},'source_before':{},'source_installed':{},'source_modes':{},'dependencies':m['dependencies'],'created':time.time(),'backups':str(dest/'backup'),'source_backups':str(dest/'source-backup')}
  for n,data in blobs.items():
   target=safe(self.root,n);p['before'][n]=sha(target);p['modes'][n]=target.stat().st_mode&0o777 if target.exists() else 0o644
   put(dest/'payload'/n,data)
   if target.exists():put(dest/'backup'/n,target.read_bytes(),p['modes'][n])
   source=safe(self.root,n+'.tex');p['source_before'][n]=sha(source);p['source_modes'][n]=source.stat().st_mode&0o777 if source.exists() else 0o644
   p['source_installed'][n]=hashlib.sha256(sources[n]).hexdigest();put(dest/'sources'/n,sources[n])
   if source.exists():put(dest/'source-backup'/n,source.read_bytes(),p['source_modes'][n])
  record(dest/'plan.json',p);return p
 def activate(self,ident):
  dest,p=self.load(ident)
  if p['phase']!='prepared':return {**p,'replay_allowed':False}
  for n in PAYLOAD:
   if sha(safe(self.root,n))!=p['before'][n] or sha(safe(self.root,n+'.tex'))!=p['source_before'][n] or sha(dest/'payload'/n)!=p['files'][n] or sha(dest/'sources'/n)!=p['source_installed'][n]:raise ValueError('Concurrent collaboration target/source change: '+n)
  for n,h in p['dependencies'].items():
   if sha(safe(self.root,n))!=h:raise ValueError('Installed dependency changed: '+n)
  p['phase']='activating';record(dest/'plan.json',p)
  try:
   # Compatible dependencies first, caller-facing agent last. No process restart or saved control is touched.
   for n in PAYLOAD:self.shared.install_blob(dest,p,n)
   loaded=self.probe()
   for n,v in loaded.items():
    if v['sha256']!=p['files']['agent/'+n+'.py']:raise ValueError('Fresh loaded hash mismatch: '+n)
   p.update(phase='active',activated=time.time(),fresh_imports=loaded,restarts=[],existing_workers='retain their imported code; next rounds/tasks load the installed modules')
  except Exception as error:p.update(phase='unknown',error=str(error),replay_allowed=False);record(dest/'plan.json',p);raise
  record(dest/'plan.json',p);return p
 def rollback(self,ident):
  dest,p=self.load(ident)
  if p['phase']=='rolled_back':return p
  if p['phase'] not in ('active','unknown','activating'):raise ValueError('Nothing activated')
  for n in PAYLOAD:
   if sha(safe(self.root,n)) not in (p['before'][n],p['files'][n]) or sha(safe(self.root,n+'.tex')) not in (p['source_before'][n],p['source_installed'][n]):raise ValueError('Collaboration rollback conflict: '+n)
   if p['before'][n] is not None and sha(dest/'backup'/n)!=p['before'][n]:raise ValueError('Backup hash mismatch: '+n)
   if p['source_before'][n] is not None and sha(dest/'source-backup'/n)!=p['source_before'][n]:raise ValueError('Source backup hash mismatch: '+n)
  p['phase']='rolling_back';record(dest/'plan.json',p)
  for n in reversed(PAYLOAD):
   target=safe(self.root,n);source=safe(self.root,n+'.tex')
   if p['before'][n] is not None:put(target,(dest/'backup'/n).read_bytes(),p['modes'][n])
   elif target.exists():target.unlink()
   if p['source_before'][n] is not None:put(source,(dest/'source-backup'/n).read_bytes(),p['source_modes'][n])
   elif source.exists():source.unlink()
   # Let Loom reconcile its own owners/maps for restored or removed sources.
   synced=subprocess.run([str(self.root/'bin/loom-linux-x86_64'),'sync',str(source),'--root',str(self.root),'--json'],capture_output=True,text=True,timeout=20)
   if synced.returncode or sha(target)!=p['before'][n]:raise ValueError('Rollback Loom/hash verification failed: '+n)
  p.update(phase='rolled_back',restarts=[]);record(dest/'plan.json',p);return p
 def call(self,a):
  action=a.get('action','draft')
  if action=='draft':return {'phase':'draft','executed':False}
  if action=='status':return {'version':VERSION,'scope':'collaboration','installed':{n:sha(safe(self.root,n)) for n in PAYLOAD},'fresh_imports':self.probe(),'load_policy':'new-worker-only'}
  with self.locked():
   if action=='prepare_candidate':return self.prepare_candidate()
   ident=a.get('id','')
   if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',ident):raise ValueError('Explicit collaboration plan id required')
   if action=='check':return self.prepare(ident,a['manifest_sha256'])
   if action=='activate':return self.activate(ident)
   if action=='rollback':return self.rollback(ident)
   if action=='plan':return self.load(ident)[1]
   raise ValueError('Unsupported collaboration action')
