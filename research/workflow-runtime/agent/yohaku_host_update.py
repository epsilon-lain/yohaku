"""Explicit host update transaction. Called by the installed native save hook only.
No sandbox escape, arbitrary target, caller argv, or automatic installation.
"""
import ast,contextlib,fcntl,hashlib,json,os,re,shutil,subprocess,sys,tempfile,time,signal,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE='files/codex-text/UPDATE.json.tex'
RECEIPT='files/codex-text/UPDATE-RESULT.json.tex'
PAYLOAD=('agent/yohaku_codex_text.py','agent/yohaku_agent.py',
 'agent/yohaku_codex_text_service.py','agent/yohaku_host_update.py',
 'config/codex-text-service.json','config/codex-text-templates/guide.source.txt',
 'config/codex-text-templates/trial.source.txt','bin/yohaku_workspace','bin/yohaku_chat_workspace','agent/yohaku_launcher.py','config/host-update.json','src/workspace.rs','src/bin/yohaku_workspace.rs','config/codex-text-templates/manifest.json','config/codex-text-templates/open-operator.source.txt')
VERSION='yohaku-host-update/3-collaboration'
WORKSPACE_BUILD='codex-text-v3-snapshot-20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def safe(root,name):
 p=root/name
 if p.resolve()!=p.absolute():raise ValueError('Symlink/path escape: '+str(p))
 return p
def put(path,data,mode=0o644):
 path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='.update-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.chmod(tmp,mode);os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def record(path,value):put(path,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode(),0o600)
