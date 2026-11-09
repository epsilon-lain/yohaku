"""Project-authorized browser recipes authored as Loom documents, never host code."""
import contextlib,fcntl,hashlib,json,os,re,stat,tempfile
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
from urllib.parse import urlencode,urlsplit,urlunsplit

FORMAT='yohaku-browser-tool/1'
INDEX_FORMAT='yohaku-browser-tools/1'
RUN_FORMAT='yohaku-browser-tool-run/1'
ALLOWED={'browser_open','browser_tabs','browser_snapshot','browser_find','browser_read',
         'browser_act','browser_fetch','browser_save','browser_materials'}
FORBIDDEN={'actor','actor_node_id','secret','path','profile','spool','socket','command','code',
           'javascript','script','executable','project_scopes','permissions','host_path',
           'password','otp','token','api_key','cookie','authorization'}
KEY=re.compile(r'[A-Za-z0-9_.-]{1,80}\Z')
REQUEST=re.compile(r'[A-Za-z0-9_.:-]{1,128}\Z')
MAX_OUTPUT=12000

def stamp():return datetime.now(timezone.utc).isoformat()
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def revision(text):return hashlib.sha256(text.encode()).hexdigest()
def valid_key(value,label):
 if not isinstance(value,str) or not KEY.fullmatch(value):raise ValueError(label+' must be a bounded ASCII identifier')
 return value
def relative(value):
 if not isinstance(value,str) or not value or '\\' in value:raise ValueError('Use a world-relative project source')
 p=PurePosixPath(value)
 if p.is_absolute() or any(s in ('..','.') for s in p.parts):raise ValueError('Use a contained project source')
 return str(p)
def safe_template(value,depth=0):
 if depth>20:raise ValueError('Browser recipe expression nesting exceeded')
 if isinstance(value,dict):
  if any(k in FORBIDDEN for k in value):raise ValueError('Browser recipe cannot set host identity, paths, execution or authorization')
  if '$ref' in value:
   if set(value)!={'$ref'} or not isinstance(value['$ref'],str) or not value['$ref'].startswith(('inputs.','steps.')):raise ValueError('Invalid browser recipe reference')
  elif '$url' in value:
   if set(value)!={'$url'} or not isinstance(value['$url'],dict) or set(value['$url'])!={'base','query'}:raise ValueError('URL expression requires base and query')
   base=value['$url']['base'];parsed=urlsplit(base) if isinstance(base,str) else None
   if parsed is None or parsed.scheme not in ('http','https') or not parsed.netloc or parsed.username or parsed.password:raise ValueError('Recipe URL base must be a literal public web URL')
   if not isinstance(value['$url']['query'],dict):raise ValueError('URL expression query must be an object')
   for child in value['$url']['query'].values():safe_template(child,depth+1)
  else:
   for child in value.values():safe_template(child,depth+1)
 elif isinstance(value,list):
  if len(value)>100:raise ValueError('Browser recipe expression array exceeded')
  for child in value:safe_template(child,depth+1)
 elif not isinstance(value,(str,int,float,bool,type(None))):raise ValueError('Unsupported browser recipe expression')

def schema_check(value,schema,path='inputs',depth=0):
 if depth>8 or not isinstance(schema,dict):raise ValueError('Browser recipe input schema is invalid')
 kind=schema.get('type')
 matches={'object':lambda:isinstance(value,dict),'array':lambda:isinstance(value,list),
          'string':lambda:isinstance(value,str),'integer':lambda:type(value)is int,
          'number':lambda:type(value)in (int,float),'boolean':lambda:type(value)is bool,
          'null':lambda:value is None}
 if kind not in matches or not matches[kind]():raise ValueError(path+' does not match its declared input type')
 if 'enum' in schema and value not in schema['enum']:raise ValueError(path+' is outside its input enum')
 if kind=='object':
  props=schema.get('properties',{})
  if not isinstance(props,dict) or len(props)>20 or any(k in FORBIDDEN or not KEY.fullmatch(k) for k in props):raise ValueError('Invalid browser recipe input names')
  required=schema.get('required',[])
  if not isinstance(required,list) or any(not isinstance(k,str) or k not in props for k in required):raise ValueError('Invalid browser recipe required inputs')
  if set(value)-set(props) or set(required)-set(value):raise ValueError(path+' has missing or unknown inputs')
  for key,item in value.items():schema_check(item,props[key],path+'.'+key,depth+1)
 elif kind=='array':
  if len(value)>min(100,schema.get('maxItems',100)):raise ValueError(path+' exceeds its input array bound')
  for item in value:schema_check(item,schema.get('items',{}),path+'[]',depth+1)
 elif kind=='string':
  if len(value)>min(8000,schema.get('maxLength',8000)) or len(value)<schema.get('minLength',0):raise ValueError(path+' exceeds its input string bounds')
 elif kind in ('integer','number'):
  if ('minimum' in schema and value<schema['minimum']) or ('maximum' in schema and value>schema['maximum']):raise ValueError(path+' exceeds its input number bounds')

