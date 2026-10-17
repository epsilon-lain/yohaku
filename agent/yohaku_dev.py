#!/usr/bin/env python3
"""Human bootstrap of a Loom-managed Yohaku development copy and read-only Rust runtime.

Preparation never executes project code. Build/test execution remains in yohaku_tools.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

import yohaku_tools as tools

PROJECT = 'files/yohaku-default'
INFO = 'memory/development.json'
GUIDE = 'memory/yohaku-development.md'
PROFILE = 'config/development-runtime.json'
ACTIONS = ('check', 'test', 'build', 'preview')


def entries():
    return [{'id': 'yohaku-'+action, 'name': 'Yohaku '+label,
             'program': 'builtin:dev', 'args': [action], 'wayland': action == 'preview'}
            for action, label in [('check', 'check'), ('test', 'core tests'),
                                  ('build', 'build candidate'), ('preview', 'preview candidate')]]


def detect_runtime():
    candidates = [Path.home()/'.cargo/bin/rustc', Path('/usr/bin/rustc')]
    found = shutil.which('rustc')
    if found: candidates.insert(0, Path(found))
    rustc = next((p for p in candidates if p.is_file() and os.access(p, os.X_OK)), None)
    if rustc is None: raise tools.ToolError('Rust is not available; use the Rust installation that builds this Yohaku')
    try:
        result = subprocess.run([str(rustc), '--print', 'sysroot'], cwd=tools.PACKAGE,
                                capture_output=True, text=True, timeout=20, check=True)
    except (OSError, subprocess.SubprocessError) as e:
        raise tools.ToolError('Could not locate the installed Rust sysroot') from e
    toolchain = Path(result.stdout.strip()).resolve(strict=True)
    registry = (Path(os.environ.get('CARGO_HOME', str(Path.home()/'.cargo')))/'registry').resolve(strict=True)
    profile = {'format': 'yohaku-dev-runtime/1', 'toolchain': str(toolchain), 'registry': str(registry)}
    validate_profile(profile)
    return profile


def validate_profile(profile):
    if not isinstance(profile, dict) or set(profile) != {'format','toolchain','registry'} or profile['format'] != 'yohaku-dev-runtime/1':
        raise tools.ToolError('Development runtime is not prepared; click Develop in Techne')
    for key in ('toolchain', 'registry'):
        value = profile[key]
        if not isinstance(value, str) or not value.startswith('/') or '\0' in value:
            raise tools.ToolError('Invalid development runtime path')
    tc = Path(profile['toolchain']).resolve(strict=True)
    for executable in ('cargo', 'rustc'):
        p = tc/'bin'/executable
        if not p.is_file() or not os.access(p, os.X_OK):
            raise tools.ToolError('Rust toolchain needs bin/cargo and bin/rustc')
    if not (tc/'lib').is_dir(): raise tools.ToolError('Rust runtime libraries are missing')
    registry = Path(profile['registry']).resolve(strict=True)
    if not all((registry/part).is_dir() for part in ('src','cache','index')):
        raise tools.ToolError('Cargo registry cache is incomplete; build this installed Yohaku once before preparing development')
    return tc, registry


def runtime_mounts(entry):
    if entry['args'] not in [[action] for action in ACTIONS]:
        raise tools.ToolError('Development action must be check, test, build or preview')
    if entry['wayland'] != (entry['args'][0] == 'preview'):
        raise tools.ToolError('Only development preview uses a Wayland socket')
    try: profile = json.loads((tools.PACKAGE/PROFILE).read_text())
    except (OSError, ValueError) as e: raise tools.ToolError('Click Develop in Techne to prepare the Rust runtime first') from e
    tc, registry = validate_profile(profile)
    home = '/world/tools/state/yohaku-development/cargo'
    mounts = ['--ro-bind', str(tc), '/opt/yohaku/rust', '--ro-bind',
              str(tools.PACKAGE/'agent/yohaku_dev_runtime.py'), '/opt/yohaku/dev-runtime.py']
    for part in ('src','cache','index'):
        mounts += ['--ro-bind', str(registry/part), home+'/registry/'+part]
    env = {'PATH':'/opt/yohaku/rust/bin:/usr/bin:/bin', 'RUSTC':'/opt/yohaku/rust/bin/rustc',
           'CARGO_HOME':home, 'CARGO_TARGET_DIR':'/world/tools/state/yohaku-development/target',
           'CARGO_NET_OFFLINE':'true', 'CARGO_BUILD_JOBS':'2',
           'LD_LIBRARY_PATH':'/opt/yohaku/rust/lib', 'YOHAKU_DEVELOPMENT':'1'}
    return mounts, env


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.yohaku-prepare-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out: out.write(data); out.flush(); os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def snapshot_files(package):
    names = {'Cargo.toml','Cargo.lock','apply_update.py','update_manifest.json','run-yohaku'}
    for directory, pattern in [('src','*.rs'),('examples','*.rs'),('tests','*.rs'),('agent','*.py'),('agent','*.ps1')]:
        names.update(str(p.relative_to(package)) for p in (package/directory).rglob(pattern))
    names.update(p.name for pattern in ('README*.md','VERIFICATION*.md','LICENSE*') for p in package.glob(pattern) if p.is_file() and p.suffix != '.tex')
    manifest = json.loads((package/'update_manifest.json').read_text())
    names.update(item['path'] for item in manifest['files'] if item['path'].startswith('bin/'))
    names.add('config/shell.json')
    for directory in ('vendor',):
        names.update(str(path.relative_to(package)) for path in (package/directory).rglob('*') if path.is_file())
    names.update(name for name in ('bin/loom-linux-x86_64','bin/yohaku_workspace','bin/yohaku-tool-window') if (package/name).is_file())
    return sorted(names)


def prepare(root, workspace=None):
    from yohaku_agent import Workspace
    package = tools.PACKAGE
    profile = detect_runtime()  # Fail before changing the world if compiler/cache is missing.
    target = tools.inside(root, PROJECT)
    marker = tools.inside(root, INFO)
    guide_path = tools.inside(root, GUIDE)
    ws = workspace or Workspace(root, package/'bin/loom-linux-x86_64')
    if target.exists():
        if not marker.is_file(): raise tools.ToolError('Development directory already exists without a bootstrap record; it was left untouched')
        info = json.loads(marker.read_text())
        if info.get('format') != 'yohaku-development/1' or info.get('project') != PROJECT or not isinstance(info.get('text_files'),list):
            raise tools.ToolError('Invalid development record; existing files were left untouched')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix='.yohaku-dev-', dir=target.parent))
        text_files = []; total = 0; hashes = {}
        try:
            for name in snapshot_files(package):
                source = package/name
                # These are selected project sources, never user worlds, credentials or caches.
                if not source.is_file() or source.is_symlink() or not source.resolve().is_relative_to(package):
                    raise tools.ToolError('Project source is not a regular contained file: '+name)
                data = source.read_bytes(); total += len(data)
                if total > 64*1024*1024: raise tools.ToolError('Development source snapshot exceeds 64 MiB')
                dest = temporary/name; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)
                dest.chmod(0o755 if source.stat().st_mode & stat.S_IXUSR else 0o644)
                hashes[name] = hashlib.sha256(data).hexdigest()
                try: data.decode('utf-8')
                except UnicodeDecodeError: continue
                if len(data) <= 2*1024*1024: text_files.append(name)
            # The candidate starts with blank model identity and no inherited secret.
            default = {'protocol':'chat','base_url':'https://api.deepseek.com','model':'deepseek-flash',
                       'api_key_env':'DEEPSEEK_API_KEY','max_tokens':4096,'max_rounds':12,'timeout':120,
                       'name':'AI','personality':'','permissions':{'read':True,'write':True,'delete':True,'import':True,'run':True}}
            path = temporary/'config/ai.json'; path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(default,indent=2)+'\n'); text_files.append('config/ai.json')
            (temporary/'worlds/default').mkdir(parents=True)
            info = {'format':'yohaku-development/1','project':PROJECT,'state':'preparing',
                    'text_files':text_files,'snapshot_sha256':hashes,'guide':GUIDE,
                    'tools':[e['id'] for e in entries()],
                    'candidate':'tools/state/yohaku-development/target/debug/examples/yohaku_compositor'}
            temporary.rename(target)
            atomic(marker, (json.dumps(info,indent=2)+'\n').encode())
        finally:
            if temporary.exists(): shutil.rmtree(temporary)
    # Adoption is idempotent and uses the exact Rust workspace lock/watch machinery.
    for name in info['text_files']:
        if not isinstance(name,str) or not name or Path(name).is_absolute() or '..' in Path(name).parts:
            raise tools.ToolError('Invalid development text path')
        ws.execute({'command':'adopt','path':PROJECT+'/'+name})
    guide = '''# Yohaku development workspace

This is the editable source copy of Yohaku default. The running host application
is kept separate so an unsuccessful change does not replace the current app.

Read memory/development.json, then list files before editing. Sources live below
files/yohaku-default/. Every initially imported UTF-8 source has a Loom .tex
beside it. Edit the .tex via read_document/patch_document/write_document; Loom
generates the .rs/.py/.json output. Preserve notes and check sync errors. To add
a nested source: write_text the new file, then adopt_file it before further edits.

Useful files: config/shell.json.tex (default UI labels),
examples/yohaku_compositor.rs.tex (native desktop),
examples/yohaku_workspace/agent.rs.tex (Socius), src/workspace.rs.tex (files).

Discover registered tools using list_tools. yohaku-check compiles all targets;
yohaku-test runs offline core tests; yohaku-build builds the candidate desktop
and workspace CLI. Run one at a time. run_tool(id, wait=true) or
tool_status(wait=true) waits up to 30 seconds without extra model calls. If it
still reports running, continue waiting. Inspect exit_code and the log_path;
starting/running is not a passed build. The complete bounded run log can be read
using read_text. Repair errors and retry within the human's requested task.

yohaku-preview starts the built candidate inside the tool area with an empty
candidate world. GUI compatibility still needs a real local display test. It
does not replace the host or publish anything. Stop it before another tool run.

Rust and the existing dependency registry are read-only reused. Compiler outputs,
caches and logs remain in this world. No downloads during code execution. A
missing dependency is an actual offline build error; do not invent success.
Model calls stay in Socius outside the execution sandbox. No API key or original
user worlds were copied into the project. Keep factual design notes in memory/.
'''
    if not guide_path.exists(): atomic(guide_path, guide.encode())
    info['state'] = 'ready'; atomic(marker, (json.dumps(info,indent=2)+'\n').encode())
    atomic(package/PROFILE, (json.dumps(profile,indent=2)+'\n').encode())
    return {'event':'development','entries':entries(),'project':PROJECT,'guide':GUIDE,
            'text_files':len(info['text_files']), 'message':'Development copy prepared; read '+GUIDE+' in Chat'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True); parser.add_argument('mode',choices=['prepare'])
    args = parser.parse_args()
    try: print(json.dumps(prepare(tools.world(args.root)),ensure_ascii=False),flush=True)
    except (tools.ToolError,OSError,ValueError,KeyError) as e:
        print(json.dumps({'event':'error','text':str(e)},ensure_ascii=False),flush=True); return 1
    return 0

if __name__ == '__main__': sys.exit(main())
