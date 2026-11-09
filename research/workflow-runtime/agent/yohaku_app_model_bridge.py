"""Trusted app-bound channel; delegates exclusively to existing codex_task APIs."""
import hashlib,json,os,re,socket,tempfile,threading,time
from pathlib import Path
import yohaku_codex_tasks as tasks
class AppBridge:
 def __init__(self,world):
  self.world=Path(world).resolve(strict=True);self.lock=threading.Lock();self.stopped=False
  package=Path(__file__).resolve().parents[1];ready=json.loads((package/'runtime/LATEST.json').read_bytes());pid=ready['host']['pid'];proc=Path('/proc')/str(pid);tail=(proc/'stat').read_text().rpartition(')')[2].split()
  if tail[19]!=ready['host']['start'] or ready['world']!=str(self.world):raise ValueError('Model channel world/host identity mismatch')
  env=dict(x.split('=',1) for x in (proc/'environ').read_bytes().decode().split('\0') if '=' in x)
  if env.get('YOHAKU_CODEX_EFFORT')!='high' or env.get('YOHAKU_NO_MODEL_REQUESTS'):raise ValueError('Verified model development entry required')
  for key in ('HOME','YOHAKU_CODEX_AUTH_HOME','YOHAKU_CODEX_PROVIDER_FILE','YOHAKU_CODEX_EFFORT','YOHAKU_CODEX_LINUX'):
   if key in env:os.environ[key]=env[key]
  self.bound_run=None
  self.state=tasks.state_root()/('swarm-'+hashlib.sha256(str(self.world).encode()).hexdigest());self.state.mkdir(mode=0o700,exist_ok=True)
  self.temp=tempfile.TemporaryDirectory(prefix='yohaku-model-channel-');self.path=Path(self.temp.name)/'channel.sock'
  self.server=socket.socket(socket.AF_UNIX);self.server.bind(str(self.path));self.path.chmod(0o600);self.server.listen(4);self.server.settimeout(.5)
  self.thread=threading.Thread(target=self.serve,daemon=True);self.thread.start()
 def close(self):
  self.stopped=True;self.server.close();self.thread.join(2);self.temp.cleanup() # Does not cancel independent model tasks.
 def serve(self):
  while not self.stopped:
   try:client,_=self.server.accept()
   except (OSError,socket.timeout):continue
   threading.Thread(target=self.connection,args=(client,),daemon=True).start()
 def connection(self,client):
  with client:
   client.settimeout(35);f=client.makefile('rwb')
   for _ in range(32):
    line=f.readline(65537)
    if not line:return
    if len(line)>65536 or not line.endswith(b'\n'):return
    ident=None
    try:
     message=json.loads(line);ident=message['id']
     with self.lock:reply={'ok':True,'result':self.call(message['tool'],message['arguments'])}
    except Exception as exc:reply={'ok':False,'error':str(exc)[:1200],'replay_allowed':False}
    f.write((json.dumps({'id':ident,'response':reply},ensure_ascii=False)+'\n').encode());f.flush()
 def call(self,name,args):
  if name not in ('codex_task_start','codex_task_status','codex_task_cancel') or not isinstance(args,dict):raise ValueError('App model channel only supports start/status/cancel')
  if set(args)-{'run_id','role','task','criteria','cursor'}:raise ValueError('No host paths, model config, credentials or arbitrary task identities accepted')
  run=args.get('run_id');role=args.get('role')
  if not isinstance(run,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',run) or role not in ('executor','checker'):raise ValueError('Invalid app run/role')
  if self.bound_run is not None and self.bound_run!=run:
   previous=json.loads((self.state/(self.bound_run+'.json')).read_bytes())
   if not previous['roles'] or any(not (b.get('published') or (b.get('last_cancel') or {}).get('cancel_confirmed')) for b in previous['roles'].values()):raise ValueError('Previous app run is not confirmed settled; query it before starting another')
  self.bound_run=run
  file=self.state/(run+'.json');record=json.loads(file.read_bytes()) if file.exists() else {'run_id':run,'roles':{}}
  request_id='swarm-'+run+'-'+role;control=tasks.Control(self.world)
  bound=record['roles'].get(role)
  if name=='codex_task_start':
   task=args.get('task');criteria=args.get('criteria','逐项核对任务要求，报告通过、问题或无法判断并说明依据。')
   if not isinstance(task,str) or not 0<len(task)<=8000 or not isinstance(criteria,str) or len(criteria)>2000:raise ValueError('Bounded task and criteria text required')
   if bound:
    if bound['task']!=task or bound['criteria']!=criteria:raise ValueError('App role identity already bound to different input')
    return self.observe(control,bound,args.get('cursor',0)) # Never dispatch again, even unknown.
   if role=='executor':prompt='你是执行者，只完成下列用户任务，只输出最终结果。不审阅自身结果。\n任务：'+task
   else:
    prior=record['roles'].get('executor')
    if not prior:raise ValueError('No owned executor publication')
    if task!=prior['task'] or criteria!=prior['criteria']:raise ValueError('Checker must review the original owned task and criteria')
    self.observe(control,prior,0)
    if not prior.get('published'):raise ValueError('Executor final result not yet published; checker not dispatched')
    publication=prior['published'];prompt='你是独立检查者。只根据原任务、已发布结果和检查标准审阅，不假定执行者私有上下文。\n'+json.dumps({'task':task,'published_result':publication,'criteria':criteria},ensure_ascii=False)
   bound={'request_id':request_id,'task':task,'criteria':criteria,'prompt':prompt,'dispatch':'reserved','task_id':None};record['roles'][role]=bound;tasks.atomic(file,record)
   # Reservation precedes the public task call; every subsequent start only queries.
   try:
    reply=control.call('codex_task_start',{'request_id':request_id,'prompt':prompt,'mode':'read_only','context_policy':'isolated_text'})
    bound.update(task_id=reply['task_id'],dispatch='accepted');tasks.atomic(file,record)
   except Exception:
    bound['dispatch']='unknown';tasks.atomic(file,record);raise
  if not bound:raise ValueError('Unknown application role; no request submitted')
  if name=='codex_task_cancel':
   if not bound.get('task_id'):return {'status':'unknown','cancel_confirmed':False,'request_id':request_id,'replay_allowed':False}
   reply=control.call('codex_task_cancel',{'task_id':bound['task_id']});bound['last_cancel']=reply
   current=self.observe(control,bound,args.get('cursor',0));current.update({k:reply[k] for k in ('cancel_accepted','cancel_confirmed','reason') if k in reply});tasks.atomic(file,record);return current
  reply=self.observe(control,bound,args.get('cursor',0));tasks.atomic(file,record);return reply
 def observe(self,control,bound,cursor):
  if type(cursor) is not int or cursor<0:raise ValueError('Nonnegative Unicode output cursor required')
  reply=control.call('codex_task_status',{'request_id':bound['request_id'],'cursor':cursor,'max_chars':4096,'wait_ms':0})
  bound['task_id']=reply['task_id']
  if reply['status']=='done' and not bound.get('published'):
   # Consume each final page once, never reconstruct an existing binary through encoding.
   parts=[];position=0
   for _ in range(64):
    page=control.call('codex_task_status',{'task_id':reply['task_id'],'cursor':position,'max_chars':16384})
    if page['next_cursor']<position or (page['has_more'] and page['next_cursor']==position):raise ValueError('Model output cursor made no progress')
    parts.append(page['output']);position=page['next_cursor']
    if not page['has_more']:break
   else:raise ValueError('Model output exceeds bounded publication; raw task result retained')
   text=''.join(parts);codex=(reply.get('receipt') or {}).get('codex',{});effective=codex.get('effective_model') or {}
   if effective.get('thread_start_model')!='gpt-6.1-sol' or effective.get('thread_start_effort')!='high':raise ValueError('Actual model/effort was not confirmed')
   bound['published']={'text':text,'sha256':hashlib.sha256(text.encode()).hexdigest(),'task_id':reply['task_id'],'session_id':codex.get('thread_id'),'actual_model':effective}
  if bound.get('published'):reply['published']=bound['published']
  reply['dispatch_state']=bound['dispatch'];return reply
