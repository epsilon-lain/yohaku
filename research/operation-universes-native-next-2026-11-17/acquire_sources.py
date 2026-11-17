#!/usr/bin/env python3
"""Acquire pinned primary PDFs into a private staging directory, never dispatch AI.

Do not publish the generated PDFs or page transcripts with the public packet.
Extraction is staging only; native import and actual reading need separate receipts.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def sha(data):
    return hashlib.sha256(data).hexdigest()


def acquire(source, out):
    name = source['filename']
    if Path(name).name != name or not name.endswith('.pdf'):
        raise ValueError('Unsafe PDF filename')
    parsed = urlparse(source['url'])
    if parsed.scheme != 'https' or parsed.hostname != 'www.kurims.kyoto-u.ac.jp':
        raise ValueError('Unexpected source origin')
    if not re.fullmatch('[a-f0-9]{64}', source['sha256']):
        raise ValueError('Invalid pinned digest')
    dest = out / name
    if dest.exists():
        data = dest.read_bytes()
    else:
        request = Request(source['url'], headers={'User-Agent': 'YohakuResearch/1.0'})
        with urlopen(request, timeout=30) as response:
            final = urlparse(response.geturl())
            if final.scheme != 'https' or final.hostname != parsed.hostname:
                raise ValueError('Source redirected outside official HTTPS origin')
            data = response.read(20_000_001)
    if len(data) > 20_000_000 or not data.startswith(b'%PDF-'):
        raise ValueError(f"{source['id']}: invalid PDF or size limit")
    if len(data) != source['bytes'] or sha(data) != source['sha256']:
        raise ValueError(f"{source['id']}: source version differs from pin; do not silently update")
    if not dest.exists():
        temp = out / (name + '.part')
        temp.write_bytes(data)
        temp.replace(dest)
    return dest


def extract(source, pdf, out):
    indices = source['read_pdf_indices_zero_based']
    if not indices:
        return {'status': 'not_assigned', 'pages': []}
    pages = []
    if importlib.util.find_spec('fitz'):
        import fitz
        with fitz.open(pdf) as document:
            if len(document) != source['pdf_pages']:
                raise ValueError('PDF page count differs from source lock')
            for i in indices:
                pages.append((i, document[i].get_text(sort=True)))
        engine = 'PyMuPDF'
    elif shutil.which('pdftotext'):
        for i in indices:
            result = subprocess.run(
                ['pdftotext', '-f', str(i + 1), '-l', str(i + 1),
                 '-enc', 'UTF-8', str(pdf), '-'],
                check=True, capture_output=True, text=True)
            pages.append((i, result.stdout))
        engine = 'pdftotext'
    else:
        return {'status': 'blocked_no_extractor', 'pages': []}
    records = []
    for index, body in pages:
        path = out / f"{source['id']}-page-{index + 1:03}.txt"
        header = (f"Source: {source['id']}\nSource SHA256: {source['sha256']}\n"
                  f"PDF index: {index} (zero-based)\nPDF/printed page: {index + 1}\n"
                  'Extracted text; inspect original PDF for mathematical glyphs.\n\n')
        path.write_text(header + body, encoding='utf-8')
        records.append({'pdf_index_zero_based': index, 'printed_page': index + 1,
                        'filename': path.name, 'sha256': sha(path.read_bytes()),
                        'text_characters': len(body),
                        'replacement_glyphs': body.count('\ufffd'),
                        'manual_math_glyph_review_required': True})
    return {'status': 'extracted_to_private_staging', 'engine': engine, 'pages': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--ids', nargs='+', default=['PANO', 'IUT1'])
    parser.add_argument('--extract', action='store_true')
    args = parser.parse_args()
    manifest = json.loads(Path(__file__).with_name('sources.json').read_text())
    sources = {source['id']: source for source in manifest['sources']}
    unknown = set(args.ids) - sources.keys()
    if unknown:
        parser.error('Unknown source IDs: ' + ', '.join(sorted(unknown)))
    args.out.mkdir(parents=True, exist_ok=True)
    records, blocked = [], False
    for sid in dict.fromkeys(args.ids):
        source = sources[sid]
        try:
            path = acquire(source, args.out)
            extraction = extract(source, path, args.out) if args.extract else {'status': 'not_requested'}
            blocked = blocked or extraction['status'] == 'blocked_no_extractor'
            records.append({'id': sid, 'url': source['url'], 'pdf_filename': path.name,
                            'sha256': source['sha256'], 'bytes': source['bytes'],
                            'source_bytes_verified': True, 'extraction': extraction,
                            'native_imported': False, 'native_read_verified': False})
        except Exception as error:
            blocked = True
            records.append({'id': sid, 'status': 'blocked', 'error': str(error),
                            'native_imported': False, 'native_read_verified': False})
    receipt = {'kind': 'private-literature-staging-only', 'status': 'blocked' if blocked else 'ready',
               'native_dispatch': False, 'native_imported': False, 'sources': records}
    (args.out / 'ACQUISITION-RECEIPT.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': receipt['status'], 'source_count': len(records),
                      'native_dispatch': False, 'native_imported': False}))
    raise SystemExit(2 if blocked else 0)


if __name__ == '__main__':
    main()
