"""Local private receipts; no account credentials or remote publication."""
import hashlib,json,sqlite3,time,zipfile
from pathlib import Path
from continuation import BASE,activate,verify_parent,save,sha
def main():
    p=activate();b=verify_parent();q=json.loads((BASE/'ROUND-PRIVATE.json').read_bytes());ids={t['task_id']for t in q['tasks']}
    dest=BASE/('private-final-'+str(time.time_ns()));dest.mkdir(mode=0o700);files=[]
    def copy(file,relative):
        file=Path(file);target=dest/relative;target.parent.mkdir(parents=True,exist_ok=True);raw=file.read_bytes();target.write_bytes(raw);files.append(dict(source=str(file),archive=relative,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    for f in BASE.iterdir():
        if f.is_file()and f.suffix in('.json','.txt','.py')and not f.name.startswith('LATEST-PRIVATE'):copy(f,'stage/'+f.name)
    for pin in b['parent_pins']:
        f=Path(pin['path']);assert sha(f)==pin['sha256'];copy(f,'old-authorities/'+f.parent.name+'/'+f.name)
    for name,source in(('knowledge.sqlite3',p['knowledge_db']),('program-budget.sqlite3',p['program_budget']['database'])):
        db=sqlite3.connect(source);out=sqlite3.connect(dest/name);db.backup(out);out.close();db.close();files.append(dict(source=source,archive=name,bytes=(dest/name).stat().st_size,sha256=sha(dest/name)))
    model=Path(p['home'])/'.local/state/yohaku/model-tasks'
    for tid in ids:
        for f in model.glob(tid+'*'):
            if f.is_file()and f.suffix!='.lock':copy(f,'model-receipts/'+f.name)
    from yohaku_project_tasks import Tasks
    tasks=Tasks(p['world'])
    for c in q['computations']:
        tid=(c.get('status')or{}).get('task_id')
        if not tid:continue
        r=tasks._owned(tid);copy(Path(p['home'])/'.local/state/yohaku/project-tasks/records'/(tid+'.json'),'project-receipts/'+tid+'.json')
        for f in tasks.logs.glob(tid+'*'):
            if f.is_file():copy(f,'project-logs/'+f.name)
        for a in(r.get('receipt')or{}).get('artifacts',[]):copy(a['host_path'],'project-artifacts/'+tid+'/'+a['path'])
    seen=set()
    for e in q['new_events']:
        if e['kind']!='file_version_observed':continue
        d=e['data'];version=d['revision']
        if version in seen:continue
        seen.add(version);f=Path(d['archive'])
        if f.is_file():assert sha(f)==version;copy(f,'file-versions/'+version)
    save(dest/'PRIVATE-MANIFEST.json',dict(at=time.time(),classification='LOCAL PRIVATE ONLY; no credentials',files=files,old_full_papers_remain_at_original_retained_paths=True,original_old_archive='diagnostics/operation-universes-continuation-20261117-01/operation-universes-six-turns-private-1794912372.zip',old_stops_and_memory_versions_retained=True))
    path=dest.with_suffix('.zip')
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED)as z:
        for f in sorted(dest.rglob('*')):
            if f.is_file():z.write(f,str(f.relative_to(dest)))
    with zipfile.ZipFile(path)as z:assert z.testzip()is None
    receipt=dict(at=time.time(),path=str(path),sha256=sha(path),bytes=path.stat().st_size,files=len(files),local_private_only=True)
    save(BASE/'LATEST-PRIVATE-ARCHIVE.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
