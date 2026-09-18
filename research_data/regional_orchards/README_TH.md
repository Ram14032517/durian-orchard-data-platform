# เริ่มอ่านผลวิเคราะห์ 4 จังหวัดข้ามภาค

ปรับปรุง 18 กันยายน 2569 — ข้อมูล/ผลวิเคราะห์อยู่ในเครื่อง ยังไม่เผยแพร่

## เปิดไฟล์ไหน

1. [ANALYSIS_NOTEBOOK.html](ANALYSIS_NOTEBOOK.html) — อ่านตาราง กราฟ วิธีคิด และข้อจำกัดโดยไม่ต้องรันโค้ด
2. [03_regional_orchards_soil_weather.ipynb](../../notebooks/03_regional_orchards_soil_weather.ipynb) — เปิดใน VS Code / Jupyter เพื่อเรียนและ Run All
3. [แผนที่ประเทศไทย](../thailand_comparison/THAILAND_MAP.html) — กดจังหวัดดูดินได้ 4 จังหวัด; อากาศแผนที่ยังใช้จุดอ้างอิงจังหวัดเดิม
4. [regional_province_year_panel.csv](regional_province_year_panel.csv) — ตารางอากาศ/ผลผลิต 80 จังหวัด–ปี สำหรับศึกษาโมเดลต่อ
5. [SOURCE_TH.md](SOURCE_TH.md), [DATA_DICTIONARY_TH.md](DATA_DICTIONARY_TH.md), [VALIDATION_TH.md](VALIDATION_TH.md) — หลักฐานและข้อควรระวัง

## สิ่งที่เพิ่มจริง

- LDD soil × land use: จันทบุรี (2568), ชุมพร (2564), ศรีสะเกษ (2565), อุตรดิตถ์ (2563); ดินปีผลิต 2561
- จุดในพื้นที่ A403 ตรงตัว 59 จุด ถ่วงน้ำหนักด้วยพื้นที่แบ่งชั้น ไม่ใช่สถานีอากาศ 59 สถานี
- NASA POWER 2006–2025: 14,160 จุด–เดือน → 960 จังหวัด–เดือน → 80 จังหวัด–ปี; ไม่ขาดระเบียนอากาศหรือผลผลิตใน panel นี้
- แยกรหัสปลูกผสม ไม่สมมติว่าพื้นที่ทั้งหมดเป็นทุเรียนล้วน
- baseline ผลผลิตต่อไร่ 2011–2025: ใช้ปีก่อน MAE 189.8 กก./ไร่; เฉลี่ย 5 ปีก่อน MAE 209.4 กก./ไร่ (60 แถวทดสอบเดียวกัน)
- native Jupyter execution; กราฟ 3 ชุด PNG + SVG; แผนที่เดิมแสดงดินที่เพิ่มแล้ว

## ค้นพบและคำแปลที่ถูกต้อง

- อุตรดิตถ์ 95.96% ของพื้นที่ polygon ที่มีรหัส A403 เป็นรหัสผสม ไม่ใช่สัดส่วนจำนวนต้น; อากาศชุดนี้ใช้ A403 ตรงตัวเท่านั้น จึงยังแทนพื้นที่ปลูกทั้งหมดไม่ได้
- A403 ตรงตัวอุตรดิตถ์ซ้อนหน่วย SC 87.0%; SC เป็นพื้นที่ลาดชันเชิงซ้อน ไม่ใช่ชื่อชุดดินละเอียด
- ศรีสะเกษ A403 ตรงตัวซ้อนหน่วยดินโชคชัย 58.9%; นี่คือสัดส่วนพื้นที่ ไม่ใช่หลักฐานว่าดินนั้นทำให้ผลผลิตดีที่สุด
- ค่าอากาศเปลี่ยนตามตำแหน่งที่เลือก; ต้องตรวจเทียบกับสถานีจริงก่อนอ้างว่าวิธีใหม่แม่นกว่า
- ยังไม่มีโมเดลอากาศที่ผ่าน validation หรือผลเชิงเหตุและผลของอุณหภูมิ ±1°C

## ทำซ้ำในเครื่องนี้

ใช้ Python `C:/project/.build/national-analysis-venv/Scripts/python.exe`
ใน VS Code เลือก kernel นี้ ไม่จำเป็นต้องล็อกอิน GitHub

```powershell
$env:PYTHONUTF8='1'
& .\.build\national-analysis-venv\Scripts\python.exe tools/fetch_regional_ldd.py
& .\.build\national-analysis-venv\Scripts\python.exe tools/prepare_regional_orchards.py
& .\.build\national-analysis-venv\Scripts\python.exe tools/fetch_orchard_weather.py
& .\.build\national-analysis-venv\Scripts\python.exe tools/build_regional_notebook.py
& .\.build\national-analysis-venv\Scripts\python.exe tools/test_regional_orchards.py
```

ต้องมี raw จันทบุรีและ OAE จากขั้นก่อน ดู README ของ `soil_evidence_chanthaburi` และ `thailand_comparison`
`fetch` ใช้ไฟล์ cache ที่มีอยู่ ไม่ดาวน์โหลดทับอัตโนมัติ; หากต้องเปลี่ยนข้อมูล ให้สร้าง snapshot ใหม่มีวันที่/manifest ใหม่

ลำดับถัดไป: คุยอาจารย์เรื่องช่วงฤดู/หน่วยเป้าหมาย → เพิ่มข้อมูลปลูกผสม/แผนที่ให้ตรงเวลา → ตัวแปรรายวัน → time-aware validation
อย่านำผลผลิตจังหวัดไปแจกเป็น label ของแต่ละ polygon หรือแต่ละชุดดิน
