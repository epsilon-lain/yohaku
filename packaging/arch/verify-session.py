"""Smoke-test the installed Arch package from a fresh graphical session."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


PROJECT = Path('/usr/lib/yohaku')
sys.path.insert(0, str(PROJECT / 'agent'))
from yohaku_agent import Tools, Workspace  # noqa: E402
from yohaku_session_startup import OUTPUT, seed  # noqa: E402


def call(tools, name, **arguments):
    response = tools.call(name, arguments)
    if not response['ok']:
        raise RuntimeError(f'{name} failed: {response}')
    return response['result']


def window_exists(title):
    result = subprocess.run(['xdotool', 'search', '--onlyvisible', '--name', title],
                            capture_output=True, text=True, timeout=5)
    return result.returncode == 0 and bool(result.stdout.strip())


def check_window(env, log, open_terminal):
    with log.open('wb') as output:
        session = subprocess.Popen(['/usr/bin/yohaku', '--backend', 'native'],
                                   env=env, stdout=output, stderr=subprocess.STDOUT)
        try:
            expected = f'open_terminal={str(open_terminal).lower()}'
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and session.poll() is None:
                text = log.read_text(errors='replace')
                if ('Yohaku session startup applied:' in text and expected in text
                        and window_exists('^Yohaku$')):
                    if window_exists('^Yohaku Terminal / same world session$') == open_terminal:
                        print(f'Installed session applied {expected}')
                        return
                time.sleep(0.2)
            raise RuntimeError(log.read_text(errors='replace')[-5000:])
        finally:
            if session.poll() is None:
                session.terminate()
                try:
                    session.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    session.kill()
                    session.wait(timeout=8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-only', action='store_true')
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='yohaku-arch-check-') as temporary:
        root = Path(temporary)
        runtime = root / 'runtime'
        runtime.mkdir(mode=0o700)
        data = root / 'data'
        world = data / 'yohaku/worlds/default'
        loom = PROJECT / 'bin/loom-linux-x86_64'
        env = dict(os.environ, XDG_CONFIG_HOME=str(root / 'config'),
                   XDG_DATA_HOME=str(data), XDG_RUNTIME_DIR=str(runtime),
                   LIBGL_ALWAYS_SOFTWARE='1', PATH='/usr/bin:/bin')
        env.pop('YOHAKU_WORKSPACE', None)
        env.pop('YOHAKU_LOOM', None)
        if arguments.workspace_only:
            seed(PROJECT, world, loom)
        else:
            check_window(env, root / 'first.log', False)

        tools = Tools(Workspace(world, loom).execute)
        entries = call(tools, 'list_entry_nodes')['nodes']
        startup = next(item for item in entries if item['id'] == 'desktop:session-startup')
        source = startup['location']['path']
        before = call(tools, 'read_document', source=source)
        call(tools, 'patch_document', source=source, revision=before['revision'],
             old='"open_terminal": false', new='"open_terminal": true', body_only=True)
        after = call(tools, 'read_document', source=source)
        assert after['revision'] != before['revision']
        assert json.loads((world / OUTPUT).read_text()) == {'open_terminal': True}

        if arguments.workspace_only:
            seed(PROJECT, world, loom)
        else:
            check_window(env, root / 'second.log', True)
        assert call(tools, 'read_document', source=source)['revision'] == after['revision']
        print(f'Loom source revision persisted: {after["revision"]}')


if __name__ == '__main__':
    main()
