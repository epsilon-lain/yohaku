"""Read-only app discovery and explicit human-requested portable app import.

No discovered program is executed here. All execution uses yohaku_tools.run.
"""
import configparser
import json
import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import tempfile
import subprocess

import yohaku_tools as tools

MAX_APPS = 256
MAX_COPY = 1024 * 1024 * 1024

def powershell_path():
    p=Path('/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')
    return p if p.is_file() and os.environ.get('WSL_INTEROP') else None

def windows_path(path):
    result=subprocess.run(['/usr/bin/wslpath','-w',str(path)],capture_output=True,text=True,timeout=5,check=True)
    return result.stdout.strip()

def windows_item(path, name=None):
    path=Path(path)
    codex=path.name.lower() in ('codex','codex.exe','codex.cmd','codex.ps1')
    name=name or ('Codex' if codex else ('Visual Studio Code' if path.name.lower() in ('code','code.exe','code.cmd') else path.stem))
    reason='Connect the existing Windows Codex account to Yohaku Chat' if codex else 'Windows application found; embedded Windows window adapter is not available yet'
    return {'entry':{'id':app_id(path),'name':name[:80],'program':'','args':[],'wayland':False},
            'address':str(path),'source':str(path),'ready':False,'reason':reason,
            'origin':'Windows','action':'codex' if codex else 'unsupported','keywords':name+' '+path.name}

def linux_codex_item(path):
    """Register a native Codex as a Chat connector, never a world executable."""
    path=Path(path).resolve(strict=True)
    executable(path)
    if path.name != 'codex':
        raise tools.ToolError('Choose the native Linux Codex binary')
    with path.open('rb') as stream:
        if stream.read(4) != b'\x7fELF':
            raise tools.ToolError('Linux Codex must be a native ELF binary')
    return {'entry':{'id':app_id(path),'name':'Codex','program':'','args':[],'wayland':False},
            'address':str(path),'source':str(path),'origin':'Linux','action':'codex',
            'ready':False,'reason':'Connect native Linux Codex to Yohaku Chat (dedicated login may be required)',
            'keywords':'Codex Linux native app-server ' + path.name}


def linux_codex_candidates():
    """Bounded discovery of VS Code's bundled native Linux Codex in WSL."""
    found=[]
    override=os.environ.get('YOHAKU_CODEX_LINUX')
    if override:
        found.append(Path(override).expanduser())
    root=Path('/mnt/c/Users')
    if root.is_dir():
        # Only well-known VS Code extension locations, not broad home traversal.
        for user in list(root.iterdir())[:80]:
            directory=user/'.vscode/extensions'
            if not directory.is_dir():continue
            for extension in sorted(directory.glob('openai.chatgpt-*'),reverse=True)[:8]:
                found.append(extension/'bin/linux-x86_64/codex')
    return found


def is_windows_path(path):
    return bool(re.match(r'^/mnt/[a-z]/',str(path)))

def is_windows_program(path):
    path=Path(path)
    if not is_windows_path(path) or not path.is_file():return False
    if path.suffix.lower() in ('.exe','.cmd','.bat','.ps1','.msi'):return True
    with path.open('rb') as stream:header=stream.read(65536)
    # Windows npm also installs a POSIX shim for WSL/Git Bash. Depending on
    # npm's version it calls plain `node`, so node.exe alone misses Codex.
    # Require its package reference and a Windows companion; do not classify
    # a genuine Linux npm install as Windows merely because it lives on C:.
    if (path.name.lower()=='codex' and b'node_modules/@openai/codex/bin/codex.js' in header.replace(b'\\',b'/')
            and any(path.with_suffix(suffix).is_file() for suffix in ('.cmd','.ps1'))):
        return True
    return header.startswith(b'MZ') or (path.name.lower() in ('code','codex','claude') and any(s in header for s in (b'node.exe',b'Code.exe',b'cmd.exe')))

