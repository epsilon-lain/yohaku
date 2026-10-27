import http.client
import io
import json
import os
from pathlib import Path
import tempfile
import tomllib
import types
import unittest
from unittest.mock import patch

import yohaku_codex as codex
import yohaku_codex_linux as linux
import yohaku_codex_provider as provider

SYNTHETIC_KEY = 'fixture-only-not-a-real-key'


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='yohaku-provider-tests-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.home_patch = patch.object(Path,'home',return_value=self.base)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def test_missing_private_config_keeps_openai_without_global_config_access(self):
        self.assertEqual(provider.load(),{'active':'openai'})
        self.assertFalse((self.base/'.codex').exists())

    def test_private_switch_preserves_key_and_restricts_permissions(self):
        value = {'active':'deepseek','deepseek_key':SYNTHETIC_KEY}
        provider.save(value)
        self.assertEqual(provider.load(),value)
        self.assertEqual(provider.private_path().stat().st_mode & 0o777,0o600)
        self.assertEqual(provider.private_path().parent.stat().st_mode & 0o777,0o700)
        value['active'] = 'openai'
        provider.save(value)
        self.assertEqual(provider.load(),value)

    def test_private_config_rejects_symlinks_and_broad_permissions(self):
        provider.save({'active':'openai'})
        path = provider.private_path()
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            provider.load()
        path.unlink()
        path.symlink_to(self.base/'missing-target')
        with self.assertRaises(OSError):
            provider.load()
        path.unlink()
        path.parent.chmod(0o755)
        with self.assertRaises(ValueError):
            provider.save({'active':'openai'})

    def test_invalid_config_error_never_echoes_private_input(self):
        provider.save({'active':'deepseek','deepseek_key':'PRIVATE invalid value'})
        with self.assertRaises(ValueError) as caught:
            provider.load()
        self.assertNotIn('PRIVATE',str(caught.exception))
        with patch('sys.argv',['provider','configure-deepseek']),patch('sys.stdin',io.StringIO(SYNTHETIC_KEY)),patch('sys.stderr',io.StringIO()) as error:
            self.assertEqual(provider.main(),1)
        self.assertNotIn(SYNTHETIC_KEY,error.getvalue())

    def test_deepseek_launch_does_not_copy_openai_auth_or_inherit_secret(self):
        executable = self.base/'codex'
        executable.write_bytes(b'\x7fELF\x02\x01'+b'\0'*12+b'\x3e\x00')
        executable.chmod(0o700)
        provider.save({'active':'deepseek','deepseek_key':SYNTHETIC_KEY})
        child = types.SimpleNamespace()
        with patch.object(linux,'_safe_auth_copy') as copy_auth,patch.object(linux.subprocess,'Popen',return_value=child) as spawn,patch.dict(os.environ,{'UNRELATED_PRIVATE_TOKEN':'not-inherited'}):
            linux.launch(str(executable))
        self.addCleanup(linux.cleanup,child)
        copy_auth.assert_not_called()
        options = spawn.call_args.kwargs
        self.assertNotIn(SYNTHETIC_KEY,json.dumps(options,default=str))
        self.assertNotIn('UNRELATED_PRIVATE_TOKEN',options['env'])
        self.assertEqual(options['env'][provider.ENV_KEY],child.yohaku_provider_relay.token)
        config = tomllib.loads((Path(options['env']['CODEX_HOME'])/'config.toml').read_text())
        self.assertEqual(config['model'],'deepseek-flash')
        self.assertEqual(config['model_reasoning_effort'],'high')
        self.assertEqual(config['shell_environment_policy']['inherit'],'none')
        self.assertFalse(config['model_providers']['deepseek']['requires_openai_auth'])
        self.assertFalse(config['permissions']['yohaku-control']['network']['enabled'])
        self.assertEqual(config['permissions']['yohaku-control']['filesystem'][':root'],'deny')
        self.assertEqual(child.yohaku_info['provider'],'deepseek')

    def test_deepseek_turn_overrides_only_model_and_effort_and_emits_wire_evidence(self):
        class Peer:
            info = {'cwd':'/empty-control'}
            linux = True
            child = types.SimpleNamespace(yohaku_provider_relay=types.SimpleNamespace(evidence=lambda:[],configure_recovery=lambda *a:None,recovery=provider.Recovery()))

            def __init__(self):
                self.requests = []
                self.closed = False

            def request(self,method,parameters):
                self.requests.append((method,parameters))
                if method=='thread/start':
                    return dict(thread={'id':'fixture-thread'},activePermissionProfile={'id':'yohaku-control'})
                if method=='config/read':
                    return dict(config={'features':dict(shell_tool=False,apps=False,plugins=False)})
                if method=='turn/start':
                    return dict(turn={'id':'fixture-turn'})
                raise AssertionError(method)

            def receive(self,timeout):
                return dict(method='turn/completed',params=dict(threadId='fixture-thread',turn=dict(id='fixture-turn',status='completed')))

            def close(self):
                self.closed = True
                self.child.yohaku_provider_relay.recovery.finish_budget()

        peer = Peer()
        import yohaku_agent as agent
        tools = agent.Tools(lambda request:None)
        tools.bootstrap=lambda context:context
        tools.definitions=[]
        initial = dict(config=dict(codex_entry='fixture',model='saved-openai-model'),context=dict(root='/world'),prompt='Offline fixture')
        info = dict(provider='deepseek',model=provider.MODEL,models=[provider.MODEL],effort='high')
        events = []
        with patch.object(codex,'connect',return_value=(peer,info)):
            result = codex.run(initial,tools,events.append)
        turn = next(parameters for method,parameters in peer.requests if method=='turn/start')
        self.assertEqual((turn['model'],turn['effort']),('deepseek-flash','high'))
        self.assertEqual(turn['permissions'],'yohaku-control')
        self.assertEqual(initial['config']['model'],'saved-openai-model')
        self.assertEqual(result['provider_evidence'],[])
        self.assertEqual(events[-1]['event'],'provider_evidence')
        self.assertTrue(peer.closed)

    def test_deepseek_probe_cannot_replace_the_saved_openai_model(self):
        peer = types.SimpleNamespace(close=lambda:None)
        with patch('sys.argv',['codex','--entry','fixture','probe']),patch.object(codex,'connect',return_value=(peer,dict(provider='deepseek',model=provider.MODEL))),patch.object(codex.apps,'address_path',return_value=Path('/fixture/codex')),patch('sys.stdout',io.StringIO()) as output:
            self.assertEqual(codex.main(),0)
        result = json.loads(output.getvalue())
        self.assertEqual(result['event'],'codex')
        self.assertEqual(result['config']['protocol'],'codex-local')
        self.assertEqual(result['config']['codex_entry'],'/fixture/codex')

    def relay_request(self,relay,payload,token=None,path='/responses'):
        connection = http.client.HTTPConnection('127.0.0.1',relay.server.server_port,timeout=4)
        try:
            connection.request('POST',path,body=json.dumps(payload),headers={'Authorization':'Bearer '+(token or relay.token)})
            response = connection.getresponse()
            return response.status,response.read()
        finally:
            connection.close()

    def test_relay_forwards_only_fixed_https_and_records_real_sse_metadata(self):
        relay = provider.Relay(SYNTHETIC_KEY)
        self.addCleanup(relay.close)
        event = dict(type='response.completed',response=dict(model='deepseek-real-fixture',usage=dict(input_tokens=11,output_tokens=7,total_tokens=18),output='must-not-be-recorded'))
        wire = ('data: '+json.dumps(event)+'\n\n').encode()
        response = io.BytesIO(wire)
        response.status = 200
        response.getheader = lambda *args:'text/event-stream'
        with patch.object(provider,'ObservedHTTPS') as upstream:
            upstream.return_value.getresponse.return_value = response
            status,received = self.relay_request(relay,dict(model=provider.MODEL,reasoning=dict(effort='high'),input='private-prompt'))
            self.assertEqual(status,200)
            self.assertEqual(received,wire)
            self.assertEqual(upstream.call_args.args[1: ],('api.deepseek.com',))
            self.assertEqual(upstream.call_args.kwargs,{'timeout':120})
            self.assertEqual(upstream.return_value.request.call_args.args[:2],('POST','/responses'))
            self.assertEqual(upstream.return_value.request.call_args.kwargs['headers']['Authorization'],'Bearer '+SYNTHETIC_KEY)
        evidence = relay.evidence()
        self.assertEqual(evidence[0]['usage'],dict(input_tokens=11,output_tokens=7,total_tokens=18))
        self.assertEqual(evidence[0]['response_models'],['deepseek-real-fixture'])
        for private in (SYNTHETIC_KEY,relay.token,'private-prompt','must-not-be-recorded'):
            self.assertNotIn(private,json.dumps(evidence))

    def test_relay_rejects_wrong_capability_target_model_and_effort(self):
        relay = provider.Relay(SYNTHETIC_KEY)
        self.addCleanup(relay.close)
        valid = dict(model=provider.MODEL,reasoning=dict(effort='high'))
        with patch.object(provider,'ObservedHTTPS') as upstream:
            self.assertEqual(self.relay_request(relay,valid,token='wrong')[0],403)
            self.assertEqual(self.relay_request(relay,valid,path='/responses?redirect=bad')[0],404)
            self.assertEqual(self.relay_request(relay,dict(model='wrong',reasoning=dict(effort='high')))[0],400)
            self.assertEqual(self.relay_request(relay,dict(model=provider.MODEL,reasoning=dict(effort='low')))[0],400)
            upstream.assert_not_called()

    def test_relay_error_does_not_forward_provider_body_or_headers(self):
        relay = provider.Relay(SYNTHETIC_KEY)
        self.addCleanup(relay.close)
        response = types.SimpleNamespace(status=401,close=lambda:None)
        with patch.object(provider,'ObservedHTTPS') as upstream:
            upstream.return_value.getresponse.return_value = response
            status,body = self.relay_request(relay,dict(model=provider.MODEL,reasoning=dict(effort='high')))
        self.assertEqual(status,502)
        self.assertEqual(json.loads(body)['error']['kind'],'upstream_http')
        self.assertEqual(json.loads(body)['error']['upstream_http_status'],401)
        self.assertEqual(relay.evidence()[0]['http_status'],401)

    def test_catalog_is_limited_to_the_requested_provider_model(self):
        models = provider.catalog()['models']
        self.assertEqual([model['slug'] for model in models],['deepseek-flash'])
        self.assertFalse(models[0]['supports_search_tool'])
        self.assertFalse(models[0]['prefer_websockets'])


if __name__=='__main__':
    unittest.main()