class Updater:
 def __init__(self,world,project=None):
  self.root=Path(project or ROOT).resolve();self.world=Path(world).resolve()
  self.bundle=self.world/'files/yohaku-default'
  # Production target is the installed module's project, never caller/world text.
  if not (self.root/'Cargo.toml').is_file():raise ValueError('Installed host project unavailable: '+str(self.root))
  from yohaku_codex_tasks import state_root
  self.state=state_root()/('updates-'+hashlib.sha256(str(self.world).encode()).hexdigest()[:16])
  self.state.mkdir(mode=0o700,exist_ok=True)
 def service(self,mode):
  argv=[sys.executable,'-B',str(self.root/'agent/yohaku_codex_text_service.py'),mode,'--world',str(self.world)]
  p=subprocess.run(argv,cwd=self.root,capture_output=True,text=True,timeout=25)
  if p.returncode:raise ValueError('Service '+mode+' failed: '+p.stderr[-2000:]+p.stdout[-2000:])
  return json.loads(p.stdout)
 def workspace_identity(self,path):
  p=subprocess.run([str(path),'--identity'],capture_output=True,text=True,timeout=10)
  if p.returncode:raise ValueError('Workspace identity unavailable: '+str(path))
  value=json.loads(p.stdout)
  if value.get('program')!='yohaku_workspace' or value.get('build_id')!=WORKSPACE_BUILD or set(value.get('capabilities',[]))!={'atomic-source-read','chat-objects-v1'}:
   raise ValueError('Workspace build/capabilities mismatch')
  return value
 def loom_inspect(self,source):
  r=subprocess.run([str(self.root/'bin/loom-linux-x86_64'),'inspect',str(source),'--json'],capture_output=True,text=True,timeout=10)
  if r.returncode:raise ValueError('Candidate tex inspect failed: '+r.stdout[-1000:]+r.stderr[-1000:])
  try:return json.loads(r.stdout)['result']
  except (ValueError,KeyError,TypeError) as error:raise ValueError('Candidate tex inspect response invalid') from error
 def bundle_root_for(self,source,expected_output):
  doc=self.loom_inspect(source);route=doc.get('routing',{}).get('output')
  matches=[root for root in (self.world,self.bundle) if safe(root,route).resolve()==Path(expected_output).resolve()]
  if len(matches)!=1:raise ValueError('Candidate Loom output ownership mismatch: '+str(source))
  return matches[0],route
 def bundle_sync(self,source_name,output_name,loom_root=None):
  source=safe(self.bundle,source_name);loom_root=Path(loom_root or self.world).resolve();output=safe(loom_root,output_name)
  raw=source.read_bytes();doc=self.loom_inspect(source)
  if doc.get('routing',{}).get('output')!=output_name:raise ValueError('Candidate Loom output ownership mismatch: '+source_name)
  r=subprocess.run([str(self.root/'bin/loom-linux-x86_64'),'sync',str(source),'--root',str(loom_root),'--json'],capture_output=True,text=True,timeout=25)
  try:value=json.loads(r.stdout)
  except ValueError as error:raise ValueError('Candidate Loom sync response invalid: '+source_name) from error
  build=value.get('result',{}).get('build',{})
  if r.returncode or value.get('ok') is not True or Path(build.get('output','')).resolve()!=output.resolve():
   raise ValueError('Candidate Loom sync/ownership failed: '+source_name+': '+str(value.get('error',r.stderr[-1000:])))
  if source.read_bytes()!=raw:raise ValueError('Candidate tex changed during Loom sync: '+source_name)
  verified=self.loom_inspect(source);body=verified['body'].encode()
  if output.read_bytes()!=body:raise ValueError('Candidate Loom output hash mismatch: '+output_name)
  return body,sha(source),build.get('build_id'),build.get('map_path')
 def prepare_candidate(self):
  if self.bundle.resolve()!=(self.world/'files/yohaku-default').resolve():raise ValueError('Fixed candidate bundle root mismatch')
  manifest_source=safe(self.bundle,'config/host-update-v3.json.tex')
  manifest_root,manifest_route=self.bundle_root_for(manifest_source,safe(self.bundle,'config/host-update-v3.json'))
  files={};sources={};builds={};loom_roots={str(self.world):0,str(self.bundle):0}
  for name in PAYLOAD:
   path=safe(self.bundle,name)
   if name.startswith('bin/'):
    if not path.is_file():raise ValueError('Candidate binary missing: '+name)
    files[name]=sha(path)
   else:
    source=safe(self.bundle,name+'.tex');loom_root,route=self.bundle_root_for(source,path)
    body,source_hash,build_id,map_path=self.bundle_sync(name+'.tex',route,loom_root)
    loom_roots[str(loom_root)]+=1
    data=safe(self.bundle,name).read_bytes()
    if data!=body:raise ValueError('Candidate source/output mismatch: '+name)
    if name.endswith('.py'):ast.parse(data,filename=name)
    files[name]=sha(safe(self.bundle,name));sources[name]=source_hash;builds[name]=build_id
  if b'codex-text/3' not in safe(self.bundle,'agent/yohaku_codex_text.py').read_bytes():raise ValueError('Wrong candidate operator version')
  if b'save-feedback/1' not in safe(self.bundle,'agent/yohaku_codex_text.py').read_bytes():raise ValueError('Candidate lacks save-feedback/1')
  identities={name:self.workspace_identity(safe(self.bundle,name)) for name in ('bin/yohaku_workspace','bin/yohaku_chat_workspace')}
  if identities['bin/yohaku_workspace']!=identities['bin/yohaku_chat_workspace']:raise ValueError('Candidate workspace binaries differ')
  dependencies={name:sha(safe(self.root,name)) for name in DEPENDENCIES}
  if any(value is None for value in dependencies.values()):raise ValueError('Candidate host dependency missing')
  manifest={'format':'yohaku-host-update-candidate/1','version':'codex-text/3','files':files,'sources':sources,'dependencies':dependencies,'workspace_identity':identities['bin/yohaku_workspace'],'feedback_version':'save-feedback/1'}
  body=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
  source=safe(self.bundle,'config/host-update-v3.json.tex');output=safe(self.bundle,'config/host-update-v3.json')
  raw=source.read_bytes();doc=self.loom_inspect(source)
  if doc.get('routing',{}).get('output')!=manifest_route:raise ValueError('Candidate manifest source changed during prepare')
  start,end=doc['body_byte_start'],doc['body_byte_end'];updated=raw[:start]+body+raw[end:]
  if source.read_bytes()!=raw:raise ValueError('Candidate manifest tex changed during prepare')
  if updated!=raw:put(source,updated,source.stat().st_mode&0o777)
  synced,source_hash,build_id,manifest_map_path=self.bundle_sync('config/host-update-v3.json.tex',manifest_route,manifest_root)
  if synced!=body or sha(output)!=hashlib.sha256(body).hexdigest():raise ValueError('Candidate manifest generation mismatch')
  return {'version':VERSION,'action':'prepare_candidate','phase':'candidate_ready','candidate_manifest_path':'files/yohaku-default/config/host-update-v3.json','candidate_source_path':'files/yohaku-default/config/host-update-v3.json.tex','candidate_manifest_sha256':sha(output),'candidate_source_sha256':source_hash,'loom_root':str(self.bundle),'candidate_files':len(files),'candidate_sources':len(sources),'host_dependencies':len(dependencies),'workspace_identity':identities['bin/yohaku_workspace'],'loom_syncs':len(builds)+1,'loom_roots':loom_roots,'manifest_build_id':build_id,'manifest_map_path':manifest_map_path}
 def source_blob(self,name,data):
  source=safe(self.bundle,name+'.tex')
  r=subprocess.run([str(self.root/'bin/loom-linux-x86_64'),'inspect',str(source),'--json'],capture_output=True,text=True,timeout=10)
  if r.returncode:raise ValueError('Candidate tex unavailable: '+name)
  doc=json.loads(r.stdout)['result']
  if doc['body'].encode()!=data:raise ValueError('Candidate tex/output mismatch: '+name)
  raw=source.read_bytes();end=doc['body_byte_end']
  tail=raw[end:].decode();tail,count=re.subn(r'(?m)^output:.*$',lambda _: 'output: '+json.dumps(name),tail,count=1)
  if count!=1:raise ValueError('Candidate tex output route missing: '+name)
  return raw[:end]+tail.encode()
 def install_blob(self,dest,plan,name):
  if name.startswith('bin/'):
   put(safe(self.root,name),(dest/'payload'/name).read_bytes(),0o755);return
  source=safe(self.root,name+'.tex');put(source,(dest/'sources'/name).read_bytes())
  r=subprocess.run([str(self.root/'bin/loom-linux-x86_64'),'sync',str(source),'--root',str(self.root),'--json'],capture_output=True,text=True,timeout=20)
  if r.returncode or sha(safe(self.root,name))!=plan['files'][name]:raise ValueError('Installed Loom generation mismatch: '+name)
 def status(self):
  s=self.service('status')
  return dict(version=VERSION,project=str(self.root),world=str(self.world),service=s,
   installed={n:sha(safe(self.root,n)) for n in PAYLOAD},
   embedded_host='unchanged; live compositor cannot be replaced in place; operator uses standalone CLI')
 def quiescent(self):
  from yohaku_agent import Workspace
  from yohaku_codex_text import parse
  from yohaku_codex_tasks import state_root,Control,alive
  ws=Workspace(self.world,self.root/'bin/loom-linux-x86_64',self.root/'bin/yohaku_workspace')
  pages=[self.world/'files/codex-text/OPERATOR.md.tex',*sorted((self.world/'files/codex-text/operators').glob('*.md.tex'))]
  for p in pages:
   if p.is_file():
    doc=ws.execute({'command':'read','source':str(p.relative_to(self.world))})
    if parse(doc['body'])['control']!='draft':raise ValueError('Pending control; preserve and reconcile: '+str(p))
  for p in state_root().glob('model-task-*.json'):
   v=json.loads(p.read_text())
   if v.get('world')!=str(self.world):continue
   actual=Control(self.world).call('codex_task_status',{'task_id':v['task_id']})
   if alive(v) or actual.get('status') not in ('done','error','cancelled') or actual.get('execution')!='ended':
    raise ValueError('Task running/unknown; no update or replay: '+v['task_id'])
  # Also block persisted pending text deliveries, even before a task binding exists.
  for p in state_root().glob('text-*.json'):
   v=json.loads(p.read_text())
   # Journals are keyed by canonical world or world+source, not a world field.
   keys=[str(self.world)]+[str(self.world)+'\n'+str(x.relative_to(self.world)) for x in pages[1:]]
   if p.stem in {'text-'+hashlib.sha256(k.encode()).hexdigest() for k in keys} and v.get('pending'):
    raise ValueError('Pending text delivery; inspect journal before update')
 def prepare(self,ident,digest):
  manifest=safe(self.bundle,'config/host-update-v3.json')
  if sha(manifest)!=digest:raise ValueError('Candidate manifest hash mismatch')
  m=json.loads(manifest.read_text())
  if m.get('version')!='codex-text/3' or set(m['files'])!=set(PAYLOAD):raise ValueError('Invalid fixed payload')
  for name,dependency_digest in m.get('dependencies',{}).items():
   if name not in DEPENDENCIES or sha(safe(self.root,name))!=dependency_digest:raise ValueError('Host dependency mismatch: '+name)
  identities={name:self.workspace_identity(safe(self.bundle,name)) for name in ('bin/yohaku_workspace','bin/yohaku_chat_workspace')}
  if identities['bin/yohaku_workspace']!=identities['bin/yohaku_chat_workspace']:raise ValueError('Candidate workspace binaries differ')
  if m.get('workspace_identity') is not None and m['workspace_identity']!=identities['bin/yohaku_workspace']:raise ValueError('Candidate workspace identity manifest mismatch')
  dest=self.state/ident
  if dest.exists():raise ValueError('Plan already exists; query status, never overwrite')
  blobs={};sources={}
  for n in PAYLOAD:
   p=safe(self.bundle,n);data=p.read_bytes()
   if hashlib.sha256(data).hexdigest()!=m['files'][n]:raise ValueError('Candidate hash mismatch: '+n)
   if n.endswith('.py'):ast.parse(data,filename=n)
   blobs[n]=data
   if not n.startswith('bin/'):
    source=safe(self.bundle,n+'.tex')
    if m.get('sources',{}).get(n)!=sha(source):raise ValueError('Candidate source manifest mismatch: '+n)
    sources[n]=self.source_blob(n,data)
  if b'codex-text/3' not in blobs['agent/yohaku_codex_text.py']:raise ValueError('Wrong operator version')
  self.quiescent()
  dest.mkdir(mode=0o700)
  plan={'id':ident,'manifest':digest,'phase':'prepared','files':m['files'],'before':{},'modes':{},'world':str(self.world),'created':time.time(),'source_before':{},'source_installed':{},'source_modes':{}}
  for n,data in blobs.items():
   target=safe(self.root,n);plan['before'][n]=sha(target)
   plan['modes'][n]=(target.stat().st_mode&0o777) if target.exists() else 0o644
   put(dest/'payload'/n,data,0o755 if n.startswith('bin/') else 0o644)
   if target.exists():put(dest/'backup'/n,target.read_bytes(),plan['modes'][n])
  for n,data in sources.items():
   src=safe(self.root,n+'.tex');plan['source_before'][n]=sha(src);plan['source_installed'][n]=hashlib.sha256(data).hexdigest();plan['source_modes'][n]=(src.stat().st_mode&0o777) if src.exists() else 0o644
   put(dest/'sources'/n,data)
   if src.exists():put(dest/'source-backup'/n,src.read_bytes(),plan['source_modes'][n])
  record(dest/'plan.json',plan);return plan
 def load(self,ident):
  dest=self.state/ident;p=json.loads((dest/'plan.json').read_text())
  if p['world']!=str(self.world):raise ValueError('Wrong world')
  return dest,p
 def activate(self,ident):
  dest,p=self.load(ident)
  if p['phase']!='prepared':return dict(p,replay_allowed=False,notice='Already observed; inspect status or explicitly rollback')
  self.quiescent()
  for n in PAYLOAD:
   if sha(safe(self.root,n))!=p['before'][n] or sha(dest/'payload'/n)!=p['files'][n]:raise ValueError('Concurrent target/candidate change: '+n)
  for n,digest in p.get('source_before',{}).items():
   if sha(safe(self.root,n+'.tex'))!=digest:raise ValueError('Concurrent target source change: '+n)
  p['was_running']=self.service('status').get('running',False)
  p['phase']='activating';record(dest/'plan.json',p)
  try:
   stopped=self.service('stop')
   if not stopped.get('stopped'):raise ValueError('Service stop unconfirmed')
   self.quiescent()
   # Recheck after stopping. No world data/credentials/requests are installed.
   for n in PAYLOAD:
    if sha(safe(self.root,n))!=p['before'][n]:raise ValueError('Concurrent install: '+n)
   for n in PAYLOAD:self.install_blob(dest,p,n)
   for name in ('bin/yohaku_workspace','bin/yohaku_chat_workspace'):self.workspace_identity(safe(self.root,name))
   self.service('ensure')
   end=time.monotonic()+18
   while time.monotonic()<end:
    s=self.service('status')
    if (s.get('healthy') and s.get('operator_version')=='codex-text/3'
      and s.get('operator_sha256')==p['files']['agent/yohaku_codex_text.py']
      and s.get('agent_sha256')==p['files']['agent/yohaku_agent.py']
      and s.get('manager_sha256')==p['files']['agent/yohaku_codex_text_service.py']
      and s.get('workspace_sha256')==p['files']['bin/yohaku_workspace']
      and s.get('chat_workspace_sha256')==p['files']['bin/yohaku_chat_workspace']
      and s.get('workspace_identity',{}).get('build_id')==WORKSPACE_BUILD):
     # Require a fresh connected observation of the trial page, not just a live PID.
     from yohaku_agent import Workspace
     ws=Workspace(self.world,self.root/'bin/loom-linux-x86_64',self.root/'bin/yohaku_workspace')
     r=json.loads(ws.execute({'command':'read','source':'files/codex-text/READINESS.json.tex'})['body'])
     trial=r.get('sources',{}).get('files/codex-text/operators/deepseek-trial.md.tex',{})
     if r.get('pid')==s.get('pid') and time.time()-r.get('observed_at',0)<15 and trial.get('connected'):
      p.update(phase='active',service=s,activated=time.time());record(dest/'plan.json',p);return p
    time.sleep(.25)
   raise ValueError('Loaded version/CLI hash/page connection not confirmed')
  except Exception as e:
   p.update(phase='unknown',error=str(e),replay_allowed=False);record(dest/'plan.json',p)
   # Partial transactions stay recoverable; never blindly replay or hide failure.
   raise
 def rollback(self,ident):
  dest,p=self.load(ident)
  if p['phase']=='rolled_back':return p
  if p['phase'] not in ('active','unknown','activating'):raise ValueError('Nothing activated')
  self.quiescent()
  for n in PAYLOAD:
   if sha(safe(self.root,n)) not in (p['before'][n],p['files'][n]):raise ValueError('Rollback conflict: '+n)
  for n,digest in p.get('source_before',{}).items():
   if sha(safe(self.root,n+'.tex')) not in (digest,p['source_installed'][n]):raise ValueError('Rollback source conflict: '+n)
  if not self.service('stop').get('stopped'):raise ValueError('Service stop unconfirmed')
  p['phase']='rolling_back';record(dest/'plan.json',p)
  for n in PAYLOAD:
   target=safe(self.root,n)
   if p['before'][n] is None:
    if target.exists():target.unlink()
   else:
    if sha(dest/'backup'/n)!=p['before'][n]:raise ValueError('Backup hash mismatch')
    put(target,(dest/'backup'/n).read_bytes(),p['modes'][n])
  for n,digest in p.get('source_before',{}).items():
   src=safe(self.root,n+'.tex')
   if digest is None:
    if src.exists():src.unlink()
   else:
    if sha(dest/'source-backup'/n)!=digest:raise ValueError('Source backup hash mismatch')
    put(src,(dest/'source-backup'/n).read_bytes(),p['source_modes'][n])
  if p.get('was_running'):self.service('ensure')
  p.update(phase='rolled_back',service=self.service('status'));record(dest/'plan.json',p);return p
 def call(self,a):
  if a.get('scope')=='collaboration':
   from yohaku_collaboration_update import CollaborationUpdate
   return CollaborationUpdate(self).call(a)
  if a.get('scope') not in (None,'codex-text'):raise ValueError('Unknown fixed update scope')
  action=a.get('action','draft')
  if action=='draft':return {'version':VERSION,'phase':'draft','executed':False}
  if action=='status':return self.status()
  if action=='prepare_candidate':
   with (self.state/'lock').open('a') as f:
    fcntl.flock(f,fcntl.LOCK_EX)
    return self.prepare_candidate()
  ident=a.get('id','')
  if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',ident):raise ValueError('Explicit update id required')
  with (self.state/'lock').open('a') as f:
   fcntl.flock(f,fcntl.LOCK_EX)
   if action=='check':return self.prepare(ident,a['manifest_sha256'])
   if action=='activate':return self.activate(ident)
   if action=='rollback':return self.rollback(ident)
   if action=='plan':return self.load(ident)[1]
   raise ValueError('Use draft/check/plan/activate/status/rollback')