def windows_inventory():
    ps=powershell_path()
    if ps is None:return [],'Windows scan unavailable (not a WSL Windows session)'
    try:
        script=windows_path(tools.PACKAGE/'agent/yohaku_windows_inventory.ps1')
        result=subprocess.run([str(ps),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',script],
                              capture_output=True,timeout=20,check=True)
        data=json.loads(result.stdout.decode('utf-8-sig'))
        if not isinstance(data,list):raise ValueError('inventory must be a list')
        found=[]
        for item in data[:MAX_APPS]:
            if isinstance(item,dict) and isinstance(item.get('name'),str) and isinstance(item.get('app_id'),str):
                ident=item['app_id']
                if 0<len(ident)<4096 and not any(ord(c)<32 for c in ident):
                    packaged=windows_item('windows-app:'+ident,item['name'])
                    packaged['origin']='Windows';packaged['action']='unsupported'
                    packaged['reason']='Windows packaged application found; embedded window adapter is not available yet'
                    found.append(packaged)
                continue
            if not isinstance(item,dict) or not isinstance(item.get('path'),str) or not isinstance(item.get('name'),str):continue
            if not re.match(r'^[A-Za-z]:[\\/]',item['path']):continue
            path=Path('/mnt/'+item['path'][0].lower()+'/'+item['path'][3:].replace('\\','/'))
            if path.is_file():found.append(windows_item(path,item['name']))
        return found,'Windows scan complete'
    except (OSError,ValueError,subprocess.SubprocessError):
        return [],'Windows scan failed; paste an app address to inspect it'


def address_path(text):
    text = text.strip()
    if re.match(r'^[A-Za-z]:[\\/]', text):
        text = '/mnt/' + text[0].lower() + '/' + text[3:].replace('\\', '/')
    path = Path(text).expanduser()
    if not path.is_absolute():
        found = shutil.which(text)
        if not found:
            raise tools.ToolError('Use an existing absolute app address or installed command name')
        path = Path(found)
    return path.resolve(strict=True)


def app_id(address):
    return 'app-' + hashlib.sha256(str(address).encode()).hexdigest()[:16]


def executable(path):
    if not path.is_file():
        raise tools.ToolError('The address is not an executable Linux program')
    with path.open('rb') as stream:
        header = stream.read(65536)
    if header.startswith(b'MZ') or path.suffix.lower() in ('.exe', '.bat', '.cmd', '.msi'):
        raise tools.ToolError('Windows application: a Windows adapter is required; use its Linux version here')
    if not os.access(path, os.X_OK):
        raise tools.ToolError('The Linux entry point is not executable; set its executable permission first')
    if not header.startswith((b'\x7fELF', b'#!')):
        raise tools.ToolError('Unsupported executable format; expected Linux ELF or a script with #!')
    if header.startswith(b'\x7fELF') and (header[4:6] != b'\x02\x01' or header[18:20] != b'\x3e\x00'):
        raise tools.ToolError('This launcher currently needs an x86_64 Linux executable')
    if header.startswith(b'#!') and (b'WSL_INTEROP' in header or b'cmd.exe' in header or b'powershell.exe' in header or b'Code.exe' in header):
        raise tools.ToolError('Windows/WSL bridge launcher: cannot run inside the world sandbox')


def desktop(path):
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise tools.ToolError('Desktop entry must be a regular file')
    if info.st_size > 65536:
        raise tools.ToolError('Desktop entry is too large')
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.optionxform = str
    try:
        parser.read_string(path.read_text(encoding='utf-8'))
    except configparser.Error as error:
        raise tools.ToolError('Invalid desktop entry: '+str(error)) from error
    section = parser['Desktop Entry']
    if section.get('Type') != 'Application' or section.get('Hidden', 'false').lower() == 'true':
        raise tools.ToolError('Not a visible application entry')
    if section.get('NoDisplay', 'false').lower() == 'true':
        raise tools.ToolError('This entry is hidden from application menus')
    raw = shlex.split(section.get('Exec', ''), posix=True)
    if not raw or any(c in raw[0] for c in '=$`'):
        raise tools.ToolError('Desktop entry needs a direct executable')
    args = []
    for token in raw[1:]:
        if token in ('%f', '%F', '%u', '%U', '%i', '%k', '%d', '%D', '%n', '%N', '%v', '%m'):
            continue
        if token == '%c':
            args.append(section.get('Name', path.stem))
            continue
        token = token.replace('%%', '\x01')
        if '%' in token:
            raise tools.ToolError('Unsupported desktop field code; use the executable address')
        args.append(token.replace('\x01', '%'))
    program = address_path(raw[0])
    if section.get('TryExec'):
        address_path(section['TryExec'])
    return program, args, section.get('Name', path.stem), section.get('Terminal', 'false').lower() == 'true'


def inspect(address, root):
    path = address_path(address)
    if is_windows_program(path):return windows_item(path)
    source = path
    args = []
    name = path.stem
    terminal = False
    bundle = None
    if path.is_dir():
        bundle = path
        choices = [path / 'code', path / 'codium', path / 'bin' / path.name]
        choices = [p for p in choices if p.is_file() and os.access(p, os.X_OK)]
        if not choices:
            choices = [p for p in path.iterdir() if p.is_file() and not p.is_symlink() and os.access(p, os.X_OK)]
        if len(choices) != 1:
            raise tools.ToolError('Application folder needs one entry point; use a Linux portable VS Code folder or a direct executable')
        source = choices[0]
        name = path.name
    elif path.suffix == '.desktop':
        source, args, name, terminal = desktop(path)
    executable(source)
    if source.name == 'codex' and not terminal:
        return linux_codex_item(source)
    if source.name in ('codex', 'claude') or terminal:
        raise tools.ToolError('CLI application needs an interactive terminal/network adapter; not available in this release')
    ident = app_id(path)
    reason = ''
    if source.is_relative_to(root):
        program = 'world:' + str(source.relative_to(root))
        tools.inside(root, str(source.relative_to(root)))
    elif source.is_relative_to('/usr'):
        program = str(source)
    else:
        program = ''
        reason = 'Import this executable, or its complete portable folder, into the world first'
    if source.name in ('code', 'code-oss', 'codium'):
        args = ['--ozone-platform=wayland', '--disable-gpu', '--no-sandbox',
                '--user-data-dir', '/world/tools/state/' + ident + '/profile',
                '--extensions-dir', '/world/tools/state/' + ident + '/extensions', '/world/files']
        name = 'Visual Studio Code' if source.name != 'codium' else 'VSCodium'
    entry = {'id': ident, 'name': name[:80], 'program': program, 'args': args, 'wayland': True}
    return {'entry': entry, 'address': str(path), 'source': str(source), 'origin':'Linux',
            'bundle': str(bundle) if bundle else None, 'ready': not reason, 'reason': reason}


def discover(root, directories=None, with_report=False):
    default_scan=directories is None
    if directories is None:
        directories = [Path.home() / '.local/share/applications', Path('/usr/local/share/applications'), Path('/usr/share/applications')]
    found = []
    seen = set()
    examined = 0
    for directory in directories:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob('*.desktop')):
            if path.name in seen:
                continue
            seen.add(path.name)
            examined += 1
            if examined > MAX_APPS:
                break
            try:
                item = inspect(str(path), root)
            except (tools.ToolError, OSError, ValueError, KeyError, configparser.Error) as error:
                item = {'entry': {'id': app_id(path), 'name': path.stem, 'program': '', 'args': [], 'wayland': True},
                        'address': str(path), 'ready': False, 'reason': str(error)}
            item.setdefault('origin','Linux app');found.append(item)
    notice=''
    if default_scan:
        for path in linux_codex_candidates():
            try:
                if path.is_file():found.append(linux_codex_item(path))
            except (OSError,ValueError,tools.ToolError):pass
        # A bounded useful command catalog, not recursive disk scanning or execution.
        for name in ('codex','claude','code','codium','python3','node','git'):
            path=shutil.which(name)
            if not path:continue
            try:
                if is_windows_program(path):item=windows_item(path)
                else:
                    try:item=inspect(path,root)
                    except tools.ToolError as error:
                        item={'entry':{'id':app_id(path),'name':name,'program':'','args':[],'wayland':False},'address':str(path),'ready':False,'reason':str(error)}
                    item['origin']='Linux command'
                    if name in ('python3','node','git'):
                        item.update(ready=False,reason='Command found; add a tool with specific arguments or use a terminal adapter')
                found.append(item)
            except (OSError,ValueError):pass
        win,notice=windows_inventory();found.extend(win)
    unique={}
    for item in found:
        key=str(item['address']).casefold()
        if item.get('action')=='codex':key=re.sub(r'\.(cmd|ps1)$','',key)
        # Prefer the friendly Windows name, while preserving the Codex connect action.
        if key not in unique or item.get('action')=='codex':unique[key]=item
    items=sorted(unique.values(),key=lambda item:item['entry']['name'].casefold())[:MAX_APPS]
    report={'scope':'Linux apps + PATH commands + Windows Start menu','notice':notice,
            'linux':sum(not i.get('origin','').startswith('Windows') for i in items),
            'windows':sum(i.get('origin','').startswith('Windows') for i in items)}
    return (items,report) if with_report else items


