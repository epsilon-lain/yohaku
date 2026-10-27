"""Real Loom regression for explicit revision/selection refusal and continuation."""
from pathlib import Path
import os,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).parent))
import yohaku_agent as a
class EditContinuation(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)/'world'
  self.tools=a.Tools(a.Workspace(self.root,a.ROOT/'bin/loom-linux-x86_64',os.environ.get('YOHAKU_TEST_BIN')).execute)
  self.path=self.ok('create_document',name='probe.txt',body='中文 Alpha 😀\nEnglish draft\n',notes={'source_version':1,'writer':'fixture','summary':'preserve note'},node={'id':'edit-continuation','name':'probe','description':'test','links':[]})['source']
 def ok(self,tool_name,**args):
  r=self.tools.call(tool_name,args);self.assertTrue(r['ok'],r);return r['result']
 def args(self):
  r=self.ok('read_range',path=self.path,view='body',start_line=1,start_column=4,end_line=1,end_column=9)
  return dict(path=self.path,view='body',revision=r['revision'],start_line=r['start_line'],start_column=r['start_column'],end_line=r['end_line'],end_column=r['end_column'],expected=r['text'],text='Beta')
 def test_success_returns_new_whole_source_revision_for_next_edit(self):
  args=self.args();r=self.ok('edit_range',**args)
  self.assertEqual(r['previous_revision'],args['revision']);self.assertNotEqual(r['revision'],args['revision'])
  current=self.ok('read_range',path=self.path,view='body');self.assertEqual(current['revision'],r['revision'])
  second=self.ok('edit_range',path=self.path,view='body',revision=r['revision'],start_line=1,start_column=9,end_line=1,end_column=10,expected='😀',text='😀中')
  self.assertTrue(second['verified']);self.assertEqual(self.ok('read_text',path=self.path[:-4])['text'],'中文 Beta 😀中\nEnglish draft\n')
 def test_three_refusals_preserve_source_output_and_offer_explicit_recovery(self):
  args=self.args();source=self.root/self.path;output=self.root/self.path[:-4]
  for code in ['stale_revision','invalid_range','expected_mismatch']:
   bad=dict(args)
   if code=='stale_revision':bad['revision']='0'*64
   elif code=='invalid_range':bad['end_column']=999
   else:bad['expected']='wrong'
   before=(source.read_bytes(),output.read_bytes());r=self.tools.call('edit_range',bad)
   self.assertFalse(r['ok']);self.assertFalse(r['saved']);self.assertEqual(r['code'],code)
   self.assertEqual((r['path'],r['view'],r['revision']),(self.path,'body',args['revision']))
   self.assertEqual((source.read_bytes(),output.read_bytes()),before)
   current=self.ok(r['recovery']['tool'],**r['recovery']['arguments']);self.assertEqual(current['revision'],r['revision'])
  self.assertTrue(self.ok('edit_range',**self.args())['verified'])
 def test_metadata_changes_invalidate_body_revision(self):
  args=self.args();r=self.ok('read_document',source=self.path)
  self.ok('write_document',source=self.path,revision=r['revision'],text=r['text'].replace('preserve note','preserve note updated'),body_only=False)
  rejected=self.tools.call('edit_range',args);self.assertEqual(rejected['code'],'stale_revision')
  self.assertIn('preserve note updated',self.ok('read_document',source=self.path)['text'])
 def test_unknown_and_missing_arguments_do_not_dispatch(self):
  requests=[];t=a.Tools(lambda request:requests.append(request))
  r=t.call('edit_range',{'path':self.path,'view':'body','extra':1})
  self.assertFalse(r['ok']);self.assertFalse(r['saved']);self.assertIn('revision',r['missing']);self.assertEqual(r['unknown'],['extra']);self.assertEqual(requests,[])
if __name__=='__main__':unittest.main()
