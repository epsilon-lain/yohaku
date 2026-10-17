import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'agent'))
import yohaku_agent as agent


def main():
    parser = argparse.ArgumentParser(description='Import an isolated three-node demo through existing workspace tools')
    parser.add_argument('--root', type=Path, default=ROOT / 'worlds/demo')
    arguments = parser.parse_args()
    world = arguments.root.resolve()
    if (world / 'files/node-demo').exists():
        raise SystemExit('Demo target already exists; no files were replaced')
    workspace = agent.Workspace(world, ROOT / 'bin/loom-linux-x86_64')
    tools = agent.Tools(workspace.execute)

    def call(name, **values):
        result = tools.call(name, values)
        if not result['ok']:
            raise SystemExit(json.dumps(result))
        return result['result']

    workspace.execute({'command': 'list'})
    registry_path = world / 'memory/tools.json'
    registry = call('read_text', path='memory/tools.json') if registry_path.exists() else None
    current = json.loads(registry['text']) if registry else {'format': 'yohaku-tools/1', 'tools': []}
    if any(tool['id'] == 'node-demo-test' for tool in current['tools']):
        raise SystemExit('Demo tool ID already exists; no files were imported')
    index = call('rebuild_node_index')
    duplicates = {issue['id'] for issue in index['issues'] if issue['kind'] == 'duplicate_id'}
    for identity in ['demo:entry', 'demo:greeting', 'demo:test']:
        result = tools.call('get_node', {'id': identity})
        if result['ok'] or identity in duplicates:
            raise SystemExit('Demo node ID already exists; no files were imported')
        if 'Node ID is missing or ambiguous' not in result.get('error', ''):
            raise SystemExit(json.dumps(result))
    macro = 'macros/raw.source.md'
    macro_text = (ROOT / macro).read_text()
    if (world / macro).exists():
        if call('read_text', path=macro)['text'] != macro_text:
            raise SystemExit('Existing raw macro differs; it was left unchanged')
    else:
        call('write_text', path=macro, revision=None, text=macro_text)
    for source in sorted((ROOT / 'examples/node-demo').glob('*.tex')):
        path = 'files/node-demo/' + source.name
        call('write_text', path=path, revision=None, text=source.read_text())
        call('adopt_file', path=path)
        call('sync_document', source=path)
    current['tools'].append(dict(id='node-demo-test', name='Node demo test', program='/usr/bin/python3',
                                 args=['/world/files/node-demo/test_greet.py'], wayland=False))
    call('write_text', path='memory/tools.json', revision=registry['revision'] if registry else None,
         text=json.dumps(current, indent=2)+'\n')
    print(json.dumps(call('get_node', id='demo:entry'), ensure_ascii=False, indent=2))
    print('Imported three nodes and registered node-demo-test; no model request was made')


if __name__ == '__main__':
    main()
