"""Use the already bundled pypdf; no dependency install or model request."""
import hashlib,importlib.util,json,time
from pathlib import Path
from pypdf import PdfReader
BASE=Path(__file__).resolve().parent;out=BASE/'inputs'
old=out/'ACQUISITION-RECEIPT.json'
if old.exists():(out/'ACQUISITION-RECEIPT-poppler-failed.json').write_bytes(old.read_bytes())
sources=json.loads((BASE/'sources.json').read_bytes());records=[]
for source in sources['sources']:
    if source['id']not in sources['default_source_ids']:continue
    p=out/source['filename'];raw=p.read_bytes();assert len(raw)==source['bytes']and hashlib.sha256(raw).hexdigest()==source['sha256']
    reader=PdfReader(p);assert len(reader.pages)==source['pdf_pages'];pages=[]
    for index in source['read_pdf_indices_zero_based']:
        body=reader.pages[index].extract_text()or''
        assert len(body)>500
        text=f"Source: {source['id']}\nOfficial URL: {source['url']}\nSource SHA256: {source['sha256']}\nPDF index: {index} (zero-based)\nPDF/printed page: {index+1}\nPrivate original-page extract; pypdf. Mathematical glyphs/formula layout not certified; use original PDF for formula-dependent claims.\n\n"+body
        dest=out/(source['id']+f'-page-{index+1:03}.txt');dest.write_text(text,encoding='utf-8',newline='\n')
        pages.append({'pdf_index_zero_based':index,'printed_page':index+1,'filename':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'text_characters':len(body),'replacement_glyphs':body.count(chr(0xfffd)),'formula_quality':'not certified; original image review required for mathematical glyphs','extraction_engine':'bundled pypdf'})
    records.append({'id':source['id'],'url':source['url'],'pdf_filename':p.name,'sha256':source['sha256'],'bytes':len(raw),'pdf_pages_verified':len(reader.pages),'source_bytes_verified':True,'extraction':{'status':'extracted_to_private_staging','engine':'bundled pypdf','pages':pages},'native_imported':False,'native_read_verified':False})
receipt={'kind':'private-literature-staging-only','status':'ready','sources':records,'native_dispatch':False,'native_imported':False,'dependency_installed':False,'prior_extractor_failures_retained':True,'at':time.time()}
(out/'ACQUISITION-RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'ready':True,'pdfs':len(records),'pages':sum(len(r['extraction']['pages'])for r in records),'pypdfium2_available':bool(importlib.util.find_spec('pypdfium2')),'native_imported':False,'model_requests':0}))
