import unittest,tempfile,json,sys,subprocess
from pathlib import Path
from unittest.mock import patch
import yohaku_agent as a
import yohaku_codex as c
import yohaku_codex_models as m
import yohaku_codex_provider as p

class ModelControlTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.path=Path(self.tmp.name)/'private/codex-provider.json'
  self.patch=patch.object(p,'private_path',return_value=self.path);self.patch.start();self.addCleanup(self.patch.stop)
  p.save({'active':'deepseek','deepseek_key':'synthetic-key-for-offline-only'})
  self.control=m.Control({'protocol':'codex-local','codex_entry':'offline','model':'legacy-model'})
  self.catalog={'provider':'openai','login':{'state':'signed_in','type':'chatgpt'},'models':[{'id':'gpt-6.1-sol'}]}
 def test_validated_selection_retains_key_and_next_turn(self):
  self.control.bind('deepseek','deepseek-flash')
  with patch.object(m,'probe',return_value=self.catalog):
   result=self.control.call('codex_model_select',{'provider':'openai','model':'gpt-6.1-sol'})
   state=self.control.call('codex_model_status',{})
  self.assertTrue(result['saved']);self.assertTrue(result['new_turn_required']);self.assertFalse(result['new_ui_session_required'])
  self.assertEqual(state['current_turn']['provider'],'deepseek');self.assertEqual(state['next_turn']['model'],'gpt-6.1-sol')
  self.assertIn('deepseek_key',p.load());self.assertNotIn('synthetic-key',json.dumps(state))
 def test_missing_model_never_saved_or_downgraded(self):
  before=self.path.read_bytes()
  with patch.object(m,'probe',return_value=self.catalog),self.assertRaisesRegex(ValueError,'absent'):
   self.control.call('codex_model_select',{'provider':'openai','model':'unlisted'})
  self.assertEqual(before,self.path.read_bytes())
 def test_login_required_keeps_selection(self):
  catalog=dict(self.catalog,login={'state':'not_signed_in'})
  with patch.object(m,'probe',return_value=catalog),self.assertRaisesRegex(ValueError,'login required'):
   self.control.call('codex_model_select',{'provider':'openai','model':'gpt-6.1-sol'})
  self.assertEqual(p.load()['active'],'deepseek')
 def test_catalog_failure_is_sanitized(self):
  with patch.object(m,'probe',side_effect=ValueError('synthetic-secret')):
   with self.assertRaises(ValueError) as got:self.control.call('codex_model_status',{})
  self.assertNotIn('synthetic-secret',str(got.exception))
 def test_stop_is_not_converted_to_tool_error(self):
  with patch.object(m,'probe',side_effect=c.CodexStopped('Codex turn stopped')):
   with self.assertRaises(c.CodexStopped):self.control.call('codex_model_status',{})
 def test_concurrent_selection_not_clobbered(self):
  before=p.load()
  def probe(*args):p.save(dict(before,openai_model='concurrent'));return self.catalog
  with patch.object(m,'probe',side_effect=probe),self.assertRaisesRegex(ValueError,'concurrently'):
   self.control.call('codex_model_select',{'provider':'openai','model':'gpt-6.1-sol'})
  self.assertEqual(p.load()['openai_model'],'concurrent')
 def test_private_schema_validates_model(self):
  p.save(dict(p.load(),openai_model='bad\nmodel'))
  with self.assertRaises(ValueError):p.load()
 def test_tools_scoped_to_codex_and_permissions(self):
  ordinary=a.Tools(lambda _:None)
  self.assertFalse(any(t['name'].startswith('codex_model_') for t in ordinary.definitions))
  ordinary.enable_model_management({'protocol':'chat'})
  self.assertFalse(any(t['name'].startswith('codex_model_') for t in ordinary.definitions))
  read=a.Tools(lambda _:None,permissions={'write':False})
  read.enable_model_management({'protocol':'codex-local'})
  self.assertIn('codex_model_status',{t['name'] for t in read.definitions})
  self.assertFalse(read.call('codex_model_select',{'provider':'openai','model':'gpt-6.1-sol'})['ok'])
  external=a.Tools(lambda _:None,native=False);external.enable_model_management({'protocol':'codex-local'})
  self.assertFalse(any(t['name'].startswith('codex_model_') for t in external.definitions))
 def test_official_close_handles_absent_relay(self):
  child=subprocess.Popen([sys.executable,'-c','import sys;sys.stdin.read()'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  child.yohaku_provider_relay=None
  c.Connection(child).close()
  self.assertEqual(child.returncode,0)

 def test_thread_confirmation_mismatch_stops_before_inference(self):
  import yohaku_codex_diagnostics as diagnostics
  for field,value in [('model','wrong-model'),('modelProvider','wrong-provider')]:
   class Peer:
    info={'cwd':'offline','provider':'openai','selected_model':'gpt-6.1-sol'}
    linux=True
    def __init__(self):self.calls=[];self.closed=False
    def request(self,method,args):
     self.calls.append(method)
     return {'thread':{'id':'fixture-thread'},'model':'gpt-6.1-sol','modelProvider':'openai',field:value}
    def close(self):self.closed=True
   peer=Peer();tools=a.Tools(lambda request:None,permissions={g:False for g in a.GROUPS})
   initial={'config':{'protocol':'codex-local','codex_entry':'offline'},'context':{},'prompt':'offline'}
   with patch.object(c,'connect',return_value=(peer,{'model':'gpt-6.1-sol','models':['gpt-6.1-sol']})),patch.object(diagnostics,'DIRECTORY',Path(self.tmp.name)/'diagnostics'):
    with self.assertRaisesRegex(c.CodexError,'different'):c.run(initial,tools,lambda event:None)
   self.assertNotIn('turn/start',peer.calls);self.assertTrue(peer.closed)

if __name__=='__main__':unittest.main()
