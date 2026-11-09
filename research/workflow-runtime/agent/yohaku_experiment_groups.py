"""Private host experiment membership, cumulative limits and owned-task cleanup.

Only trusted host Python configures/binds groups. World documents and tool
arguments cannot grant membership or reset this journal.
"""
import contextlib,fcntl,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path

LIMITS={'active_nodes':None,'dispatches':None,'tool_calls':None,'seconds':None}
from open_capacity import capacity,CapacityBusy
class BudgetExceeded(RuntimeError):pass

class Groups:
 def __init__(self,world):
  self.world=str(Path(world).resolve(strict=True))
  from yohaku_codex_tasks import state_root
  self.path=state_root()/('experiment-'+hashlib.sha256(self.world.encode()).hexdigest()+'.json')
 @contextlib.contextmanager
 def locked(self):
  from yohaku_codex_tasks import atomic
  fd=os.open(str(self.path)+'.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
  try:
   fcntl.flock(fd,fcntl.LOCK_EX)
   if self.path.is_symlink():raise ValueError('Private group journal must not be a symlink')
   v=json.loads(self.path.read_text()) if self.path.exists() else {'world':self.world,'groups':{},'nodes':{}}
   if v['world']!=self.world:raise ValueError('Private group world mismatch')
   before=json.dumps(v,sort_keys=True)
   try:yield v
   finally:
    if json.dumps(v,sort_keys=True)!=before:atomic(self.path,v)
  finally:os.close(fd)
 def configure(self,group_id):
  if not isinstance(group_id,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',group_id):raise ValueError('Invalid experiment group ID')
  with self.locked() as v:
   g=v['groups'].setdefault(group_id,{'group_id':group_id,'limits':dict(LIMITS),'created_at':time.time(),'started_at':None,'deadline':None,'dispatches':{},'tool_calls':0,'closed':False,'reason':None,'cleanup_complete':False,'cleanup':[]})
   if g['limits']!=LIMITS:raise ValueError('Existing experiment limits differ; cannot reset cumulative budget')
   return json.loads(json.dumps(g))
 def bind(self,group_id,node_ids):
  with self.locked() as v:
   g=v['groups'][group_id]
   if g['closed']:raise BudgetExceeded('Experiment group is closed')
   for node in node_ids:
    if node=='main' or not isinstance(node,str):raise ValueError('Only independent node IDs may join experiments')
    if node in v['nodes'] and v['nodes'][node]!=group_id:raise ValueError('Node already belongs to a different experiment')
   for node in node_ids:v['nodes'][node]=group_id
   return {'group_id':group_id,'node_ids':list(node_ids),'limits':dict(LIMITS)}
 def group_for(self,node):
  with self.locked() as v:return v['nodes'].get(node)
 def inherit(self,parent,node):
  group=self.group_for(parent)
  if group:self.bind(group,[node])
 def same_group(self,actor,target):
  with self.locked() as v:
   group=v['nodes'].get(actor)
   if not group or v['nodes'].get(target)!=group:raise ValueError('Caller and target must belong to the same host-bound experiment group')
   return group
 def _finished(self,tid):
  from yohaku_codex_tasks import read_record,alive,identity
  try:r=read_record(tid)
  except ValueError:return False
  return bool((r.get('receipt') or {}).get('native_cleanup_complete') and not alive(r) and not any((p:=identity(n.get('pid'))) and p['start']==n.get('start') and p['state']!='Z' for n in r.get('native',[])))
 def reserve(self,node,tid):
  group=self.group_for(node)
  if not group:return None
  error=None
  with self.locked() as v:
   g=v['groups'][group]
   if tid in g['dispatches']:return group
   active=sum(not x.get('queued_cancelled') and not self._finished(t) for t,x in g['dispatches'].items())
   if g['closed']:error='Experiment group is closed: '+str(g['reason'])
   elif g['deadline'] is not None and time.time()>=g['deadline']:error='Experiment wall-time budget exhausted'
   elif active>=capacity():raise CapacityBusy('Machine capacity busy; retry/query same node identity after confirmed cleanup')
   if error:g.update(closed=True,reason=error)
   else:
    if g['started_at'] is None:g.update(started_at=time.time(),deadline=None)
    g['dispatches'][tid]={'node_id':node,'reserved_at':time.time(),'stop_requested':False}
  self.ensure_watch(group)
  if error:raise BudgetExceeded(error)
  return group
 def before_start(self,node,tid):
  group=self.reserve(node,tid)
  if not group:return True
  with self.locked() as v:
   g=v['groups'][group];entry=g['dispatches'][tid]
   if g['closed'] or(g['deadline']is not None and time.time()>=g['deadline'])or entry.get('stop_requested'):
    entry.update(stop_requested=True,queued_cancelled=True)
    return False
  return True
 def after_start(self,node):
  group=self.group_for(node)
  if not group:return
  with self.locked() as v:
   g=v['groups'][group]
   pass # Dispatch count remains evidence, never an experimental stop rule.
 def stop_task(self,actor,target,tid):
  group=self.same_group(actor,target)
  with self.locked() as v:
   entry=v['groups'][group]['dispatches'].get(tid)
   if not entry or entry['node_id']!=target:raise ValueError('Target task is not bound to this experiment node')
   entry['stop_requested']=True
  return group
 def before_tool(self,node,tid):
  group=self.group_for(node)
  if not group:return
  error=None
  with self.locked() as v:
   g=v['groups'][group]
   if tid not in g['dispatches'] or g['dispatches'][tid]['node_id']!=node:raise ValueError('Tool caller has no host-bound experiment dispatch')
   if g['closed']:error='Experiment group closed: '+str(g['reason'])
   elif g['deadline']is not None and time.time()>=g['deadline']:error='Node-requested deadline exhausted'
   if error:g.update(closed=True,reason=error)
   else:g['tool_calls']+=1
  if error:
   self.ensure_watch(group)
   raise BudgetExceeded(error)
 def after_tool(self,node):
  group=self.group_for(node)
  if not group:return
  with self.locked() as v:
   g=v['groups'][group]
   pass # Tool count remains evidence, never an experimental stop rule.
 def project_request(self,node,task_id,request_id):
  group=self.group_for(node)
  if not group:return
  with self.locked() as v:
   g=v['groups'][group]
   if g['closed']:raise BudgetExceeded('Experiment closed before offline task submission')
   g.setdefault('project_requests',{}).setdefault(request_id,{'request_id':request_id,'model_task_id':task_id,'node_id':node})
 def status(self,group_id):
  with self.locked() as v:result=json.loads(json.dumps(v['groups'][group_id]))
  result['dispatch_count']=len(result['dispatches'])
  result['active_count']=sum(not x.get('queued_cancelled') and not self._finished(t) for t,x in result['dispatches'].items())
  result['remaining_seconds']=max(0,result['deadline']-time.time())if result['deadline']else None
  result['machine_capacity_admission']=capacity()
  return result
 def ensure_watch(self,group):
  from yohaku_codex_tasks import identity
  with self.locked() as v:
   g=v['groups'][group];old=g.get('watch') or {};current=identity(old.get('pid'))
   if current and current['start']==old.get('start') and current['state']!='Z':return
   log=self.path.with_suffix('.watch.log').open('ab')
   try:child=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'watch',self.world,group],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
   finally:log.close()
   g['watch']=identity(child.pid)
   import threading
   threading.Thread(target=child.wait,daemon=True).start()
 def close(self,group_id,reason='Host closed experiment',wait_seconds=25):
  with self.locked() as v:
   g=v['groups'][group_id];g.update(closed=True,reason=g['reason'] or reason)
  self.ensure_watch(group_id)
  end=time.monotonic()+wait_seconds
  while True:
   result=self.status(group_id)
   if result['cleanup_complete'] or time.monotonic()>=end:return result
   time.sleep(.1)
 def watch(self,group):
  from yohaku_codex_tasks import Control,read_record
  while True:
   with self.locked() as v:
    g=v['groups'][group]
    if g['deadline'] is not None and time.time()>=g['deadline']:g.update(closed=True,reason=g['reason'] or 'Experiment wall-time budget exhausted')
    closed=g['closed'];pending=list(g['dispatches'])
   if closed:break
   time.sleep(.2)
  tasks=Control(self.world);end=time.monotonic()+90;cleanup={}
  while True:
   for tid in pending:
    try:
     with self.locked() as v:
      entry=v['groups'][group]['dispatches'][tid];entry['stop_requested']=True
      try:read_record(tid)
      except ValueError:entry['queued_cancelled']=True
      queued=entry.get('queued_cancelled',False)
     if queued:
      cleanup[tid]={'task_id':tid,'queued_cancelled':True,'cleanup_confirmed':True,'native':[]}
     else:
      result=tasks.cancel({'task_id':tid});r=read_record(tid)
      cleanup[tid]={'task_id':tid,'status':result['status'],'cancel_confirmed':result.get('cancel_confirmed'),'cleanup_confirmed':self._finished(tid),'runner':{'pid':r.get('pid'),'start':r.get('start')},'receipt':r.get('receipt')}
    except Exception as exc:cleanup[tid]={'task_id':tid,'cleanup_confirmed':False,'error':str(exc)[:500]}
   complete=all(cleanup[t].get('cleanup_confirmed') for t in pending)
   # Project submissions are recorded before the tool runs, so lost receipts
   # and model cancellation cannot hide still-running sandbox processes.
   with self.locked() as v:project_requests=list(v['groups'][group].get('project_requests',{}).values())
   project_cleanup=[]
   from yohaku_project_tasks import Tasks as ProjectTasks,alive as project_alive
   from yohaku_project_schema import ProjectError
   projects=ProjectTasks(self.world)
   for submission in project_requests:
    try:
     p=projects.status(request_id=submission['request_id']);p=projects.cancel(p['task_id']);r=projects._owned(p['task_id'])
     project_cleanup.append({'request_id':submission['request_id'],'task_id':p['task_id'],'status':p['status'],'receipt':p.get('receipt'),'cleanup_confirmed':bool((p.get('receipt') or {}).get('cleanup_confirmed')) and not project_alive(r)})
    except ProjectError as exc:
     project_cleanup.append({'request_id':submission['request_id'],'cleanup_confirmed':complete and exc.kind=='unknown_task','not_submitted':exc.kind=='unknown_task','error':str(exc)[:500]})
    except Exception as exc:project_cleanup.append({'request_id':submission['request_id'],'cleanup_confirmed':False,'error':str(exc)[:500]})
   complete=complete and all(x['cleanup_confirmed'] for x in project_cleanup)
   with self.locked() as v:v['groups'][group].update(cleanup=list(cleanup.values()),project_cleanup=project_cleanup,cleanup_complete=complete,cleanup_observed_at=time.time())
   if complete or time.monotonic()>=end:return
   time.sleep(.2)

if __name__=='__main__':
 if len(sys.argv)!=4 or sys.argv[1]!='watch':raise SystemExit('Private host group watchdog only')
 Groups(sys.argv[2]).watch(sys.argv[3])
