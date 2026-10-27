import contextlib
import http.server
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import yohaku_agent as agent
import yohaku_apps as apps
import yohaku_entries as entries


class EntryTests(unittest.TestCase):
    def test_private_reference_is_endpoint_bound_and_never_a_world_key(self):
        import yohaku_codex_provider as private
        configuration={'credential_source':'yohaku-private-deepseek'}
        with patch.object(private,'load',return_value={'deepseek_key':'TEST_ONLY'}) as load:
            self.assertEqual(entries.private_key(configuration,'https://api.deepseek.com/chat/completions'),'TEST_ONLY')
            for url in ('https://example.org','http://api.deepseek.com','https://api.deepseek.com:444'):
                with self.assertRaises(ValueError):entries.private_key(configuration,url)
            self.assertEqual(load.call_count,1)
        with patch.dict(os.environ,{'LOCAL_TEST_KEY':'LOCAL_ONLY'}):
            self.assertEqual(entries.private_key({'api_key_env':'LOCAL_TEST_KEY'},'https://example.org'),'LOCAL_ONLY')
        with self.assertRaises(ValueError):entries.private_key({'credential_source':'unknown'},'https://example.org')

    def test_world_connector_reload_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'memory').mkdir()
            path=root/'memory/socius.json'
            self.assertIsNone(entries.codex_entry(root))
            for address in ('/one/codex','/two/codex'):
                path.write_text(json.dumps({'codex_entry':address}))
                self.assertEqual(entries.codex_entry(root),address)
            for value in ('relative',False,'/bad\nentry'):
                path.write_text(json.dumps({'codex_entry':value}))
                with self.assertRaises(ValueError):entries.codex_entry(root)
            path.unlink();path.symlink_to(root/'outside')
            with self.assertRaises(ValueError):entries.codex_entry(root)

    def test_configured_codex_is_discovered_not_registered_or_executed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'memory').mkdir()
            executable=root/'codex';executable.write_bytes(Path('/usr/bin/true').read_bytes());executable.chmod(0o755)
            (root/'memory/socius.json').write_text(json.dumps({'codex_entry':str(executable)}))
            items=apps.discover(root,directories=[])
            self.assertEqual(len(items),1)
            self.assertEqual(items[0]['action'],'codex')
            self.assertFalse(items[0]['ready'])
            self.assertFalse((root/'memory/tools.json').exists())
            self.assertIn('unchanged',items[0]['reason'])

    def test_missing_configured_codex_does_not_hide_installed_native_connector(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'memory').mkdir()
            missing=root/'removed-extension/codex'
            (root/'memory/socius.json').write_text(json.dumps({'codex_entry':str(missing)}))
            binary=root/'current/codex';binary.parent.mkdir()
            binary.write_bytes(Path('/usr/bin/true').read_bytes());binary.chmod(0o755)
            with patch.object(apps,'linux_codex_candidates',return_value=[binary]),patch.object(apps,'windows_inventory',return_value=([],'')),patch.object(apps.shutil,'which',return_value=None),patch.object(apps.subprocess,'run') as execute:
                items=apps.discover(root)
                execute.assert_not_called()
            failed=next(item for item in items if item['address']==str(missing))
            self.assertFalse(failed['ready']);self.assertNotEqual(failed.get('action'),'codex')
            live=next(item for item in items if item['address']==str(binary))
            self.assertEqual(live['action'],'codex');self.assertIn('建设聊天',live['entry']['name'])
            self.assertFalse((root/'memory/tools.json').exists())

    def test_non_codex_configured_program_is_unavailable_not_executed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'memory').mkdir()
            (root/'memory/socius.json').write_text(json.dumps({'codex_entry':'/usr/bin/true'}))
            with patch.object(apps.subprocess,'run') as execute:
                items=apps.discover(root,directories=[])
                execute.assert_not_called()
            self.assertEqual(len(items),1);self.assertFalse(items[0]['ready'])
            self.assertNotEqual(items[0].get('action'),'codex')

    def test_deepseek_probe_emits_connection_not_global_switch(self):
        import yohaku_codex as codex
        with patch.object(codex,'connect',return_value=(unittest.mock.Mock(),{'provider':'deepseek','model':'fixture-model'})),patch.object(codex.apps,'address_path',return_value=Path('/fixture/codex')),patch.object(sys,'argv',['probe','--entry','/fixture/codex','probe']):
            output=io.StringIO()
            with contextlib.redirect_stdout(output):self.assertEqual(codex.main(),0)
            value=json.loads(output.getvalue())
            self.assertEqual(value['event'],'codex')
            self.assertEqual(value['config']['protocol'],'codex-local')

    def test_wire_codex_dispatch_preserves_native_tools(self):
        import yohaku_codex as codex
        initial={'config':{'protocol':'codex-local'},'context':{},'prompt':'offline only'}
        seen=[]
        def run(request,tools,emit):
            seen.append(request)
            self.assertIn('get_node',{item['name'] for item in tools.definitions})
            return {'history':[],'tool_calls':0}
        output=io.StringIO()
        with patch.object(codex,'run',side_effect=run),patch.object(agent.sys,'stdin',io.StringIO(json.dumps(initial)+'\n')),contextlib.redirect_stdout(output):agent.wire()
        self.assertEqual(len(seen),1)
        self.assertEqual(json.loads(output.getvalue())['event'],'done')


def serve():
    destination=Path(sys.argv[2])
    class Handler(http.server.BaseHTTPRequestHandler):
        rounds=[]
        def log_message(self,*arguments):pass
        def do_POST(self):
            value=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            self.rounds.append(value)
            if len(self.rounds)==1:
                message={'role':'assistant','content':None,'tool_calls':[{'id':'fixture-read','type':'function','function':{'name':'read_text','arguments':json.dumps({'path':'files/guide.txt'})}}]}
            else:
                result=next(item for item in value['messages'] if item.get('role')=='tool')
                parsed=json.loads(result['content'])
                assert parsed['ok'] and parsed['result']['text']=='offline native guide\n',parsed
                message={'role':'assistant','content':'OFFLINE_NATIVE_TOOL_ROUNDTRIP_OK'}
            payload=json.dumps({'choices':[{'message':message,'finish_reason':'tool_calls' if len(self.rounds)==1 else 'stop'}],'model':'offline-fixture','usage':{'total_tokens':0}}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
            destination.write_text(json.dumps({'requests':len(self.rounds),'path':self.path,'tool_returned':len(self.rounds)==2,'model_service_called':False}))
    server=http.server.HTTPServer(('127.0.0.1',0),Handler)
    print(server.server_port,flush=True)
    server.serve_forever()


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='serve':serve()
    else:unittest.main()
