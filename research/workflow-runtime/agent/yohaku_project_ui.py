"""Bound project UI RPC over inherited standard streams.

The GUI has no host filesystem, socket or mount authority. A trusted supervisor
passes one native Tools instance, world, project_id and action. Every operation
uses Tools.call and the existing persistent task facade; this module owns no task
state. RPC id is correlation only. Durable execution identity remains request_id.
"""
import collections
import copy
import hashlib
import json
import marshal
import os
from pathlib import Path
import re
import sys
import time

from yohaku_project_schema import TOOLS, identifier

FORMAT = 'yohaku-project-ui/1'
ALLOWED = frozenset(('project_describe', 'project_plan', 'task_submit', 'task_status',
                     'task_output', 'task_cancel', 'task_provenance'))
SCHEMAS = {row['name']: row['parameters'] for row in TOOLS if row['name'] in ALLOWED}
MAX_REQUEST = 65536
MAX_RESPONSE = 8 * 1024 * 1024
RECENT_IDS = 256


class BridgeFault(ValueError):
    def __init__(self, kind, message, **details):
        super().__init__(message)
        self.kind, self.details = kind, details

    def reply(self):
        return {'ok': False, 'kind': self.kind, 'error': str(self),
                'replay_allowed': False, **self.details}


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def _wire_id(value):
    if not isinstance(value, str) or re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', value) is None:
        raise BridgeFault('invalid_rpc_id', 'RPC id must be 1..128 ASCII identifier characters', executed=False)
    return value


def _task_id(value):
    if not isinstance(value, str) or re.fullmatch(r'[A-Za-z0-9_.:-]{1,256}', value) is None:
        raise BridgeFault('invalid_task_id', 'A returned opaque task id is required', executed=False)
    return value


def _request_id(value):
    if not isinstance(value, str) or re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', value) is None:
        raise BridgeFault('invalid_request_id', 'Stable request_id must use the existing task identifier contract', executed=False)
    return value


