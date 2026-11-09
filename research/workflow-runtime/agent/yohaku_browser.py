"""Native public browser facade: host identity, bounded results, project sources."""
import datetime,fcntl,hashlib,json,os,re,uuid
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
from yohaku_browser_runtime import BrowserError
from yohaku_wired_runtime import Runtime

S={'type':'string'};I={'type':'integer'};B={'type':'boolean'}
def definition(name,description,props=None,required=()):
 return {'name':name,'description':description,'parameters':{'type':'object','properties':props or {},'required':list(required),'additionalProperties':False}}
R={'request_id':S};P={'page_id':S};Q={**P,'snapshot_id':S};N={**Q,'node_ref':S};BOUNDS={'offset':I,'max_chars':I}
TOOLS=[
 definition('browser_status','Query Wired, displayed_page_id and the selected real Chrome view. When a view is selected, read, act and save that page. Public reading is not proof of authentication.'),
 definition('browser_start','Start/restore Wired. The normal-browser extension keeps login under user control in the normal browser; no cookie or credential transfer.'),
 definition('browser_tabs','List accessible tabs; main sees all, descendants see their own.'),
 definition('browser_open','Open a public HTTP(S) URL. With a selected Wired view, pass displayed_page_id as page_id to navigate that same real tab. Otherwise opens a new actor-owned tab. No simulated access.',{'url':S,**P,**R},['url']),
 definition('browser_switch','Show an accessible tab in the browser window.',{**P,**R},['page_id']),
 definition('browser_snapshot','Read current structured page, links and bounded text. Retain page_id/snapshot_id/node_ref; stale references fail.',{**P,'max_chars':I,'limit':I},['page_id']),
 definition('browser_find','Find snapshot nodes by text, role, tag, href or disabled state.',{**Q,'text':S,'role':S,'tag':S,'href':S,'disabled':B,'limit':I},['page_id','snapshot_id']),
 definition('browser_read','Read a snapshot/node text fragment; use next_offset to continue.',{**N,**BOUNDS},['page_id','snapshot_id']),
 definition('browser_act','Click, follow or fill a current node reference. Never enter credentials; user logs in manually. Re-snapshot after action.',{**N,'action':{'type':'string','enum':['click','follow','fill']},'value':S,**R},['page_id','snapshot_id','node_ref','action']),
 definition('browser_close','Close your page; main can close the complete service. Persistent profile is retained.',{**P,**R}),
 definition('browser_fetch','Actually fetch a public URL into private download storage. Return bounded preview and a ticket; save separately to an authorized project.',{'url':S,'max_bytes':I,**R},['url']),
 definition('browser_download_read','Read a bounded UTF-8 download fragment. Binary originals require browser_save; no invented PDF extraction.',{'download_id':S,**BOUNDS},['download_id']),
 definition('browser_save','Save a trusted download OR current page snapshot through public project/Loom sources, with full provenance and citation.',{'project_id':S,'download_id':S,**Q,'kind':{'type':'string','enum':['text','html']},'name':S,'node_id':S,**R},['project_id']),
 definition('browser_materials','Find saved material/source nodes inside an authorized project.',{'project_id':S,'offset':I,'limit':I},['project_id']),
 definition('browser_history','Read bounded durable access receipts for this actor, including source/save locations.',{'offset':I,'limit':I}),
 definition('browser_operation','Query original mutation receipt without replay; use the returned request_id.',{'request_id':S},['request_id']),
 definition('browser_search_status','Discover actual general search backend status; site search remains available through browser/recipes.'),
 definition('browser_search','General search: returns a truthful unavailable error until an authorized backend is configured.',{'query':S},['query']),
 definition('browser_tool_register','Register an authorized .tex → Loom JSON browser recipe (yohaku-browser-tool/1). No arbitrary host code.',{'source':S,'tool_id':S},['source']),
 definition('browser_tool_list','List reusable browser recipes and their authoring contract in authorized projects.',{'project_id':S,'offset':I,'limit':I}),
 definition('browser_tool_run','Run a registered recipe through the same public browser tools; requires read,write,run permissions.',{'tool_id':S,'inputs':{'type':'object'},**R},['tool_id','inputs','request_id'])]
NAMES={d['name'] for d in TOOLS}
READ={'browser_status','browser_tabs','browser_snapshot','browser_find','browser_read','browser_download_read','browser_materials','browser_history','browser_operation','browser_search_status','browser_tool_list'}
WRITE={'browser_save','browser_tool_register'}
RUN=NAMES-READ-WRITE
PRIVATE_KEYS={'snapshot_storage','secret','profile','spool','socket','cookies','storage_state','authorization'}
SENSITIVE=re.compile(r'(^|[_-])(token|password|passwd|secret|key|code|state|auth|session)($|[_-])',re.I)
def url_public(value):
 try:
  u=urlsplit(value)
  if value=='about:blank':return value
  return urlunsplit((u.scheme,u.hostname+((':'+str(u.port)) if u.port else ''),u.path,urlencode([(k,'[redacted]' if SENSITIVE.search(k) else v) for k,v in parse_qsl(u.query,keep_blank_values=True)]),''))
 except (ValueError,TypeError,AttributeError):return '[invalid URL]'
