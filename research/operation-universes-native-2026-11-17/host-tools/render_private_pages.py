import json
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image,ImageDraw
BASE=Path(__file__).resolve().parent;out=BASE/'inputs/rendered';out.mkdir(exist_ok=True)
lock=json.loads((BASE/'sources.json').read_bytes());thumbs=[]
for s in lock['sources']:
    if s['id']not in('PANO','IUT1'):continue
    doc=pdfium.PdfDocument(str(BASE/'inputs'/s['filename']))
    for i in s['read_pdf_indices_zero_based']:
        page=doc[i];bitmap=page.render(scale=1.2);im=bitmap.to_pil();name=s['id']+f'-p{i+1:03}.png';im.save(out/name)
        t=im.copy();t.thumbnail((440,570));tile=Image.new('RGB',(460,610),'white');tile.paste(t,((460-t.width)//2,30));ImageDraw.Draw(tile).text((12,8),s['id']+' page '+str(i+1),fill='black');thumbs.append(tile)
    doc.close()
sheet=Image.new('RGB',(460*3,610*4),'#cccccc')
for k,t in enumerate(thumbs):sheet.paste(t,((k%3)*460,(k//3)*610))
sheet.save(out/'contact-sheet.png');print(json.dumps({'rendered_private_pages':len(thumbs),'renderer':'existing bundled pypdfium2','contact_sheet':str(out/'contact-sheet.png'),'source_PDFs_unchanged':True}))