class BoundProjectBridge:
    """Only a trusted supervisor constructs this binding; wire arguments cannot."""
    def __init__(self, tools, project_id, action, *, world=None, audit=None):
        identifier(project_id, 'project_id'); identifier(action, 'action')
        bound = getattr(tools, 'host_world_root', None)
        if not bound:
            raise BridgeFault('native_world_required', 'The UI bridge requires bootstrapped native Tools')
        self.world = Path(bound).resolve(strict=True)
        if world is not None and Path(world).resolve(strict=True) != self.world:
            raise BridgeFault('world_binding_conflict', 'Tools and supervisor must name the same world')
        self.tools, self.project_id, self.action = tools, project_id, action
        self.audit = audit
        self.recent = collections.OrderedDict()

    def _audit(self, event, **fields):
        if self.audit is not None:
            try:
                self.audit(copy.deepcopy({'format': FORMAT, 'event': event,
                    'time_ns': time.time_ns(), 'project_id': self.project_id,
                    'action': self.action, **fields}))
            except Exception as exc:
                raise BridgeFault('bridge_audit_unavailable', 'Bridge evidence could not be saved; query the original task before any retry',
                                  outcome='unknown', replay_allowed=False, detail=type(exc).__name__) from exc

    def _scope(self, result, tool):
        if (not isinstance(result, dict) or result.get('format') != 'yohaku-task/1'
                or result.get('project_id') != self.project_id or result.get('action') != self.action):
            if tool == 'task_submit':
                raise BridgeFault('bridge_result_unknown', 'Submission did not confirm the bound task identity', outcome='unknown')
            raise BridgeFault('scope_denied', 'This task is not available through the bound project/action', executed=False)
        _task_id(result.get('task_id'))

    def _invoke(self, tool, args, *, known_task_id=None):
        try:
            reply = self.tools.call(tool, args)
        except Exception as exc:
            raise BridgeFault('tool_outcome_unknown', 'Tools did not return a complete receipt; query the original request_id',
                              outcome='unknown', detail=type(exc).__name__) from exc
        if not isinstance(reply, dict) or type(reply.get('ok')) is not bool:
            raise BridgeFault('tool_outcome_unknown', 'Tools returned no complete public receipt', outcome='unknown')
        if reply['ok'] and tool in ('task_status', 'task_submit'):
            self._scope(reply.get('result'), tool)
        if (tool == 'task_submit' and not reply['ok'] and reply.get('kind') == 'request_conflict'
                and reply.get('task_id') is not None and reply['task_id'] != known_task_id):
            raise BridgeFault('scope_denied', 'request_id was claimed by another bound operation', executed=False)
        value = reply.get('result') if isinstance(reply.get('result'), dict) else {}
        if (reply['ok'] and tool in ('task_output', 'task_cancel', 'task_provenance')
                and value.get('task_id') != args['task_id']):
            raise BridgeFault('bridge_result_unknown', 'Receipt belongs to another task identity', outcome='unknown')
        self._audit('tool_result', tool=tool, arguments=args, response=reply,
                    task_id=value.get('task_id'), request_id=value.get('request_id'),
                    event_seq=value.get('event_seq'), state=value.get('state'))
        return reply

    def _status(self, args, *, allow_missing=False):
        reply = self._invoke('task_status', args)
        if not reply['ok']:
            if allow_missing and reply.get('kind') == 'unknown_task':
                return None
            return reply
        result = reply['result']
        if (args.get('task_id') is not None and result.get('task_id') != args['task_id']) or (
                args.get('request_id') is not None and result.get('request_id') != args['request_id']):
            raise BridgeFault('bridge_result_unknown', 'Status receipt does not match the requested identity', outcome='unknown')
        return reply

    def _arguments(self, name, args):
        if not isinstance(args, dict) or set(args) - set(SCHEMAS[name]['properties']):
            raise BridgeFault('invalid_arguments', 'Use this tool schema; host paths and unknown fields are not accepted', executed=False)
        args = dict(args)
        if name in ('project_describe', 'project_plan', 'task_submit'):
            if args.get('project_id', self.project_id) != self.project_id:
                raise BridgeFault('scope_denied', 'project_id differs from the supervisor binding', executed=False)
            args['project_id'] = self.project_id
        if name in ('project_plan', 'task_submit'):
            if args.get('action', self.action) != self.action:
                raise BridgeFault('scope_denied', 'action differs from the supervisor binding', executed=False)
            args['action'] = self.action
        if name == 'task_submit':
            _request_id(args.get('request_id'))
        if name == 'task_status':
            if ('task_id' in args) == ('request_id' in args):
                raise BridgeFault('invalid_arguments', 'Query exactly one task_id or request_id', executed=False)
            if 'task_id' in args: _task_id(args['task_id'])
            else: _request_id(args['request_id'])
        if name in ('task_output', 'task_cancel', 'task_provenance'):
            _task_id(args.get('task_id'))
        return args

    def handle(self, message):
        """Return one envelope. Repeated RPC id never substitutes a cached status.

        A recent id with different arguments is rejected. An identical repeat is
        dispatched through the same real tool; task_submit deduplicates durably
        by request_id, including after the UI/bridge has been restarted. The 256
        entry wire-id history is not execution identity and owns no task state.
        """
        wire_id, duplicate, name, args = None, False, None, None
        try:
            if not isinstance(message, dict) or set(message) != {'id', 'tool', 'arguments'}:
                raise BridgeFault('invalid_envelope', 'Use exactly id/tool/arguments', executed=False)
            wire_id = _wire_id(message['id'])
            name = message['tool']
            if not isinstance(name, str) or name not in ALLOWED:
                raise BridgeFault('unsupported_ui_tool', 'This bridge exposes only its fixed project/task operations', executed=False)
            args = self._arguments(name, message['arguments'])
            signature = hashlib.sha256(canonical(message).encode('ascii')).hexdigest()
            previous = self.recent.get(wire_id)
            if previous is not None and previous != signature:
                raise BridgeFault('rpc_id_conflict', 'Recent RPC id already names different arguments; use a new correlation id', executed=False)
            duplicate = previous is not None
            self.recent[wire_id] = signature
            self.recent.move_to_end(wire_id)
            while len(self.recent) > RECENT_IDS:
                self.recent.popitem(last=False)
            self._audit('rpc_request', rpc_id=wire_id, tool=name, arguments=args, duplicate=duplicate)
            if name == 'task_status':
                reply = self._status(args)
            elif name == 'task_submit':
                # Check a reused request's scope before forwarding a submission.
                # Any missing/unknown ledger error except proven unknown_task is
                # returned unchanged. It is never permission to launch again.
                current = self._status({'request_id': args['request_id']}, allow_missing=True)
                if current is not None and not current['ok']:
                    reply = current
                else:
                    reply = self._invoke(name, args, known_task_id=(current or {}).get('result', {}).get('task_id'))
            elif name in ('task_output', 'task_cancel', 'task_provenance'):
                current = self._status({'task_id': args['task_id']})
                reply = current if not current['ok'] else self._invoke(name, args)
            else:
                reply = self._invoke(name, args)
        except BridgeFault as exc:
            reply = exc.reply()
            if exc.details.get('outcome') == 'unknown' and args and (args.get('request_id') or args.get('task_id')):
                key = 'request_id' if args.get('request_id') else 'task_id'
                reply['recovery'] = {'tool': 'task_status', 'arguments': {key: args[key]}}
        except (TypeError, ValueError, UnicodeError) as exc:
            reply = BridgeFault('invalid_message', 'RPC message cannot be represented by the public contract',
                                executed=False, detail=type(exc).__name__).reply()
        return {'id': wire_id, 'response': reply,
                'bridge': {'format': FORMAT, 'duplicate_rpc_id': duplicate,
                           'durable_submission_identity': 'request_id', 'recent_rpc_ids': RECENT_IDS}}


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError('non-finite JSON value')