def public(value):
 if isinstance(value,dict):return {k:(url_public(v) if k in ('url','final_url') and isinstance(v,str) else public(v)) for k,v in value.items() if k not in PRIVATE_KEYS and not(k=='path' and isinstance(v,str) and Path(v).is_absolute())}
 if isinstance(value,list):return [public(v) for v in value]
 return value
def integer(value,default,low,high):
 if value is None:return default
 if type(value)is not int or not low<=value<=high:raise BrowserError('Integer argument outside supported bounds','invalid_arguments',minimum=low,maximum=high)
 return value
def request(value=None):
 value=value or 'browser-'+uuid.uuid4().hex
 if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',value):raise BrowserError('request_id must be a bounded ASCII identifier','invalid_arguments')
 return value

class Control:
 def __init__(self,world,actor='main',project_scopes=None,workspace=None):
  from yohaku_agent import Workspace
  if not isinstance(actor,str) or not re.fullmatch(r'main|ai-node-[A-Za-z0-9-]+',actor):raise BrowserError('Host-bound node identity required','invalid_actor')
  if actor!='main' and not isinstance(project_scopes,list):raise BrowserError('Child project scope must be inherited from the host','project_authorization')
  self.world=Path(world).resolve(strict=True);self.actor=actor;self.project_scopes=project_scopes
  package=Path(__file__).resolve().parents[1];self.workspace=workspace or Workspace(self.world,package/'bin/loom-linux-x86_64',package/'bin/yohaku_chat_workspace')
  self.runtime=Runtime(self.world);self.recipe_state_dir=self.runtime.recipe_state_dir
 def _materials(self):
  from yohaku_browser_materials import Materials
  return Materials(self.world,self.actor,self.project_scopes,self.workspace,self.runtime.spool)
 def check_project(self,project_id):return self._materials()._project(project_id)[0]
 def read_project_source(self,source):
  from yohaku_project_sources import Projects,relative,contained
  relative(source);projects=Projects(self.world,workspace=self.workspace)
  scopes=self.project_scopes
  if scopes is None:
   scopes=[]
   registry,_=projects._registry()
   for p in registry['projects']:
    info=projects._description(p['id']);scopes.append({'project_id':p['id'],'root':info['manifest']['root'],'manifest_source':info['manifest_source']})
  scope=next((s for s in scopes if source.startswith(s['root']+'/')),None)
  if scope is None:raise BrowserError('Recipe source is outside authorized registered projects','project_authorization')
  self.check_project(scope['project_id']);contained(self.world,source)
  captured=projects._document(source,projects._entries());doc=self.workspace.execute({'command':'read','source':source})
  if hashlib.sha256(doc['text'].encode()).hexdigest()!=captured['source_hash']:raise BrowserError('Recipe source changed during route validation','source_conflict')
  if not captured['output'].startswith(scope['root']+'/'):raise BrowserError('Recipe output escapes its authorized project','project_authorization')
  return doc
 def _ticket(self,download_id):return self.runtime.call('get_ticket',{'download_id':download_id},self.actor)
 def _download_read(self,args):
  from yohaku_browser_materials import text_mime
  ticket=self._ticket(args['download_id'])
  if not text_mime(ticket['mime'].split(';')[0]) or ticket['bytes']>2*1024*1024:raise BrowserError('Binary or oversized text material: save the original; PDF text extraction is not configured','binary_content',material=public(ticket))
  try:text=Path(ticket['path']).read_bytes().decode('utf-8')
  except UnicodeDecodeError:raise BrowserError('Download is not UTF-8; preserve its original bytes','binary_content') from None
  offset=integer(args.get('offset'),0,0,len(text));size=integer(args.get('max_chars'),3000,1,8000);end=min(len(text),offset+size)
  return {**public(ticket),'text':text[offset:end],'offset':offset,'next_offset':end,'total_chars':len(text),'has_more':end<len(text),'complete_content':'browser_save then read_range by source/revision'}
 def _record(self,record):
  path=self.runtime.base/'access.jsonl';fd=os.open(path,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'a') as f:
   fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps(public(record),ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
 def _history(self,args):
  offset=integer(args.get('offset'),0,0,1000000);limit=integer(args.get('limit'),20,1,100);rows=[];total=0;p=self.runtime.base/'access.jsonl'
  if p.exists():
   with p.open() as f:
    for line in f:
     row=json.loads(line)
     if self.actor!='main' and row['actor_node_id']!=self.actor:continue
     if offset<=total<offset+limit:rows.append(row)
     total+=1
  return {'visits':rows,'offset':offset,'next_offset':min(total,offset+limit),'total':total,'has_more':offset+limit<total,'archive':'host-bound browser access receipts; browser_history is the public reader'}
 def _operation(self,args):
  rid=request(args['request_id']);key=hashlib.sha256((self.actor+'\0'+rid).encode()).hexdigest();p=self.runtime.spool/'requests'/(key+'.json')
  if not p.exists():return {'request_id':rid,'state':'not_found','replay_allowed':False}
  value=json.loads(p.read_text());return {'request_id':rid,'record':public(value),'replay_allowed':False}
 def call(self,name,args):
  if name not in NAMES:raise BrowserError('Unknown public browser tool','unknown_tool')
  args=dict(args);rid=request(args.get('request_id'));visit='browser-visit-'+uuid.uuid4().hex
  record={'visit_ref':visit,'actor_node_id':self.actor,'tool':name,'request_id':rid,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'url':args.get('url'),'page_id':args.get('page_id')}
  try:
   result=self._call(name,args,rid)
   result=public(result)
   if not isinstance(result,dict):result={'value':result}
   result.update(visit_ref=visit)
   record.update(ok=True,final_url=result.get('final_url') or result.get('url'),status=result.get('status'),source=result.get('source'),asset_path=result.get('asset_path'),node_id=result.get('node_id'),download_id=result.get('download_id'),duplicate=result.get('duplicate',False))
   return result
  except Exception as error:
   if isinstance(error,BrowserError):failure=error
   elif hasattr(error,'to_dict'):
    raw=error.to_dict();failure=BrowserError(raw.pop('error',str(error)),raw.pop('kind','browser_error'),**{k:v for k,v in raw.items() if k not in ('ok','replay_allowed')})
   elif isinstance(error,(ValueError,OSError,KeyError,TypeError)):failure=BrowserError(str(error),'invalid_arguments' if not isinstance(error,OSError) else 'browser_storage_error')
   else:raise
   record.update(ok=False,error=str(failure),kind=failure.kind);failure.details=public(dict(failure.details,visit_ref=visit));raise failure from None
  finally:
   record['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();self._record(record)
 def _call(self,name,args,rid):
  op=name.removeprefix('browser_')
  if op=='status':return self.runtime.status(self.actor)
  if op=='start':return self.runtime.start(self.actor)
  if op in ('open','fetch'):self.runtime.start(self.actor)
  if op=='close' and not args.get('page_id'):return self.runtime.close(self.actor)
  if op in ('tabs','open','switch','snapshot','find','read','act','close','fetch'):
   forwarded={k:v for k,v in args.items() if k!='request_id'}
   if op=='snapshot' and 'max_nodes' in forwarded:forwarded['limit']=forwarded.pop('max_nodes')
   target_op='navigate' if op=='open' and forwarded.get('page_id') else op
   result=self.runtime.call(target_op,forwarded,self.actor,rid)
   if op=='fetch':
    try:result.update(preview=self._download_read({'download_id':result['download_id'],'max_chars':3000}).get('text'))
    except BrowserError as error:result.update(preview=None,content_note=str(error))
   return result
  if op=='download_read':return self._download_read(args)
  if op=='save':
   self.check_project(args['project_id'])
   if bool(args.get('download_id'))==bool(args.get('page_id')):raise BrowserError('Provide a download_id OR page_id plus snapshot_id','invalid_arguments')
   if args.get('download_id'):ticket=self._ticket(args['download_id'])
   else:
    if not args.get('snapshot_id'):raise BrowserError('Saving a page requires its current snapshot_id','invalid_arguments')
    ticket=self.runtime.call('export',{'page_id':args['page_id'],'snapshot_id':args['snapshot_id'],'kind':args.get('kind','text')},self.actor,rid)
   return self._materials().save(ticket,args['project_id'],args.get('name'),args.get('node_id'))
  if op=='materials':return self._materials().list(args['project_id'],integer(args.get('limit'),20,1,100),integer(args.get('offset'),0,0,1000000))
  if op=='history':return self._history(args)
  if op=='operation':return self._operation(args)
  if op=='search_status':return {'available':False,'backend':None,'state':'not_configured','site_search':'Use generic browser_open/find/act, or register the arXiv example recipe. No general search backend was found in this candidate.'}
  if op=='search':raise BrowserError('No authorized general search backend is configured; URL reading/download and browser site search remain available','search_backend_unavailable',available=False)
  from yohaku_browser_recipes import Recipes
  recipes=Recipes(self)
  if op=='tool_register':return recipes.register(args['source'],args.get('tool_id'))
  if op=='tool_list':
   result=recipes.list(args.get('project_id'),integer(args.get('offset'),0,0,1000000),integer(args.get('limit'),20,1,100))
   result['authoring']={'format':'yohaku-browser-tool/1','source':'Use create_document/write_document/sync_document in an inherited project, then browser_tool_register(source). Revision changes require registration again.','fields':['id','name','description','project_id','inputs','steps','output'],'step':{'id':'open','tool':'browser_open','arguments':{'url':{'$ref':'inputs.url'}}},'expressions':['$ref: inputs.field or steps.step.field','$url: {base: literal public URL, query: {key: expression}}'],'allowed_tools':sorted(__import__('yohaku_browser_recipes').ALLOWED),'output_example':{'page_id':{'$ref':'steps.open.page_id'}},'execution':'Bounded declarative composition; calls the same host-authorized public tools; no host code evaluation.'}
   return result
  if op=='tool_run':return recipes.run(args['tool_id'],args['inputs'],rid)
  raise BrowserError('Unsupported operation','unknown_tool')
