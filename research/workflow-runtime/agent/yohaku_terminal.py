#!/usr/bin/env python3
"""World-scoped PTY service. Normal input/output is AI-readable, never secret input."""
import argparse
import base64
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import signal
import socket
import struct
import subprocess
import sys
import termios
import threading
import time
import uuid

import yohaku_tools as tools

# One 64 KiB page may need 6x JSON escaping plus base64; keep the
# transport bound above that worst case while bounding raw page size.
MAX_MESSAGE = 524288
OPERATIONS = {'terminal_start', 'terminal_write', 'terminal_read', 'terminal_status',
              'terminal_list', 'terminal_interrupt', 'terminal_close', 'terminal_resize'}
# Fixed launcher text, not a shell command. All caller values remain separate argv.
TTY_EXEC = """import os,fcntl,termios,sys
try: os.setsid()
except PermissionError: pass
fcntl.ioctl(0,termios.TIOCSCTTY,0)
os.tcsetpgrp(0,os.getpgrp())
os.execv(sys.argv[1],sys.argv[1:])
"""


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise tools.ToolError('Integer outside supported range')
    return value


def address(root):
    # Abstract sockets are isolated by the existing network namespace. No socket
    # under the writable /world mount can be replaced by the sandboxed program.
    return '\0yohaku-terminal-' + hashlib.sha256((str(os.getuid())+':'+str(root)).encode()).hexdigest()


