"""Native Linux Codex app-server runtime for Yohaku.

Host inference is separate from world tools. No Windows setup and no automatic
credential import. Native command/exec is verified in a deny-by-default policy.
"""
import json
import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

# Import the existing bridge module only when needed; avoid import cycles.
import yohaku_apps as apps
import yohaku_codex_provider as provider

PROFILE='yohaku-control'
PROBE='''import json,pathlib,sys
cwd,outer=map(pathlib.Path,sys.argv[1:])
r={}
try:r['control_read']=(cwd/'read-control').read_text()=='yohaku-readable-control'
except OSError:r['control_read']=False
for key,path in [('workspace_write_denied',cwd/'write-probe'),('outside_write_denied',outer/'outside-write')]:
 try:path.write_text('probe');r[key]=False
 except OSError:r[key]=True
try:(outer/'outside-read').read_bytes();r['outside_read_denied']=False
except OSError:r['outside_read_denied']=True
print(json.dumps(r))
'''


def is_linux_codex(address):
    try:
        path=apps.address_path(address)
        if path.name!='codex' or not path.is_file() or not os.access(path,os.X_OK):return False
        with path.open('rb') as stream:hdr=stream.read(20)
        return len(hdr)==20 and hdr[:6]==b'\x7fELF\x02\x01' and hdr[18:20]==b'\x3e\x00'
    except (OSError,ValueError,apps.tools.ToolError):return False


def _auth_home():
    override=os.environ.get('YOHAKU_CODEX_AUTH_HOME')
    if not override:return Path.home()/'.local/state/yohaku/codex-linux-login'
    path=Path(override)
    if not path.is_absolute() or str(path).startswith('/mnt/') or path.resolve()!=path:
        raise ValueError('Dedicated Codex login must be an explicit native Linux directory, without symlinks')
    metadata=path.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid!=os.getuid() or metadata.st_mode & 0o022:
        raise ValueError('Dedicated Codex login directory must be owned and not writable by other users')
    return path


def _runtime_config(executable,cwd):
    return '''approval_policy = "never"
default_permissions = "yohaku-control"
cli_auth_credentials_store = "file"
mcp_servers = {}
hooks = {}
plugins = {}
[features]
shell_tool = false
multi_agent = false
apps = false
plugins = false
use_legacy_landlock = false
[permissions.yohaku-control.filesystem]
":root" = "deny"
":minimal" = "read"
'''+json.dumps(str(executable)) + ' = "read"\n' + json.dumps(str(cwd))+''' = "read"
[permissions.yohaku-control.network]
enabled = false
'''


