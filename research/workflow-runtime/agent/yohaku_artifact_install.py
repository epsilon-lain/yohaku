"""Install one verified owned ELF without exporting bytes through model tools.

Version files are immutable. A project-scoped JSON entry is replaced only after
copy, fsync and read-back; launchers resolve that entry without executing here.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

from yohaku_apps import open_directory
from yohaku_project_consistency import Consistency, _artifact_open, _artifact_hash, MAX_ARTIFACT_BYTES
from yohaku_project_schema import ProjectError, identifier
from yohaku_project_sources import read_bytes
from yohaku_project_tasks import atomic, locked

FORMAT = 'yohaku-artifact-install/1'


class Installer:
    def __init__(self, projects, tasks):
        self.projects, self.tasks = projects, tasks
        self.world = projects.world

    def install(self, task_id, artifact_id):
        try:
            return self._install(task_id, artifact_id)
        except OSError as error:
            raise ProjectError('installation_io_failed', 'Host artifact installation I/O failed; inspect the current entry before retrying', detail=type(error).__name__) from error

    def _install(self, task_id, artifact_id):
        if os.name != 'posix':
            raise ProjectError('unsupported_platform', 'Artifact installation requires the native Linux host')
        consistency = Consistency(self.projects, self.tasks)
        record = consistency._task(task_id)
        receipt = record.get('receipt') or {}
        if (type(receipt.get('exit_code')) is not int or receipt['exit_code'] != 0
                or receipt.get('cleanup_confirmed') is not True or receipt.get('error') is not None
                or receipt.get('cancel_observed') is True):
            raise ProjectError('producer_not_succeeded', 'A successful target exit and confirmed cleanup are required')
        report = consistency.provenance(task_id)
        matches = [a for a in report['artifacts'] if a['id'] == artifact_id]
        if len(matches) != 1:
            raise ProjectError('unknown_artifact', 'Use one artifact ID returned by task_provenance for this task')
        artifact = matches[0]
        if not report['snapshot_valid'] or not artifact['valid'] or not artifact.get('actual_executable'):
            raise ProjectError('artifact_not_installable', 'The owned snapshot and executable artifact must still verify')
        source_fd = _artifact_open(self.tasks.work / task_id / 'output', artifact['path'])
        try:
            header = os.read(source_fd, 64)
        finally:
            os.close(source_fd)
        if header[:6] != b'\x7fELF\x02\x01' or header[18:20] != b'\x3e\x00':
            raise ProjectError('unsupported_executable', 'Minimal installer accepts x86_64 Linux ELF executables')
        project_id = identifier(record['project_id'], 'project_id')
        version = artifact['expected_sha256']
        base = 'tools/apps/project-' + project_id
        program = base + '/' + version + '/program'
        entry = {'format': FORMAT, 'project_id': project_id, 'task_id': task_id,
                 'artifact_id': artifact_id, 'snapshot_id': report['snapshot_id'],
                 'source_set': report['source_set'], 'sha256': version, 'bytes': artifact['bytes'],
                 'program': 'world:' + program, 'path': program}
        directory_fd = open_directory(self.world, ('tools', 'apps', 'project-' + project_id), create=True)
        # All destination operations stay under this host-pinned directory descriptor.
        pinned = Path('/proc/self/fd') / str(directory_fd) / '.'
        try:
            with locked(pinned / 'install.lock'):
                return self._commit(pinned, record, artifact, entry, base)
        finally:
            os.close(directory_fd)

    def _commit(self, pinned, record, artifact, entry, base):
        current = pinned / 'current.json'
        old = None
        if current.exists() or current.is_symlink():
            old = json.loads(read_bytes(str(pinned) + '/', 'current.json', limit=65536))
            if old.get('format') != FORMAT or old.get('project_id') != entry['project_id']:
                raise ProjectError('installation_conflict', 'Existing application entry is unrecognized; preserved')
        version = entry['sha256']
        destination = pinned / version
        reused = destination.exists() or destination.is_symlink()
        if reused:
            actual = _artifact_hash(str(pinned) + '/', version + '/program')
            if actual != {'sha256': version, 'bytes': entry['bytes'], 'executable': True}:
                raise ProjectError('installed_artifact_drift', 'Existing version changed; preserved without switching entry')
        else:
            # Source is opened from this task output, rejecting every symlink component.
            output = self.tasks.work / record['task_id'] / 'output'
            source_fd = _artifact_open(output, artifact['path'])
            staging = None
            try:
                before = os.fstat(source_fd)
                if not stat.S_ISREG(before.st_mode) or not before.st_mode & 0o111:
                    raise ProjectError('artifact_not_installable', 'Executable source changed before copying')
                staging = Path(tempfile.mkdtemp(prefix='.install-', dir=pinned))
                checksum, size, header = hashlib.sha256(), 0, b''
                with (staging / 'program').open('xb') as outgoing:
                    while True:
                        chunk = os.read(source_fd, 1024 * 1024)
                        if not chunk:
                            break
                        if not size:
                            header = chunk[:64]
                        size += len(chunk)
                        if size > MAX_ARTIFACT_BYTES:
                            raise ProjectError('artifact_scan_limit', 'Artifact grew beyond the bounded copy limit')
                        checksum.update(chunk)
                        outgoing.write(chunk)
                    outgoing.flush()
                    os.fchmod(outgoing.fileno(), 0o700)
                    os.fsync(outgoing.fileno())
                if header[:6] != b'\x7fELF\x02\x01' or header[18:20] != b'\x3e\x00':
                    raise ProjectError('unsupported_executable', 'Minimal installer accepts x86_64 Linux ELF executables')
                if size != entry['bytes'] or checksum.hexdigest() != entry['sha256']:
                    raise ProjectError('artifact_drift', 'Copied bytes differ from the verified task artifact')
                after = os.fstat(source_fd)
                identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode)
                if identity(before) != identity(after) or _artifact_hash(output, artifact['path']) != {
                        'sha256': entry['sha256'], 'bytes': size, 'executable': True}:
                    raise ProjectError('artifact_changed_during_read', 'Artifact changed while installing')
                if _artifact_hash(staging, 'program') != {'sha256': entry['sha256'], 'bytes': size, 'executable': True}:
                    raise ProjectError('installation_verification_failed', 'Installed bytes failed read-back')
                staging_fd = os.open(staging, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(staging_fd)
                finally:
                    os.close(staging_fd)
                os.rename(staging, destination)
                staging = None
                parent_fd = os.open(pinned, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(parent_fd)
                finally:
                    os.close(parent_fd)
            finally:
                os.close(source_fd)
                if staging is not None:
                    # Only remove our uncommitted, known single-file staging directory.
                    (staging / 'program').unlink(missing_ok=True)
                    staging.rmdir()
        # A durable per-binding receipt exists before the one atomic entry switch.
        binding = hashlib.sha256((entry['task_id'] + '\0' + entry['artifact_id']).encode()).hexdigest()
        receipt_name = 'receipt-' + binding + '.json'
        if (pinned / receipt_name).exists():
            if json.loads(read_bytes(str(pinned) + '/', receipt_name, limit=65536)) != entry:
                raise ProjectError('installation_conflict', 'Existing install receipt differs; preserved')
        else:
            atomic(pinned / receipt_name, entry)
        duplicate = old == entry
        if not duplicate:
            atomic(current, entry)
        return {**entry, 'installed': True, 'reused_version': reused, 'duplicate': duplicate,
                'entry_changed': not duplicate, 'entry_path': base + '/current.json',
                'receipt_path': base + '/' + receipt_name, 'executed': False,
                'previous_entry': old, 'replay_allowed': False}
