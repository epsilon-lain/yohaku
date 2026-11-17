"""Trusted launch wrapper for all Python project programs and Python children."""
import json,os,runpy,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import meter
def main():
    args=sys.argv[1:];assert args[:1]==['--allocation'];allocation=args[1];args=args[2:]
    mode='search'
    if args[:1]==['--mode']:mode=args[1];args=args[2:]
    assert args[0]=='--';argv=args[1:];assert Path(argv[0]).name.startswith('python')
    allowed=json.loads((ROOT/'official-apply-hashes.json').read_bytes())
    meter.install(allocation,allowed,mode=='verification')
    original_popen=subprocess.Popen
    def popen(command,*a,**kw):
        if isinstance(command,str)or kw.get('shell'):raise RuntimeError('Shell subprocess cannot bypass program meter')
        if not command or not Path(str(command[0])).name.startswith('python'):raise RuntimeError('Only metered Python child interpreters are supported in this phase')
        child_mode='verification'if '-m'in command and command[command.index('-m')+1]=='verifier'else mode
        command=[sys.executable,'-B',str(ROOT/'runner.py'),'--allocation',allocation,'--mode',child_mode,'--',*map(str,command)]
        return original_popen(command,*a,**kw)
    subprocess.Popen=popen
    target=argv[1:]
    while target and target[0]in('-B','-u'):target=target[1:]
    if target[:1]==['-m']:
        sys.path.insert(0,os.getcwd())
        module=target[1];sys.argv=[module,*target[2:]];runpy.run_module(module,run_name='__main__',alter_sys=True)
    elif target[:1]==['-c']:
        sys.path.insert(0,os.getcwd())
        sys.argv=['-c',*target[2:]];exec(compile(target[1],'<metered-python-c>','exec'),{'__name__':'__main__'})
    else:
        assert target and not target[0].startswith('-'),'Unsupported interpreter flags; no unmetered fallback'
        sys.argv=target;sys.path.insert(0,str(Path(target[0]).resolve().parent));runpy.run_path(target[0],run_name='__main__')
    meter.close_all()
if __name__=='__main__':main()
