"""Create ONE top-level entry point with saved notebook outputs; preserve old files."""
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from jupyter_client import KernelManager

ROOT = Path(__file__).resolve().parents[1]
md = nbformat.v4.new_markdown_cell
code = nbformat.v4.new_code_cell
nb = nbformat.v4.new_notebook(cells=[
md('''# รายงานทุเรียน 5 จังหวัด — เปิดไฟล์นี้ไฟล์เดียว

**ผลรันบันทึกไว้แล้ว เลื่อนลงอ่านได้เลย ไม่ต้องเปิด Terminal**

หากต้องการเปลี่ยนช่วงเวลา: แก้ `PROVINCE`, `YEAR`, `MONTH` ในเซลล์แรก แล้วกด **Run All**
เลือก kernel จาก Python environment ที่ใช้งานได้ ไม่เลือก `.venv` เก่า (Python 3.9.5)
เครื่องนี้ใช้ `C:/project/.build/national-analysis-venv/Scripts/python.exe`

## สรุปและขอบเขต
รายงานฉบับล่าสุดนี้ใช้ข้อมูลที่ดาวน์โหลดไว้ถึงรอบ 26 ก.ย. 2569 ไม่ใช่ข้อมูลสด
เปิดตัวอย่าง **สุราษฎร์ธานี กรกฎาคม 2568** ให้ตรงกับตัวอย่างหน้ารายเดือนเดิม
รวมอากาศ ผลผลิต กรอบระยะ ข่าวจริง และข้อมูลดินในสมุดเดียว
อากาศเป็น NASA POWER ณ จุดอ้างอิงจังหวัด ผลผลิตเป็นยอดทั้งจังหวัดทุกพันธุ์ ไม่ใช่สุขภาพต้นทุเรียนรายต้น

[เปิดแผนที่คลิกชุดดิน](http://127.0.0.1:8871/research_data/five_province_history/UNIFIED_MAP.html)
— แผนที่โต้ตอบยังอยู่หน้าเดิม ต้องเปิดเซิร์ฟเวอร์; ตารางและกราฟด้านล่างอ่านได้โดยไม่ใช้เซิร์ฟเวอร์'''),
code('''# แก้เฉพาะ 3 บรรทัดนี้ แล้ว Run All
PROVINCE = "84"  # 22 จันทบุรี, 33 ศรีสะเกษ, 53 อุตรดิตถ์, 84 สุราษฎร์ธานี, 86 ชุมพร
YEAR = 2025      # ปี ค.ศ.
MONTH = 7        # เดือน 1–12'''),
md('''## 1. โหลดข้อมูลและตรวจคีย์
ใช้ CSV เดิมในโปรเจกต์ ไม่ดาวน์โหลดใหม่และไม่เปลี่ยนข้อมูลต้นฉบับ
วันอากาศเป็น Local Solar Time; ช่องว่างไม่เติมเป็นศูนย์
ปฏิทินกรมวิชาการเกษตรเป็นกรอบภูมิภาค ไม่ใช่ระยะจริงที่สังเกตทุกปี'''),
code('''from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown

root = next((p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'research_data/five_province_history').is_dir()), None)
if root is None:
    raise FileNotFoundError('เปิด notebook จากโฟลเดอร์ project ที่มี research_data อยู่ด้วย')
base = root / 'research_data/five_province_history'
def load(name):
    return pd.read_csv(base / name, dtype={'province_code': str})
weather = load('weather_monthly.csv')
harvest = load('harvest_monthly.csv').rename(columns={'month_number': 'month'})
points = load('reference_points.csv')
evidence = json.loads((base / 'phenology_evidence.json').read_text(encoding='utf-8'))
assert not weather.duplicated(['province_code', 'year_ce', 'month']).any()
assert not harvest.duplicated(['province_code', 'year_ce', 'month']).any()
assert PROVINCE in set(points.province_code) and 1 <= MONTH <= 12
name = points.set_index('province_code').loc[PROVINCE, 'province_name']
def table(frame):
    display(frame.style.format(precision=2, na_rep='—').hide(axis='index').set_table_styles([
        {'selector':'th', 'props':[('text-align','left'),('border-bottom','1px solid #aaa')]},
        {'selector':'td', 'props':[('border-bottom','1px solid #eee'),('padding','7px')]}
    ]))
display(Markdown(f'### พื้นที่เลือก: {name} · เดือน {MONTH} ปี {YEAR + 543}'))
print(f'อากาศรายเดือน {len(weather):,} แถว; ผลผลิตรายเดือนที่มีระเบียน {len(harvest):,} แถว')'''),
md('## 2. เปรียบเทียบห้าจังหวัดในเดือนเดียวกัน\nอากาศจุดอ้างอิงจังหวัด ไม่ใช่ค่าเฉลี่ยเชิงพื้นที่จังหวัดหรืออำเภอ ฝนเดือนที่วันไม่ครบคือยอดเฉพาะวันที่มีค่า'),
code('''selected_weather = weather[(weather.year_ce == YEAR) & (weather.month == MONTH)]
selected_harvest = harvest[(harvest.year_ce == YEAR) & (harvest.month == MONTH)]
comparison = points[['province_code', 'province_name']].merge(selected_weather, on='province_code', how='left', validate='one_to_one').merge(selected_harvest[['province_code', 'tonnes']], on='province_code', how='left', validate='one_to_one')
table(comparison[['province_name','temperature_c','rain_mm','humidity_pct','solar_mj_m2_day','tonnes']].rename(columns={
    'province_name':'จังหวัด','temperature_c':'อุณหภูมิ °C','rain_mm':'ฝนรวม มม.',
    'humidity_pct':'RH %','solar_mj_m2_day':'แสง MJ/m²/วัน','tonnes':'ผลผลิต ตัน'}))
table(comparison[['province_name','days_temperature','days_rain','expected_days']].rename(columns={
    'province_name':'จังหวัด','days_temperature':'วันมีอุณหภูมิ','days_rain':'วันมีฝน','expected_days':'วันทั้งเดือน'}))'''),
md('## 3. อากาศและผลผลิตทั้งปีของจังหวัดที่เลือก\nแยกแกนคนละกราฟเพราะหน่วยต่างกัน เส้นขาดคือข้อมูลหาย ไม่ใช่ศูนย์ ไม่มีช่วงความเชื่อมั่นในต้นทาง และกราฟนี้ไม่พิสูจน์สาเหตุของผลผลิต'),
code('''plt.rcParams.update({'font.family':'Tahoma','font.size':12,'axes.spines.top':False,
                     'axes.spines.right':False,'axes.edgecolor':'#6F6F6F',
                     'figure.facecolor':'white','axes.facecolor':'white'})
months = pd.DataFrame({'month': range(1,13)})
year_data = months.merge(weather[(weather.province_code == PROVINCE) & (weather.year_ce == YEAR)], on='month', how='left', validate='one_to_one')
year_data = year_data.merge(harvest[(harvest.province_code == PROVINCE) & (harvest.year_ce == YEAR)][['month','tonnes']], on='month', how='left', validate='one_to_one')
fig, axes = plt.subplots(3, 1, figsize=(10,9), sharex=True, constrained_layout=True)
for ax, metric, title in zip(axes, ['temperature_c','rain_mm','tonnes'], ['อุณหภูมิเฉลี่ย (°C)','ฝนรวม (มม.)','ผลผลิตทั้งจังหวัด ทุกพันธุ์ (ตัน)']):
    if metric == 'tonnes':
        ax.bar(year_data.month, year_data[metric], color='#1F6F5F', width=.65)
        ax.set_ylim(bottom=0)
    else:
        ax.plot(year_data.month, year_data[metric], color='#1F6F5F', marker='o', linewidth=1.7)
        if metric == 'rain_mm': ax.set_ylim(bottom=0)
    ax.set_title(title, loc='left', fontsize=13)
    ax.grid(axis='y', color='#E8E8E5', linewidth=.6)
    ax.set_axisbelow(True)
    if not year_data[metric].notna().any():
        ax.text(.5,.5,'ไม่มีข้อมูลในปีนี้',transform=ax.transAxes,ha='center')
axes[-1].set_xticks(range(1,13))
axes[-1].set_xlabel('เดือน')
fig.suptitle(f'{name} ปี {YEAR + 543} — อากาศจุดอ้างอิงและผลผลิตจังหวัด', fontsize=15)
plt.show()
display(Markdown('แหล่ง: [NASA POWER](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) และ [สศก. รายเดือน](https://catalog.oae.go.th/dataset/durian_product_month)'))'''),
md('## 4. ช่วงนี้เป็นระยะไหน\nกรอบหมอนทองในฤดูตามคู่มือ ไม่ยืนยันต้นจริง ภาคใต้มีหลายระยะทับซ้อนกันในระดับภูมิภาค ไม่หมายถึงต้นเดียวอยู่ทุกระยะพร้อมกัน'),
code('''region = next(r for r in evidence['regions'].values() if PROVINCE in r['provinces'])
calendar_rows = []
for month in range(1,13):
    phases = [evidence['stages'][p['stage']]['short'] for p in region['periods'] if month in p['months']]
    calendar_rows.append({'เดือน':month, 'กรอบระยะทั่วไป':' / '.join(phases)})
table(pd.DataFrame(calendar_rows))
source = evidence['calendar_source']
display(Markdown(f"ที่มา: [{source['title']}]({source['url']}) · {source['locator']}"))
display(Markdown('**เดือนที่เลือก:** ' + calendar_rows[MONTH-1]['กรอบระยะทั่วไป']))'''),
md('## 5. ข่าวและรายงานที่ตรงเดือน–ปี\nกรองตามเดือนเกิดเหตุหรือวันกำหนด ไม่ใช่เดือนเผยแพร่ข่าว ข่าวปีอื่นไม่ถูกนำมาแทน'),
code('''events = [e for e in evidence['events'] if e['province_code'] == PROVINCE and e['year'] == YEAR and MONTH in e['months']]
if not events:
    display(Markdown('ยังไม่มีรายงานที่ตรวจยืนยันในฐานสำหรับเดือน–ปีนี้ **ไม่ได้แปลว่าไม่มีเหตุการณ์**'))
for e in events:
    display(Markdown(f"### {e['title']}\\n{e['summary']}\\n\\nวันเหตุ/กำหนด: {e['event_date']} · เผยแพร่: {e.get('published_date') or 'ไม่ระบุ'}\\n\\n[อ่านต้นทาง]({e['url']})"))'''),
md('## 6. ข้อมูลดินในจังหวัด\nเป็นคุณสมบัติตามแผนที่ ไม่ใช่ผลตรวจดินสวนปัจจุบัน ตารางตัวอย่างไม่ใช่จัดอันดับพื้นที่ปลูก ห้ามแจกผลผลิตจังหวัดลงดินแต่ละชุด'),
code('''soil = pd.read_csv(base / 'soil_properties_by_district.csv')
province_column = 'province' if 'province' in soil.columns else 'province_name'
selected_soil = soil[soil[province_column].astype(str).str.contains(name, regex=False)]
print(f'พบ {len(selected_soil):,} ระเบียน แสดง 10 แถวแรก')
table(selected_soil[['district','soil_code','soil_name','fertility','topsoil_ph','topsoil_texture']].head(10).rename(columns={
    'district':'อำเภอ','soil_code':'รหัสดิน','soil_name':'ชุดดิน','fertility':'ความอุดมสมบูรณ์','topsoil_ph':'ปฏิกิริยาดิน','topsoil_texture':'เนื้อดิน'}))
display(Markdown('ที่มา: กรมพัฒนาที่ดิน ปี 2561 แผนที่ต้นฉบับ 1:25,000 ไม่ใช้ระบุแนวเขตแปลง'))'''),
md('## 7. ข้อมูลที่เตรียมไว้เทรน\nชุดนี้ยังไม่ได้ฝึกโมเดล เป้าหมายคือผลผลิตรายเดือนระดับจังหวัด ไม่ใช่โรคหรือสุขภาพต้น และไม่มีเซนเซอร์สวน/ค่า gateway ค้างปะปน'),
code('''training = pd.read_csv(base / 'training/monthly_model_panel.csv', dtype={'province_code':str})
usable = training[training.eligible_for_baseline.eq(1)]
table(usable.groupby('suggested_split').size().rename('แถวที่เข้าเงื่อนไข').reset_index())
display(Markdown(f'มีข้อมูลทั้งหมด **{len(training):,} แถว** เข้าเงื่อนไขเบื้องต้น **{len(usable):,} แถว** ไม่เติม target ที่ขาดเป็นศูนย์'))
print('ไฟล์ข้อมูล:', base / 'training/monthly_model_panel.csv')
print('รวมไฟล์สำหรับย้ายเครื่อง:', base / 'training/training_bundle.zip')'''),
md('''## ข้อสรุปที่ใช้ได้และสิ่งที่ยังไม่ทราบ
- ใช้ดูว่าเดือนเดียวกันแต่ละจังหวัดมีอากาศและผลผลิตต่างกันอย่างไร แล้วตั้งคำถามวิจัยต่อ
- ระยะทั่วไปไม่ใช่ label ระยะจริงของต้น ส่วนข่าวเป็นทะเบียนตัวอย่างที่ยังไม่ครบทุกพื้นที่
- ยังสรุปไม่ได้ว่าอากาศทำให้ดอก/ผลร่วงกี่ตัน หรือต้นในสวนต้องให้น้ำเท่าใด ต้องมีวันระยะจริง การจัดการ และผลสังเกตต้น
- อากาศปี 2569 เป็นช่วงไม่ครบปี ผลผลิตที่รวบรวมถึงปี 2568 ไม่ควรเปรียบเทียบยอดทั้งปีกับปีที่ยังไม่ครบ

### ไฟล์ที่ควรใช้
**กลับมาเปิด `00_OPEN_ME.ipynb` ไฟล์นี้เป็นหลัก**
ข้อมูลต้นทางยังอยู่ใน `research_data/five_province_history/` ไม่ต้องเปิดไฟล์ HTML ใน `tools/`
คู่มือแหล่งอ้างอิง: `research_data/five_province_history/PHENOLOGY_SOURCES_TH.md`
คู่มือเทรน: `research_data/five_province_history/training/README_TH.md`''')])
nb.metadata['kernelspec'] = {'display_name':'Python (durian analysis)', 'language':'python','name':'python3'}
km = KernelManager(kernel_name='python3')
km.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
NotebookClient(nb, km=km, timeout=120, resources={'metadata':{'path':str(ROOT)}}).execute()
nbformat.validate(nb)
nbformat.write(nb, ROOT / '00_OPEN_ME.ipynb')
preview = ROOT / '.build/monthly_notebook_preview.html'
body, _ = HTMLExporter().from_notebook_node(nb)
preview.write_text(body, encoding='utf-8')
# QA previews stay out of the user's top-level folder.
import base64
for cell in nb.cells:
    for output in cell.get('outputs', []):
        if 'image/png' in output.get('data', {}):
            (ROOT / '.build/monthly_notebook_chart.png').write_bytes(base64.b64decode(output['data']['image/png']))
print('Saved executed notebook:', ROOT / '00_OPEN_ME.ipynb')
