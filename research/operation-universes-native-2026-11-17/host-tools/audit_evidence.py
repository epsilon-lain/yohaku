"""Read-only audit of registered sources and new-round native evidence."""
import hashlib,json,sqlite3,time
from pathlib import Path
from launch_operations import BASE,activate,save,sha,verify_parent

def main():
    p=activate();verify_parent()
    from yohaku_ai_nodes import Control
    ctrl=Control(p['world']);world=Path(p['world'])
    imp=json.loads((BASE/'IMPORT-RECEIPT.json').read_bytes())
    expected={r['id']:r for r in imp['native_documents']};locations={i:[]for i in expected}
    # Registered node metadata is a JSON mapping on the canonical .tex header.
    for source in world.rglob('*.tex'):
        if any(x in source.parts for x in ('.git','.loom','.yohaku')):continue
        lines=source.read_text(errors='replace').splitlines()
        if not lines or lines[0]!='---':continue
        for line in lines[1:]:
            if line=='---':break
            if line.startswith('node: '):
                try:node=json.loads(line[6:])
                except json.JSONDecodeError:continue
                if node.get('id')in locations:locations[node['id']].append(str(source.relative_to(world)))
    checked=[]
    for eid,r in expected.items():
        doc=ctrl.read(r['source'])
        assert locations[eid]==[r['source']],(eid,locations[eid])
        assert doc['valid'] and doc['revision']==r['source_revision']
        assert hashlib.sha256(doc['body'].encode()).hexdigest()==r['body_sha256']
        assert (world/r['generated']).read_text()==doc['body']
        checked.append(dict(id=eid,canonical_source=r['source'],revision=doc['revision'],
                            registered_occurrences=locations[eid],body_sha256=r['body_sha256'],
                            generated_equal=True,valid=True))
    save(BASE/'MAPPING-AUDIT.json',dict(at=time.time(),documents=len(checked),
         unique_registered_mapping=True,documents_verified=checked,source_text_published=False))
    before=json.loads((BASE/'BEFORE.json').read_bytes());prefix=before['knowledge_prefix']
    db=sqlite3.connect(p['knowledge_db']);db.row_factory=sqlite3.Row
    events=[]
    for row in db.execute('SELECT * FROM events WHERE seq>? ORDER BY seq',(prefix,)):
        raw=dict(row)
        # Actor/data are independent JSON columns in the registered schema.
        events.append(dict(raw,actor=json.loads(raw['actor']),data=json.loads(raw['data'])))
    db.close()
    current=json.loads((BASE/'START-AND-READ-RECEIPTS.json').read_bytes())
    ids={t['task_id']for t in current['tasks']};meta=[];computations=[]
    for e in events:
        if e['actor'].get('task_id')not in ids:continue
        row={k:e[k]for k in ('seq','kind','actor')}
        if e['kind']=='native_tool_completed':
            tool=e['data']['name'];args=e['data']['arguments'];result=e['data']['result']
            row.update(tool=tool,ok=result.get('ok'),argument_keys=list(args))
            if tool in ('task_submit','task_status','task_read','task_result','task_artifacts'):
                computations.append(dict(seq=e['seq'],actor=e['actor'],tool=tool,arguments=args,result=result))
        elif e['kind']in ('math_adopt','math_published','ai_plan_changed','message_sent','ai_message_sent'):
            row['data']=e['data']
        meta.append(row)
    save(BASE/'EVENT-METADATA.json',dict(at=time.time(),prefix=prefix,events=meta))
    save(BASE/'COMPUTATIONS-PRIVATE.json',computations)
    print(json.dumps(dict(mapping_documents=len(checked),unique_mapping=True,
          native_events=len(meta),computations=computations),ensure_ascii=False))

if __name__=='__main__':main()
