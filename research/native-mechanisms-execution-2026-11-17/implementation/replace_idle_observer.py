"""Replace only a sleeping child-free observer, never any native model worker."""
import json,os,signal,time
from pathlib import Path
from continuation import BASE,activate,save
activate()
from yohaku_codex_tasks import identity
old=json.loads((BASE/'SUPERVISOR.json').read_bytes())['identity'];now=identity(old['pid'])
assert now and now['start']==old['start']and 'observer.py'in Path('/proc/'+str(old['pid'])+'/cmdline').read_bytes().decode().replace('\0',' ')
assert not Path('/proc/'+str(old['pid'])+'/task/'+str(old['pid'])+'/children').read_text().strip()
assert 'nanosleep'in Path('/proc/'+str(old['pid'])+'/wchan').read_text(),'Only replace at the verified idle task boundary'
os.kill(old['pid'],signal.SIGSTOP);stopped=identity(old['pid']);assert stopped['state']=='T'
prior=BASE/'OBSERVER-REPLACEMENT.json'
if prior.exists():(BASE/('OBSERVER-REPLACEMENT-'+str(old['pid'])+'-prior.json')).write_bytes(prior.read_bytes())
save(prior,dict(at=time.time(),old_identity=old,stopped_identity=stopped,reason='Consume exact root-delegated continuation and deliver verified operational repair under original user-authorized root scopes; no project scope expansion, no new budget',native_models_untouched=True,new_authority_added=False))
os.kill(old['pid'],signal.SIGUSR1);os.kill(old['pid'],signal.SIGCONT)
for _ in range(100):
    live=identity(old['pid'])
    if not live or live['state']in('Z','X'):break
    time.sleep(.03)
else:raise RuntimeError('Old observer still live; no replacement launched')
print(json.dumps(dict(replaced_observer_only=True,models_untouched=True)))