class Session:
    def __init__(self, root, request):
        program = request.get('program', '/usr/bin/bash')
        argv = request.get('args', ['--noprofile', '--norc', '-i'] if program == '/usr/bin/bash' else [])
        cwd = request.get('cwd', 'files')
        directory = tools.inside(root, cwd)
        if not directory.is_dir():
            raise tools.ToolError('cwd must be an existing world directory')
        self.id = uuid.uuid4().hex
        entry = dict(id='term-'+self.id, name='Interactive terminal', program=program, args=argv, wayland=False)
        if program.startswith('builtin:'):
            raise tools.ToolError('Terminals accept existing system or world programs, not builtins')
        command = tools.command(root, entry)
        tools.check(root)  # Mandatory real sandbox preflight. No fallback.
        at = command.index('--chdir')
        command[at+1] = '/world/'+cwd
        at = command.index('--')
        command[at+1:at+1] = ['/usr/bin/python3', '-B', '-c', TTY_EXEC]
        self.cwd = '/world/'+cwd
        self.program = program
        self.kind = request.get('kind', 'shell' if program == '/usr/bin/bash' else 'program')
        if self.kind not in ('program', 'shell'):
            raise tools.ToolError('kind must be program or shell')
        self.lock = threading.Condition()
        self.size = 0
        self.input_pending = bytearray()
        self.discarded_input_bytes = 0
        self.complete = False
        self.closed = False
        self.exit_code = None
        self.launcher_exit_code = None
        self.evidence = 'pending'
        self.rows = integer(request.get('rows', 24), 2, 300)
        self.cols = integer(request.get('cols', 80), 2, 400)
        self.log_path, self.log = tools.create_log(root, entry['id'])
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', self.rows, self.cols, 0, 0))
        # Preserve LF and avoid echoing ordinary input twice. This does not make
        # the channel suitable for credentials: programs may still print input.
        attrs = termios.tcgetattr(slave)
        attrs[1] &= ~termios.ONLCR
        attrs[3] &= ~termios.ECHO
        termios.tcsetattr(slave, termios.TCSANOW, attrs)
        status_r, status_w = os.pipe()
        command[1:1] = ['--json-status-fd', str(status_w)]
        try:
            with tools.PinnedMounts(command, root) as pinned:
                self.child = subprocess.Popen(pinned.argv, stdin=slave, stdout=slave, stderr=slave,
                    pass_fds=[*pinned.fds, status_w], env={}, close_fds=True, start_new_session=True)
        except BaseException:
            os.close(self.master); os.close(status_r); self.log.close()
            raise
        finally:
            os.close(slave); os.close(status_w)
        os.set_blocking(self.master, False)
        threading.Thread(target=self.collect, args=(status_r,), daemon=True).start()

    def collect(self, status_r):
        def status_reader():
            documents = []
            with os.fdopen(status_r) as stream:
                # bubblewrap writes JSON objects (potentially multi-line).
                text = stream.read()
            decoder = json.JSONDecoder()
            while text.strip():
                try:
                    document, end = decoder.raw_decode(text.lstrip())
                except ValueError:
                    break
                documents.append(document); text = text.lstrip()[end:]
            with self.lock:
                for document in documents:
                    if type(document.get('exit-code')) is int:
                        self.exit_code = document['exit-code']
                        self.evidence = 'bubblewrap-json-status'
        reader = threading.Thread(target=status_reader, daemon=True); reader.start()
        try:
            while True:
                with self.lock: writers = [self.master] if self.input_pending else []
                readable, writable, _ = select.select([self.master], writers, [], .05)
                if writable:
                    with self.lock:
                        try:
                            count = os.write(self.master, self.input_pending)
                            del self.input_pending[:count]
                        except BlockingIOError: pass
                if not readable:
                    continue
                try:
                    data = os.read(self.master, 65536)
                except OSError as error:
                    if error.errno == errno.EIO: break  # PTY EOF, not process-exit evidence
                    if error.errno == errno.EAGAIN: continue
                    raise
                if not data: break
                with self.lock:
                    self.log.write(data); self.log.flush(); self.size += len(data)
                    self.lock.notify_all()
        except OSError:
            with self.lock: self.evidence = 'output-disconnected'
        finally:
            code = self.child.wait()
            reader.join()
            with self.lock:
                self.launcher_exit_code = code
                self.discarded_input_bytes = len(self.input_pending)
                self.input_pending.clear()
                self.complete = True
                self.lock.notify_all()

    def status(self):
        state = 'closed' if self.closed else ('exited' if self.complete and self.exit_code is not None else
                'unknown' if self.complete else 'running')
        return dict(session_id=self.id, cwd=self.cwd, program=self.program, kind=self.kind,
            state=state, running=not self.complete, exit_code=self.exit_code,
            exit_scope='session_program', command_exit_code=None, evidence=self.evidence,
            launcher_exit_code=self.launcher_exit_code, output_end=self.size,
            output_complete=self.complete, log_path=self.log_path, secret_input='disabled',
            input_pending_bytes=len(self.input_pending), discarded_input_bytes=self.discarded_input_bytes,
            rows=getattr(self,'rows',24), cols=getattr(self,'cols',80))

    def read(self, request):
        cursor = integer(request.get('cursor', 0), 0, self.size)
        limit = integer(request.get('max_bytes', 16384), 4, 65536)
        wait = integer(request.get('wait_ms', 0), 0, 1000)
        deadline = time.monotonic()+wait/1000
        while self.size == cursor and not self.complete and time.monotonic() < deadline:
            self.lock.wait(deadline-time.monotonic())
        data = os.pread(self.log.fileno(), min(limit, self.size-cursor), cursor)
        # Keep valid UTF-8 codepoints whole at page boundaries; base64 is exact
        # for arbitrary bytes and invalid UTF-8. Cursor always counts bytes.
        try: text = data.decode('utf-8')
        except UnicodeDecodeError as error:
            if error.reason == 'unexpected end of data' and (cursor+len(data) < self.size or not self.complete):
                data = data[:error.start]
            text = data.decode('utf-8', 'replace')
        return dict(self.status(), cursor=cursor, next_cursor=cursor+len(data), text=text,
                    data_base64=base64.b64encode(data).decode(), has_more=cursor+len(data)<self.size)

    def write(self, text):
        if not isinstance(text, str) or '\0' in text or len(text.encode()) > 8192:
            raise tools.ToolError('Ordinary input must be a string of at most 8192 UTF-8 bytes without NUL')
        if self.complete: raise tools.ToolError('Session process has ended')
        data = text.encode()
        # Queue whole UTF-8 messages; the writer owns byte-level partial writes.
        # This is a backpressure buffer, not a call/session budget.
        if len(self.input_pending)+len(data) > 65536:
            raise tools.ToolError('Input buffer busy; no bytes accepted; read status before continuing')
        self.input_pending.extend(data)
        return dict(self.status(), accepted_bytes=len(data), input_bytes=len(data))

    def resize(self, rows, cols):
        rows = integer(rows, 2, 300); cols = integer(cols, 2, 400)
        if self.complete: raise tools.ToolError('Session process has ended')
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
        self.rows, self.cols = rows, cols
        return dict(self.status(), resized=True)

    def interrupt(self):
        if self.complete: raise tools.ToolError('Session process has ended')
        # Kernel foreground process group, not a guessed PID or output marker.
        os.killpg(os.tcgetpgrp(self.master), signal.SIGINT)
        return dict(self.status(), interrupt_requested=True)

    def close(self):
        if not self.complete:
            self.child.kill()  # bwrap owns the PID namespace and reaps descendants
            self.child.wait()
        self.closed = True
        # Collector owns completion and final output; keep fd until it finishes.
        deadline = time.monotonic()+5
        while not self.complete and time.monotonic() < deadline: self.lock.wait(.05)
        if self.complete:
            os.close(self.master); self.log.close()
        return self.status()


