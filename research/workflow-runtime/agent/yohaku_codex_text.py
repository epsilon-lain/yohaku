"""codex-text/3: trusted host service; world documents are data, never code.
Transport delegates to existing Control/Rust authority. Journal records delivery,
not a second business state. Run only from the installed host with R/W/Run grant.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
from pathlib import Path
import re
import time
import uuid
from yohaku_codex_tasks import Control, atomic, state_root

VERSION = 'codex-text/3'
FEEDBACK_VERSION = 'save-feedback/2'
# /2 adds scoped diagnostics; all /1 receipt fields and control semantics remain.
FEEDBACK_COMPATIBILITY = ('save-feedback/1', FEEDBACK_VERSION)

def source_revision(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
SOURCE = 'files/codex-text/OPERATOR.md.tex'
ID = r'[A-Za-z0-9_.:-]{1,128}'
TERMINAL = {'done', 'error', 'cancelled', 'unknown'}

def parse(body):
    # Structural markers are exact standalone LF lines; escaped lines are data.
    lines = body.splitlines(keepends=True)
    markers = [('[input]', '[/input]'), ('[control]', '[/control]'), ('[result]', '[/result]')]
    spans = {}
    pos = 0
    for line in lines:
        token = line.rstrip('\n')
        if token in {x for pair in markers for x in pair}:
            if token in spans: raise ValueError('duplicate delimiter: ' + token)
            spans[token] = (pos, pos + len(line))
        pos += len(line)
    order = [x for pair in markers for x in pair]
    if set(spans) != set(order) or [x for x,_ in sorted(spans.items(),key=lambda x:x[1][0])] != order:
        raise ValueError('expected exactly input/control/result in order; escape literal markers')
    regions = {}
    for opening, closing in markers:
        regions[opening[1:-1]] = (spans[opening][1], spans[closing][0])
    raw = body[slice(*regions['input'])]
    # Remove exactly one framing LF; all other whitespace is prompt data.
    raw = raw[:-1] if raw.endswith('\n') else raw
    prompt = '\n'.join(line[1:] if line.startswith('\\') else line for line in raw.split('\n'))
    control = body[slice(*regions['control'])].strip()
    if control not in ('draft', 'ka', 'stop') and not re.fullmatch(r'(ka|status|stop) ' + ID, control):
        raise ValueError('invalid control; use draft, ka or stop')
    return {'prompt':prompt, 'control':control, 'regions':regions}

def splice(body, regions, changes):
    for key in sorted(changes, key=lambda k:regions[k][0], reverse=True):
        start,end = regions[key]
        body = body[:start] + changes[key] + body[end:]
    return body

def encode_result(value):
    # JSON escapes embedded newlines, so model output cannot manufacture delimiters.
    return json.dumps(value,ensure_ascii=False,indent=2) + '\n'

class Operator:
    def __init__(self, world, execute, transport=None, journal=None, source=SOURCE):
        self.world = str(Path(world).resolve())
        self.source = source
        if source != SOURCE and not re.fullmatch(r'files/codex-text/operators/[A-Za-z0-9_-]+[.]md[.]tex', source):
            raise ValueError('source outside registered operator directory')
        self.execute = execute
        self.transport = transport or Control(world)
        self.journal = journal or state_root()/('text-'+hashlib.sha256((self.world if self.source==SOURCE else self.world+'\n'+self.source).encode()).hexdigest()+'.json')

    @contextlib.contextmanager
    def lock(self):
        self.journal.parent.mkdir(parents=True,exist_ok=True)
        with open(str(self.journal)+'.lock','a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            yield

    def load(self):
        return json.loads(self.journal.read_text()) if self.journal.exists() else {'version':VERSION,'bindings':{},'pending':None,'selected':None}

    def save(self, journal): atomic(self.journal,journal)

    def receipt(self, saved_revision):
        # Delivery evidence lives in the existing journal, never business status.
        journal = self.load()
        value = {'feedback_version':FEEDBACK_VERSION, 'saved_revision':saved_revision,
                 'submission':'pending_confirmation', 'execution_status':'unknown',
                 'replay_allowed':False, 'query':{'tool':'read_document','source':self.source}}
        for rid,binding in journal['bindings'].items():
            for operation in binding.get('operations',[]):
                if operation['source_revision'] == saved_revision:
                    value.update(operation, request_id=rid,
                                 submission=(operation.get('submission') or ('accepted' if operation['action']=='ka' and binding['delivery']=='accepted' else 'pending_confirmation')),
                                 delivery=binding['delivery'])
                    return value
        pending = journal.get('pending')
        if pending and source_revision(pending['source_text']) == saved_revision:
            value.update(request_id=pending['request_id'], action=pending['action'])
        return value

    def read(self):
        doc = self.execute({'command':'read','source':self.source})
        if not doc.get('valid'): raise ValueError('operator tex invalid; nothing dispatched')
        output = self.execute({'command':'read_text','path':self.source[:-4]})
        if output['text'] != doc['body']: raise ValueError('Loom output differs; nothing dispatched')
        return doc, parse(doc['body'])

    def write(self, doc, parsed, changes):
        updated = splice(doc['body'],parsed['regions'],changes)
        if updated == doc['body']: return
        result = self.execute({'command':'save','source':self.source,'expected':doc['text'],'text':updated,'body_only':True})
        if result.get('sync_error') or result.get('loom',{}).get('ok') is False:
            raise ValueError('source saved but Loom failed; inspect before continuing')

    def project(self, rid, actual, journal):
        # Read-only projection, same authority as chat-task-summary; no business state.
        path='files/codex-text/details/'+rid+'.json.tex'
        payload={'version':VERSION,'request_id':rid,'actual':actual,
                 'history':list(journal['bindings']),
                 'diagnostics':journal['bindings'].get(rid,{}).get('diagnostics',[]),
                 'legacy_notice':journal['bindings'].get(rid,{}).get('notice')}
        body=encode_result(payload)
        target=Path(self.world)/path
        if target.exists():
            detail=self.execute({'command':'read','source':path})
            if detail['body']!=body:
                result=self.execute({'command':'save','source':path,'expected':detail['text'],'text':body,'body_only':True})
                if result.get('sync_error') or result.get('loom',{}).get('ok') is False:
                    raise ValueError('Detail Loom sync failed; no successful projection')
        else:
            result=self.execute({'command':'create','name':rid+'.json','directory':'files/codex-text/details',
                          'body':body})
            if result.get('sync_error') or result.get('loom',{}).get('ok') is False:
                raise ValueError('Detail Loom sync failed; no successful projection')
        value={'version':VERSION,'status':actual.get('status','unknown'),
               'request_id':rid,'object':actual.get('object'),'task_id':actual.get('task_id'),
               'status_source':actual.get('status_source','Rust chat object'),
               'reply':actual.get('output','')[:4000],
               'reply_truncated':len(actual.get('output',''))>4000,
               'error':('' if actual.get('status')=='cancelled' and actual.get('error')=='stop'
                        else str(actual.get('error') or '')[:300]), 'details':path}
        operations=journal['bindings'].get(rid,{}).get('operations',[])
        if operations:
            operation=operations[-1]
            value.update(self.receipt(operation['source_revision']))
            value['execution_status']=actual.get('status','unknown')
            if operation.get('action')=='stop':
                value['cancel_confirmed']=bool(operation.get('cancel_confirmed') is True
                    and actual.get('status')=='cancelled' and actual.get('execution')=='ended')
        # Only the latest operation's diagnostic may guide the current action.
        # Legacy request-wide notices remain in details, without invented attribution.
        for diagnostic in journal['bindings'].get(rid,{}).get('diagnostics',[]):
            evidence=self.receipt(diagnostic['source_revision'])
            if evidence['submission']=='accepted' and diagnostic['submission']=='pending_confirmation' and diagnostic.get('delivery_uncertainty'):
                diagnostic['resolved_by']='accepted'
            if operations and diagnostic['source_revision']==operations[-1]['source_revision'] and not diagnostic.get('resolved_by'):
                value['notice']=diagnostic['message']
                value['notice_revision']=diagnostic['source_revision']
        return encode_result(value)

    def status(self, rid):
        if hasattr(self.transport, 'object'):
            original = self.transport.object.request(rid)
            binding = self.load()['bindings'][rid]
            if original['prompt'] != binding['prompt']: raise ValueError('host request_snapshot_conflict; no retry or clear')
        result = self.transport.call('codex_task_status',{'request_id':rid,'max_chars':16384})
        output = result.get('output','')
        while result.get('has_more'):
            page = self.transport.call('codex_task_status',{'request_id':rid,'cursor':result['next_cursor'],'max_chars':16384})
            if page['next_cursor'] <= result['next_cursor']: raise ValueError('nonadvancing output cursor')
            output += page.get('output','');result=page
        return dict(result,output=output)

    def tick(self):
        try:
            return self._tick()
        except Exception as error:
            # Preserve source/control and pending on failure. Publish transport/CAS
            # uncertainty when the current document is still parseable.
            try:
                with self.lock():
                    doc,parsed=self.read()
                    journal=self.load()
                    self.report_error(doc,parsed,journal,'operation unresolved: '+str(error),(journal.get('pending') or {}).get('request_id') or journal['selected'])
            except Exception:
                pass  # invalid/unsynced documents are never rewritten
            raise

    def _tick(self):
        with self.lock():
            doc,parsed = self.read()
            journal = self.load()
            command = parsed['control']
            pending = journal['pending']
            # Durable operation precedes ALL transport calls and any control reset.
            if pending is None and command != 'draft':
                if command == 'ka':
                    if journal['selected']:
                        current=self.status(journal['selected'])
                        if current.get('status') not in TERMINAL or current.get('status')=='unknown':
                            return self.report_error(doc,parsed,journal,'当前任务尚未确认结束；请等待或 stop，输入已保留',journal['selected'],reset=True)
                    rid = 'text-' + uuid.uuid4().hex
                    action = 'ka'
                elif command == 'stop':
                    rid = journal['selected']
                    if not rid:
                        return self.report_error(doc,parsed,journal,'没有当前运行任务',None,reset=True)
                    actual = self.status(rid)
                    if actual.get('status')=='unknown':
                        return self.report_error(doc,parsed,journal,'当前任务状态未知；保留输入，请维护者核对原请求',rid,reset=True)
                    if actual.get('status') in TERMINAL:
                        return self.report_error(doc,parsed,journal,'任务已完成，未取消' if actual.get('status')=='done' else '没有当前运行任务',rid,reset=True)
                    action = 'stop'
                else:
                    action,rid=command.split(' ')
                prompt=parsed['prompt']
                if action=='ka':
                    if not prompt.strip(): raise ValueError('empty input; nothing dispatched')
                    binding=journal['bindings'].get(rid)
                    if binding and binding['prompt'] != prompt:
                        return self.report_error(doc,parsed,journal,'request_snapshot_conflict',rid)
                    if binding is None:
                        journal['bindings'][rid]={'prompt':prompt,'sha256':hashlib.sha256(prompt.encode()).hexdigest(),'delivery':'reserved'}
                elif rid not in journal['bindings']:
                    return self.report_error(doc,parsed,journal,'unknown_operator_request; inspect history; no replay',rid)
                pending={'command':command,'action':action,'request_id':rid,'phase':'prepared','source_text':doc['text']}
                journal['pending']=pending;self.save(journal)
            if pending:
                # Persist reset intent before touching the page. Only the observed
                # source can be acknowledged; a concurrent successor is preserved.
                if not pending.get('reset_complete'):
                    if doc['text'] == pending.get('source_text'):
                        self.write(doc,parsed,{'control':'draft\n'})
                    elif parsed['control']==pending['command']:
                        return self.report_error(doc,parsed,journal,'acknowledgement conflict; pending snapshot retained; set draft to recover',pending['request_id'])
                    if doc['text'] == pending.get('source_text'):
                        binding = journal['bindings'][pending['request_id']]
                        binding.setdefault('operations',[]).append({
                            'source_revision':source_revision(pending['source_text']),
                            'action':pending['action'], 'consumed':True})
                    pending['reset_complete']=True
                    self.save(journal)
                rid=pending['request_id'];action=pending['action']
                binding=journal['bindings'][rid]
                if binding['delivery']=='conflict':
                    return self.report_error(doc,parsed,journal,'host request_snapshot_conflict; pending retained for inspection',rid)
                if action=='ka':
                    if binding['delivery']=='reserved' and pending['phase']=='prepared':
                        # Persist uncertain BEFORE start. Crash recovery only queries.
                        binding['delivery']='uncertain';pending['phase']='calling';self.save(journal)
                        try:
                            receipt=self.transport.call('codex_task_start',{'request_id':rid,'prompt':binding['prompt']})
                            if receipt.get('prompt_accepted') is False:
                                binding['delivery']='conflict';self.save(journal)
                                return self.report_error(doc,parsed,journal,'host request_snapshot_conflict',rid)
                            binding['delivery']='accepted'
                        except Exception as error:
                            # Keep pending and input; no speculative start retry.
                            self.save(journal)
                            return self.report_error(doc,parsed,journal,'start outcome unknown: '+str(error),rid,reset=False)
                        self.save(journal)
                    actual=self.status(rid)
                    binding['delivery']='accepted'
                elif action=='stop':
                    actual=self.status(rid)
                    # Idempotent cancellation is scoped to this bound task only.
                    if actual.get('status') not in TERMINAL:
                        if pending['phase']=='calling':
                            return self.report_error(doc,parsed,journal,'stop outcome pending confirmation; query only, no replay',rid)
                        pending['phase']='calling';self.save(journal)
                        actual=self.transport.call('codex_task_cancel',{'task_id':actual['task_id']})
                    if actual.get('status')=='unknown':
                        return self.report_error(doc,parsed,journal,'stop outcome unknown; query only, no replay',rid)
                else: actual=self.status(rid)
                for operation in binding.get('operations',[]):
                    if operation['source_revision']==source_revision(pending['source_text']):
                        operation['submission']='accepted'
                        if action=='stop':
                            operation['cancel_confirmed']=bool(actual.get('cancel_confirmed') is True
                                and actual.get('status')=='cancelled' and actual.get('execution')=='ended')
                            operation['execution_status']=actual.get('status','unknown')
                            operation['task_id']=actual.get('task_id')
                self.save(journal)
                # Reread after slow transport. Never overwrite a newer control or draft.
                doc,parsed=self.read()
                changes={}
                # Reset already completed before transport; never consume successor.
                journal['selected']=rid
                # A successor control is not consumed by this acknowledgement.
                # Journal has no business status; result is a projection of actual.
                changes['result']=self.project(rid,actual,journal)
                if actual.get('status')=='done' and not binding.get('completion_seen') and parsed['control']=='draft' and parsed['prompt']==binding['prompt']:
                    changes['input']='\n'
                if actual.get('status')=='done':
                    binding['completion_seen']=True
                    self.save(journal)  # consume cleanup once before CAS; conflicts preserve input
                self.write(doc,parsed,changes)
                journal['pending']=None;self.save(journal)
                return actual
            rid=journal['selected']
            if rid:
                actual=self.status(rid);binding=journal['bindings'][rid]
                doc,parsed=self.read()
                changes={'result':self.project(rid,actual,journal)}
                if actual.get('status')=='done' and not binding.get('completion_seen') and parsed['control']=='draft' and parsed['prompt']==binding['prompt']:changes['input']='\n'
                if actual.get('status')=='done':
                    binding['completion_seen']=True
                    self.save(journal)  # consume cleanup once before CAS; conflicts preserve input
                self.write(doc,parsed,changes)
                self.save(journal)
                return actual
            return {'version':VERSION,'dispatched':False,'control':'draft'}

    def report_error(self,doc,parsed,journal,error,rid,reset=False):
        observed=doc['text']
        rejected=reset or 'snapshot_conflict' in error or error.startswith('unknown_operator_request')
        pending=journal.get('pending')
        evidence_revision=source_revision(pending['source_text']) if pending and pending['request_id']==rid else source_revision(observed)
        if rid in journal['bindings']:
            binding=journal['bindings'][rid]
            if rejected:
                binding.setdefault('operations',[]).append({
                    'source_revision':evidence_revision,'action':parsed['control'].split()[0],
                    'consumed':bool(reset),'submission':'not_applied'})
            binding.setdefault('diagnostics',[]).append({
                'source_revision':evidence_revision,'message':error[:400],
                'delivery_uncertainty':('Workspace is busy' in error or error.startswith('start outcome unknown:')),
                'submission':'not_applied' if rejected else 'pending_confirmation'})
            self.save(journal)
        doc,parsed=self.read()
        value={'version':VERSION,'operator_error':error[:400],'request_id':rid,'business_status':'unknown','replay_allowed':False}
        if rid and rid in journal['bindings']:
            try:
                actual=self.status(rid)
                value=json.loads(self.project(rid,actual,journal)) | value
            except Exception:
                value['status']='unknown'
        pending=journal.get('pending')
        evidence_revision=source_revision(pending['source_text']) if pending and pending['request_id']==rid else source_revision(observed)
        value.update(self.receipt(evidence_revision))
        if rejected:
            value['submission']='not_applied'
        elif value['submission']=='accepted' and ('Workspace is busy' in error or error.startswith('start outcome unknown:')):
            value['diagnostic']=value.pop('operator_error')
            value['notice']='该保存版本已接受；此前接单确认异常已恢复，无需重发'
        changes={'result':encode_result(value)}
        if reset and doc['text']==observed:changes['control']='draft\n'
        self.write(doc,parsed,changes)
        receipt=self.receipt(source_revision(observed))
        if rejected:receipt['submission']='not_applied'
        if receipt['submission']=='accepted' and not rejected and ('Workspace is busy' in error or error.startswith('start outcome unknown:')):
            return dict(receipt,diagnostic=error,notice='该保存版本已接受；此前接单确认异常已恢复，无需重发')
        return dict(receipt,operator_error=error)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--world',required=True)
    parser.add_argument('--source',default=SOURCE)
    parser.add_argument('--once',action='store_true')
    parser.add_argument('--grant-read-write-run',action='store_true')
    args=parser.parse_args()
    if not args.grant_read_write_run:parser.error('explicit host Read/Write/Run service grant required')
    from yohaku_codex_text_service import serve
    return serve(args)

if __name__=='__main__':raise SystemExit(main())
