"""Fixed built-in Yohaku UI SDK import through Workspace and real Loom.

No caller-selected host path, backend argv or project execution is accepted. The
bundle is validated by real Loom in a private temporary directory. Destination
sources are created/synced only through the existing Workspace interface.
"""
import copy
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
import time
import uuid

from yohaku_project_schema import ProjectError
from yohaku_project_sources import Projects, contained, read_bytes, relative

VERSION = 'yohaku-ui/1'
FORMAT = 'yohaku-ui-sdk/1'
REGISTRY = 'memory/ui-sdk-imports.json'
REGISTRY_FORMAT = 'yohaku-ui-sdk-imports/1'
FILES = ('Cargo.toml', 'Cargo.lock', 'README.md', 'src/lib.rs', 'src/text.rs',
         'src/clipboard.rs', 'src/geometry.rs', 'src/button.rs', 'src/task.rs',
         'src/wayland.rs', 'src/task_rpc.rs', 'examples/offline.rs', 'examples/task-receipt.json',
         'tests/contracts.rs', 'tests/wayland_protocol.rs')
COMPONENTS = ('TextField', 'SelectableText', 'Clipboard', 'Button', 'Viewport', 'TaskView')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


class _ValidatedBundle:
    """Read adapter populated only by actual Loom inspect/build responses."""
    def __init__(self, documents, entries):
        self.documents = documents
        self.entries = entries

    def execute(self, request):
        if request['command'] == 'list':
            return {'files': list(self.entries.values())}
        if request['command'] == 'read':
            doc = self.documents[request['source']]
            return {'source': request['source'], 'valid': True,
                    'text': doc['original'], 'body': doc['body']}
        raise ProjectError('sdk_validator', 'Bundle validation adapter is read-only')


