"""Patch only the new copied candidate, with a bounded auditable diff."""
import hashlib,json,shutil
from pathlib import Path
BASE=Path(__file__).resolve().parent;C=BASE/'candidate'
def patch(path,old,new):
    s=path.read_text()
    if new in s:return
    if s.count(old)!=1:raise RuntimeError('Exact runtime patch context differs: '+str(path))
    path.write_text(s.replace(old,new))
def main():
    lock=json.loads((BASE/'external/workflow/OFFICIAL-SOURCE-LOCK.json').read_bytes())
    hashes=[r['sha256']for r in lock['files']if r['path'].endswith(('/verifier/core.py','/verifier/stable_core.py'))]
    assert len(hashes)==2
    (BASE/'guard/official-apply-hashes.json').write_text(json.dumps(hashes)+'\n')
    dest=C/'guard';dest.mkdir(exist_ok=True)
    for f in(BASE/'guard').glob('*'):
        if f.is_file():shutil.copy2(f,dest/f.name)
    shutil.copy2(BASE/'mechanisms_host.py',C/'agent/mechanisms_host.py')
    p=C/'agent/yohaku_native_research_runtime.py'
    s=p.read_text();p.write_text(s.rstrip()+'\n');needle='    return tools\n'
    patch(p,needle,"    if g.policy.get('program_budget'):\n        from mechanisms_host import wrap\n        return wrap(tools,workspace,node,task_id)\n    return tools\n")
    p=C/'agent/yohaku_native_research_gate.py'
    patch(p,"            if len(v['turns'])>=self.policy['limits']['turns']:raise GateStopped('Native turn envelope reached')\n            active=", "            if len(v['starts'])>=self.policy['limits']['turns']:raise GateStopped('Native admitted-attempt envelope reached')\n            active=")
    p=C/'agent/yohaku_project_tasks.py'
    patch(p,"        task_id = self.task_id(request_id)\n        if action not", "        from mechanisms_host import budget_binding\n        program_budget = budget_binding(self.world,project,action,request_id,snapshot,plan)\n        task_id = self.task_id(request_id)\n        if action not")
    patch(p,"                   'source_set': snapshot.get('source_set'), 'runtime': plan.get('runtime')}","                   'source_set': snapshot.get('source_set'), 'runtime': plan.get('runtime'), 'program_budget':program_budget}")
    patch(p,"'project_id': project['id'], 'action': action, 'project': project,", "'project_id': project['id'], 'action': action, 'project': project, 'program_budget':program_budget,")
    patch(p,"        sandbox_world = self.work / record['task_id'] / 'sandbox-world'", "        from mechanisms_host import guard_mounts\n        binding=record['program_budget'];mounts += guard_mounts(binding)\n        argv=['/usr/bin/python3','-B','/budget-runtime/runner.py','--allocation',binding['allocation'],'--',*argv]\n        sandbox_world = self.work / record['task_id'] / 'sandbox-world'")
    patch(p,"            timeout = record['project']['tasks'][record['action']].get('timeout_seconds', 900)","            timeout = min(record['project']['tasks'][record['action']].get('timeout_seconds', 900), max(1,record['program_budget']['deadline']-time.time()))")
    patch(p,"        receipt['finished'] = time.time()", "        from mechanisms_host import receipt as program_receipt\n        try:receipt['program_budget']=program_receipt(record['program_budget'])\n        except Exception as exc:receipt['program_budget_error']=str(exc)\n        receipt['finished'] = time.time()")
    seal={str(f.relative_to(C)):hashlib.sha256(f.read_bytes()).hexdigest()for part in('agent','bin','config','runtime','guard','macros')for f in(C/part).rglob('*')if f.is_file()and '__pycache__'not in f.parts}
    (BASE/'RUNTIME-SEAL.json').write_text(json.dumps(dict(files=seal,old_runtime_modified=False),indent=2)+'\n')
    print(json.dumps(dict(isolated_runtime_ready=True,files=len(seal),official_apply_hashes=hashes,old_runtime_modified=False)))
if __name__=='__main__':main()
