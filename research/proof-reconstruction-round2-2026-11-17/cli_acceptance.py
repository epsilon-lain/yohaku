#!/usr/bin/env python3
"""Run the fixed official CLI entry point; count real verification applications."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--official-root', type=Path, required=True)
    args = p.parse_args()
    here = Path(__file__).resolve().parent
    lock = json.loads((here/'OFFICIAL-SOURCE-LOCK.json').read_text())
    assert lock['commit'] == 'a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e'
    for row in lock['files']:
        data = (args.official_root/row['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row['sha256']
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == row['git_blob']
    with tempfile.TemporaryDirectory(prefix='proof-cli-clean-cache-') as cache:
        sys.pycache_prefix = cache
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(args.official_root/'competition/tools'))
        from verifier import cli, stable_core
        original = stable_core.apply_move
        calls = [0]
        def counted(state, move):
            calls[0] += 1
            return original(state, move)
        stable_core.apply_move = counted
        reports = []
        for filename, manifest in (
            ('training-submission.txt','competition/examples/training_manifest.json'),
            ('incumbent-submission.txt','competition/tools/verifier/data/manifest.json')):
            out, err = io.StringIO(), io.StringIO()
            before = calls[0]
            argv = ['--manifest', str(args.official_root/manifest),
                    '--submission', str(here/filename), '--pretty']
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = cli.main(argv)
            verdict = json.loads(out.getvalue())
            assert rc == 0 and verdict['accepted'] is True
            reports.append({'submission': filename, 'manifest': manifest,
                'returncode':rc, 'official_apply_calls':calls[0]-before,
                'stdout':out.getvalue(), 'stderr':err.getvalue(),
                'submission_sha256':hashlib.sha256((here/filename).read_bytes()).hexdigest()})
        report = {'status':'passed', 'scope':'Official cli.main entry point, source-locked 30-file checkout; no platform upload.',
            'official_apply_calls':calls[0], 'reports':reports,
            'source_lock_sha256':hashlib.sha256((here/'OFFICIAL-SOURCE-LOCK.json').read_bytes()).hexdigest(),
            'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        (here/'CLI-ACCEPTANCE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':report['status'],'official_apply_calls':calls[0],
                          'files':[r['submission'] for r in reports]},ensure_ascii=False))

if __name__ == '__main__': main()