class UiSdk:
    def __init__(self, workspace, repository_root):
        self.workspace = workspace
        self.repository = Path(repository_root).resolve(strict=True)
        world = getattr(workspace, 'root', getattr(workspace, 'world', None))
        if world is None:
            raise ProjectError('sdk_world_required', 'A fixed Workspace world binding is required')
        self.world = Path(world).resolve(strict=True)
        self.projects = Projects(self.world, workspace=workspace)
        self._validation_generated = False

    def _execute(self, request):
        try:
            result = self.workspace.execute(request)
        except ProjectError:
            raise
        except Exception as exc:
            raise ProjectError('sdk_workspace_error', str(exc), operation=request['command'],
                               outcome='unknown', replay_allowed=False) from exc
        if not isinstance(result, dict):
            raise ProjectError('sdk_workspace_unknown', 'Workspace returned no structured receipt', replay_allowed=False)
        return result

    def _loom(self):
        value = getattr(self.workspace, 'loom', None) or os.environ.get('YOHAKU_NATIVE_LOOM')
        if value is None:
            package = getattr(self.workspace, 'package', None)
            if package is not None:
                value = Path(package) / 'loom.exe'
        if value is None:
            value = self.repository / 'bin/loom-linux-x86_64'
        binary = Path(value).resolve(strict=True)
        if not binary.is_file():
            raise ProjectError('sdk_loom_missing', 'SDK validation requires the installed actual Loom')
        return binary

    def _loom_call(self, binary, scratch, arguments, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProjectError('sdk_validation_timeout', 'Private SDK Loom validation exceeded its budget')
        environment = {'PATH': '/usr/bin:/bin', 'HOME': str(scratch), 'TMPDIR': str(scratch), 'LANG': 'C.UTF-8'}
        if os.name == 'nt':
            system = os.environ.get('SystemRoot', r'C:\Windows')
            environment.update(SystemRoot=system, WINDIR=system, TEMP=str(scratch), TMP=str(scratch),
                               PATH=str(binary.parent) + os.pathsep + str(Path(system) / 'System32'))
        try:
            result = subprocess.run([str(binary), *map(str, arguments), '--json'],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    cwd=scratch, env=environment, timeout=min(10, remaining),
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            value = json.loads(result.stdout.decode('utf-8'))
        except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired) as exc:
            raise ProjectError('sdk_validation_failed', 'Actual private Loom validation did not return a complete result',
                               detail=type(exc).__name__) from exc
        if result.returncode != 0 or value.get('ok') is not True:
            raise ProjectError('sdk_bundle_invalid', 'Actual Loom rejected the built-in SDK authority',
                               loom_error=value.get('error'), exit_code=result.returncode)
        return value

    def _bundle(self):
        self._validation_generated = False
        captured = {}
        for name in FILES:
            full = 'sdk/yohaku-ui/' + name
            captured[full + '.tex'] = read_bytes(self.repository, full + '.tex', limit=4 * 1024 * 1024)
            captured[full] = read_bytes(self.repository, full, limit=4 * 1024 * 1024)
        macro_name = 'macros/raw.source.md'
        macro = read_bytes(self.repository, macro_name, limit=256 * 1024)
        binary = self._loom()
        records = {}
        deadline = time.monotonic() + 40
        with tempfile.TemporaryDirectory(prefix='yohaku-sdk-validate-') as temporary:
            scratch = Path(temporary).resolve(strict=True)
            (scratch / 'macros').mkdir()
            (scratch / macro_name).write_bytes(macro)
            documents = {}
            entries = {}
            for name in FILES:
                full = 'sdk/yohaku-ui/' + name
                source = full + '.tex'
                destination = scratch / source
                destination.parent.mkdir(parents=True, exist_ok=True)
                # Copy existing authority only into private validation, never into a world.
                destination.write_bytes(captured[source])
                inspected = self._loom_call(binary, scratch, ['inspect', destination], deadline)['result']
                if inspected.get('original') != captured[source].decode('utf-8'):
                    raise ProjectError('sdk_bundle_conflict', 'SDK source changed during validation', source=source)
                header = inspected.get('header') or {}
                if header.get('target') != 'text' or header.get('macro') != '[[macros/raw]]' or (
                        (inspected.get('routing') or {}).get('output') != full):
                    raise ProjectError('sdk_bundle_invalid', 'Fixed SDK source changed its macro or output routing', source=source)
                built = self._loom_call(binary, scratch, ['sync', destination, '--root', scratch], deadline)
                self._validation_generated = True
                entries[source] = {'source': source, 'output': full,
                                   'last_sync': built}
                documents[source] = inspected
            adapter = _ValidatedBundle(documents, entries)
            validator = Projects(scratch, workspace=adapter)
            for name in FILES:
                full = 'sdk/yohaku-ui/' + name
                validated = validator._document(full + '.tex', entries)
                if validated['output_data'] != captured[full]:
                    raise ProjectError('sdk_bundle_drift', 'Built-in SDK generated file differs from its actual Loom authority',
                                       path=full, preserved=True,
                                       expected=validated['output_hash'], actual=sha(captured[full]))
                records[name] = {'body': validated['body'], 'notes': documents[full + '.tex'].get('ai_note') or {},
                                 'source_hash': validated['source_hash'], 'output_hash': validated['output_hash']}
        # Freeze the observed bundle across all validation subprocesses.
        for name, data in captured.items():
            if read_bytes(self.repository, name, limit=4 * 1024 * 1024) != data:
                raise ProjectError('sdk_bundle_conflict', 'Built-in SDK changed during private validation', path=name)
        if read_bytes(self.repository, macro_name, limit=256 * 1024) != macro:
            raise ProjectError('sdk_bundle_conflict', 'SDK macro changed during private validation')
        identity = sha(canonical({name: {'source': row['source_hash'], 'output': row['output_hash']}
                                  for name, row in records.items()}).encode('utf-8'))
        return records, identity

    def info(self):
        result = {'format': FORMAT, 'version': VERSION, 'package': 'yohaku-ui',
                  'components': list(COMPONENTS), 'features': ['default-std', 'task-json', 'wayland'],
                  'workflow': ['ui_sdk_prepare(project_root)', 'read returned authoritative sources',
                               'use returned Cargo path', 'project_plan/task_submit/task_status/task_output'],
                  'executed': False, 'project_code_executed': False,
                  'generated_in_private_validation': False,
                  'task_transport': {'module':'task_rpc', 'feature':'task-json or wayland',
                      'wire':'yohaku-project-ui/1 over inherited stdin/stdout',
                      'authority':'trusted launcher binds world/project/action; Tools/Control own task state',
                      'recovery':'query the original request_id after disconnect; no automatic submit replay'},
                  'lockfile_policy': {'bundled': 'Real Cargo.lock for the imported crate',
                      'application_workflow': 'Register the returned SDK root; use or add examples as applications',
                      'outer_application': 'A separate outer app requires its own authoritative Cargo.lock',
                      'automatic_lock_generation': False, 'cargo_path_implies_build_ready': False}}
        try:
            records, identity = self._bundle()
            result.update(available=True, bundle_hash=identity,
                          files=[{'path': name, 'source': 'sdk/yohaku-ui/' + name + '.tex',
                                  'source_hash': records[name]['source_hash'], 'output_hash': records[name]['output_hash']}
                                 for name in FILES],
                          authority={'ok': True, 'method': 'actual Loom inspect/sync and Projects source-map validation'})
        except (ProjectError, OSError) as exc:
            failure = exc.to_dict() if isinstance(exc, ProjectError) else {'kind': 'sdk_unavailable', 'error': str(exc)}
            result.update(available=False, authority=failure)
        result['generated_in_private_validation'] = self._validation_generated
        return result

    def _registry(self):
        file = contained(self.world, REGISTRY)
        if not file.exists():
            return {'format': REGISTRY_FORMAT, 'imports': {}}, None
        result = self._execute({'command': 'read_text', 'path': REGISTRY})
        text = result.get('text')
        try:
            value = json.loads(text)
        except (ValueError, TypeError) as exc:
            raise ProjectError('sdk_registry_invalid', 'SDK import registry is not JSON') from exc
        if not isinstance(value, dict) or set(value) != {'format', 'imports'} or (
                value['format'] != REGISTRY_FORMAT or not isinstance(value['imports'], dict)):
            raise ProjectError('sdk_registry_invalid', 'Unsupported SDK import registry')
        return value, text

    def _save(self, registry, expected, root):
        text = json.dumps(registry, ensure_ascii=False, indent=2) + '\n'
        self._execute({'command': 'write_text', 'path': REGISTRY, 'expected': expected, 'text': text})
        actual, actual_text = self._registry()
        if actual['imports'].get(root) != registry['imports'].get(root):
            raise ProjectError('sdk_registry_unknown', 'SDK import receipt changed before read-back; inspect before replay', replay_allowed=False)
        return actual, actual_text

    def _root(self, project_root):
        relative(project_root)
        if not project_root.startswith('files/') or len(project_root.encode('utf-8')) > 1800:
            raise ProjectError('invalid_path', 'SDK project_root must be a contained directory below files/')
        target = project_root + '/vendor/yohaku-ui'
        path = contained(self.world, target)
        if path.exists() and not path.is_dir():
            raise ProjectError('sdk_import_conflict', 'SDK destination root is already a file', path=target, preserved=True)
        return target

    def _partial(self, root, completed, remaining, error, *, retry=False, unknown=False, mutated=False):
        failure = error.to_dict() if isinstance(error, ProjectError) else {'kind': type(error).__name__, 'error': str(error)}
        return {'format': FORMAT, 'ok': False, 'root': root, 'sources': list(completed),
                'completed': list(completed), 'remaining': list(remaining), 'partial': bool(completed) or mutated,
                'unknown': unknown, 'retry_allowed': retry, 'replay_allowed': False,
                'failure': failure, 'executed': False, 'project_code_executed': False,
                'generated_in_private_validation': True, 'preserved': True}

    def prepare(self, project_root):
        root = self._root(project_root)
        sources = [root + '/' + name + '.tex' for name in FILES]
        records, identity = self._bundle()
        registry, expected = self._registry()
        old = registry['imports'].get(root)
        if old is not None and (not isinstance(old, dict) or old.get('bundle_hash') != identity):
            return self._partial(root, [], sources, ProjectError('sdk_version_conflict', 'Existing SDK import belongs to another bundle; no update or overwrite', preserved=True))
        record = old or {'version': VERSION, 'bundle_hash': identity, 'files': {}, 'pending': None}
        if set(record) != {'version', 'bundle_hash', 'files', 'pending'} or record.get('version') != VERSION or not isinstance(record.get('files'), dict) or set(record['files']) - set(FILES):
            raise ProjectError('sdk_registry_invalid', 'SDK import record has invalid fields or file receipts')
        for saved in record['files'].values():
            if (not isinstance(saved, dict) or set(saved) != {'source_hash', 'output_hash', 'output_exists', 'status'}
                    or not isinstance(saved.get('source_hash'), str) or not re.fullmatch('[0-9a-f]{64}', saved['source_hash'])
                    or type(saved.get('output_exists')) is not bool or saved.get('status') not in ('saved', 'complete')
                    or (saved['output_exists'] and (not isinstance(saved.get('output_hash'), str) or not re.fullmatch('[0-9a-f]{64}', saved['output_hash'])))
                    or (not saved['output_exists'] and saved.get('output_hash') is not None)):
                raise ProjectError('sdk_registry_invalid', 'SDK import file receipt is incomplete or invalid')
        if record.get('pending'):
            completed = [root + '/' + name + '.tex' for name in FILES if record['files'].get(name, {}).get('status') == 'complete']
            return self._partial(root, completed, [s for s in sources if s not in completed],
                                 ProjectError('sdk_import_unknown', 'A previous create has no confirmed import receipt; inspect its source and pending record before any retry', pending=record['pending']), unknown=True)
        completed = []
        entries = self.projects._entries()
        for name in FILES:
            source = root + '/' + name + '.tex'
            output = root + '/' + name
            saved = record['files'].get(name)
            source_path = contained(self.world, source)
            output_path = contained(self.world, output)
            if saved is None:
                if source_path.exists() or output_path.exists() or source in entries:
                    return self._partial(root, completed, [s for s in sources if s not in completed],
                                         ProjectError('sdk_import_conflict', 'Untracked source/output already exists; existing data was preserved', source=source, output=output))
                continue
            try:
                if sha(read_bytes(self.world, source)) != saved['source_hash']:
                    raise ProjectError('sdk_import_conflict', 'Imported authority was modified; no overwrite', source=source)
                if saved['output_exists'] and saved['output_hash'] != records[name]['output_hash']:
                    raise ProjectError('sdk_import_conflict', 'Recorded output does not match the fixed SDK bundle; no sync or overwrite',
                                       source=source, output=output, preserved=True)
                if not saved['output_exists'] and output_path.exists():
                    raise ProjectError('sdk_import_conflict', 'An output appeared after a recorded missing generation; no overwrite', output=output)
                if saved['output_exists'] and sha(read_bytes(self.world, output)) != saved['output_hash']:
                    raise ProjectError('sdk_import_conflict', 'Imported output was modified; no overwrite', output=output)
                if saved.get('status') == 'complete':
                    doc = self.projects._document(source, entries)
                    if doc['output_hash'] != records[name]['output_hash']:
                        raise ProjectError('sdk_import_conflict', 'Imported output no longer matches this bundle', source=source)
                    completed.append(source)
            except (ProjectError, OSError, KeyError) as exc:
                return self._partial(root, completed, [s for s in sources if s not in completed], exc)
        if len(completed) == len(FILES):
            return {'format': FORMAT, 'ok': True, 'root': root, 'sources': sources,
                    'cargo_path': 'vendor/yohaku-ui', 'bundle_hash': identity, 'duplicate': True,
                    'created_sources': [], 'reused_sources': sources, 'partial': False,
                    'executed': False, 'project_code_executed': False, 'generated_in_private_validation': True}
        registry['imports'][root] = record
        try:
            registry, expected = self._save(registry, expected, root)
        except ProjectError as exc:
            return self._partial(root, completed, [s for s in sources if s not in completed], exc, retry=True)
        created = []
        for name in FILES:
            source = root + '/' + name + '.tex'
            if source in completed:
                continue
            record = registry['imports'][root]
            saved = record['files'].get(name)
            try:
                if saved is None:
                    record['pending'] = {'source': source, 'operation': uuid.uuid4().hex}
                    registry, expected = self._save(registry, expected, root)
                    notes = copy.deepcopy(records[name]['notes'])
                    notes.setdefault('source_version', 1); notes.setdefault('writer', 'Yohaku SDK importer')
                    notes['summary'] = str(notes.get('summary', '')) + '\nImported by Yohaku UI SDK: ' + VERSION + '; upstream source sha256=' + records[name]['source_hash']
                    destination = PurePosixPath(root + '/' + name)
                    result = self._execute({'command': 'create', 'name': destination.name,
                                            'directory': destination.parent.as_posix(), 'body': records[name]['body'], 'notes': notes})
                    if result.get('source') != source:
                        raise ProjectError('sdk_create_unknown', 'Workspace create did not confirm the exact source', source=source)
                    current = self._execute({'command': 'read', 'source': source})
                    data = current.get('text')
                    if not isinstance(data, str) or data.encode('utf-8') != read_bytes(self.world, source):
                        raise ProjectError('sdk_create_unknown', 'Created source could not be confirmed by read-back', source=source)
                    output = contained(self.world, root + '/' + name)
                    output_existed = output.exists()
                    output_hash = sha(read_bytes(self.world, root + '/' + name)) if output_existed else None
                    if output_existed and output_hash != records[name]['output_hash']:
                        # Never adopt an intervening foreign output as a retry-authorizing receipt.
                        # Pending remains durable: the source exists, but this import cannot replay.
                        raise ProjectError('sdk_import_conflict', 'Created output differs from the fixed SDK bundle; no retry overwrite',
                                           source=source, output=root + '/' + name, preserved=True,
                                           source_saved=True, saved_revision=sha(data.encode('utf-8')))
                    record = registry['imports'][root]
                    record['files'][name] = {'source_hash': sha(data.encode('utf-8')), 'output_hash': output_hash, 'output_exists': output_existed, 'status': 'saved'}
                    record['pending'] = None
                    registry, expected = self._save(registry, expected, root)
                    created.append(source)
                else:
                    # Retry generation only for a recorded, byte-unchanged saved source.
                    self._execute({'command': 'sync', 'source': source})
                entries = self.projects._entries()
                doc = self.projects._document(source, entries)
                if doc['body'] != records[name]['body'] or doc['output_hash'] != records[name]['output_hash']:
                    raise ProjectError('sdk_generation_conflict', 'Destination Loom did not produce the fixed bundle content', source=source, preserved=True)
                record = registry['imports'][root]
                record['files'][name] = {'source_hash': doc['source_hash'], 'output_hash': doc['output_hash'], 'output_exists': True, 'status': 'complete'}
                registry, expected = self._save(registry, expected, root)
                completed.append(source)
            except (ProjectError, OSError, KeyError) as exc:
                pending = registry['imports'][root].get('pending') is not None
                uncertain = isinstance(exc, ProjectError) and exc.kind in ('sdk_workspace_error', 'sdk_workspace_unknown', 'sdk_registry_unknown')
                pending = pending or uncertain
                result = self._partial(root, completed, [s for s in sources if s not in completed], exc,
                                       retry=not pending, unknown=pending, mutated=True)
                result['saved_sources'] = [root + '/' + n + '.tex' for n in FILES if n in registry['imports'][root]['files']]
                return result
        return {'format': FORMAT, 'ok': True, 'root': root, 'sources': sources,
                'cargo_path': 'vendor/yohaku-ui', 'bundle_hash': identity, 'duplicate': False,
                'created_sources': created, 'reused_sources': [s for s in sources if s not in created],
                'partial': False, 'executed': False, 'project_code_executed': False,
                'generated_in_private_validation': True}
