"""External engineering helper: restore and hash-check fixed public resources.

No model, search, platform upload or research is performed by this helper.
"""
import base64,hashlib,io,json,tarfile
from pathlib import Path

def restore(destination='round2-fixed-resources'):
    here=Path(__file__).resolve().parent
    lock=json.loads((here/'RESOURCE-LOCK.json').read_bytes())
    raw=base64.b64decode((here/'resources.b64').read_text(),validate=False)
    if hashlib.sha256(raw).hexdigest()!=lock['archive_sha256']:raise ValueError('Pinned public-resource archive hash differs')
    dest=Path(destination).resolve();dest.mkdir(parents=True,exist_ok=True)
    expected={row['path']:row['sha256']for row in lock['files']}
    with tarfile.open(fileobj=io.BytesIO(raw))as archive:
        members=archive.getmembers()
        if any(not m.isfile()or m.name not in expected or not(dest/m.name).resolve().is_relative_to(dest)for m in members):raise ValueError('Unexpected resource archive member')
        archive.extractall(dest,members=members,filter='data')
    for relative,digest in expected.items():
        if hashlib.sha256((dest/relative).read_bytes()).hexdigest()!=digest:raise ValueError('Fixed source byte mismatch: '+relative)
    return {'official':str(dest/'official'),'acceptance':str(dest/'acceptance'),'archive_sha256':lock['archive_sha256'],'files_verified':len(expected)}

if __name__=='__main__':print(json.dumps(restore(),ensure_ascii=False))
