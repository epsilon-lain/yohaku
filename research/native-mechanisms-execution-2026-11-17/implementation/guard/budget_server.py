"""Host-only durable allocations and non-refundable per-process apply leases."""
import argparse,hashlib,json,os,re,socket,socketserver,sqlite3,struct,time
from pathlib import Path

def proc(pid):
    try:
        fields=Path('/proc/'+str(pid)+'/stat').read_text().split(') ')[1].split()
        return dict(pid=pid,parent=int(fields[1]),start=fields[19],cmd=Path('/proc/'+str(pid)+'/cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'))
    except OSError:return None
def ancestry(pid):
    out=[]
    for _ in range(64):
        r=proc(pid)
        if not r:break
        out.append(r)
        if r['parent']<=0 or r['parent']==pid:break
        pid=r['parent']
    return out

class Budget:
    def __init__(self,config):
        self.p=json.loads(Path(config).read_bytes());self.config=str(Path(config).resolve());self.path=Path(self.p['database'])
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.db()as d:
            d.executescript('CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT);CREATE TABLE IF NOT EXISTS allocations(id TEXT PRIMARY KEY,spec TEXT UNIQUE,node TEXT,project TEXT,search_cap INTEGER,verification_cap INTEGER,search_issued INTEGER DEFAULT 0,verification_issued INTEGER DEFAULT 0,task TEXT,source_set TEXT);CREATE TABLE IF NOT EXISTS leases(id INTEGER PRIMARY KEY,allocation TEXT,kind TEXT,pid INTEGER,start TEXT,n INTEGER,reported INTEGER DEFAULT 0,closed INTEGER DEFAULT 0);CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,at REAL,kind TEXT,data TEXT);')
            expected={k:str(self.p[k])for k in('goal_id','search_cap','verification_cap')}
            for k,v in expected.items():
                old=d.execute('SELECT v FROM meta WHERE k=?',(k,)).fetchone()
                if old:assert old[0]==v,'Existing budget cannot be reset'
                else:d.execute('INSERT INTO meta VALUES(?,?)',(k,v))
    def db(self):
        d=sqlite3.connect(self.path,timeout=30);d.row_factory=sqlite3.Row;d.execute('PRAGMA journal_mode=WAL');d.execute('PRAGMA synchronous=FULL');return d
    def event(self,d,kind,data):d.execute('INSERT INTO events(at,kind,data)VALUES(?,?,?)',(time.time(),kind,json.dumps(data,ensure_ascii=False)))
    def admission(self):
        if self.p.get('fixture'):return
        state=json.loads(Path(self.p['state_path']).read_bytes())
        if state.get('shared_stop')or state['phase']!='open':raise ValueError('Stage admission stopped')
        if state.get('first_send_at')and time.time()>=state['first_send_at']+5400:raise ValueError('Stage deadline elapsed')
    def model_auth(self,req,pid):
        if self.p.get('fixture'):
            assert any(r['pid']==self.p['fixture_parent_pid']for r in ancestry(pid));return
        tid=req['model_task'];assert re.fullmatch('model-task-[0-9a-f]{32}',tid)
        r=json.loads((Path(self.p['model_records'])/(tid+'.json')).read_bytes());ctx=r['node_context']
        assert ctx['node_id']==req['actor']and ctx['workflow']['policy_sha256']==self.p['policy_sha256']
        chain=ancestry(pid);assert not any('yohaku_project_tasks.py'in x['cmd']for x in chain),'Programs cannot allocate resources'
        assert any(x['pid']==r['pid']and x['start']==str(r['start'])for x in chain)
    def program_auth(self,a,pid):
        if self.p.get('fixture'):
            assert any(r['pid']==self.p['fixture_parent_pid']for r in ancestry(pid));return
        assert a['task'],'Allocation not bound to immutable producer'
        r=json.loads((Path(self.p['project_records'])/(a['task']+'.json')).read_bytes())
        assert r['snapshot']['source_set']==a['source_set']and r['program_budget']['allocation']==a['id']
        assert any(x['pid']==r['pid']and x['start']==str(r['start'])for x in ancestry(pid))
    def call(self,req,pid):
        op=req['op']
        with self.db()as d:
            d.execute('BEGIN IMMEDIATE')
            if op=='status':
                alloc=[dict(r)for r in d.execute('SELECT * FROM allocations ORDER BY id')]
                leases=[dict(r)for r in d.execute('SELECT * FROM leases ORDER BY id')]
                return dict(goal_id=self.p['goal_id'],caps=dict(search=self.p['search_cap'],verification=self.p['verification_cap']),allocations=alloc,
                    issued={k:sum(a[k+'_issued']for a in alloc)for k in('search','verification')},
                    reported={k:sum(r['reported']for r in leases if r['kind']==k)for k in('search','verification')},
                    unresolved_leases=[r for r in leases if not r['closed']],unused_issued_is_not_refunded=True)
            if op=='allocate':
                self.admission();self.model_auth(req,pid)
                state=json.loads(Path(self.p['state_path']).read_bytes())if not self.p.get('fixture')else None
                if state:
                    assert req['node']in state['members'];assert req['project']in {s['project_id']for s in state['members'][req['node']]['scopes']}
                    assert req['project']in {s['project_id']for s in state['members'][req['actor']]['scopes']}
                assert all(type(req[k])is int and req[k]>=0 for k in('search','verification'))
                spec=json.dumps({k:req[k]for k in('actor','request_id','node','project','search','verification','purpose')},sort_keys=True)
                aid='program-'+hashlib.sha256((req['actor']+'\0'+req['request_id']).encode()).hexdigest()[:24]
                old=d.execute('SELECT * FROM allocations WHERE id=?',(aid,)).fetchone()
                if old:assert old['spec']==spec,'Original allocation input conflict';return dict(old)
                for k in('search','verification'):
                    used=d.execute('SELECT COALESCE(SUM('+k+'_cap),0) FROM allocations').fetchone()[0]
                    assert used+req[k]<=self.p[k+'_cap'],'Shared '+k+' allocation envelope exhausted'
                d.execute('INSERT INTO allocations(id,spec,node,project,search_cap,verification_cap)VALUES(?,?,?,?,?,?)',(aid,spec,req['node'],req['project'],req['search'],req['verification']))
                self.event(d,'allocation_reserved',dict(req,pid=pid,allocation=aid));return dict(d.execute('SELECT * FROM allocations WHERE id=?',(aid,)).fetchone())
            a=d.execute('SELECT * FROM allocations WHERE id=?',(req['allocation'],)).fetchone();assert a,'Unknown original allocation'
            if op=='bind':
                self.admission();self.model_auth(req,pid);assert a['node']==req['actor']and a['project']==req['project']
                assert a['task']in(None,req['task'])and a['source_set']in(None,req['source_set']),'Allocation already belongs to another producer; never reset/reuse it'
                d.execute('UPDATE allocations SET task=?,source_set=?WHERE id=?',(req['task'],req['source_set'],a['id']))
                self.event(d,'producer_bound',dict(req,pid=pid));return dict(d.execute('SELECT * FROM allocations WHERE id=?',(a['id'],)).fetchone())
            self.program_auth(a,pid)
            if op=='lease':
                kind=req['kind'];assert kind in('search','verification');chunk=64 if kind=='search'else 8
                remaining=a[kind+'_cap']-a[kind+'_issued'];n=min(chunk,remaining)
                if n<=0:
                    self.event(d,'blocked_before_apply',dict(allocation=a['id'],kind=kind,pid=pid));return dict(allowed=False,error='Hard '+kind+' apply cap reached')
                d.execute('UPDATE allocations SET '+kind+'_issued='+kind+'_issued+? WHERE id=?',(n,a['id']))
                q=d.execute('INSERT INTO leases(allocation,kind,pid,start,n)VALUES(?,?,?,?,?)',(a['id'],kind,pid,proc(pid)['start'],n))
                return dict(allowed=True,lease=q.lastrowid,n=n,kind=kind)
            if op=='report':
                r=d.execute('SELECT * FROM leases WHERE id=?',(req['lease'],)).fetchone()
                assert r and r['allocation']==a['id']and r['pid']==pid and r['start']==proc(pid)['start']
                assert r['reported']<=req['used']<=r['n']and(not r['closed']or req['used']==r['reported'])
                d.execute('UPDATE leases SET reported=?,closed=1 WHERE id=?',(req['used'],r['id']));return dict(recorded=True)
            raise ValueError('Unknown budget operation')

class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        pid=struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))[0]
        for line in self.rfile:
            try:result={'ok':True,'result':self.server.budget.call(json.loads(line),pid)}
            except Exception as exc:result={'ok':False,'error':str(exc)or type(exc).__name__,'error_type':type(exc).__name__}
            self.wfile.write((json.dumps(result,ensure_ascii=False)+'\n').encode());self.wfile.flush()
class Server(socketserver.ThreadingUnixStreamServer):daemon_threads=True
def main():
    p=argparse.ArgumentParser();p.add_argument('config');a=p.parse_args();budget=Budget(a.config);path=Path(budget.p['socket'])
    # Removing a stale Unix socket is allowed only after its original PID is gone;
    # the supervisor performs that identity check. Never reset the database.
    if path.exists():raise RuntimeError('Budget socket already exists: inspect its original server')
    with Server(str(path),Handler)as server:
        server.budget=budget;path.chmod(0o600);server.serve_forever()
if __name__=='__main__':main()
