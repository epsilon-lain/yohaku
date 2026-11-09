"""Project-scoped reuse of existing Yohaku documents, Loom and public tasks."""
import hashlib,re
from pathlib import Path,PurePosixPath
from yohaku_project_schema import relative,identifier,ProjectError,TOOL_NAMES

DOCUMENT_TOOLS={'context','list_directory','read_document','read_text','read_range',
 'search_text','search_notes','create_document','adopt_file','write_document',
 'patch_document','sync_document','write_text','patch_text','edit_range'}
READ_DOCUMENT_TOOLS={'read_document','read_text','read_range'}

def project_scopes(world,project_ids,parent=None):
 """Resolve registered IDs once; descendants can inherit/subset, never expand."""
 from yohaku_project_sources import Projects
 if project_ids is None:return [dict(s) for s in (parent or [])]
 if not isinstance(project_ids,list) or len(project_ids)>100 or any(not isinstance(p,str) for p in project_ids):raise ValueError('project_ids must be existing registered IDs')
 ids=sorted(set(project_ids));grants={s['project_id']:s for s in parent or []}
 if parent is not None and not set(ids)<=set(grants):raise ValueError('Child project authorization cannot exceed its parent')
 projects=Projects(world);result=[]
 for pid in ids:
  identifier(pid,'project_id');info=projects._description(pid)
  scope={'project_id':pid,'root':info['manifest']['root'],'manifest_source':info['manifest_source']}
  relative(scope['root']);relative(scope['manifest_source'])
  if not scope['manifest_source'].startswith(scope['root']+'/'):raise ValueError('Authorized manifest must stay in its project root')
  if parent is not None and scope!=grants[pid]:raise ValueError('Inherited project binding changed; no privilege expansion')
  result.append(scope)
 return result

class ProjectControl:
 def __init__(self,world,scopes,persist=lambda **fields:None):
  from yohaku_projects import Control
  self.control=Control(world);self.scopes={s['project_id']:dict(s) for s in scopes};self.persist=persist;self.operations=[]
 def check(self,pid):
  scope=self.scopes.get(pid)
  if scope is None:raise ValueError('Project is outside this node authorization')
  info=self.control.projects._description(pid)
  if info['manifest']['root']!=scope['root'] or info['manifest_source']!=scope['manifest_source']:raise ValueError('Authorized project root/manifest changed; no operation performed')
  return scope
 def call(self,name,args):
  if name not in TOOL_NAMES:raise ValueError('Unknown public project tool')
  if name in ('project_schema','ui_sdk_info'):return self.control.call(name,args)
  if name=='project_list':
   rows=[]
   for pid in self.scopes:
    self.check(pid);info=self.control.projects._description(pid)
    rows.append({'project_id':pid,'root':info['manifest']['root'],'manifest_source':info['manifest_source'],'tasks':info['tasks']})
   return {'format':'yohaku-projects/1','projects':rows,'authorization':'inherited project scopes'}
  if name=='task_list':
   ids=[args['project_id']] if args.get('project_id') else list(self.scopes);rows=[]
   for pid in ids:self.check(pid);rows.extend(self.control.call(name,{'project_id':pid})['tasks'])
   return {'format':'yohaku-task/1','tasks':rows}
  if name=='project_register':
   scope=next((s for s in self.scopes.values() if s['manifest_source']==args['manifest_source']),None)
   if scope is None:raise ValueError('Cannot register an ungranted project or manifest')
   self.check(scope['project_id'])
  elif name=='ui_sdk_prepare':
   scope=next((s for s in self.scopes.values() if s['root']==args['project_root']),None)
   if scope is None:raise ValueError('SDK import must target an authorized project')
   self.check(scope['project_id'])
  elif 'project_id' in args:self.check(args['project_id'])
  elif args.get('task_id') or args.get('request_id'):
   status=self.control.tasks.status(task_id=args.get('task_id'),request_id=args.get('request_id'))
   self.check(status['project_id'])
  else:raise ValueError('An authorized project or task identity is required')
  result=self.control.call(name,args)
  self.operations.append({'tool':name,'arguments':dict(args),'task_id':result.get('task_id') if isinstance(result,dict) else None})
  self.persist(project_operations=list(self.operations))
  return result

def envelope(text):
 m=re.search(r'(?m)^## 正文\s*\n(`{3,})[^\n]*\n',text)
 if m is None:raise ValueError('Use body_only=true for this document format')
 end=text.find('\n'+m[1],m.end())
 if end<0:raise ValueError('Malformed authoritative tex body')
 return text[:m.end()],text[end:]

class Workspace:
 """File operations stay in pinned projects; execution stays in Project/Task."""
 def __init__(self,workspace,node_context,persist=lambda **fields:None):
  self.workspace=workspace;self.root=Path(workspace.root);self.scopes=node_context.get('project_scopes',[])
  self.projects=ProjectControl(self.root,self.scopes,persist);self.persist=persist;self.operations=[]
  self.memory=node_context.get('memory_source');continuation=node_context.get('continuation') or {}
  self.archive=(continuation.get('archive') or {}).get('source')
 def path(self,value,write=False):
  relative(value)
  path=self.root
  for part in PurePosixPath(value).parts:
   path=path/part
   if path.is_symlink():raise ValueError('Node project paths must not use symlinks')
  if value==self.memory or (not write and value==self.archive):return value
  scope=next((s for s in self.scopes if value==s['root'] or value.startswith(s['root']+'/')),None)
  if scope is None:raise ValueError('Document is outside this node authorized projects/memory/archive')
  self.projects.check(scope['project_id']);return value
 def document(self,source,write=False):
  self.path(source,write);doc=self.workspace.execute({'command':'read','source':source})
  projects=self.projects.control.projects
  captured=projects._document(source,projects._entries())
  if hashlib.sha256(doc['text'].encode()).hexdigest()!=captured['source_hash']:raise ValueError('Document changed during scoped routing validation')
  output=captured['output']
  if source==self.memory:
   if output!=source[:-4]:raise ValueError('Memory output binding changed')
  elif source==self.archive:
   if write or output!=source[:-4]:raise ValueError('Archive is read-only reference material')
  else:self.path(output,write)
  return doc
 def execute(self,request):
  command=request.get('command');write=command in ('create','adopt','save','sync','write_text')
  if command=='create':
   directory=request.get('directory')
   if not isinstance(directory,str):raise ValueError('Node create_document requires an explicit authorized project directory')
   self.path(directory+'/'+request['name'],True)
  elif command in ('read','save','sync'):
   source=request['source'];doc=self.document(source,write)
   if command=='save' and request.get('body_only') is not True and envelope(request['text'])!=envelope(doc['text']):raise ValueError('Scoped full-tex edits must preserve routing/notes; use body_only=true')
  elif command in ('read_text','write_text','directory','adopt'):
   path=request['path'];self.path(path,write)
   if command=='write_text' and path.endswith('.tex'):
    doc=self.document(path,True)
    if envelope(request['text'])!=envelope(doc['text']):raise ValueError('Scoped tex writes must preserve routing/notes; use document body tools')
  else:raise ValueError('Node world command is not part of authorized document/Loom operations')
  result=self.workspace.execute(request)
  if write:
   self.operations.append({'command':command,'source':request.get('source') or request.get('path'),'directory':request.get('directory'),'name':request.get('name')})
   self.persist(world_operations=list(self.operations))
  return result