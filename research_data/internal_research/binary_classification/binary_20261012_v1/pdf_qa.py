"""Inspect real rendered PDF pages and headline metrics, then create contact sheets."""
from pathlib import Path
import json
from PIL import Image,ImageDraw
from pypdf import PdfReader
OUT=Path(__file__).resolve().parent;QA=OUT/'pdf_qa'
def main():
 reader=PdfReader(OUT/'binary_classification_report_th.pdf');assert len(reader.pages)==10
 txt='\n'.join(p.extract_text() for p in reader.pages);c=json.loads((OUT/'conclusion.json').read_text(encoding='utf-8'))
 for value in [c['candidate_score']['macro_f1'],c['majority_score']['macro_f1'],c['previous_known_direction_score']['macro_f1']]:assert f'{value:.3f}' in txt
 assert 'ทุเรียน' in txt and '\ufffd' not in txt and 'Step 0' in txt and 'Step 6' in txt
 png=sorted(QA.glob('page-*.png'));assert len(png)==10
 for start in [0,5]:
  canvas=Image.new('RGB',(1100,330),'#dbe3e6');draw=ImageDraw.Draw(canvas)
  for i,p in enumerate(png[start:start+5]):
   im=Image.open(p).convert('RGB');im.thumbnail((210,297));canvas.paste(im,(i*220,25));draw.text((i*220+8,7),f'PAGE {start+i+1}',fill='black')
  canvas.save(QA/f'contact_{start+1}_{start+5}.png')
 with (QA/'text_page_verification.json').open('x',encoding='utf-8') as f:json.dump(dict(pages=10,rounded_metrics_verified=True,thai_text_present=True,actual_pdf_pages_rendered=10),f,indent=2)
 print('PDF QA:10 pages rendered and key results verified')
if __name__=='__main__':main()