class Service:
    def __init__(self, root):
        self.root = root; self.sessions = {}; self.instance = uuid.uuid4().hex

    def execute(self, request):
        operation = request.get('command')
        fields = {
            'terminal_start': {'program','args','cwd','kind','rows','cols'},
            'terminal_write': {'session_id','text'},
            'terminal_read': {'session_id','cursor','max_bytes','wait_ms'},
            'terminal_status': {'session_id'}, 'terminal_list': {'cursor','limit'},
            'terminal_interrupt': {'session_id'}, 'terminal_close': {'session_id'},
            'terminal_resize': {'session_id','rows','cols'}}
        for key in fields:
            if key not in ('terminal_start','terminal_list'): fields[key].add('service_instance')
        if request.get('service_instance') is not None and request['service_instance'] != self.instance:
            raise tools.ToolError('Terminal service instance changed; old attachment is invalid. Do not rerun.')
        if operation not in fields or set(request)-fields[operation]-{'command'}:
            raise tools.ToolError('Unknown terminal operation or argument')
        if operation == 'terminal_list':
            all_sessions = list(self.sessions.values())
            cursor = integer(request.get('cursor', 0), 0, len(all_sessions))
            limit = integer(request.get('limit', 50), 1, 100)
            end = min(cursor+limit, len(all_sessions))
            result = dict(sessions=[s.status() for s in all_sessions[cursor:end] if not s.closed],
                          cursor=cursor, next_cursor=end, has_more=end<len(all_sessions))
        elif operation == 'terminal_start':
            session = Session(self.root, request); self.sessions[session.id] = session
            result = session.status()
        else:
            session = self.sessions.get(request.get('session_id'))
            if session is None: raise tools.ToolError('Unknown session; no exit evidence. Do not automatically rerun.')
            with session.lock:
                if session.closed: raise tools.ToolError('Session is closed')
                if operation == 'terminal_read': result = session.read(request)
                elif operation == 'terminal_write': result = session.write(request['text'])
                elif operation == 'terminal_resize': result = session.resize(request['rows'], request['cols'])
                elif operation == 'terminal_interrupt': result = session.interrupt()
                elif operation == 'terminal_close': result = session.close()
                else: result = session.status()
        return dict(result, service_instance=self.instance, service_version=2)


def receive(stream):
    line = stream.readline(MAX_MESSAGE+1)
    if len(line) > MAX_MESSAGE: raise tools.ToolError('Terminal message too large')
    value = json.loads(line)
    if not isinstance(value, dict): raise tools.ToolError('Expected terminal request object')
    return value