def serve(reader, writer, tools, project_id, action, *, world=None, audit=None, bridge=None):
    """Serve binary child.stdout -> child.stdin pipes until EOF/broken delivery.

    The supervisor owns this function, not the sandboxed GUI. A dropped stream
    does not cancel or relaunch tasks. The UI reconnects and queries its original
    request_id. Oversize/incomplete frames close this connection without trying
    to interpret a remaining fragment as another request. Raw tool receipts go
    to audit; no credential/environment resources are opened for the GUI.
    """
    bridge = bridge or BoundProjectBridge(tools, project_id, action, world=world, audit=audit)
    summary = {'format': FORMAT, 'requests': 0, 'responses': 0, 'protocol_errors': 0,
               'exit_reason': 'eof', 'delivery_unknown': False, 'automatic_task_cancel': False}
    while True:
        line = reader.readline(MAX_REQUEST + 1)
        if not line:
            break
        summary['requests'] += 1
        terminal_frame = False
        value = None
        try:
            if not isinstance(line, bytes):
                raise ValueError('binary pipe required')
            if len(line) > MAX_REQUEST:
                terminal_frame = True
                reply = {'id': None, 'response': BridgeFault('message_too_large', 'RPC request exceeds 65536 bytes; connection closed', executed=False).reply()}
            elif not line.endswith(b'\n'):
                terminal_frame = True
                reply = {'id': None, 'response': BridgeFault('incomplete_message', 'EOF before complete JSON line; no operation dispatched', executed=False).reply()}
            else:
                value = json.loads(line.decode('utf-8'), object_pairs_hook=_no_duplicate_keys, parse_constant=_invalid_constant)
                reply = bridge.handle(value)
        except (ValueError, UnicodeError):
            reply = {'id': None, 'response': BridgeFault('invalid_json', 'RPC requires one strict UTF-8 JSON object per line', executed=False).reply()}
        if reply['response'].get('ok') is False:
            summary['protocol_errors'] += 1
        data = (canonical(reply) + '\n').encode('ascii')
        if len(data) > MAX_RESPONSE:
            args = value.get('arguments', {}) if isinstance(value, dict) else {}
            recovery = {key: args[key] for key in ('request_id', 'task_id') if key in args}
            reply = {'id': reply.get('id'), 'response': BridgeFault('response_too_large', 'Receipt exceeds UI transport limit; query through native task tools',
                      outcome='unknown', recovery={'tool': 'task_status', 'arguments': recovery}).reply()}
            data = (canonical(reply) + '\n').encode('ascii')
        try:
            written = writer.write(data)
            if written is not None and written != len(data):
                raise OSError('short response write')
            writer.flush()
        except (OSError, ValueError) as exc:
            summary.update(exit_reason='delivery_failed', delivery_unknown=True)
            try: bridge._audit('delivery_failed', rpc_id=reply.get('id'), detail=type(exc).__name__, recovery='Query original request_id; do not replay based on pipe failure')
            except BridgeFault: pass
            break
        summary['responses'] += 1
        if terminal_frame:
            summary['exit_reason'] = 'invalid_frame'
            break
    return summary


SENSITIVE = re.compile(r'(api[-_]?key|token|password|secret|authorization|cookie|credential|bearer|prompt|message|header)', re.I)


def public_argv(argv):
    """Preserve launch identity while withholding credential and prompt values."""
    output, hide_next = [], False
    for value in argv:
        if hide_next:
            output.append('[REDACTED]'); hide_next = False; continue
        if not isinstance(value, str):
            output.append('[INVALID]'); continue
        if value.startswith('-'):
            key, sep, body = value.partition('=')
            if SENSITIVE.search(key) or key in ('--prompt', '--system-prompt', '--message'):
                output.append(key + ('=[REDACTED]' if sep else ''))
                hide_next = not bool(sep)
                continue
        if value.startswith(('sk-', 'Bearer ', 'bearer ')) or SENSITIVE.search(value):
            output.append('[REDACTED]'); continue
        value = re.sub(r'(://)[^/@\s]+:[^/@\s]+@', r'\1[REDACTED]@', value)
        value = re.sub(r'([?&](?:api_key|token|secret|password)=)[^&\s]*', r'\1[REDACTED]', value, flags=re.I)
        output.append(value[:2048] + ('[TRUNCATED]' if len(value) > 2048 else ''))
    return output[:128]


