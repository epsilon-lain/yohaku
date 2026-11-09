import hashlib,json
from pathlib import Path
meta=json.loads(Path('input/metadata.json').read_text(encoding='utf-8'))
for key,path in [('source_version','input/source.tex'),('body_sha256','input/document.md')]:
    actual=hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if meta[key]!=actual: raise ValueError('frozen input mismatch: '+path)
print(json.dumps({'verified':True,'metadata':meta},ensure_ascii=False))
