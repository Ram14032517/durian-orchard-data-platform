# Checkpoint: ตามโจทย์อาจารย์ — ข้อมูลทุเรียน ดิน อากาศ ผลผลิต

บันทึกเมื่อusageรอบ5ชั่วโมงถึง80% / รายสัปดาห์52% ตามคำขอผู้ใช้
commitเฉพาะโค้ด/คำอธิบายงานรอบนี้ใน durian-orchard-data-platform ไม่push ไม่login
ไม่รวมการแก้AppsScript/ML/model/.gitignoreหลักที่ค้างก่อนงานนี้ และไม่แตะrepoอื่น

## เปิดผลงาน

- `research_data/thailand_comparison/THAILAND_MAP.html` แผนที่77จังหวัดกดได้
- `research_data/thailand_comparison/ANALYSIS_NOTEBOOK.html` ผลวิเคราะห์อ่านง่าย
- `notebooks/02_thailand_durian_comparison.ipynb` Jupyterรันจริง7cellsแล้ว
- `research_data/thailand_comparison/README_TH.md` วิธีเปิด ข้อค้นพบ และแผนต่อ
- `research_data/thailand_comparison/VALIDATION_TH.md` ผลทดสอบ6testsและvisualQA

## สิ่งที่สร้างรอบนี้

1. `prepare_national_comparison.py`: cache+SHA provenance, ขอบเขตGISTDA77จังหวัด,
   ตารางผลผลิตOAEจังหวัด/ประเทศ, NASA4parameters×77points×60months → panel385แถว
2. `build_national_notebook.py` + `national_map_controls.html`: nativeJupyter
   country/region summaries, source reconciliation, 3charts, Foliumofflineinteractive map,
   year/metric/region/province/2-province selectors และsource/gapwarnings
3. `test_national_comparison.py`: ตรวจsource/key/missing/unit/aggregation/nativeoutputs
4. isolatedvenv+kernelชื่อdurian-national ไม่มีการแก้Anacondaหรือvenvเดิม

## ประเด็นตรวจพบ

- DPMจังหวัดมี76featuresขาดสตูล จึงเปลี่ยนgeometryทั้งหมดเป็นGISTDA77
- DPMใช้เฉพาะREGION_6และเติมสตูลภาคใต้; ไม่อ้างว่าเป็นOAEregionaldefinition
- OAE2025มี67จังหวัด; ปี2021–2025มี49,59,59,67,67ระเบียนจังหวัดตามลำดับ
- ผลรวมประเทศปี2025ต่างต้นทาง0.31ตันคงไว้;2024ต่าง0.77ตัน
- NASAหน่วยฝนmm/dayจึงต้องคูณdaysก่อนsum;ใช้months01–12ไม่sumเดือน13
- ชุดดินที่ซ้อนแปลงแล้วมีจันทบุรีเท่านั้น ไม่ใส่ดินสมมติให้จังหวัดอื่น
- pointweatherเป็นrepresentative_pointของจังหวัด ไม่ใช่พิกัดทุเรียน ต้องแก้ระดับข้อมูลก่อนโมเดลจริง

## งานต่อที่สำคัญ — อย่าเรียกงานวิจัยเสร็จแล้ว

ขยายLDDsoil+land-useจังหวัดข้ามภาค (ชุมพร/ศรีสะเกษ/อุตรดิตถ์เป็นจังหวัดที่เสนอจากOAE)
แล้วสกัดA403จริง หลายจุด/พื้นที่ถ่วงกริดอากาศ ขยายย้อนหลัง แบ่งฤดูตามภูมิภาค
อย่ากระจายผลผลิตจังหวัดเป็นlabelผลผลิตแต่ละsoilpolygon
โมเดลต้องมีbaseline, timesplit, held-outprovince, uncertainty, factorconfounding
อุณหภูมิ±1°Cเป็นscenarioไม่ใช่causalforecastโดยอัตโนมัติ
ก่อนเผยแพร่datasetต้องยืนยันสิทธิ์OAE/LDD/GISTDAและทำdictionary/versioning

raw/derivedoutputsและnotebookมีข้อมูลสืบเนื่องที่ยังตรวจสิทธิ์ไม่ครบ จึงgitignoreไว้ในเครื่อง
code+provenance+วิธีรันเก็บในgit; ไม่มีrawสวนส่วนตัวถูกอัปโหลด