def _file_identity(path):
    before = Path(path).stat()
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): h.update(block)
    after = Path(path).stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('file changed during capture')
    return {'bytes': after.st_size, 'sha256': h.hexdigest(),
            'device': after.st_dev, 'inode': after.st_ino, 'mtime_ns': after.st_mtime_ns}


def _start_token(text):
    # comm may contain spaces and parentheses; fields after its final ')' start at 3.
    tail = text.rpartition(')')[2].split()
    if len(tail) < 20: raise ValueError('incomplete proc stat')
    return tail[19]


def _process_identity(pid):
    base = Path('/proc') / str(pid)
    result = {'pid': pid}
    try:
        before = _start_token((base / 'stat').read_text())
        result.update(start=before, exe=os.readlink(base / 'exe'), cwd=os.readlink(base / 'cwd'),
            argv=public_argv((base / 'cmdline').read_bytes().decode('utf-8', 'replace').rstrip('\0').split('\0')),
            executable=_file_identity(base / 'exe'))
        after = _start_token((base / 'stat').read_text())
        current_exe = (base / 'exe').stat()
        if (before != after or os.readlink(base / 'exe') != result['exe']
                or (current_exe.st_dev, current_exe.st_ino) != (result['executable']['device'], result['executable']['inode'])):
            raise ValueError('process identity changed during capture')
        result['identity_confirmed'] = True
    except (OSError, ValueError) as exc:
        result.update(identity_confirmed=False, state='unknown', error=type(exc).__name__)
    return result


def capture_identity(pids=(), *, include_compositors=False, module_names=None):
    """Read-only Linux identity capture, invoked by the new worker itself.

    No environ is read. Module disk hashes are observed at capture time; in-memory
    function-code hashes are separate, never claimed equal to source-file hashes.
    A supervisor should freeze/check the source manifest before starting workers.
    """
    if not sys.platform.startswith('linux'):
        raise RuntimeError('Linux /proc identity capture only; no inference from Windows files')
    selected = {os.getpid()}
    for pid in pids:
        if type(pid) is not int or pid <= 0: raise ValueError('positive integer pid required')
        selected.add(pid)
    if include_compositors:
        for directory in Path('/proc').iterdir():
            if directory.name.isdigit():
                try:
                    if directory.joinpath('comm').read_text().strip() == 'yohaku_composit': selected.add(int(directory.name))
                except OSError: pass
    names = module_names or ('yohaku_agent', 'yohaku_projects', 'yohaku_project_schema',
        'yohaku_project_sources', 'yohaku_project_tasks', 'yohaku_project_ui')
    modules = []
    for name in names:
        module = sys.modules.get(name)
        if module is None:
            modules.append({'name': name, 'loaded': False}); continue
        file = getattr(module, '__file__', None)
        row = {'name': name, 'loaded': True, 'path': str(Path(file).resolve()) if file else None}
        try:
            row['disk_at_capture'] = _file_identity(file) if file else None
        except (OSError, ValueError) as exc: row['disk_error'] = type(exc).__name__
        h, count = hashlib.sha256(), 0
        for key, member in sorted(vars(module).items()):
            candidates = [(key, member)]
            if isinstance(member, type) and member.__module__ == name:
                candidates += [(key + '.' + k, getattr(v, '__func__', v)) for k, v in sorted(vars(member).items())]
            for label, item in candidates:
                code = getattr(item, '__code__', None)
                if code is not None and getattr(item, '__module__', None) == name:
                    h.update(label.encode('utf-8')); h.update(marshal.dumps(code)); count += 1
        row.update(in_memory_function_code_sha256=h.hexdigest(), functions_hashed=count)
        modules.append(row)
    return {'format': 'yohaku-linux-identity/1', 'observed_at_ns': time.time_ns(),
        'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'capturing_pid': os.getpid(), 'parent_pid': os.getppid(),
        'processes': [_process_identity(pid) for pid in sorted(selected)],
        'loaded_python_modules': modules, 'environ_read': False,
        'module_hash_semantics': 'disk_at_capture and in-memory function-code fingerprints are separate observations'}