def import_address(address, root):
    item = inspect(address, root)
    # Chat adapters do not belong to the sandboxed world-app import registry.
    if item.get('action')=='codex' or item.get('origin')=='Windows':return item
    if item['ready']:
        tools.validate({'format': 'yohaku-tools/1', 'tools': [item['entry']]})
        return item
    source = Path(item['source'])
    bundle = Path(item['bundle']) if item['bundle'] else None
    ident = item['entry']['id']
    parent = tools.inside(root, 'tools/apps')
    destination = tools.inside(root, 'tools/apps/' + ident)
    if destination.exists():
        raise tools.ToolError('An imported app already occupies this address; remove its world copy before importing again')
    total = 0
    count = 0
    candidates = [source] if bundle is None else bundle.rglob('*')
    for path in candidates:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise tools.ToolError('Portable imports must contain only regular files and directories, without symlinks')
        if path.is_mount() and path != bundle:
            raise tools.ToolError('Portable imports cannot contain nested mounts')
        total += info.st_size if stat.S_ISREG(info.st_mode) else 0
        count += 1
        if total > MAX_COPY or count > 20000:
            raise tools.ToolError('Portable app exceeds 1 GiB or 20000 entries')
    # Explicit import only: copy no host home, credentials or global configuration.
    parent_fd = open_directory(root, ('tools', 'apps'), create=True)
    source_base = bundle or source.parent
    try:
        source_fd = open_directory(source_base, ())
    except BaseException:
        os.close(parent_fd); raise
    try:
        staging = Path(tempfile.mkdtemp(prefix='.import-', dir='/proc/self/fd/'+str(parent_fd)))
    except BaseException:
        os.close(source_fd); os.close(parent_fd); raise
    copied = 0
    copied_count = 0
    try:
        paths = [source] if bundle is None else bundle.rglob('*')
        for path in paths:
            relative = Path(path.name) if bundle is None else path.relative_to(bundle)
            output = staging / relative
            # Walk from the pinned source directory, rejecting every symlink component.
            fd = os.dup(source_fd)
            try:
                for part in relative.parts:
                    next_fd = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                    os.close(fd); fd = next_fd
                info = os.fstat(fd)
                copied_count += 1
                if copied_count > 20000:
                    raise tools.ToolError('Portable folder grew during import')
                if stat.S_ISDIR(info.st_mode):
                    output.mkdir(parents=True, exist_ok=True)
                elif stat.S_ISREG(info.st_mode):
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with os.fdopen(os.dup(fd), 'rb') as incoming, output.open('xb') as outgoing:
                        while True:
                            chunk = incoming.read(65536)
                            if not chunk: break
                            copied += len(chunk)
                            if copied > MAX_COPY: raise tools.ToolError('Portable app grew beyond 1 GiB')
                            outgoing.write(chunk)
                    output.chmod(info.st_mode & 0o777)
                else:
                    raise tools.ToolError('Portable folder changed to a special file')
            finally:
                os.close(fd)
        os.rename(staging.name, ident, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
    finally:
        if staging.exists(): shutil.rmtree(staging)
        os.close(source_fd); os.close(parent_fd)
    relative = Path(source.name) if bundle is None else source.relative_to(bundle)
    item['entry']['program'] = 'world:tools/apps/' + ident + '/' + str(relative)
    item['ready'] = True
    item['reason'] = ''
    tools.validate({'format': 'yohaku-tools/1', 'tools': [item['entry']]})
    return item


def open_directory(root, parts, create=False):
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts:
            if create:
                try: os.mkdir(part, 0o755, dir_fd=fd)
                except FileExistsError: pass
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = next_fd
        return fd
    except BaseException:
        os.close(fd); raise
