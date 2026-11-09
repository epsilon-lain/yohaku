"""Bounded protocol frames and per-turn output progress. Full large payloads stay private."""
import hashlib,json,os,stat,threading,uuid
from pathlib import Path
INLINE_FRAME=2*1024*1024
MAX_ARCHIVE=64*1024*1024
MAX_SESSION_ARCHIVE=128*1024*1024
INLINE_RESULT=128*1024

class PayloadError(ValueError):pass
class NoOutputProgress(ValueError):pass

class ArchivedFrame:
 def __init__(self,archive,record):self.archive=archive;self.record=record
 def load(self):
  try:
   descriptor=os.open(self.record['path'],os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
   with os.fdopen(descriptor,'rb') as stream:
    meta=os.fstat(stream.fileno())
    if not stat.S_ISREG(meta.st_mode) or meta.st_size!=self.record['bytes']:raise PayloadError('Archived frame identity changed; no call executed')
    raw=stream.read(MAX_ARCHIVE+1)
   if hashlib.sha256(raw).hexdigest()!=self.record['sha256']:raise PayloadError('Archived frame bytes changed; no call executed')
   value=json.loads(raw)
  except (ValueError,UnicodeError,RecursionError):raise PayloadError('Invalid JSON in archived protocol frame; full private file preserved; login status undetermined') from None
  if not isinstance(value,dict):raise PayloadError('Archived protocol frame is not an object; full private file preserved')
  if value.get('method')=='item/completed':
   item=value.get('params',{}).get('item',{})
   if item.get('type')=='agentMessage' and isinstance(item.get('text'),str) and len(item['text'].encode())>INLINE_RESULT:
    text=item['text'];item['text']=text[:8192]+'\n[Large response continued in private payload file: '+self.record['path']+' ; JSON pointer /params/item/text ; full frame bytes='+str(self.record['bytes'])+' ; SHA256='+self.record['sha256']+'. Preview only; original retained in full.]'
    item['yohaku_payload_ref']={**self.record,'json_pointer':'/params/item/text','text_utf8_bytes':len(text.encode()),'preview_only':True}
  return value

class PayloadArchive:
 def __init__(self,root,session_id=None,observer=None):
  self.root=Path(root);self.directory=self.root/((session_id or uuid.uuid4().hex)+'.payloads');self.observer=observer
  self.total=0;self.lock=threading.Lock()
 def _directory(self):
  self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
  self.directory.mkdir(exist_ok=True,mode=0o700)
  for path in (self.root,self.directory):
   meta=path.lstat()
   if not stat.S_ISDIR(meta.st_mode) or (hasattr(os,'getuid') and (meta.st_uid!=os.getuid() or meta.st_mode & 0o077)):
    raise PayloadError('Private payload directory is not safe; no unprotected raw frame saved')
 def _file(self,kind):
  self._directory();path=self.directory/(kind+'-'+uuid.uuid4().hex+'.json')
  fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
  return path,os.fdopen(fd,'wb')
 def _notify(self,record):
  if self.observer is not None:self.observer(record)
 def receive(self,first,stream):
  path,file=self._file('incoming');digest=hashlib.sha256();size=0;complete=False
  try:
   part=first
   while part:
    with self.lock:
     if size+len(part)>MAX_ARCHIVE or self.total+len(part)>MAX_SESSION_ARCHIVE:
      raise PayloadError('Protocol archive limit exceeded; captured prefix explicitly incomplete; no oversized call executed')
     self.total+=len(part)
    file.write(part);digest.update(part);size+=len(part)
    if part.endswith(b'\n'):complete=True;break
    part=stream.readline(65536)
  finally:
   file.flush();os.fsync(file.fileno());file.close()
   record={'kind':'incoming_protocol_frame','path':str(path),'bytes':size,'sha256':digest.hexdigest(),'complete':complete,'inline_limit':INLINE_FRAME,'archive_limit':MAX_ARCHIVE,'delivery':'private reference, consumed once; no inline limit increase'}
   self._notify(record)
  if not complete:raise PayloadError('Protocol frame ended without newline; incomplete raw frame preserved, no call executed')
  return ArchivedFrame(self,record)
 def save_json(self,value,kind='tool-result'):
  data=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
  with self.lock:
   if len(data)>MAX_ARCHIVE or self.total+len(data)>MAX_SESSION_ARCHIVE:raise PayloadError('Private payload archive limit exceeded; no silent result truncation')
   self.total+=len(data)
  path,file=self._file(kind)
  with file:file.write(data);file.flush();os.fsync(file.fileno())
  record={'kind':kind,'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'complete':True}
  self._notify(record);return record
 def compact(self,result,args):
  value=result.get('result') if isinstance(result,dict) else None
  # Raw task pages are already bounded by the shared 64KiB contract. Deliver every byte, not a summary of a page.
  if isinstance(value,dict) and value.get('cursor_unit')=='bytes' and type(value.get('cursor')) is int and type(value.get('next_cursor')) is int and 0<=value['next_cursor']-value['cursor']<=65536 and isinstance(value.get('base64'),str) and len(value['base64'])<=87384 and len(json.dumps(result,ensure_ascii=False).encode())<INLINE_FRAME:
   return result
  if len(json.dumps(result,ensure_ascii=False).encode())<=INLINE_RESULT:return result
  ref=self.save_json(result)
  def shrink(value,pointer=''):
   if isinstance(value,str) and len(value.encode())>8192:
    return {'payload_ref':ref,'json_pointer':pointer,'utf8_bytes':len(value.encode()),'preview':value[:512],'preview_only':True}
   if isinstance(value,list) and len(json.dumps(value,ensure_ascii=False).encode())>8192:
    return {'payload_ref':ref,'json_pointer':pointer,'items':len(value),'preview_only':False}
   if isinstance(value,dict):return {key:shrink(v,pointer+'/'+key.replace('~','~0').replace('/','~1')) for key,v in value.items()}
   return value
  answer=shrink(result);answer['payload_delivery']={'original':ref,'inline_is_summary':True,'full_original_preserved':True}
  source=args.get('source',args.get('path')) if isinstance(args,dict) else None
  if isinstance(source,str):answer['payload_delivery']['read_world_source']={'tool':'read_range','path':source,'view':'body' if source.endswith('.tex') else 'text','start_line':1,'start_column':1}
  if len(json.dumps(answer,ensure_ascii=False).encode())>INLINE_RESULT:
   value=result.get('result',{}) if isinstance(result,dict) else {}
   keep=('task_id','request_id','source','path','saved','save_status','saved_revision','revision','state','exit_code','next_cursor','has_more','output_complete')
   answer={'ok':result.get('ok'),'result':{k:value[k] for k in keep if k in value},'payload_delivery':answer['payload_delivery']}
  return answer
 def audit(self,ident,name,args,result):
  if name not in ('task_output','task_status','task_watch'):return
  args=args if isinstance(args,dict) else {}
  self._directory();value=result.get('result',{}) if isinstance(result,dict) else {};value=value if isinstance(value,dict) else {}
  allowed=('task_id','request_id','stream','cursor','max_bytes','after_seq','wait_ms')
  row={'origin':'real_codex_tool_call','call_id':str(ident),'tool':name,'arguments':{k:v for k,v in args.items() if k in allowed and (type(v) in (int,bool) or isinstance(v,str) and len(v)<256)},'ok':result.get('ok'),'error':result.get('error') if isinstance(result.get('error'),str) and len(result['error'])<512 else None,'result':{k:value[k] for k in ('task_id','stream','cursor_unit','cursor','next_cursor','output_end','bytes_returned','has_more','output_complete','read_state','state','exit_code','event_seq') if k in value}}
  if isinstance(value.get('text'),str):row['result']['text_utf8_bytes']=len(value['text'].encode())
  if isinstance(value.get('base64'),str):row['result']['base64_chars']=len(value['base64'])
  fd=os.open(self.directory/'task-reads.jsonl',os.O_WRONLY|os.O_CREAT|os.O_APPEND|getattr(os,'O_NOFOLLOW',0),0o600)
  with os.fdopen(fd,'a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')

class OutputProgress:
 """Model-turn policy only; stateless task API/manual history reads remain unchanged."""
 def __init__(self):self.pages={};self.confirmed={}
 def observe(self,name,args,result):
  if not result.get('ok') or not isinstance(result.get('result'),dict):return result
  value=result['result'];tid=value.get('task_id')
  if name=='task_status':
   if value.get('state') in ('succeeded','failed','cancelled') and type(value.get('exit_code')) is int:self.confirmed[tid]={k:value.get(k) for k in ('state','exit_code','event_seq')}
   return result
  if name!='task_output':return result
  if value.get('exit_code') is None and tid in self.confirmed:
   value=dict(value,last_confirmed_status=self.confirmed[tid]);result={**result,'result':value}
  key=(tid,value.get('stream'),value.get('cursor'))
  stamp=(value.get('next_cursor'),hashlib.sha256(value.get('base64','').encode()).hexdigest(),value.get('event_seq'),value.get('output_complete'))
  previous=self.pages.get(key);count=previous[1]+1 if previous and previous[0]==stamp else 0
  self.pages[key]=(stamp,count)
  if len(self.pages)>512:self.pages.pop(next(iter(self.pages)))
  if count>=3:raise NoOutputProgress('Repeated output page made no progress three times; turn stopped, tasks and full logs preserved. Resume by stable task_id and next_cursor; never resubmit')
  if count:
   complete=value.get('read_state')=='complete'
   return {'ok':False,'kind':'output_already_read' if complete else 'output_no_progress','error':'This exact page was already delivered; use next_cursor, or task_watch/task_status while pending. No task was executed.','task_id':tid,'stream':value.get('stream'),'cursor_unit':'bytes','next_cursor':value.get('next_cursor'),'read_state':value.get('read_state'),'repeat_count':count,'replay_allowed':False,'status_query':{'tool':'task_status','task_id':tid}}
  return result