DEPENDENCIES=('agent/yohaku_codex_tasks.py','agent/yohaku_chat_object.py','agent/yohaku_codex.py','agent/yohaku_codex_linux.py','agent/yohaku_codex_models.py','agent/yohaku_codex_provider.py','agent/yohaku_provider_transport.py','agent/yohaku_provider_diagnostics.py','agent/yohaku_codex_diagnostics.py','agent/yohaku_apps.py','agent/yohaku_tools.py','agent/yohaku_coordinates.py','agent/yohaku_entries.py','bin/loom-linux-x86_64')

def after_save(world,execute):
 doc=execute({'command':'read','source':SOURCE});a=json.loads(doc['body'])
 if a.get('action','draft')=='draft':return {'phase':'draft','executed':False}
 updater=Updater(world);revision=hashlib.sha256(doc['text'].encode()).hexdigest()
 journal=updater.state/'dispatch.json'
 with (updater.state/'dispatch.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  prior=json.loads(journal.read_text()) if journal.exists() else {}
  if prior.get('revision')==revision:
   return prior.get('result',{'phase':'unknown','replay_allowed':False,'notice':'Dispatch was reserved; inspect the plan; no automatic replay'})
  record(journal,{'revision':revision,'action':a.get('action'),'id':a.get('id'),'reserved_at':time.time()})
  try:result=updater.call(a)
  except Exception as error:
   result={'version':VERSION,'phase':'error','action':a.get('action'),'id':a.get('id'),'error':str(error),'replay_allowed':False}
   if a.get('id') and re.fullmatch(r'[A-Za-z0-9_-]{1,64}',a['id']):
    try:result['plan_phase']=updater.load(a['id'])[1]['phase']
    except (OSError,ValueError):pass
  # Reconcile the known legacy metadata defect only against this exact
  # reviewed candidate and immutable staged payload, never against a bare input.
  if a.get('scope')!='collaboration' and a.get('action')=='plan' and result.get('phase') in ('prepared','active'):
   candidate=updater.bundle/'config/host-update-v3.json'
   digest=sha(candidate);m=json.loads(candidate.read_text())
   if digest==a.get('manifest_sha256') and result.get('files')==m.get('files') and result.get('manifest')!=digest:
    dest,plan=updater.load(a['id'])
    if all(sha(dest/'payload'/n)==h for n,h in plan['files'].items()) and all(sha(dest/'sources'/n)==h for n,h in plan.get('source_installed',{}).items()):
     plan['manifest_audit']={'previous':plan.get('manifest'),'verified_manifest_sha256':digest,'payload_and_sources_verified':True,'observed_at':time.time()}
     plan['manifest']=digest;record(dest/'plan.json',plan);result=plan
  result={**result,'request_action':a.get('action'),'request_id':a.get('request_id'),'request_revision':revision,'observed_at':time.time(),'updater_version':VERSION}
  record(journal,{'revision':revision,'result':result})
  try:
   old=execute({'command':'read','source':RECEIPT})
   execute({'command':'save','source':RECEIPT,'expected':old['text'],'body_only':True,'text':json.dumps(result,ensure_ascii=False,indent=2)+'\n'})
  except Exception as error:
   result={**result,'receipt_write_error':str(error),'read_plan_before_retry':True};record(journal,{'revision':revision,'result':result})
  return result

def dispatcher_paths(world):
 state=Updater(world).state
 return state/'dispatcher.json',state/'dispatcher.lock',state/'dispatcher.log'

def dispatcher_status(world):
 from yohaku_codex_tasks import alive
 meta,_,_=dispatcher_paths(world);v=json.loads(meta.read_text()) if meta.exists() else {}
 return {**v,'running':bool(v and alive(v)),'healthy':bool(v and alive(v) and time.time()-v.get('heartbeat',0)<15)}

def ensure_configured(project):
 project=Path(project).resolve();config=project/'config/host-update.json'
 if not config.exists():return {'enabled':False}
 c=json.loads(config.read_text())
 if not c.get('enabled_by_default') or not c.get('launch_on_yohaku_start'):return {'enabled':False}
 if project!=ROOT or c.get('source')!=SOURCE or set(c.get('required_permissions',[]))!={'read','write','run'}:raise ValueError('Invalid fixed host updater configuration')
 world=(project/c['world']).resolve()
 if not world.is_relative_to(project/'worlds'):raise ValueError('Update world outside installed project')
 v=dispatcher_status(world)
 if v.get('running'):
  if v.get('project')!=str(ROOT) or v.get('updater_sha256')!=sha(Path(__file__)):raise ValueError('Existing updater version differs; preserve and inspect')
  return v
 meta,_,log=dispatcher_paths(world)
 with log.open('ab') as output:
  child=subprocess.Popen([sys.executable,'-B',str(Path(__file__)),'serve','--world',str(world)],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=output,stderr=output,start_new_session=True)
 threading.Thread(target=child.wait,daemon=True).start()
 end=time.monotonic()+10
 while time.monotonic()<end:
  v=dispatcher_status(world)
  if v.get('running'):return v
  if child.poll() is not None:raise ValueError('Host updater exited before readiness; inspect dispatcher log')
  time.sleep(.05)
 raise ValueError('Host updater readiness unconfirmed; do not start another')

def serve(world):
 from yohaku_agent import Workspace
 from yohaku_codex_tasks import identity
 world=Path(world).resolve();meta,lock,log=dispatcher_paths(world)
 with lock.open('a') as owner:
  try:fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  info={'version':VERSION,'project':str(ROOT),'world':str(world),'updater_sha256':sha(Path(__file__)),**identity(os.getpid())};stopped=False
  def stop(*args):
   nonlocal stopped
   stopped=True
  signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
  ws=Workspace(world,ROOT/'bin/loom-linux-x86_64',ROOT/'bin/yohaku_workspace')
  while not stopped:
   info.update(heartbeat=time.time());record(meta,info)
   try:
    doc=ws.execute({'command':'read','source':SOURCE})
    generated=ws.execute({'command':'read_text','path':SOURCE[:-4]})
    if doc['body']!=generated['text']:raise ValueError('Update source/output not synchronized')
    value=json.loads(doc['body'])
    if value.get('action','draft')!='draft':after_save(world,ws.execute)
    info.pop('last_error',None)
   except Exception as error:info['last_error']=str(error)[:600]
   for _ in range(5):
    if stopped:break
    time.sleep(.1)
  info.update(stopped=True,heartbeat=time.time());record(meta,info)

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('serve','ensure','dispatcher-status'));parser.add_argument('--world')
 args=parser.parse_args()
 if args.mode=='serve':serve(args.world)
 else:print(json.dumps(ensure_configured(ROOT) if args.mode=='ensure' else dispatcher_status(args.world),ensure_ascii=False))