def serve(root):
    # Lock is host-only via the existing read-only .yohaku mount in the sandbox.
    lock_path = tools.inside(root, '.yohaku/terminal.lock')
    fd = os.open(lock_path, os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC, 0o600)
    try: fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: os.close(fd); return
    service = Service(root)
    with socket.socket(socket.AF_UNIX) as server:
        server.bind(address(root)); server.listen()
        while True:
            connection, _ = server.accept()
            # Reply directly with sendall: no partial socket writes or buffered
            # makefile.__exit__ flush after a peer's BrokenPipeError.
            connection.settimeout(25)
            with connection, connection.makefile('rb') as stream:
                try:
                    _, uid, _ = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                    if uid != os.getuid(): raise tools.ToolError('Terminal service owner mismatch')
                    request = receive(stream)
                    response = dict(ok=True, result=service.execute(request))
                except (tools.ToolError, OSError, ValueError, KeyError, TypeError) as error:
                    response = dict(ok=False, error=str(error))
                try: connection.sendall((json.dumps(response, ensure_ascii=False)+'\n').encode())
                except OSError: pass  # A model/client disconnect never kills a session.


def call(root, request):
    """One request, no replay after send. Keep exact parameters and receipts."""
    root = tools.world(root)
    # Use the same pinned, exclusive, 0600 world-log creation as PTY output.
    # Every short-lived client gets its own file, also with an older live service.
    try:
        audit_path, audit = tools.create_log(root, 'terminal-rpc')
    except OSError as error:
        raise tools.ToolError('Terminal audit unavailable; no request sent') from error
    def record(event, **fields):
        audit.write((json.dumps(dict(format='yohaku-terminal-rpc/1',
            event=event, time_ns=time.time_ns(), **fields), ensure_ascii=False)+'\n').encode())
        audit.flush(); os.fsync(audit.fileno())
    connection = socket.socket(socket.AF_UNIX); connection.settimeout(25)
    dispatch_attempted = False
    try:
        data = (json.dumps(request, ensure_ascii=False)+'\n').encode()
        if len(data) > MAX_MESSAGE: raise tools.ToolError('Terminal message too large; no request sent')
        record('request', request=request, request_wire_sha256=hashlib.sha256(data).hexdigest())
        try: connection.connect(address(root))
        except ConnectionRefusedError:
            subprocess.Popen(['/usr/bin/python3','-B',str(Path(__file__).resolve()),'--root',str(root),'serve'],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env={}, close_fds=True, start_new_session=True)
            deadline = time.monotonic()+5
            while True:
                try: connection.connect(address(root)); break
                except ConnectionRefusedError:
                    if time.monotonic() > deadline: raise tools.ToolError('Terminal service unavailable; no request sent')
                    time.sleep(.05)
        with connection.makefile('rwb') as stream:
            record('dispatch_attempt')
            dispatch_attempted = True
            stream.write(data); stream.flush()
            response = receive(stream)
            if isinstance(response.get('result'), dict):
                response['result']['rpc_audit_path'] = audit_path
            try:
                record('response', response=response)
            except OSError:
                # The authoritative result is already known. Do not turn a saved
                # command into an unknown outcome or prompt any input replay.
                notice = 'Receipt received; audit write failed; do not replay'
                response.get('result', response)['rpc_audit_error'] = notice
            return response
    except (OSError, ValueError, tools.ToolError) as error:
        try:
            record('error', outcome='unknown' if dispatch_attempted else 'not_sent',
                exception_type=type(error).__name__)
        except OSError: pass
        if not dispatch_attempted:
            if isinstance(error, tools.ToolError): raise
            raise tools.ToolError('Terminal connection failed before dispatch; no request sent; audit='+audit_path) from error
        raise tools.ToolError('Terminal connection failed; outcome unknown; do not automatically rerun; audit='+audit_path) from error
    finally:
        connection.close()
        try: audit.close()
        except OSError: pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True); parser.add_argument('mode', choices=('serve','request'))
    args = parser.parse_args()
    try:
        root = tools.world(args.root)
        if args.mode == 'serve': serve(root); return 0
        response = call(root, receive(sys.stdin.buffer))
    except (tools.ToolError, OSError, ValueError) as error:
        response = dict(ok=False, error=str(error))
    print(json.dumps(response, ensure_ascii=False)); return 0 if response['ok'] else 1


if __name__ == '__main__': sys.exit(main())
