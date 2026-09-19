"""Build and execute the local, source-backed soil inspection notebook."""
from pathlib import Path
import sys

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks/04_soil_drydown_review.ipynb"

cells = [
    nbf.v4.new_markdown_cell("""# ตรวจความชื้นดินช่วงฟื้นต้น — 19 กันยายน 2026

## TL;DR
สองเหตุการณ์ที่มีสัญญาณฝนใกล้จุดสูงสุด วันที่ 12 และ 13 กันยายน มีค่าดินลดจาก 62.7 และ 58.1% เหลือ 43.7 และ 43.8% หลัง 3 ชั่วโมง ไม่ใช่หลักฐานว่าทุเรียนมีน้ำพอหรือขาดน้ำ

Notebook นี้เป็นการตรวจเชิงตัวเลข ไม่ใช่โมเดลพยากรณ์หรือคำสั่งให้น้ำ และไม่เขียนกลับ Google Sheets

## Context and methods
ผู้ใช้แจ้งว่าทุเรียนหมอนทองอายุ 9 ปีอยู่ช่วงฟื้นต้น เซนเซอร์แนวตั้งชายพุ่ม ลงจากผิวดิน 12 นิ้ว ยังไม่มีข้อมูลสอบเทียบหรือช่วงรากที่ดูดน้ำจริง

[แหล่งต้นทาง: Farm IoT Data](https://docs.google.com/spreadsheets/d/1-CDRERyx20UNCy5Oq3a8wt4lv3SmBx9nH2Kf2IQZvVE/edit), แท็บ `readings_15min`, A1:Z2410; สำเนา 2026-09-19 06:24:05 UTC; เวลาทั้งหมดที่รายงานเป็น Asia/Bangkok

เลือกกลุ่มค่าดิน >=50% และจุดสูงสุดของกลุ่ม โดยแยกเมื่อข้อมูลห่าง >30 นาที ตรวจสัญญาณฝน ±1 ชั่วโมง หาจุด +1/+2/+3 ชั่วโมงแบบเวลาตรงกัน ไม่ประมาณค่าขาด เกณฑ์ 50/40 ใช้ตรวจข้อสังเกต ไม่ใช่เกณฑ์พืชขาดน้ำ
"""),
    nbf.v4.new_code_cell("""from pathlib import Path
import sys
import json
import pandas as pd

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents]
            if (p / 'tools/analyze_live_soil_drydown.py').exists())
if str(ROOT / 'tools') not in sys.path:
    sys.path.insert(0, str(ROOT / 'tools'))
from analyze_live_soil_drydown import inspect_snapshot
df, profile, daily, events, gaps, flatlines = inspect_snapshot()
print(json.dumps(profile, ensure_ascii=False, indent=2))"""),
    nbf.v4.new_markdown_cell("""## Data quality
กฎอากาศค้างคือ outdoor temperature, outdoor humidity, pressure, light และ UV ไม่เปลี่ยนพร้อมกันอย่างน้อย 60 นาที โดยแยกเมื่อช่วงห่าง >30 นาที ปิดใช้คอลัมน์อากาศเฉพาะสำเนาวิเคราะห์ แต่คงข้อมูลดินทุกแถว กฎนี้อาจจับช่วงนิ่งจริงด้วย ไม่ใช่เวลาปลั๊กหลุดที่ยืนยันแล้ว

ความครบถ้วนคำนวณจากสมมติฐานว่าส่งทุก 15 นาทีตลอดช่วงแรกถึงสุดท้าย ไม่มีการสรุปสาเหตุข้อมูลขาด และไม่บวกค่าฝน rolling 1h/24h เป็นผลรวมฝนรายวัน
"""),
    nbf.v4.new_code_cell("""print(f\"Observed slots: {profile['rows']}/{profile['expected_15min_slots']}\")
print(f\"Missing slots: {profile['missing_15min_slots']}\")
print(f\"Suspected weather flatlines: {profile['additional_weather_flatline_rows']} rows\")
print(daily.tail(12).to_string(index=False))
print(gaps.tail(10).to_string(index=False))"""),
    nbf.v4.new_markdown_cell("""## Results: first three hours
แสดงทุกเหตุการณ์ที่ถึง 50% ก่อน จึงไม่ซ่อนกรณีที่ข้อมูลฝนใช้ไม่ได้ `rain_not_established` ไม่ได้แปลว่าไม่มีฝน
"""),
    nbf.v4.new_code_cell("""cols = ['peak_time_th', 'peak_sheet_row', 'peak_moisture',
        'moisture_1h', 'moisture_2h', 'moisture_3h', 'rain_attribution']
print(events[cols].to_string(index=False))

confirmed = events.loc[events.rain_attribution.eq('rain_signal_present')].copy()
assert confirmed.peak_sheet_row.tolist() == [1986, 2055]
assert confirmed.peak_moisture.tolist() == [62.7, 58.1]
assert confirmed.moisture_3h.tolist() == [43.7, 43.8]
print('Both selected 0-3h windows cross-checked against live formatted Sheet ranges.')"""),
    nbf.v4.new_code_cell("""# Display the 26 exact observations, not interpolated values.
for peak in confirmed.itertuples():
    t = pd.Timestamp(peak.peak_time_th)
    window = df.loc[df.timestamp_th.between(t, t + pd.Timedelta(hours=3))]
    assert len(window) == 13
    assert window.timestamp.diff().iloc[1:].eq(pd.Timedelta(minutes=15)).all()
    print(window[['sheet_row', 'timestamp_th', 'soil_moisture_percent']].to_string(index=False))"""),
    nbf.v4.new_markdown_cell("""## Takeaways and limits

- การลดเร็วช่วงแรกเกิดขึ้นจริง แต่ไม่ทราบสัดส่วนที่เป็นการระบายน้ำ การกระจายตัว น้ำที่พืชใช้ หรือความคลาดเคลื่อนหัววัด
- วันที่ 12 กันยายนพบค่าครั้งแรก <=40% เวลา 21:15; วันถัดไปเวลา 14:00 อ่านได้ 33.1% นี่คือค่าที่วัดตามเวลา ไม่ใช่การยืนยันว่าตลอดช่วงไม่มีฝนซ้ำ
- วันที่ 13 กันยายนมีช่องว่างข้อมูลก่อนพบค่า <=40% จึงไม่ใช้ค่านั้นระบุเวลาข้ามเกณฑ์ที่แน่นอน
- ค่าฝนใช้ไม่ได้ในหลายช่วง ไม่ใช้ค่าว่างแทนศูนย์และไม่เรียกวันนั้นว่าไม่มีฝน
- จุด +24/+48 ชั่วโมงอาจมีฝนซ้ำ ยังไม่ได้ตัดช่วงที่เปียกซ้ำออกจาก dry-down event
- เซนเซอร์หนึ่งจุดไม่เป็นตัวแทนน้ำทั้งเขตราก ค่า 31.3% ล่าสุดไม่ได้แปลว่าน้ำเหลือให้ใช้ 31.3%
- ขั้นต่อไป: เทียบกับดินจริง/การสอบเทียบ และวัดการเก็บน้ำของดินก่อนกำหนดเกณฑ์แจ้งเตือนในช่วงฟื้นต้น ไม่มีเกณฑ์ปั๊มหรือปริมาณลิตรที่ยืนยันจากการตรวจครั้งนี้

## Sources and rerun
[University of Minnesota Extension — Soil moisture sensors for irrigation scheduling](https://extension.umn.edu/natural-resources/conservation/agricultural-soil-and-water/irrigation/soil-moisture-sensors-for-irrigation-scheduling) อธิบาย field capacity, available water และการสอบเทียบ เป็นหลักการทั่วไป ไม่ใช่ค่ามาตรฐานทุเรียน

โค้ด `tools/analyze_live_soil_drydown.py`; สำเนา `data/analysis_soil_2026-09-19/live_readings_snapshot.json`; รายละเอียด `docs/SOIL_DRYDOWN_REVIEW_2026-09-19_TH.md` ภายในโครงการนี้

เปิดใน VS Code เลือก Python `.build/national-analysis-venv` แล้ว Run All ไม่ต้องล็อกอิน GitHub สำเนาดิบอยู่ในเครื่องเท่านั้น ไม่ถูก commit หรือ push
"""),
]

nb = nbf.v4.new_notebook(cells=cells)
nb.metadata.kernelspec = {
    "display_name": "Python (durian-national)", "language": "python", "name": "durian-national"
}
nb.metadata.language_info = {"name": "python", "version": sys.version.split()[0]}
NotebookClient(nb, timeout=90, kernel_name="durian-national", resources={"metadata": {"path": str(ROOT)}}).execute()
nbf.validate(nb)
OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUT)
print(f"Executed and saved: {OUT}")
