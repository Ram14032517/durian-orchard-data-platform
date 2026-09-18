# จุดส่งต่องาน 18 กันยายน 2569

## ทำแล้วในรอบนี้

1. LDD 3จังหวัดเพิ่ม ชุมพร/ศรีสะเกษ/อุตรดิตถ์ พร้อม provenance; รวมจันทบุรีเป็น4จังหวัด
2. GIS full geometry soil×A403 แยกmixed; สร้าง59จุดในA403และน้ำหนัก; เก็บmanifest/QA
3. NASA monthly2006–2025ครบ14,160จุด–เดือน →960จังหวัด–เดือน →80จังหวัด–ปี เชื่อมOAEครบ
4. Notebook03รันnativeครบ มีกราฟดิน/วิธีเลือกอากาศ/อากาศย้อนหลัง และbaselineผลผลิตต่อไร่
5. แผนที่เดิมและnotebook02อัปเดตสถานะดิน4จังหวัด แต่อากาศยังเป็นจุดอ้างอิงจังหวัดเดิม ไม่ปนชุดใหม่
6. Tests7ใหม่+6เดิมผ่าน; browserตรวจprovince missing/รายละเอียดและmobile; PNG3ภาพกับgrayscaleผ่านตรวจสายตา

## เปิดผล

- `C:/project/research_data/regional_orchards/ANALYSIS_NOTEBOOK.html`
- `C:/project/notebooks/03_regional_orchards_soil_weather.ipynb`
- `C:/project/research_data/thailand_comparison/THAILAND_MAP.html`
- วิธีทำซ้ำ/แหล่ง/คำจำกัดความ/QA: `C:/project/research_data/regional_orchards/README_TH.md`
- Python: `C:/project/.build/national-analysis-venv/Scripts/python.exe`; kernel durian-national; ไม่แก้ .venvเดิมที่เสีย
- previewชั่วคราว localhost8866 bind127.0.0.1 directoryเฉพาะresearch_data; ไฟล์HTMLเปิดได้แม้serverหยุด

## ข้อค้นพบสำหรับคุยอาจารย์

อุตรดิตถ์95.96%ของพื้นที่รหัสที่มีA403เป็นmixed; A403ตรงตัวมี2,377ไร่และ87.0%ซ้อนSC(ไม่ใช่ชุดดินเฉพาะ)
ศรีสะเกษ58.9%ของA403ตรงตัวซ้อนหน่วยโชคชัย; ไม่ใช่ผลพิสูจน์ความเหมาะสม/เหตุผลผลิตสูง
baselineปีก่อน MAE189.8กก./ไร่ดีกว่าค่าเฉลี่ย5ปีก่อน209.4ในผลรวม60ตัวอย่าง แต่เป็นretrospective ไม่ใช่liveforecast

## ทำต่อ

1. ตกลงเป้าหมายจังหวัด–ปีและหน้าต่างออกดอก/ติดผลกับอาจารย์
2. แก้coverageสวนผสมและข้อมูลแผนที่ให้สอดคล้องเวลา; ทดสอบความไวกรอบsampling ไม่ถือ59จุดเป็นสถานีอิสระ
3. เพิ่มdaily weatherเพื่อdry spell/extremes; ไม่อนุมานextremesจากmonthlymeans
4. โมเดลพื้นฐานอย่างง่าย + walk-forward/held-outprovince เทียบbaseline; ห้ามใช้footprintอนาคตแล้วอ้างไร้leakage
5. ตีพิมพ์ต้องยืนยันlicense โดยเฉพาะ LDD NC-ND ก่อน ไม่publicdatasetอัตโนมัติ

## ขอบเขต / quota

repoตรวจremoteแล้วคือ Ram14032517/durian-orchard-data-platform เท่านั้น ไม่แตะrepoอื่น ไม่login ไม่push
เก็บraw/derived/กราฟ/executednotebookไว้ในเครื่องและignoreGit; commitเฉพาะโค้ดและเอกสารรอบนี้
คงdirtyเดิม .gitignore, google-apps-script/Code.gs, ml/train_statistical_baseline.py, models/statistical_baseline.json และuntrackedเดิม
ล่าสุดก่อนcheckpoint:5ชั่วโมงใช้85%,รายสัปดาห์68%; ไม่ใช้resetcredit
