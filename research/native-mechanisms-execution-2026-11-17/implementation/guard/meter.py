"""Sandbox meter: immutable pinned apply hooks, durable host leases, descendants."""
import atexit,contextlib,hashlib,json,os,socket,sys,threading
from pathlib import Path
_local=threading.local();_clients=[];_lock=threading.Lock();_hashes={};ALLOCATION=None;SOCKET='/budget.sock';ALLOWED=set();FORCE_VERIFY=False
def rpc(req,sock=None):
    own=sock is None
    if own:sock=socket.socket(socket.AF_UNIX);sock.connect(SOCKET)
    try:
        sock.sendall((json.dumps(req)+'\n').encode());line=b''
        while not line.endswith(b'\n'):
            p=sock.recv(65536)
            if not p:raise RuntimeError('Budget server closed; fail closed')
            line+=p
        out=json.loads(line)
        if not out['ok']:raise RuntimeError(out['error'])
        return out['result']
    finally:
        if own:sock.close()
class Client:
    def __init__(self):
        self.sock=socket.socket(socket.AF_UNIX);self.sock.connect(SOCKET);self.slots={};self.actual={'search':0,'verification':0};self.closed=False
        with _lock:_clients.append(self)
    def report(self,kind):
        x=self.slots.get(kind)
        if x:rpc(dict(op='report',allocation=ALLOCATION,lease=x['lease'],used=x['used']),self.sock);self.slots.pop(kind,None)
    def consume(self,kind):
        x=self.slots.get(kind)
        if not x or x['used']>=x['n']:
            self.report(kind);r=rpc(dict(op='lease',allocation=ALLOCATION,kind=kind),self.sock)
            if not r['allowed']:hard_stop(r['error'],86)
            x=dict(r,used=0);self.slots[kind]=x
        x['used']+=1;self.actual[kind]+=1
    def close(self):
        if self.closed:return
        for k in list(self.slots):self.report(k)
        self.closed=True;self.sock.close()
def client():
    if not hasattr(_local,'client'):_local.client=Client()
    return _local.client
def close_all():
    for c in list(_clients):
        try:c.close()
        except Exception:pass
def hard_stop(message,code):
    close_all()
    try:
        Path('/output/PROGRAM-BUDGET-ERROR.json').write_text(json.dumps(dict(error=message,code=code,pid=os.getpid(),allocation=ALLOCATION,already_issued_not_refunded=True))+'\n')
        os.write(2,('PROGRAM_BUDGET_HARD_STOP '+message+'\n').encode())
    finally:os._exit(code)
@contextlib.contextmanager
def verification(reason='explicit independent/final verification'):
    old=getattr(_local,'manual_verification',False);_local.manual_verification=True
    try:yield
    finally:_local.manual_verification=old
def independent_step(fn):
    def wrapped(*a,**k):client().consume('verification');return fn(*a,**k)
    return wrapped
def profile(frame,event,arg):
    try:
        if not hasattr(_local,'verify_frames'):_local.verify_frames=set()
        code=frame.f_code;name=code.co_name;filename=code.co_filename
        if event=='call':
            obj=frame.f_locals.get('self');typename=type(obj).__name__ if obj is not None else ''
            if name.startswith(('verify','validate'))and ('/verifier/'in filename or typename=='Official'):_local.verify_frames.add(id(frame))
            if name=='apply_move'and Path(filename).name in('core.py','stable_core.py'):
                if filename not in _hashes:_hashes[filename]=hashlib.sha256(Path(filename).read_bytes()).hexdigest()
                if _hashes[filename]not in ALLOWED:hard_stop('Official apply source differs from fixed a0fd6e6f lock',87)
                kind='verification'if FORCE_VERIFY or _local.verify_frames or getattr(_local,'manual_verification',False)else'search'
                client().consume(kind)
        elif event=='return':_local.verify_frames.discard(id(frame))
    except BaseException as exc:hard_stop(str(exc),87)
def install(allocation,allowed,force_verification=False):
    global ALLOCATION,ALLOWED,FORCE_VERIFY
    ALLOCATION=allocation;ALLOWED=set(allowed);FORCE_VERIFY=force_verification
    sys.setprofile(profile);threading.setprofile(profile);atexit.register(close_all)
    def forbidden(*a,**k):raise RuntimeError('Use metered Python subprocesses; disabling/forking around the budget guard is forbidden')
    sys.setprofile=forbidden;threading.setprofile=forbidden
    for name in('fork','forkpty','system','execv','execve','execvp','execvpe'):
        if hasattr(os,name):setattr(os,name,forbidden)
