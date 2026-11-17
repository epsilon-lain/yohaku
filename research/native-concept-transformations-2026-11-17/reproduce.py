"""Reproduce a captured Python computation from hash-pinned public inputs.

Requires Linux bubblewrap and Python3. No model/API/contest upload is invoked.
This replays the captured implementation; it is not an independent algorithm.
"""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def reproduce(task_id,output_root):
    manifest=json.loads((HERE/'snapshots'/(task_id+'.json')).read_bytes())
    if manifest['task_id']!=task_id or manifest['task']['kind']!='python':raise ValueError('Only the named captured Python task can be replayed')
    bwrap=shutil.which('bwrap')
    if not bwrap:raise RuntimeError('Linux bubblewrap is required; no unisolated fallback')
    root=Path(output_root).resolve();root.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix=task_id+'-',dir=root));source=work/'source';out=work/'output';source.mkdir();out.mkdir()
    for f in manifest['files']:
        target=source/f['path']
        if not target.resolve().is_relative_to(source):raise ValueError('Invalid captured path')
        blob=HERE/'blobs'/f['sha256']
        if not blob.is_file()or digest(blob)!=f['sha256']:raise ValueError('Captured input blob mismatch: '+f['path'])
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(blob,target)
    argv=[bwrap,'--die-with-parent','--new-session','--unshare-all','--clearenv','--ro-bind','/usr','/usr']
    for path in('/lib','/lib64','/bin'):
        if Path(path).exists():argv+=['--ro-bind',str(Path(path).resolve()),path]
    argv+=['--proc','/proc','--dev','/dev','--tmpfs','/tmp','--ro-bind',str(source),'/project','--bind',str(out),'/output','--chdir','/project','--setenv','HOME','/tmp','--setenv','PATH','/usr/bin:/bin','--setenv','LANG','C.UTF-8','/usr/bin/python3','-B','/project/'+manifest['task']['entry'],*manifest['task'].get('args',[])]
    started=time.time();run=subprocess.run(argv,capture_output=True,text=True,timeout=manifest['task'].get('timeout_seconds',900)+30)
    (work/'stdout.txt').write_text(run.stdout);(work/'stderr.txt').write_text(run.stderr)
    artifacts=[]
    for name in manifest['task'].get('artifacts',[]):
        path=out/name
        artifacts.append({'path':name,'exists':path.is_file(),'sha256':digest(path)if path.is_file()else None,'bytes':path.stat().st_size if path.is_file()else None})
    result={'task_id':task_id,'source_set':manifest['source_set'],'exit_code':run.returncode,'started_at':started,'finished_at':time.time(),'artifacts':artifacts,'work_directory':str(work),'label':'external_same-code_reproduction; not a native model task or independent algorithm','network_disabled':True,'model_requests':0,'platform_upload':False}
    (work/'reproduction-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('task_id');parser.add_argument('--output',default='reproduction-runs');args=parser.parse_args();result=reproduce(args.task_id,args.output);print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['exit_code']==0 else 1)
