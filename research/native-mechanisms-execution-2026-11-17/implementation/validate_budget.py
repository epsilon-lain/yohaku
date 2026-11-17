"""Zero-model isolated hard-cap fixture; never charged as real research."""
import hashlib,importlib.util,json,os,shutil,socketserver,subprocess,sys,threading,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
def main():
    root=BASE/('fixture-'+str(time.time_ns()));root.mkdir();guard=root/'guard';shutil.copytree(BASE/'guard',guard)
    core=root/'core.py';core.write_text('def apply_move(x):\n    return x+1\n')
    (root/'verifier').mkdir();(root/'verifier/__init__.py').write_text('');(root/'verifier/__main__.py').write_text('from core import apply_move\napply_move(0)\n')
    (guard/'official-apply-hashes.json').write_text(json.dumps([hashlib.sha256(core.read_bytes()).hexdigest()]))
    spec=importlib.util.spec_from_file_location('fixture_budget',BASE/'guard/budget_server.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    config=root/'config.json';config.write_text(json.dumps(dict(goal_id='FIXTURE_ONLY',database=str(root/'budget.sqlite3'),socket=str(root/'budget.sock'),search_cap=6,verification_cap=16,fixture=True,fixture_parent_pid=os.getpid())))
    budget=m.Budget(config);server=m.Server(str(root/'budget.sock'),m.Handler);server.budget=budget;threading.Thread(target=server.serve_forever,daemon=True).start()
    def call(**kw):return budget.call(kw,os.getpid())
    a=call(op='allocate',actor='fixture',model_task='none',request_id='a',node='fixture',project='p',search=3,verification=0,purpose='cap before fourth apply')
    b=call(op='allocate',actor='fixture',model_task='none',request_id='b',node='fixture',project='p',search=3,verification=16,purpose='child and verification')
    assert a==call(op='allocate',actor='fixture',model_task='none',request_id='a',node='fixture',project='p',search=3,verification=0,purpose='cap before fourth apply')
    for alloc in(a,b):call(op='bind',allocation=alloc['id'],actor='fixture',model_task='none',project='p',task=alloc['id'],source_set='frozen-fixture')
    rejected=False
    try:call(op='allocate',actor='fixture',model_task='none',request_id='overflow',node='fixture',project='p',search=1,verification=0,purpose='should reject')
    except AssertionError:rejected=True
    assert rejected
    def run(alloc,code):
        path=root/(alloc['id']+'.py');path.write_text(code)
        command=['bwrap','--tmpfs','/','--ro-bind','/usr','/usr','--ro-bind','/etc','/etc','--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64','--ro-bind',str(root),str(root),'--bind',str(root),'/output','--ro-bind',str(root/'budget.sock'),'/budget.sock','--ro-bind',str(guard),'/budget-runtime','--unshare-net','--unshare-pid','--proc','/proc','--dev','/dev','--die-with-parent','--chdir',str(root),'/usr/bin/python3','-B','/budget-runtime/runner.py','--allocation',alloc['id'],'--','/usr/bin/python3','-B',str(path)]
        return subprocess.run(command,capture_output=True,text=True,timeout=30)
    r=run(a,"from core import apply_move\nfrom pathlib import Path\nfor i in range(4):\n    apply_move(i)\n    Path('/output/body-count.txt').write_text(str(i+1))\n")
    assert r.returncode==86 and(root/'body-count.txt').read_text()=='3',(r.returncode,r.stderr)
    r2=run(b,"from core import apply_move\nimport subprocess,sys\nfrom meter import independent_step\napply_move(0)\nclass Official:\n    def verify(self):apply_move(0)\nOfficial().verify()\n@independent_step\ndef own(x):return x+1\nown(0)\nsubprocess.run([sys.executable,'-m','verifier'],check=True)\nprint('fixture-child-done')\n")
    assert r2.returncode==0,(r2.returncode,r2.stderr)
    status=call(op='status');assert status['reported']==dict(search=4,verification=3)and status['issued']==dict(search=6,verification=16)and not status['unresolved_leases'],status
    assert m.Budget(config).call(dict(op='status'),os.getpid())['issued']==status['issued']
    server.shutdown();out=dict(passed=True,actual_model_requests=0,fixture_is_not_research=True,hard_stop_before_fourth_apply=True,cross_process_subprocess_and_independent_verification=True,source_hash_guard=True,global_allocation_overflow_rejected=True,restart_does_not_reset=True,fixture_counts=status,stdout=r2.stdout,old_runtime_modified=False,at=time.time())
    (BASE/'ENGINEERING-VALIDATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
