"""Fixed external input acquisition, no models or research execution."""
import concurrent.futures,hashlib,json,shutil,time,urllib.request
from pathlib import Path
BASE=Path(__file__).resolve().parent
OLD=BASE.parent/'native-two-team-sol-20261116/candidate'
WORK='c51ccae2ea38ab14aa376fecdfed774403ce776b'
MATH='d2afe810877587f0dd621fce8a49bc9b25d41df0'
TASK='3b729871d1ee83e4f3ab5ea048bfaa0fe67209ce'
PREFIX='research/proof-mechanisms-portfolio-2026-11-17/'
def get(repo,ref,path,dest,expected=None,blob=None,size=None):
    url='https://raw.githubusercontent.com/'+repo+'/'+ref+'/'+path
    if not dest.exists():
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Yohaku-fixed-input'}),timeout=45)as r:raw=r.read(5000000)
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    raw=dest.read_bytes();digest=hashlib.sha256(raw).hexdigest();git=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    assert expected is None or digest==expected,(path,digest)
    assert blob is None or git==blob,(path,git)
    assert size is None or len(raw)==size,(path,len(raw))
    return dict(repo=repo,ref=ref,path=path,url=url,local=str(dest.relative_to(BASE)),bytes=len(raw),sha256=digest,git_blob=git)
def main():
    rows=[]
    rows.append(get('epsilon-lain/yohaku',TASK,'research/native-mechanisms-next-2026-11-17/CODEX_TASK.md',BASE/'task/CODEX_TASK.md',blob='9c79b7ef39273657e386e0fa0a79a02103fdb32f'))
    rows.append(get('epsilon-lain/yohaku',TASK,'research/native-mechanisms-next-2026-11-17/TASK.json',BASE/'task/TASK.json',blob='918c7ed29c1092c5ccc7838eff86007e06e03968'))
    rows.append(get('epsilon-lain/yohaku',WORK,PREFIX+'MANIFEST.json',BASE/'external/workflow/MANIFEST.json'))
    manifest=json.loads((BASE/'external/workflow/MANIFEST.json').read_bytes())
    with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:
        jobs=[pool.submit(get,'epsilon-lain/yohaku',WORK,PREFIX+r['path'],BASE/'external/workflow'/r['path'],r['sha256'],r.get('git_blob'),r['bytes'])for r in manifest['files']]
        rows.extend(f.result()for f in jobs)
    math=json.loads((BASE/'MATH-FILES.json').read_bytes())
    for r in math:rows.append(get(r['repo'],r['ref'],r['path'],BASE/'external/math'/Path(r['path']).name,blob=r['sha'],size=r['bytes']))
    assert hashlib.sha256((BASE/'external/workflow/symbolic_rules/RULES.json').read_bytes()).hexdigest()=='701b9b233a7ba0a1e926d0333ae8fef652e6c9bd83ab4a6ef12070bbd617e2bc'
    receipt=dict(at=time.time(),files=rows,root_manifest_verified=True,all_workflow_files_sha256_verified=True,
        math_manifest_404_retained=True,math_integrity_basis='Fixed-commit directory listing Git blob SHA and byte size; no root MANIFEST exists in math mirror.',
        models_started=0,external_code_executed=False)
    (BASE/'ACQUISITION.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    new=BASE/'candidate'
    if not new.exists():shutil.copytree(OLD,new,ignore=shutil.ignore_patterns('__pycache__'))
    print(json.dumps(dict(verified_files=len(rows),workflow_files=len(manifest['files']),math_files=len(math),isolated_candidate_created=True,models_started=0)))
if __name__=='__main__':main()
