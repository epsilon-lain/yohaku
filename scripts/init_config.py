import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    for name in ['ai', 'shell']:
        data = (ROOT / f'config/{name}.example.json').read_bytes()
        json.loads(data)
        destination = ROOT / f'config/{name}.json'
        try:
            with destination.open('xb') as stream:
                stream.write(data)
            print(f'Created local {destination.name}')
        except FileExistsError:
            print(f'Kept existing local {destination.name}')


if __name__ == '__main__':
    main()
