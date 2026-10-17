import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description='Regenerate listed text with Loom, or compare without replacing it')
    parser.add_argument('--check', action='store_true')
    arguments = parser.parse_args()
    sources = json.loads((ROOT / 'source-documents.json').read_text())['sources']
    loom = ROOT / 'bin/loom-linux-x86_64'
    with tempfile.TemporaryDirectory(prefix='yohaku-source-check-') as temporary:
        destination = Path(temporary) if arguments.check else ROOT
        if arguments.check:
            shutil.copytree(ROOT / 'macros', destination / 'macros')
        for name in sources:
            result = subprocess.run([str(loom), 'sync', str(ROOT / name), '--root', str(destination), '--json'],
                                    capture_output=True, text=True, check=True)
            reply = json.loads(result.stdout)
            if not reply.get('ok'):
                raise SystemExit(f'Loom failed for {name}: {reply}')
            output = name.removesuffix('.tex')
            if arguments.check and (destination / output).read_bytes() != (ROOT / output).read_bytes():
                raise SystemExit(f'Generated text differs: {output}')
    print(f'{"Checked" if arguments.check else "Regenerated"} {len(sources)} Loom source documents')


if __name__ == '__main__':
    main()