def expand(value,context,depth=0):
 if depth>20:raise ValueError('Browser recipe expression nesting exceeded')
 if isinstance(value,dict):
  if set(value)=={'$ref'}:
   item=context
   for part in value['$ref'].split('.'):
    if isinstance(item,dict) and part in item:item=item[part]
    elif isinstance(item,list) and part.isdigit() and int(part)<len(item):item=item[int(part)]
    else:raise ValueError('Browser recipe reference is unavailable: '+value['$ref'])
   return json.loads(json.dumps(item,ensure_ascii=False))
  if set(value)=={'$url'}:
   spec=value['$url'];parsed=urlsplit(spec['base']);query={k:expand(v,context,depth+1) for k,v in spec['query'].items()}
   if any(not isinstance(v,(str,int,float,bool)) for v in query.values()):raise ValueError('URL query expression must resolve to scalar values')
   encoded=urlencode(query);return urlunsplit((parsed.scheme,parsed.netloc,parsed.path,parsed.query+('&' if parsed.query and encoded else '')+encoded,parsed.fragment))
  return {k:expand(v,context,depth+1) for k,v in value.items()}
 if isinstance(value,list):return [expand(v,context,depth+1) for v in value]
 return value

class Recipes:
 """All document writes use the existing Rust Workspace/Loom public commands."""
 def __init__(self,control):self.control=control;self.world=Path(control.world);self.actor=control.actor
 def _host_path(self,key):
  from yohaku_project_tasks import private_dir
  base=private_dir(getattr(self.control,'recipe_state_dir',None) or Path.home()/'.local/state/yohaku/browser-recipes')
  if base.is_relative_to(self.world.resolve()):raise ValueError('Browser recipe host receipts must stay outside public world files')
  directory=private_dir(base/digest(str(self.world.resolve()))[:24]);return directory/(key+'.json')
 @contextlib.contextmanager
 def _host_locked(self,key):
  path=self._host_path(key);fd=os.open(path.with_suffix('.lock'),os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
  try:fcntl.flock(fd,fcntl.LOCK_EX);yield path
  finally:fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
 def _host_read(self,path):
  if not path.exists():return None
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  try:
   info=os.fstat(fd)
   if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or info.st_size>256*1024:raise ValueError('Browser recipe host receipt is unsafe')
   with os.fdopen(fd,'r',closefd=False) as stream:return json.load(stream)
  finally:os.close(fd)
 def _host_write(self,path,record):
  data=json.dumps(record,ensure_ascii=False,indent=2)+'\n'
  if len(data.encode())>256*1024:raise ValueError('Browser recipe host receipt exceeded bound; no replay')
  fd,temporary=tempfile.mkstemp(prefix='.recipe-',dir=path.parent)
  try:
   with os.fdopen(fd,'w') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
   os.replace(temporary,path)
  finally:
   if os.path.exists(temporary):os.unlink(temporary)
 def _scope(self,project_id):
  scope=self.control.check_project(project_id)
  if not isinstance(scope,dict) or not isinstance(scope.get('root'),str):raise ValueError('Browser recipe needs a valid registered project binding')
  return scope
 def _path(self,source,project_id):
  source=relative(source);scope=self._scope(project_id)
  if not source.startswith(scope['root']+'/') or not source.endswith('.tex'):raise ValueError('Browser recipe document is outside its authorized project')
  path=self.world
  for part in PurePosixPath(source).parts:
   path=path/part
   if path.is_symlink():raise ValueError('Browser recipe paths must not use symlinks')
  if path.with_suffix('').is_symlink():raise ValueError('Browser recipe output must not be a symlink')
  return path
 def _read(self,source,project_id):
  self._path(source,project_id);doc=self.control.read_project_source(source)
  if not isinstance(doc,dict) or not isinstance(doc.get('text'),str) or not isinstance(doc.get('body'),str):raise ValueError('Browser recipe source read failed')
  return dict(doc,revision=revision(doc['text']))
 def _write(self,source,value,project_id,expected=None):
  path=self._path(source,project_id);text=json.dumps({k:v for k,v in value.items() if k!='public_revision'},ensure_ascii=False,indent=2)+'\n'
  if path.exists():
   current=self._read(source,project_id)
   if expected is None or current['revision']!=expected:raise ValueError('Browser recipe document changed; query the original operation before retrying')
   result=self.control.workspace.execute({'command':'save','source':source,'expected':current['text'],'text':text,'body_only':True})
  else:
   if expected is not None or path.with_suffix('').exists():raise ValueError('Browser recipe document has conflicting output; preserved')
   result=self.control.workspace.execute({'command':'create','directory':str(PurePosixPath(source).parent),'name':path.name[:-4],'body':text,
     'notes':{'source_version':1,'writer':self.actor,'summary':'Host-bound browser recipe registry/operation record; no credential or arbitrary code execution.'}})
  if result.get('sync_error') or result.get('loom',{}).get('ok') is False:raise ValueError('Browser recipe document may be saved but Loom failed; inspect before retrying')
  back=self._read(source,project_id)
  if back['body']!=text:raise ValueError('Browser recipe save read-back mismatch; do not replay')
  return back
 def _index_source(self,pid):return self._scope(pid)['root']+'/research/browser-tools.json.tex'
 def _index(self,pid):
  source=self._index_source(pid)
  if not self._path(source,pid).exists():return source,{'format':INDEX_FORMAT,'project_id':pid,'tools':{}},None
  doc=self._read(source,pid);value=json.loads(doc['body'])
  if value.get('format')!=INDEX_FORMAT or value.get('project_id')!=pid or not isinstance(value.get('tools'),dict):raise ValueError('Invalid browser recipe project index')
  return source,value,doc['revision']
 def _spec(self,source,tool_id=None):
  source=relative(source)
  # The facade must enforce current project scope and successful Loom generation.
  doc=self.control.read_project_source(source)
  if len(doc['body'].encode())>65536:raise ValueError('Browser recipe source exceeds 64 KiB')
  spec=json.loads(doc['body'])
  if not isinstance(spec,dict) or set(spec)-{'format','id','name','description','project_id','inputs','steps','output'}:raise ValueError('Invalid browser recipe specification')
  if spec.get('format')!=FORMAT:raise ValueError('Unsupported browser recipe format')
  local=valid_key(spec.get('id'),'Browser tool id');pid=spec.get('project_id')
  if not isinstance(pid,str) or not 1<=len(pid)<=128:raise ValueError('Browser recipe needs a registered project_id')
  self._path(source,pid)
  if not isinstance(spec.get('name'),str) or not 1<=len(spec['name'])<=160 or not isinstance(spec.get('description',''),str) or len(spec.get('description',''))>500:raise ValueError('Browser recipe name/description is invalid')
  qualified=pid+':'+local
  if tool_id is not None and tool_id not in (local,qualified):raise ValueError('Browser tool id must match the authoritative project specification')
  schema=spec.get('inputs');steps=spec.get('steps')
  if not isinstance(schema,dict) or schema.get('type')!='object' or not isinstance(steps,list) or not 1<=len(steps)<=20:raise ValueError('Browser recipe requires an object input schema and 1..20 steps')
  if len(json.dumps(schema,ensure_ascii=False))>6000:raise ValueError('Browser recipe input schema exceeds discovery bound')
  # Validate declarations even if all fields are optional and no input was given.
  props=schema.get('properties',{});required=schema.get('required',[])
  if not isinstance(props,dict) or len(props)>20 or not isinstance(required,list) or any(not isinstance(k,str) or k not in props for k in required):raise ValueError('Invalid browser recipe input schema')
  if any(k in FORBIDDEN or not KEY.fullmatch(k) for k in props):raise ValueError('Browser recipe cannot expose host identity/path inputs')
  seen=set()
  for step in steps:
   if not isinstance(step,dict) or set(step)!={'id','tool','arguments'}:raise ValueError('Each browser recipe step requires id/tool/arguments')
   key=valid_key(step['id'],'Step id')
   if key in seen or not isinstance(step['tool'],str) or step['tool'] not in ALLOWED or not isinstance(step['arguments'],dict):raise ValueError('Browser recipe has duplicate step ids or unsupported tools')
   seen.add(key);safe_template(step['arguments'])
  safe_template(spec.get('output',{'$ref':'steps.'+steps[-1]['id']}))
  return spec,qualified,revision(doc['text'])
 def register(self,source,tool_id=None):
  source=relative(source);spec,qualified,version=self._spec(source,tool_id);pid=spec['project_id'];index_source,index,expected=self._index(pid)
  entry={'tool_id':qualified,'local_id':spec['id'],'name':spec['name'],'description':spec.get('description',''),'project_id':pid,'source':source,'revision':version,
         'registered_by':self.actor,'registered_at':stamp(),'binding':self._scope(pid),'inputs':spec['inputs']}
  old=index['tools'].get(qualified)
  if old and all(old.get(k)==entry.get(k) for k in ('source','revision','binding','name','description','inputs')):
   return {'registered':True,'duplicate':True,'tool':old,'citation':source+'@'+version,'index_source':index_source}
  index['tools'][qualified]=entry;back=self._write(index_source,index,pid,expected)
  return {'registered':True,'duplicate':False,'tool':entry,'citation':source+'@'+version,'index_source':index_source,'index_revision':back['revision']}
 def _project_ids(self,project_id=None):
  if project_id is not None:self._scope(project_id);return [project_id]
  scopes=getattr(self.control,'project_scopes',None)
  if scopes is not None:return [s['project_id'] for s in scopes]
  from yohaku_project_sources import Projects
  registry,_=Projects(self.world,workspace=self.control.workspace)._registry();return [row['id'] for row in registry['projects']]
 def list(self,project_id=None,offset=0,limit=20):
  if type(offset)is not int or offset<0 or type(limit)is not int or not 1<=limit<=100:raise ValueError('Invalid browser tool listing bounds')
  rows=[];errors=[]
  for pid in self._project_ids(project_id):
   try:
    _,index,_=self._index(pid)
    for entry in index['tools'].values():
     if not isinstance(entry,dict) or entry.get('project_id')!=pid or not isinstance(entry.get('tool_id'),str) or not entry['tool_id'].startswith(pid+':') or not KEY.fullmatch(entry['tool_id'][len(pid)+1:]):raise ValueError('Invalid project browser tool entry')
     self._path(entry.get('source'),pid)
     rows.append({k:entry.get(k) for k in ('tool_id','name','description','project_id','source','revision','inputs')})
   except ValueError as error:errors.append({'project_id':pid,'error':str(error)[:500]})
  rows.sort(key=lambda e:e['tool_id']);page=[]
  for row in rows[offset:offset+limit]:
   if page and len(json.dumps(page+[row],ensure_ascii=False))>10000:break
   page.append(row)
  return {'tools':page,'next_offset':offset+len(page),'has_more':offset+len(page)<len(rows),'errors':errors[:10],'errors_truncated':len(errors)>10,'starts_models':False}
 def _entry(self,tool_id):
  if not isinstance(tool_id,str) or ':' not in tool_id:raise ValueError('Use the qualified project_id:tool_id from browser tool list')
  pid,local=tool_id.rsplit(':',1);valid_key(local,'Browser tool id');self._scope(pid);_,index,_=self._index(pid);entry=index['tools'].get(tool_id)
  if not isinstance(entry,dict) or entry.get('project_id')!=pid or entry.get('binding')!=self._scope(pid):raise ValueError('Unknown browser tool or changed authorized project binding')
  return pid,entry
 def run(self,tool_id,inputs,request_id):
  if not isinstance(request_id,str) or not REQUEST.fullmatch(request_id):raise ValueError('Browser tool request_id must be a bounded ASCII identifier')
  pid,entry=self._entry(tool_id);spec,qualified,version=self._spec(entry['source'],tool_id)
  if version!=entry['revision']:raise ValueError('stale_tool_requires_register: authoritative browser tool changed; register its current Loom version before calling')
  schema_check(inputs,spec['inputs']);key=digest([self.actor,request_id])[:32]
  run_source=self._scope(pid)['root']+'/research/browser-tool-runs/'+key+'.json.tex';immutable={'actor':self.actor,'tool_id':qualified,'source':entry['source'],'revision':version,'inputs':inputs,'request_id':request_id}
  record={'format':RUN_FORMAT,'input':immutable,'status':'processing','started_at':stamp(),'steps':[],'replay_allowed':False}
  with self._host_locked(key) as host_path:
   prior=self._host_read(host_path)
   if prior is not None:
    if prior.get('input')!=immutable:raise ValueError('Browser tool request_id has different immutable input; no replay')
    public_revision=prior.get('public_revision');result={'tool_id':qualified,'request_id':request_id,'status':prior.get('status') if prior.get('status') in ('done','failed') else 'unknown','duplicate':True,
      'output':prior.get('output'),'error':prior.get('error'),'replay_allowed':False,'run_source':run_source,'run_revision':public_revision,'citation':run_source+'@'+public_revision if public_revision else None,'receipt_source':'host private browser recipe receipt'}
    if len(json.dumps(result,ensure_ascii=False))>MAX_OUTPUT:raise ValueError('Stored browser recipe result exceeds response bound; no replay')
    return result
   if self._path(run_source,pid).exists():raise ValueError('Public browser run document has no trusted host receipt; preserved without replay')
   self._host_write(host_path,record)
  saved=self._write(run_source,record,pid);record['public_revision']=saved['revision'];self._host_write(host_path,record);context={'inputs':inputs,'steps':{}}
  try:
   for step in spec['steps']:
    self._scope(pid);args=expand(step['arguments'],context)
    if not isinstance(args,dict) or any(k in FORBIDDEN for k in args):raise ValueError('Browser recipe resolved unsupported host arguments')
    if 'project_id' in args and args['project_id']!=pid:raise ValueError('Browser recipe cannot save or inspect a different project')
    if step['tool'] in ('browser_save','browser_materials'):args.setdefault('project_id',pid)
    if step['tool'] in ('browser_open','browser_act','browser_fetch','browser_save'):
     if 'request_id' in args:raise ValueError('Recipe step request_id is host-derived; do not supply one')
     args['request_id']='recipe-'+digest([self.actor,request_id,qualified,step['id']])[:48]
    # Each facade call binds actor and authorizations again. Never call the broker directly.
    output=self.control.call(step['tool'],args)
    if isinstance(output,dict) and output.get('ok') is False:raise ValueError('Browser recipe step failed: '+str(output.get('error') or output.get('kind') or step['id']))
    context['steps'][step['id']]=output
    record['steps'].append({'id':step['id'],'tool':step['tool'],'status':'done','output_sha256':digest(output),'references':{k:output.get(k) for k in ('page_id','snapshot_id','node_id','source','revision','download_id') if isinstance(output,dict) and k in output}})
    saved=self._write(run_source,record,pid,saved['revision'])
    record['public_revision']=saved['revision'];self._host_write(host_path,record)
   output=expand(spec.get('output',{'$ref':'steps.'+spec['steps'][-1]['id']}),context)
   encoded=json.dumps(output,ensure_ascii=False)
   record.update(status='done',finished_at=stamp(),output=output if len(encoded)<=10000 else {'truncated':True,'preview':encoded[:8000],'notice':'Read the run source for references; complete materials are separately saved nodes.'})
  except Exception as error:
   unknown=getattr(error,'kind',None) in ('outcome_unknown','dispatch_unknown') or 'outcome unknown' in str(error).lower()
   record.update(status='unknown' if unknown else 'failed',finished_at=stamp(),error={'type':type(error).__name__,'message':str(error)[:1200],'step':spec['steps'][len(record['steps'])]['id'] if len(record['steps'])<len(spec['steps']) else None})
  saved=self._write(run_source,record,pid,saved['revision'])
  record['public_revision']=saved['revision'];self._host_write(host_path,record)
  result={'tool_id':qualified,'request_id':request_id,'status':record['status'],'duplicate':False,'output':record.get('output'),'error':record.get('error'),'replay_allowed':False,
          'tool_citation':entry['source']+'@'+version,'run_source':run_source,'run_revision':saved['revision'],'citation':run_source+'@'+saved['revision'],
          'continue':{'tool':'read_range','arguments':{'path':run_source,'view':'body'}}}
  if len(json.dumps(result,ensure_ascii=False))>MAX_OUTPUT:raise ValueError('Browser recipe result exceeded bound; read operation record '+run_source+'; do not replay')
  return result