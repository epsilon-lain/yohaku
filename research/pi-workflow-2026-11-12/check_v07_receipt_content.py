"""No-network metadata counterexamples for the proposed v07 receipt correction.

Extract only verification_status and the pure lean_result serializer with AST.
Do not import uploaded runtime modules, controllers, native processes or models.
Native completion is stipulated as a fixture input; a synthetic confirmed owner
request contains the exact serialized returned tool output. The tested question
is what content that successful receipt can establish, not native execution.
"""
import argparse
import ast
import contextlib
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types

LEAN = None

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def digest(value):
    return sha(json.dumps(value,sort_keys=True,ensure_ascii=False).encode())

def extract(path,name,scope):
    tree=ast.parse(path.read_text())
    node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),scope)
    return scope[name]


TASK='model-task-'+'1'*32
PEER='model-task-'+'2'*32

def evaluate(path,kind='artifact',saved='PEER VERSION B',returned=None,complete=True,owner_confirmed=True,writer_revision='match'):
    returned=saved if returned is None else returned
    with tempfile.TemporaryDirectory(prefix='v07-metadata-')as directory:
        root=Path(directory)
        class FixturePath(type(root)):
            @classmethod
            def home(cls):
                return cls(root/'home')
        modelroot=FixturePath.home()/'.local/state/yohaku/model-tasks'
        toolroot=modelroot.parent/'adaption-tasks'/TASK
        toolroot.mkdir(parents=True);versions=root/'versions';versions.mkdir()
        v=versions/'peer.source';v.write_text(saved);revision=sha(saved.encode());source='files/p/peer.tex';reported=revision if writer_revision=='match'else writer_revision
        owner={'node_id':'lead','task_id':TASK,'binding':{'task_id':TASK,'node_id':'lead'}}
        peer={'node_id':'sol','task_id':PEER,'grant_id':'g','binding':{'task_id':PEER,'node_id':'sol'}}
        if kind.startswith('await'):
            args={'node_id':'sol','task_id':PEER};name='yohaku_ai_await_helper'
            ret={'task_id':PEER,'workflow_binding':peer['binding'],'classification':'completed','text':returned,'text_utf8_sha256':sha(saved.encode()),'text_complete':returned==saved}
        else:
            args={'source':source};name='yohaku_read_range'if kind=='read_range'else'yohaku_read_text'
            ret={'source':source,'revision':sha(returned.encode()),'text':returned}
        tool={'name':name,'call_id':'c','arguments':args,'result':{'ok':True,'result':ret}}
        toolpath=toolroot/(TASK+':tool:c.json');toolpath.write_text(json.dumps(tool))
        wire=json.dumps(LEAN(name,tool['result'],args),ensure_ascii=False)
        journal={'workflow_binding':owner['binding'],'confirmed':owner_confirmed,'request':{'input':[{'type':'function_call_output','call_id':'c','output':wire}]}}
        state={'helpers':{'h':{'node_id':'sol','owner':'lead'}},'starts':{'owner':owner,'peer':peer},'grants':{},'requests':{},'events':[
            {'kind':'tool_observed','payload':{'task_id':PEER,'name':'patch_document','ok':True,'source':source,'copied_source_sha256':revision,'version_copy':str(v),'result_sha256':'saved-peer','observed_revision':reported,'copied_source_matches_reported_revision':reported==revision if reported else None}},
            {'kind':'tool_observed','payload':{'task_id':TASK,'name':'read_text','ok':True,'source':source,'result_sha256':digest(tool['result']),'copied_source_sha256':revision,'observed_revision':sha(returned.encode()),'copied_source_matches_reported_revision':returned==saved}}
        ]}
        class Gate:
            policy={'world':str(root/'world'),'lead_node_id':'lead','artifact_versions':str(versions),'experiment_id':'metadata-fixture'}
            @contextlib.contextmanager
            def tx(self):yield state
            def check_actor(self,state,actor,binding):assert actor=='lead'
            def binding(self,op):return op['binding']
        def proof(actual,rounds,binding):
            out=json.dumps(LEAN(actual['name'],actual['result'],actual['arguments']),ensure_ascii=False)
            assert rounds[0][1]['workflow_binding']==binding
            assert rounds[0][1]['request']['input'][0]['output']==out
            return[{'confirmed_model_input':rounds[0][1]['confirmed'],'wire_output_sha256':sha(out.encode())}]
        def native(root,op,binding,world):
            return{'completed':complete,'private_task_record_verified':True,'terminal_confirmed':complete,'result_saved':complete,'visible_result_sha256':sha(saved.encode())},saved
        scope={'Path':FixturePath,'json':json,'_sha':sha,'_digest':digest,'_valid_task':lambda v:v in(TASK,PEER),'_load':lambda p:json.loads(Path(p).read_text()),'_unbox':lambda v:v.get('result',v),'_native':native,'_journal_rows':lambda root,task:[(toolpath,journal)],'_delivery_proof':proof}
        fn=extract(path,'verification_status',scope)
        result=fn(Gate(),'lead',owner['binding'])['participants'][0]
        return{'confirmed_deliveries':result['counts']['confirmed_owner_result_deliveries'],'scopes':[x['full_or_partial']for x in result['result_deliveries']],'returned_chars':[x['delivered_content_scope'].get('returned_chars')for x in result['result_deliveries']],'verified_saved_artifact_versions':result['counts']['verified_saved_artifact_versions']}


