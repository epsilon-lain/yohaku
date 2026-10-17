import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
import yohaku_agent as agent


class Nodes(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='yohaku-nodes-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'world'
        self.tools = agent.Tools(agent.Workspace(self.root, agent.ROOT / 'bin/loom-linux-x86_64').execute)

    def call(self, tool, **args):
        reply = self.tools.call(tool, args)
        self.assertTrue(reply['ok'], reply)
        return reply['result']

    def node(self, identity, links=(), entry=False, filename=None):
        created = self.call('create_document', name=filename or identity+'.py', body='value = "旧 🧸"\r\n')
        source = created['source']
        doc = self.call('read_document', source=source)
        node = dict(id=identity, name='节点 '+identity, description='模块检索 '+identity, entry=entry,
                    links=[dict(relation=relation, target=target) for relation, target in links])
        note = '\n## AI 笔记\n' + chr(96)*3 + 'yaml\nsource_version: 1\nwriter: human\nsummary: keep me\n' + chr(96)*3 + '\n'
        text = doc['text'].replace('target: text', 'target: text\nnode: '+json.dumps(node, ensure_ascii=False), 1)+note
        self.call('write_document', source=source, revision=doc['revision'], text=text, body_only=False)
        return source

    def test_index_graph_bounds_cycles_duplicates_and_no_body(self):
        root = self.node('root', [('contains','module'),('contains','module'),('related','missing')], True)
        module = self.node('module', [('tests','test')])
        self.node('test', [('related','root')])
        entries = self.call('list_entry_nodes')['nodes']
        self.assertEqual([node['id'] for node in entries], ['root'])
        self.assertNotIn('body', entries[0])
        self.assertNotIn('links', entries[0])
        found = self.call('find_nodes', query='模块检索 module')['nodes'][0]
        self.assertEqual(found['location']['path'], module)
        self.assertNotIn('text', json.loads((self.root/'.yohaku/nodes.json').read_text())['nodes']['root'])
        node = self.call('get_node', id='root')['node']
        self.assertEqual(len(node['links']), 2)
        self.assertEqual(node['links'][1]['status'], 'missing')
        walked = self.call('walk_nodes', id='root', max_depth=8, limit=100)
        self.assertEqual([(item['node']['id'],item['depth']) for item in walked['nodes']], [('root',0),('module',1),('test',2)])
        self.assertTrue(self.call('walk_nodes',id='root',limit=1)['truncated'])
        self.assertTrue(self.call('walk_nodes',id='root',max_depth=0)['depth_limited'])
        self.node('module', filename='duplicate.py')
        rebuilt = self.call('rebuild_node_index')
        self.assertTrue(any(issue['kind']=='duplicate_id' for issue in rebuilt['issues']))
        self.assertFalse(self.tools.call('get_node',dict(id='module'))['ok'])
        self.assertEqual(self.call('get_node',id='root')['node']['links'][0]['status'],'ambiguous')
        self.assertEqual(len(self.call('walk_nodes',id='root')['nodes']),1)
        (self.root/root).unlink()
        self.assertEqual(self.call('list_entry_nodes')['nodes'],[])

    def test_existing_tex_register_edit_rebuild_and_stale_coordinates(self):
        source = self.node('root', [('related','absent')], True)
        original = (self.root/source).read_bytes()
        (self.root/'.yohaku/files.json').write_text(json.dumps({'format':'yohaku-workspace/0.1','files':[]}))
        located = self.call('list_entry_nodes')['nodes'][0]
        self.assertFalse(located['registered'])
        self.assertFalse(self.tools.call('read_range',located['location'])['ok'])
        self.call('adopt_file',path=located['location']['path'])
        self.assertEqual((self.root/source).read_bytes(),original)
        selected = self.call('read_range',path=source,view='body',start_line=1,start_column=10,end_line=1,end_column=11)
        self.assertEqual(selected['text'],'旧')
        edit = dict(path=source,view='body',revision=selected['revision'],start_line=1,start_column=10,end_line=1,end_column=11,expected='旧',text='你好')
        saved = self.call('edit_range',**edit)
        self.assertTrue(saved['verified'] and saved['loom']['ok'])
        self.assertFalse(self.tools.call('edit_range',edit)['ok'])
        current = self.call('read_document',source=source)
        self.assertIn('summary: keep me',current['text'])
        self.assertIn('"target": "absent"',current['text'])
        self.assertIn("macro: '[[macros/raw]]'",current['text'])
        self.assertEqual((self.root/'files/root.py').read_bytes(),'value = "你好 🧸"\r\n'.encode())
        self.assertNotEqual(current['revision'],selected['revision'])
        (self.root/'.yohaku/nodes.json').write_text('invalid cached index')
        self.assertEqual(self.call('rebuild_node_index')['node_count'],1)
        self.assertTrue(self.call('get_node',id='root')['node']['registered'])
        self.assertTrue(self.call('sync_document',source=source)['ok'])

    def test_registration_rejects_conflicts_invalid_sources_and_symlinks(self):
        source = self.node('root',entry=True)
        text = (self.root/source).read_text()
        (self.root/'files/other.tex').write_text(text)
        self.assertFalse(self.tools.call('adopt_file',dict(path='files/other.tex'))['ok'])
        (self.root/'files/broken.tex').write_text('human draft')
        self.assertFalse(self.tools.call('adopt_file',dict(path='files/broken.tex'))['ok'])
        self.assertEqual((self.root/'files/broken.tex').read_text(),'human draft')
        (self.root/'files/link.tex').symlink_to(self.root/source)
        self.assertFalse(self.tools.call('adopt_file',dict(path='files/link.tex'))['ok'])
        self.assertFalse(self.tools.call('adopt_file',dict(path='../escape.tex'))['ok'])
        self.assertEqual((self.root/source).read_text(),text)

    def test_limits_permissions_metadata_changes_and_mcp_discovery(self):
        self.node('root',entry=True)
        for args in [dict(id='root',max_depth=9),dict(id='root',limit=0),dict(id='root',limit=101),dict(id='root',max_depth=True)]:
            self.assertFalse(self.tools.call('walk_nodes',args)['ok'])
        restricted = agent.Tools(self.tools.execute,permissions={'read':False})
        self.assertFalse(restricted.call('get_node',dict(id='root'))['ok'])
        source = self.call('get_node',id='root')['node']['location']['path']
        doc = self.call('read_document',source=source)
        self.call('write_document',source=source,revision=doc['revision'],text=doc['text'].replace('节点 root','Renamed node'),body_only=False)
        self.assertEqual(self.call('find_nodes',query='renamed')['nodes'][0]['id'],'root')
        requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{}},
                  {'jsonrpc':'2.0','method':'notifications/initialized'},
                  {'jsonrpc':'2.0','id':2,'method':'tools/list'}]
        run=subprocess.run([sys.executable,str(agent.ROOT/'agent/yohaku_agent.py'),'--root',str(self.root),'--config',str(self.root/'no-model-config.json'),'mcp'],input='\n'.join(map(json.dumps,requests))+'\n',capture_output=True,text=True,check=True)
        names={item['name'] for item in json.loads(run.stdout.splitlines()[-1])['result']['tools']}
        self.assertTrue({'get_node','walk_nodes','read_range','edit_range'} <= names)


if __name__ == '__main__':
    unittest.main()

