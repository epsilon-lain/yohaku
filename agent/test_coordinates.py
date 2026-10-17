import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).parent))
import yohaku_agent as agent
import yohaku_coordinates as coord


class Coordinates(unittest.TestCase):
    def test_unicode_crlf_and_exclusive_end(self):
        text='甲🧸e\u0301\r\n第二行\n'
        selected=coord.read(text,1,2,1,3)
        self.assertEqual(selected['text'],'🧸')
        self.assertEqual((selected['eof_line'],selected['eof_column']),(3,1))
        self.assertEqual(coord.replace(text,1,2,1,3,'🧸','猫'),'甲猫e\u0301\r\n第二行\n')
        self.assertEqual(coord.read(text,1,5,2,1)['text'],'\r\n')
        for line,col in [(1,6),(0,1),(1,0),(True,1),(1,True),(4,1)]:
            with self.assertRaises(ValueError):coord.read(text,line,col)

    def test_empty_document_insert_delete_and_multiline(self):
        self.assertEqual(coord.read('')['text'],'')
        self.assertEqual(coord.replace('',1,1,1,1,'','你好\n'),'你好\n')
        self.assertEqual(coord.replace('a\nb\nc',1,2,3,1,'\nb\n','!'),'a!c')
        self.assertEqual(coord.replace('abc',1,1,1,4,'abc',''),'')
        with self.assertRaises(ValueError):coord.replace('abc',1,3,1,2,'','x')
        with self.assertRaises(ValueError):coord.replace('abc',1,1,1,2,'b','x')

    def test_paging_and_bounds_are_explicit(self):
        text=''.join(str(i)+'\n' for i in range(100))
        first=coord.read(text)
        self.assertTrue(first['has_more']);self.assertEqual((first['end_line'],first['end_column']),(81,1))
        second=coord.read(text,first['end_line'],first['end_column'])
        self.assertEqual(first['text']+second['text'],text)
        with self.assertRaises(ValueError):coord.read('中'*(coord.MAX_RANGE_BYTES//3+1))


class WorldEditing(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'world'
        self.workspace=agent.Workspace(self.root,agent.ROOT/'bin/loom-linux-x86_64')
        self.tools=agent.Tools(self.workspace.execute)
    def call(self,tool,**args):
        result=self.tools.call(tool,args)
        self.assertTrue(result['ok'],result)
        return result['result']
    def create(self,body='print("重复")\r\nprint("重复")\r\n'):
        return self.call('create_document',name='coordinate-demo.py',body=body)['source']
    def edit_args(self,path,**extra):
        r=self.call('read_range',path=path,view='body',start_line=2,start_column=8,end_line=2,end_column=10)
        return dict(path=path,view='body',revision=r['revision'],start_line=2,start_column=8,end_line=2,end_column=10,expected=r['text'],text='你好🧸',**extra)
    def test_same_text_second_line_and_notes_preserved_with_real_loom(self):
        source=self.create()
        doc=self.call('read_document',source=source)
        note='\n## AI 笔记\n```yaml\nsource_version: 1\nwriter: human\nsummary: keep this note\n```\n'
        self.call('write_document',source=source,revision=doc['revision'],text=doc['text']+note,body_only=False)
        result=self.call('edit_range',**self.edit_args(source))
        self.assertTrue(result['verified'] and result['loom']['ok'])
        self.assertIn(note,(self.root/source).read_text())
        self.assertEqual((self.root/'files/coordinate-demo.py').read_bytes(),'print("重复")\r\nprint("你好🧸")\r\n'.encode())
        self.assertEqual(result['revision'],self.call('read_document',source=source)['revision'])
    def test_stale_revision_and_wrong_selection_leave_files_unchanged(self):
        source=self.create();args=self.edit_args(source)
        args['expected']='different'
        before=(self.root/source).read_bytes()
        self.assertFalse(self.tools.call('edit_range',args)['ok']);self.assertEqual((self.root/source).read_bytes(),before)
        args=self.edit_args(source)
        doc=self.call('read_document',source=source)
        self.call('write_document',source=source,revision=doc['revision'],text=doc['text']+'\n',body_only=False)
        before=(self.root/source).read_bytes()
        self.assertFalse(self.tools.call('edit_range',args)['ok']);self.assertEqual((self.root/source).read_bytes(),before)
    def test_plain_text_full_tex_invalid_tex_and_generated_output(self):
        self.call('write_text',path='memory/test.md',revision=None,text='A🧸\nB')
        r=self.call('read_range',path='memory/test.md',view='text')
        self.call('edit_range',path='memory/test.md',view='text',revision=r['revision'],start_line=1,start_column=2,end_line=1,end_column=3,expected='🧸',text='你好')
        self.assertEqual((self.root/'memory/test.md').read_text(),'A你好\nB')
        source=self.create();r=self.call('read_range',path=source,view='text',start_line=1,end_line=1)
        args=dict(path=source,view='text',revision=r['revision'],start_line=1,start_column=1,end_line=1,end_column=2,expected=r['text'][0],text='!')
        self.assertFalse(self.tools.call('edit_range',args)['ok'])
        output='files/coordinate-demo.py';r=self.call('read_range',path=output,view='text')
        result=self.tools.call('edit_range',dict(path=output,view='text',revision=r['revision'],start_line=1,start_column=1,end_line=1,end_column=2,expected='p',text='P'))
        self.assertFalse(result['ok']);self.assertIn('tex source',result['error'])
        (self.root/source).write_text('broken source')
        self.assertFalse(self.tools.call('read_range',{'path':source,'view':'body'})['ok'])
        self.assertEqual(self.call('read_range',path=source,view='text')['text'],'broken source')
    def test_native_delegation_uses_only_existing_rpc_tags_and_restores_active_name(self):
        source=self.create();tags=[];tools=None
        allowed={'read_document':{'read'},'write_document':{'read','save'}}
        def execute(request):
            tags.append((tools.active_name,request['command']))
            self.assertIn(request['command'],allowed[tools.active_name])
            return self.workspace.execute(request)
        tools=agent.Tools(execute)
        read=tools.call('read_range',{'path':source,'view':'body'})
        args=self.edit_args(source);args['revision']=read['result']['revision']
        result=tools.call('edit_range',args)
        self.assertTrue(result['ok'],result);self.assertIsNone(tools.active_name)
        self.assertIn(('write_document','save'),tags)
        self.assertNotIn('edit_range',{name for name,command in tags})
    def test_read_write_permission_and_bad_arguments_fail_before_saving(self):
        source=self.create();args=self.edit_args(source)
        for permissions in ({'read':False,'write':True},{'read':True,'write':False}):
            tools=agent.Tools(self.workspace.execute,permissions=permissions)
            self.assertFalse(tools.call('edit_range',args)['ok'])
        for key,value in [('start_line',True),('end_column',0),('view','pixels'),('path','../outside.tex')]:
            bad=dict(args);bad[key]=value
            self.assertFalse(self.tools.call('edit_range',bad)['ok'])
        self.assertEqual((self.root/'files/coordinate-demo.py').read_bytes(),'print("重复")\r\nprint("重复")\r\n'.encode())
    def test_race_between_read_and_write_is_rejected_by_rust(self):
        source=self.create();args=self.edit_args(source);edited=False
        def execute(request):
            nonlocal edited
            if request['command']=='save' and not edited:
                edited=True
                (self.root/source).write_bytes((self.root/source).read_bytes()+b'\n')
            return self.workspace.execute(request)
        result=agent.Tools(execute).call('edit_range',args)
        self.assertFalse(result['ok']);self.assertIn('changed',result['error'].lower())
        self.assertNotIn('你好'.encode(),(self.root/source).read_bytes())
    def test_readback_change_is_not_reported_as_success(self):
        source=self.create();args=self.edit_args(source);written=False
        def execute(request):
            nonlocal written
            result=self.workspace.execute(request)
            if request['command']=='save':
                written=True
                # A subsequent human edit is visible to the verification read.
                (self.root/source).write_bytes((self.root/source).read_bytes().replace('你好🧸'.encode(),'later'.encode()))
            return result
        result=agent.Tools(execute).call('edit_range',args)
        self.assertTrue(written);self.assertFalse(result['ok']);self.assertTrue(result['saved']);self.assertFalse(result['verified'])
    def test_cli_and_mcp_expose_same_coordinates_and_unicode(self):
        source=self.create();script=agent.ROOT/'agent/yohaku_text.py'
        command=[sys.executable,'-B',str(script),'--root',str(self.root)]
        read=subprocess.run(command+['read',source,'--view','body','--start','2:8','--end','2:10'],capture_output=True,text=True,check=True)
        r=json.loads(read.stdout)['result'];self.assertEqual(r['text'],'重复')
        write=subprocess.run(command+['replace',source,'--view','body','--start','2:8','--end','2:10','--revision',r['revision'],'--expected','重复','--text','中文🧸'],capture_output=True,text=True,check=True)
        self.assertTrue(json.loads(write.stdout)['result']['verified'])
        denied=subprocess.run(command+['replace',source,'--view','body','--start','2:8','--end','2:10','--revision',r['revision'],'--expected','重复','--text','bad'],capture_output=True,text=True)
        self.assertEqual(denied.returncode,1)
        requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{}},{'jsonrpc':'2.0','method':'notifications/initialized'},
            {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'read_range','arguments':{'path':source,'view':'body','start_line':2,'start_column':8,'end_line':2,'end_column':11}}}]
        replies=subprocess.run([sys.executable,'-B',str(agent.ROOT/'agent/yohaku_agent.py'),'--root',str(self.root),'--config',str(self.root/'no-model-config.json'),'mcp'],input='\n'.join(map(json.dumps,requests))+'\n',capture_output=True,text=True,check=True)
        answer=json.loads(json.loads(replies.stdout.splitlines()[-1])['result']['content'][0]['text'])
        self.assertEqual(answer['result']['text'],'中文🧸')


if __name__=='__main__':
    unittest.main()