def main():
    global LEAN
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent-dir',type=Path,required=True,help='Original sealed agent source directory; read as source only')
    parser.add_argument('--candidate',type=Path,required=True,help='Suggested or isolated patched receipt module')
    parser.add_argument('--output',type=Path,help='Write JSON regression results here')
    args=parser.parse_args()
    original=args.agent_dir/'yohaku_review_receipts.py';fixed=args.candidate
    LEAN=extract(args.agent_dir/'yohaku_recovery.py','lean_result',{})
    module=types.ModuleType('yohaku_recovery');module.lean_result=LEAN;sys.modules['yohaku_recovery']=module
    cases=[
        ('stale_A_read_after_peer_B_current',{'returned':'OLD UNRELATED VERSION A'},0,None),
        ('unrelated_returned_text',{'returned':'UNRELATED CONTENT'},0,None),
        ('exact_visible_peer_artifact',{},1,'full'),
        ('ordinary_partial_read_unestablished',{'returned':'PEER'},0,None),
        ('empty_ordinary_read_unestablished',{'returned':''},0,None),
        ('short_await_full',{'kind':'await'},1,'full'),
        ('short_await_partial',{'kind':'await','returned':'PEER'},1,'partial'),
        ('long_await_lean_truncation',{'kind':'await','saved':'B'*15000},1,'partial'),
        ('unconfirmed_HTTP429_input',{'kind':'await','owner_confirmed':False},0,'full'),
        ('ordinary_full_raw_but_lean_truncated',{'saved':'B'*15000},0,None),
        ('read_range_with_sufficient_wire_limit',{'kind':'read_range','saved':'B'*15000},1,'full'),
        ('no_completed_peer',{'kind':'await','complete':False},0,None),
        ('writer_A_observed_current_B_read_B',{'writer_revision':sha(b'WRITER VERSION A')},0,None),
        ('missing_writer_reported_revision',{'writer_revision':None},0,None),
    ]
    records=[]
    for name,case_args,count,scope in cases:
        before=evaluate(original,**case_args);after=evaluate(fixed,**case_args)
        assert after['confirmed_deliveries']==count,(name,after)
        if scope is not None:assert after['scopes']==[scope],(name,after)
        records.append({'name':name,'original':before,'suggested':after,'passed':True})
    assert records[0]['original']['confirmed_deliveries']==1
    assert records[7]['original']['scopes']==['full']
    assert records[7]['suggested']['returned_chars']==[10000]
    assert records[-2]['original']['confirmed_deliveries']==1
    assert records[-2]['suggested']['verified_saved_artifact_versions']==0
    assert records[-1]['suggested']['verified_saved_artifact_versions']==0
    report={'format':'v07-receipt-content-metadata-regression/1','scope':'AST-extracted metadata function + actual pure lean_result only; native completion stipulated, exact owner wire delivery checked synthetically. No uploaded runtime imported or executed; no network/model/native process.', 'tests':len(records),'passed':True,'original_source_sha256':sha(original.read_bytes()),'suggested_source_sha256':sha(fixed.read_bytes()),'lean_result_source_sha256':sha((args.agent_dir/'yohaku_recovery.py').read_bytes()),'cases':records}
    if args.output:args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':True,'tests':len(records),'source':report['suggested_source_sha256']},ensure_ascii=False))

if __name__=='__main__':main()
