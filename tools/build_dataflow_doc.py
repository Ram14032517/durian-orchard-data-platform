"""Build the offline Thai dataflow reader from its versioned Markdown source."""
import argparse
import html
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/architecture/DATAFLOW_TH.md'
OUTPUT=SOURCE.with_suffix('.html')
LANES=[
    ('เซนเซอร์จริง','Gateway / farm-ingest','validity / เวลา / device','sensor_readings','GET /api/orchard-status','สวนของฉัน','ค่าที่วัด / ประวัติ'),
    ('NASA POWER','อากาศกริดย้อนหลัง','ช่วงวัน / hash / cache','GET /api/weather','เลือกพื้นที่ A/B','สภาพอากาศ','กราฟ / ตาราง / CSV'),
    ('GAP + LDD','ทะเบียน / แผนที่ดิน','QC พิกัด / quality flags','manifest + GeoJSON','ไม่ย้ายพิกัดที่ไม่ผ่าน','แผนที่ / GAP','ตำแหน่งทะเบียน ≠ ยืนยันสวน'),
    ('CSV จังหวัด','ผลผลิต / อากาศย้อนหลัง','เตรียม features / audit','โมเดลจังหวัดที่บันทึกไว้','GET /api/province-estimate','ผลผลิต / ฤดูกาล','ไม่ใช่ผลผลิตรายสวน'),
    ('พิกัดเจ้าของยืนยัน','configuration ฝั่ง server','สิทธิ์ / Open-Meteo / QC','GET /api/orchard-forecast','cache ใน memory','พยากรณ์ส่วนตัว','แบบจำลอง ≠ sensor'),
    ('ผลผลิตที่เจ้าของบันทึก','แบบฟอร์มในเว็บ','session / CSRF / หน่วย','/api/orchard-harvest','Supabase เฉพาะเจ้าของ','ประวัติผลผลิตสวน','ไม่ train อัตโนมัติ'),
]

def diagram():
    rows=[]
    for index,lane in enumerate(LANES):
        cells=[(lane[0],lane[1]),(lane[2],''),(lane[3],lane[4]),(lane[5],lane[6])]
        y=58+index*84
        for col,(title,detail) in enumerate(cells):
            x=10+col*282
            rows.append(f'<rect x="{x}" y="{y}" width="260" height="66" rx="9"/>')
            rows.append(f'<text x="{x+12}" y="{y+27}" class="node-title">{html.escape(title)}</text>')
            rows.append(f'<text x="{x+12}" y="{y+48}" class="node-detail">{html.escape(detail)}</text>')
            if col<3:rows.append(f'<path d="M{x+262} {y+33}h17" marker-end="url(#arrow)"/>')
    headings=''.join(f'<text x="{22+i*282}" y="28" class="column">{label}</text>' for i,label in enumerate(['ต้นทาง','ตรวจ / ประมวลผล','API / ที่เก็บข้อมูล','แสดงผล']))
    return '<div class="diagram"><svg viewBox="0 0 1120 570" role="img" aria-labelledby="flow-title"><title id="flow-title">การไหลของข้อมูลหกสาย แยกค่าที่วัด พยากรณ์ ทะเบียน และผลผลิต</title><defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0 0L6 3L0 6"/></marker></defs>'+headings+''.join(rows)+'</svg></div>'

def render(markdown):
    import mistune
    content=mistune.html(markdown)
    headings=[]
    def heading(match):
        anchor='section-'+str(len(headings)+1);label=re.sub('<[^>]+>','',match[1]);headings.append((anchor,label))
        return f'<h2 id="{anchor}">{match[1]}</h2>'
    content=re.sub(r'<h2>(.*?)</h2>',heading,content)
    links=''.join(f'<a href="#{anchor}">{html.escape(label)}</a>' for anchor,label in headings)
    return '''<!doctype html><html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Dataflow · Durian Orchard</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f7f4;color:#213c33;font:15px/1.85 -apple-system,BlinkMacSystemFont,"Thonburi",Tahoma,sans-serif}.page{max-width:1440px;margin:auto;display:grid;grid-template-columns:245px minmax(0,1fr);gap:32px;padding:32px}nav{position:sticky;top:24px;align-self:start}nav a{display:block;font-size:13px;padding:5px 0}main{background:#fff;border:1px solid #dce6de;border-radius:16px;padding:30px;min-width:0}h1{font-size:29px;line-height:1.4}h2{font-size:21px;scroll-margin-top:25px;border-top:1px solid #dce6de;padding-top:24px;margin-top:32px}a{color:#1b7154;text-underline-offset:3px;overflow-wrap:anywhere}code{font:12px/1.7 ui-monospace,monospace;background:#edf3ee;border-radius:4px;padding:2px 4px;overflow-wrap:anywhere}pre{overflow:auto;padding:16px;background:#edf3ee;border-radius:10px}pre code{white-space:pre;overflow-wrap:normal}.caption{color:#586e63;font-size:12px}.diagram{overflow:auto;border:1px solid #dce6de;border-radius:12px;margin:24px 0;background:#fafcf9}.diagram svg{display:block;width:100%;min-width:880px;font-family:inherit}.diagram rect{fill:#fff;stroke:#ccdcd0}.diagram path{fill:none;stroke:#408365;stroke-width:1.6}.diagram marker path{fill:#408365;stroke:none}.diagram text{fill:#253f33;font-size:12px}.diagram .node-title{font-weight:650}.diagram .node-detail{font-size:10.5px;fill:#566e60}.diagram .column{font-size:13px;font-weight:700}footer{margin-top:36px;border-top:1px solid #dce6de;padding-top:18px}@media(max-width:900px){.page{grid-template-columns:1fr;padding:16px;gap:12px}nav{position:static}nav a{display:inline-block;margin-right:12px}main{padding:20px}h1{font-size:25px}}@media print{nav{display:none}.page{display:block;padding:0}main{border:0;padding:0}.diagram svg{min-width:0}h2{break-after:avoid}a{color:inherit}}
</style></head><body><div class="page"><nav aria-label="สารบัญ"><strong>Durian Orchard · Dataflow</strong>'''+links+'''</nav><main><p class="caption">ภาพรวมโค้ด · 1 พฤศจิกายน 2569 · ไม่มี live API หรือข้อมูลส่วนตัวในไฟล์นี้</p>'''+diagram()+'''<p class="caption">ลูกศรแสดงการไหลของข้อมูลที่ใช้แสดงผล ไม่ได้หมายถึงการ train อัตโนมัติ · แต่ละสายมีแหล่งและระดับข้อมูลต่างกัน</p>'''+content+'''<footer><a href="DATAFLOW_TH.md">ต้นฉบับ Markdown</a> · เปิดอ่าน offline ได้ ไม่ต้องรัน server และไม่เปลี่ยนข้อมูลเมื่อเปิดอ่าน</footer></main></div></body></html>
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    result=render(SOURCE.read_text(encoding='utf-8'))
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding='utf-8')!=result:raise RuntimeError('Rebuild DATAFLOW_TH.html from Markdown')
        print('Dataflow HTML matches source; offline, no live scripts')
    else:
        OUTPUT.write_text(result,encoding='utf-8');print(OUTPUT.relative_to(ROOT))

if __name__=='__main__':main()