def _safe_auth_copy(target):
    # Login is explicit and credentials remain solely on the user's device.
    source=_auth_home()/'auth.json'
    try:
        metadata=source.lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size>1024*1024:
        raise ValueError('Invalid dedicated Linux Codex authentication file')
    # Open without following a replaced symlink.
    fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        current=os.fstat(fd)
        if not stat.S_ISREG(current.st_mode) or current.st_size>1024*1024:
            raise ValueError('Invalid Codex credential file')
        with os.fdopen(fd,'rb',closefd=False) as src:
            with target.open('xb') as dest:
                dest.write(src.read(1024*1024+1))
        target.chmod(0o600)
    finally:os.close(fd)
    return {'source':str(source),'original_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'device':current.st_dev,'inode':current.st_ino}


def preserve_refreshed_auth(child):
    # Same conditional persistence rule as the mature Windows bridge. No login flow or credential values in diagnostics.
    lease=getattr(child,'yohaku_auth_lease',None)
    if not lease:return {'state':'not_applicable'}
    runtime=getattr(child,'yohaku_runtime',None)
    fresh=Path(runtime.name)/'state/auth.json'
    source=Path(lease['source']);pending=None
    try:
        if fresh.is_symlink():return {'state':'invalid_runtime_file_preserved_source'}
        data=fresh.read_bytes()
        if not 0<len(data)<=1024*1024:return {'state':'invalid_runtime_file_preserved_source'}
        if hashlib.sha256(data).hexdigest()==lease['original_sha256']:return {'state':'unchanged'}
        parent=os.open(source.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            def unchanged():
                descriptor=os.open(source.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
                try:
                    meta=os.fstat(descriptor)
                    if not stat.S_ISREG(meta.st_mode) or (meta.st_dev,meta.st_ino)!=(lease['device'],lease['inode']) or meta.st_uid!=os.getuid() or meta.st_mode&0o077:return False
                    with os.fdopen(descriptor,'rb',closefd=False) as original:body=original.read(1024*1024+1)
                    return hashlib.sha256(body).hexdigest()==lease['original_sha256']
                finally:os.close(descriptor)
            if not unchanged():return {'state':'concurrent_login_preserved'}
            descriptor,pending=tempfile.mkstemp(prefix='.yohaku-auth-refresh-',dir=source.parent)
            with os.fdopen(descriptor,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
            if not unchanged():return {'state':'concurrent_login_preserved'}
            os.replace(pending,source);pending=None;os.fsync(parent)
            return {'state':'refreshed_saved','mode':'0600','same_dedicated_linux_store':True}
        finally:os.close(parent)
    except OSError:return {'state':'refresh_persistence_unconfirmed','source_not_intentionally_overwritten':True}
    finally:
        if pending is not None:
            try:os.unlink(pending)
            except OSError:pass


class NodeRuntime:
    """Private persistent native conversation store; credentials are leased per process."""
    def __init__(self,node_key):
        if not isinstance(node_key,str) or not __import__('re').fullmatch(r'[0-9a-f]{24}/ai-node-[0-9a-f]{24}',node_key):raise ValueError('Invalid host node runtime key')
        root=Path.home()/'.local/state/yohaku/ai-node-native'
        root.mkdir(mode=0o700,parents=True,exist_ok=True)
        if root.is_symlink() or root.resolve()!=root or root.stat().st_uid!=os.getuid() or root.stat().st_mode&0o077:raise ValueError('Native node store must be canonical, private and host-owned')
        for part in node_key.split('/'):
            root=root/part
            if root.is_symlink():raise ValueError('Node runtime symlink rejected')
            root.mkdir(mode=0o700,exist_ok=True)
            if root.stat().st_uid!=os.getuid() or root.stat().st_mode&0o077:raise ValueError('Node runtime must be private and host-owned')
        self.name=str(root)
    def cleanup(self):
        # Preserve sessions/SQLite/rollouts; never keep a second durable credential store.
        auth=Path(self.name)/'state/auth.json'
        if auth.exists() and not auth.is_symlink():auth.unlink()


def launch(address, selection=None, node_key=None):
    if not is_linux_codex(address):
        raise ValueError('Choose a native x86_64 Linux Codex ELF executable')
    executable=apps.address_path(address)
    python=shutil.which('python3',path='/usr/bin:/bin')
    if python is None:raise ValueError('System python3 is needed for the Linux boundary probe')
    cache=Path.home()/'.cache/yohaku'
    cache.mkdir(mode=0o700,parents=True,exist_ok=True)
    runtime=NodeRuntime(node_key) if node_key else tempfile.TemporaryDirectory(prefix='codex-bridge-',dir=cache)
    relay=None
    try:
        outer=Path(runtime.name);home=outer/'state';cwd=outer/'control'
        for p in (home,cwd,home/'tmp'):
            if p.is_symlink():raise ValueError('Native node runtime symlink rejected')
            p.mkdir(mode=0o700,exist_ok=bool(node_key))
        if node_key and (home/'auth.json').exists():raise ValueError('Node native home has an unclosed credential lease; inspect previous process')
        (cwd/'read-control').write_text('yohaku-readable-control')
        (outer/'outside-read').write_text('outside-canary')
        selection=provider.load() if selection is None else dict(selection)
        relay=provider.Relay(selection['deepseek_key']) if selection['active']=='deepseek' else None
        policy=_runtime_config(executable,cwd)
        effort=(selection.get('openai_reasoning_effort') or os.environ.get('YOHAKU_CODEX_EFFORT')) if relay is None else None
        if effort:
            provider.validate_reasoning_effort(effort)
            policy='model_reasoning_effort = '+json.dumps(effort)+'\n'+policy
        if relay is not None:
            (home/'models.json').write_text(json.dumps(provider.catalog()))
            policy=provider.runtime_config(home,relay.base_url,policy)
        policy+='\n[shell_environment_policy]\ninherit = \"none\"\nignore_default_excludes = false\n'
        (home/'config.toml').write_text(policy)
        (home/'config.toml').chmod(0o600)
        if relay is None:
            policy='model_provider = "openai"\n'+policy
            (home/'config.toml').write_text(policy)
            auth_lease=_safe_auth_copy(home/'auth.json')
        env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(home),'CODEX_HOME':str(home),
             'TMPDIR':str(home/'tmp'),'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'}
        if relay is not None:env[provider.ENV_KEY]=relay.token
        child=subprocess.Popen([str(executable),'app-server','--listen','stdio://'],env=env,cwd=cwd,
                               stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        child.yohaku_auth_lease=auth_lease if relay is None else None
        child.yohaku_provider_relay=relay
        child.yohaku_linux=True
        child.yohaku_runtime=runtime
        child.yohaku_info={'cwd':str(cwd),'outside':str(outer),'readProbe':str(outer/'outside-read'),
                           'python':python,'executable':str(executable)}
        child.yohaku_info['provider']=selection['active']
        child.yohaku_info['selected_model']=provider.MODEL if relay is not None else selection.get('openai_model')
        child.yohaku_info['selected_reasoning_effort']='high' if relay is not None else effort
        return child
    except BaseException:
        if relay is not None:relay.close()
        runtime.cleanup()
        raise


def verify_boundaries(connection):
    from yohaku_codex import CodexError
    info=connection.info
    result=connection.request('command/exec',{'command':[info['python'],'-I','-B','-c',PROBE,info['cwd'],info['outside']],
        'cwd':info['cwd'],'permissionProfile':PROFILE,'timeoutMs':10000},timeout=25)
    if result.get('exitCode')!=0:raise CodexError('Linux Codex sandbox probe failed to execute; no model turn started')
    raw=result.get('stdout')
    if not isinstance(raw,str) or len(raw)>4096:raise CodexError('Linux Codex sandbox probe returned invalid output')
    try:
        checks=json.loads(raw)
    except ValueError:raise CodexError('Linux Codex sandbox probe returned invalid JSON')
    expected={'control_read','workspace_write_denied','outside_write_denied','outside_read_denied'}
    if not isinstance(checks,dict) or set(checks)!=expected or any(type(checks[k]) is not bool for k in expected):
        raise CodexError('Linux Codex sandbox probe returned invalid checks')
    # A tmpfs write inside bwrap does not imply a write to the host filesystem.
    host_blocked=not (Path(info['outside'])/'outside-write').exists()
    if not all(checks[k] for k in ('control_read','workspace_write_denied','outside_read_denied')) or not host_blocked:
        raise CodexError('Linux Codex sandbox boundary check failed; no model turn started')


def cleanup(child):
    relay=getattr(child,'yohaku_provider_relay',None)
    if relay is not None:relay.close()
    runtime=getattr(child,'yohaku_runtime',None)
    try:child.yohaku_auth_refresh_persistence=preserve_refreshed_auth(child)
    finally:
        if runtime is not None:runtime.cleanup()


def login(address):
    """Only performed by an explicit user-invoked login command; never during probe."""
    if not is_linux_codex(address):raise ValueError('Choose a native Linux Codex executable')
    directory=_auth_home();directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    env=os.environ.copy();env['CODEX_HOME']=str(directory)
    print('Sign in to dedicated Yohaku Linux Codex storage; no Windows credentials are copied.',flush=True)
    return subprocess.call([str(apps.address_path(address)),'login','--device-auth'],env=env)