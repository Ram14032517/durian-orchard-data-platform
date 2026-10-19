# Phase 11A — ความพร้อมข้อมูลผลผลิตทุเรียนพื้นที่ย่อยจันทบุรี

12 ตุลาคม 2026 · Feasibility Audit เท่านั้น · Internal Only / **Public HOLD**

## ข้อสรุป

**ยังไม่พบตารางผลผลิต–พื้นที่ให้ผลระดับอำเภอ ตำบล หรือสวนของจันทบุรีที่ยืนยันได้ใน Assets ที่ตรวจ** จึงยังศึกษาความสัมพันธ์ดิน–อุณหภูมิ–Yield ในพื้นที่ย่อยจากข้อมูลเดิมไม่ได้ ไม่ควรสร้าง Target ด้วยการกระจายยอด OAE จังหวัดลง A403

ทำได้ทันทีโดยไม่สร้างข้อมูลสมมติ: อธิบายองค์ประกอบหน่วยแผนที่ดินภายใน Pure A403 ของท่าใหม่ และตรวจข้อจำกัดของ Weather Exposure ที่มี ส่วนการวิเคราะห์ Weather–Yield ระดับจังหวัดใช้ข้อมูลจริงเดิมได้ในเชิง Exploratory แต่ตอบความแตกต่างระหว่างสวน/อำเภอไม่ได้

## 1. สิ่งที่พบจริงและขอบเขตการตรวจ

| Assets เดิม | Grain / Coverage ที่ยืนยันไว้ | ใช้เป็น Target พื้นที่ย่อยจันทบุรีได้หรือไม่ |
|---|---|---|
| OAE `durian_province.xlsx`, Phase 9D | จังหวัด–ปี; จันทบุรี 2006–2025 ครบ 20 ปี ตาม QC Phase 9D | ไม่ได้ |
| `production_source_review.json`, เอกสารจันทบุรี เม.ย. 2569 | ยอดจังหวัดปีผลผลิต 2568; ไม่ใช่ปีรายงาน 2569 และไม่ใช่ตารางอำเภอ | ไม่ได้ |
| ทะเบียนหลักฐานอุตรดิตถ์ | 14 อำเภอ–ปีใน 2020/2021, 8 แถวมี Production/Bearing Area ครบ, 6 แถวมีค่าหาย; Finality ยังไม่ยืนยัน | พบข้อมูลพื้นที่ย่อยจริง แต่คนละจังหวัด ไม่ทดแทนจันทบุรี |
| Phase 10F/10G ท่าใหม่ | Pure A403 1,504 Fragments, Soil Composition 43 แถว รวม Uncovered | มี Soil Exposure หนึ่งอำเภอ ไม่มี Yield |
| `district_reference_points.csv`, `district_soil_exploration.csv`, `soil_properties_by_district.csv` | จุดอ้างอิง/ข้อมูลดิน ตาม Inventory Phase 10A | ไม่ใช่ผลผลิตหรือพื้นที่ให้ผล |
| Workbook สวน 2 สำเนาที่ตรวจหัวตาราง | `readings_15min`, `forecast_hourly`, `forecast_daily`, `ndvi_daily` และชีตที่ไม่พบหัวตารางแถวแรก | ไม่พบคอลัมน์น้ำหนักเก็บเกี่ยว/Bearing Area/ผลผลิตสวน–ปีในหัวตารางที่ตรวจ |

Workbook สวนเป็นข้อมูลเซนเซอร์/พยากรณ์ ไม่ใช่ Harvest Ledger ที่ยืนยันแล้ว ตรวจทุก Sheet เฉพาะหัวตาราง ไม่อ่าน/แสดงแถวข้อมูลส่วนตัว และไม่อนุมานจำนวนแถวจาก `max_row=null` ข้อมูลออนไลน์ Supabase/ชีตล่าสุด/บันทึกนอกเครื่องยังไม่ได้ตรวจ จึงไม่กล่าวว่าไม่มีบันทึกเก็บเกี่ยวที่ใดเลย

ขอบเขตค้น: Inventory/รายงาน Phase 9D, 10A, 10F–10G, Source Review เดิม และชื่อไฟล์เกี่ยวข้องใต้ `data`/`research_data` รวม ignored files ไม่เปิด ZIP Backup ทุกไฟล์ ไม่ตรวจทุก Notebook/ทุกโฟลเดอร์ทั้งเครื่อง และไม่ค้นหรือดาวน์โหลดข้อมูลใหม่ภายนอก

## 2. Data Requirements ที่ต้องขอ

| ชุดข้อมูล | คีย์/เวลา/พื้นที่ | Measures และหน่วย | Metadata ที่ขาดไม่ได้ |
|---|---|---|---|
| อำเภอ–ปี | province_code `22`, district_code เป็น string เช่น `2203`, district_name, year_ce, crop/harvest_year และ season_id ถ้ามีหลายรอบ; Boundary Version/Code Crosswalk | Production ตันหรือกก.; Bearing Area ไร่; Planted Area ไร่แยกต่างหาก; Reported Yield กก./ไร่ | พืช/พันธุ์และขอบเขตประชากร, ฤดู/วันที่เริ่ม–สิ้นสุดเก็บเกี่ยว, วิธีสำรวจ/ประมาณการ, หน่วยก่อนแปลง, วันที่เผยแพร่/ปรับปรุง, Version/First-release/Revised/Forecast-vs-Actual, Missing Meaning, Rounding และ License |
| ตำบล–ปี (ถ้ามีจริง) | tambon_code + district_code + year/season และ Boundary Version; ตรวจว่าการรวมตำบลครบทั้งอำเภอหรือเป็นตัวอย่าง | Measures เช่นเดียวกับอำเภอ | ห้ามถือพื้นที่ตัวอย่างเป็น Census; เก็บ Sampling Coverage/Expansion Weights ถ้าผู้ผลิตข้อมูลใช้ |
| สวน–ปี/ฤดู | orchard_id แบบ Pseudonym ที่คงเดิม, year/season, รหัสตำบล/อำเภอ; Geometry/พิกัดที่เจ้าของยืนยันพร้อม CRS, Accuracy, Valid Period และ Consent | Total Harvest กก., Bearing Area ไร่, Bearing Trees จำนวนต้น; Grade/Discard/Loss/Sold Weight แยก ไม่ถือยอดขายเป็น Total Harvest โดยอัตโนมัติ | Cultivar/Mixed Cultivar, Tree Age, Density, Irrigation/วันที่ให้น้ำ, Pruning/Fertilizer, Flowering/Fruit-set/Harvest Dates, Disease/Storm Loss, วิธีชั่ง/แหล่งบันทึก/ความครบถ้วน, Source Version และสิทธิ์ใช้ข้อมูล |

ขอข้อมูลทุกปีที่หน่วยงานมีจริง พร้อมปีที่หาย ไม่กำหนดว่าต้องครบ 2006–2025 โดยไม่มีหลักฐาน ควรขอช่วงหลายปีต่อเนื่องและค่าก่อนปัดเศษ แต่จำนวนขั้นต่ำสำหรับทดสอบสถิติต้องพิจารณาหลังเห็นจำนวนหน่วยอิสระ/ความแปรปรวน ไม่อ้างว่า 5 หรือ 10 ปีเพียงพออัตโนมัติ

สูตรเมื่อ Production และ Bearing Area มีจริงและขอบเขต/ปีตรงกัน:
`derived_yield_kg_rai = production_tonnes × 1000 / bearing_area_rai`
คำนวณเฉพาะ Bearing Area > 0; Missing/ศูนย์ที่ไม่ชัดให้ null ไม่เติมศูนย์ เก็บ Reported Yield แยกจากค่าหารและบันทึก Rounding Difference ห้ามใช้ A403/Planted Area แทน Bearing Area หรือเฉลี่ย Yield อำเภอแบบไม่ถ่วงตัวหาร

## 3. แหล่งที่เสนอให้ขอข้อมูล — ยังไม่ติดต่อ

| แหล่ง | สิ่งที่ตรวจพบแล้ว | รายการที่ควรขอ/สถานะ |
|---|---|---|
| สำนักงานเกษตรและสหกรณ์จังหวัดจันทบุรี | มีรายงานยอดจังหวัดในทะเบียนเดิม [ต้นทางที่บันทึกไว้](https://www.opsmoac.go.th/chanthaburi-dwl-files-481291791849) | ถามว่ามีตาราง Production/Bearing Area/Yield แยก 10 อำเภอรายปีหรือไม่; ขอ Excel/CSV, Source Agency, Revision History และนิยามเอกภาพ **ตารางอำเภอยังไม่ยืนยัน** |
| สำนักงานเกษตรจังหวัดจันทบุรี / เกษตรอำเภอท่าใหม่ / กรมส่งเสริมการเกษตร | ใน Inventory นี้ยังไม่มี Target จันทบุรีที่ยืนยันจากหน่วยงานเหล่านี้ | ขอรายงานพืชเศรษฐกิจรายอำเภอ/ตำบล และจำนวนพื้นที่ให้ผลตามปี/พันธุ์; แยกทะเบียนผู้ปลูกออกจากผลเก็บเกี่ยวจริง **การมีทะเบียนไม่พิสูจน์ว่ามีน้ำหนักผลผลิต** |
| สศก. / หน่วยงานระดับเขตที่ดูแลจันทบุรี (เสนอ สศท.6 ให้ยืนยันผู้รับผิดชอบก่อน) | มี Workbook OAE ระดับจังหวัดจริงในโครงการ | ขอแจ้งว่าผลสำรวจเผยแพร่ได้ละเอียดถึงระดับใด, ค่ารายอำเภอ/ข้อมูลตัวอย่างมีหรือไม่, Weights/Precision/Publication Dates; ไม่สมมติว่าสามารถเปิด Microdata ได้ |
| กลุ่มแปลงใหญ่/สหกรณ์/เจ้าของสวนที่ยินยอม | พบเพียงไฟล์เซนเซอร์สวน ไม่พบ Harvest Ledger ที่ยืนยัน | ขอสมุดชั่ง/บันทึกผลผลิตหลายฤดู + Bearing Area/พันธุ์/การจัดการ; ตรวจว่าเป็นยอดสวนจริงหรือยอดรับซื้อรวมจากหลายสวน |
| อาจารย์/นักวิจัย/สถานีวิจัยพืชสวนในพื้นที่ | ยังไม่มี Dataset ทดลองระดับสวนที่ยืนยันใน Inventory | ขอระบุโครงการที่มี Plot ID, Treatment, Cultivar, Replication, Harvest Weight และพิกัดที่ใช้ได้; ตรวจสิทธิ์/การเลือกตัวอย่างก่อน Join |

รายชื่อที่เสนอเป็นช่องทางสอบถาม ไม่ใช่ข้อยืนยันว่าแต่ละแห่งมี Dataset พร้อมให้ใช้ URL ข้างต้นเป็นหลักฐานที่บันทึกไว้เดิม ไม่ได้เปิดตรวจเว็บไซต์สดในรอบนี้ ไม่มีส่งข้อความหรือคำขอข้อมูล และไม่มีติดต่อเจ้าของสวน

## 4. Join Feasibility และความเสี่ยง

**อำเภอ–ปี:** ต้อง Join Yield ด้วย district_code + year/season + Boundary Version; Soil ใช้ district + Land-use/Soil/Admin Map Vintages ไม่ทำให้ดินหนึ่งรุ่นกลายเป็นตัวอย่างอิสระทุกปี ปัจจุบัน Soil Composition แบบ Full-resolution ผ่าน Policy v2 เฉพาะท่าใหม่ จึงยังไม่รองรับการ Join เปรียบเทียบ 10 อำเภอ การมี code ตรงกันไม่พิสูจน์ว่า Pure A403 ปี 2568 ตรงกับพื้นที่ให้ผลของทุกปีหรือทุกพันธุ์

**Weather:** Cache จันทบุรีมี 16 จุด, 2006–2025; Phase 10A พบ 6 Meteorology Response Signatures และ 11 Combined Weather Signatures ไม่ใช่จำนวน Native Grids/สถานีอิสระ Native Grid IDs/Bounds ยังไม่ยืนยัน และ District–Stratum/Grid Area Weights ยังไม่มี ห้ามนำ Weight จังหวัดมาใช้เป็น District Exposure ต้องออกแบบแยกภายหลัง ไม่คำนวณในรอบนี้ Seasonal/Phenological Windows ต้องตรงกับฤดูและพันธุ์ ไม่สรุปจากอุณหภูมิเฉลี่ยทั้งปีแทนช่วงสำคัญโดยไม่มีเหตุผล

**สวน:** ต้องมีสวนที่เจ้าของยืนยันและช่วงเวลาขอบเขตใช้ได้ จึงพิจารณา Soil Map/Weather Footprint Join ได้ จุดเซนเซอร์เดียวไม่แทนสภาพทั้งสวน ต้องทราบตำแหน่ง/ความสูงติดตั้ง/Calibration/Data Gaps และจับคู่ Harvest Period ห้ามใช้ A403 Polygon เป็น orchard_id

**Confounding/Temporal Change:** พันธุ์ อายุ/สัดส่วนต้นให้ผล การให้น้ำช่วงติดผล ปุ๋ย โรค การตัดแต่ง และการขยายสวนอาจสัมพันธ์กับดิน/อุณหภูมิและผลผลิต ไม่มีข้อมูลเหล่านี้ยังแยกผลไม่ได้ Soil Production 2561 และ Land-use Map 2568 เป็นคนละ Vintage/ไม่ใช่ Survey Date ที่ยืนยัน; Soil Map Unit ไม่เท่ากับค่าดินตรวจจริงในสวน ความละเอียด POWER อาจไม่แยก Gradient ระหว่างพื้นที่ใกล้กันได้

## 5. Data Gap Matrix และโจทย์ที่ทำได้

| Gap | สถานะปัจจุบัน | ผลต่อโจทย์ / ลำดับ |
|---|---|---|
| จันทบุรี Production + Bearing Area พื้นที่ย่อยตามปี | ยังไม่พบ Target ที่ยืนยัน | **P1** ข้อมูลคู่นี้เป็น Gate ก่อนวิเคราะห์ความสัมพันธ์พื้นที่ย่อย |
| ปี/นิยาม/Finality/Publication/Revisions | ยอดจังหวัดมี; พื้นที่ย่อยยังต้องขอ | **P1** ป้องกัน Join ผิดฤดูและใช้ข้อมูลต่างฉบับ |
| Confirmed Orchard IDs/Harvest/Consent | ยังไม่พบคู่ข้อมูลพร้อมใช้ | **P1** หากเลือกการศึกษาระดับสวน |
| District Soil Composition หลายอำเภอ | ผ่านเฉพาะท่าใหม่ | **P2** ต้องอนุมัติงาน GIS แยกก่อนขยาย |
| District Weather Weights/Native Grid Evidence | ยังไม่พร้อม | **P2** ไม่สร้างอากาศละเอียดด้วยการ Rename Province Profile |
| Cultivar/Tree Age/Management/Phenology | มี Context บางส่วน ไม่ใช่ Panel หลายสวน | **P2** ลด Confounding/กำหนด Exposure Windows |
| Historical Bearing Footprints/Boundary Crosswalk | ยังไม่ยืนยัน | **P2** Static A403 ไม่ตรง Population ตามเวลาโดยอัตโนมัติ |
| Field Soil Measurements/Spatial Accuracy/License | ยังมีช่องว่าง; Public HOLD | **P3** การตีความและการเผยแพร่ยังจำกัด |

ทางเลือกตาม Yield ที่ได้จริง:

- **ข้อมูลเดิมเท่านั้น:** งาน Descriptive Soil Composition ของท่าใหม่ทำได้; Province Weather–Yield ใช้ 20 Province-years จันทบุรีเชิง Exploratory ได้ตามข้อจำกัด ไม่ตอบ Soil–Yield ระหว่างพื้นที่เพราะ Soil Snapshot เดียว ไม่มี Scenario/สถิติรันในรอบนี้
- **อำเภอ/ตำบลปีเดียว:** เปรียบเทียบเชิงพรรณนาได้หลัง Soil/Weather Join พร้อม แต่หน่วยน้อยและ Climatic Variation อาจต่ำ ไม่เหมาะใส่ตัวแปรดินหลายสิบรหัสแล้วอ้างอิทธิพลอุณหภูมิ
- **อำเภอหลายปี:** พิจารณา Panel Association หลัง Data/QC พร้อม; Repeated Years มี Temporal/Spatial Dependence ไม่ใช่จำนวนตัวอย่างอิสระเต็ม n×ปี ดินคงที่ถูก District Fixed Effects ดูดซับ จึงต้องเลือกโจทย์ Between-area หรือ Soil×Weather Interaction อย่างมีเหตุผลก่อนดูผล; Cluster Count น้อยทำให้ Inference ไม่เสถียร
- **สวนหลายแห่งหลายฤดู:** เหมาะกับการศึกษา Soil–Temperature–Yield มากกว่าเมื่อมี Ground Measurements/Management และ Harvest จริง แต่สวนซ้ำไม่ใช่ตัวอย่างอิสระแต่ละปี และ Convenience Sample ไม่แทนทั้งจังหวัด สวนเดียวหลายปีทำ Case Study ได้ ไม่แยกผลดินระหว่างสวนหรืออ้างสาเหตุ

สัดส่วนดินรวมเป็น 100% จึงมี Compositional Constraint ห้ามใส่ครบทุก Share กับ Intercept โดยไม่ออกแบบ Contrast/กลุ่มล่วงหน้า ห้ามใช้ Soil Units หลายแถวที่มี Yield อำเภอเดียวกันเป็นตัวอย่าง Yield อิสระ และห้ามอ้าง Causal Impact จาก Association

## 6. คำถามสำหรับอาจารย์และงานที่รออนุมัติ

1. ต้องการตอบความแตกต่างระหว่างพื้นที่ หรือการตอบสนองต่ออุณหภูมิระหว่างฤดู? จะใช้หน่วยอำเภอ/ตำบล/สวนใดตาม Target ที่หาได้จริง?
2. เข้าถึง Production/Bearing Area หรือ Harvest Ledger ของจันทบุรีจากใครได้ และมีปี/ฤดูที่ตรงกันกี่ปี?
3. ใช้ทุเรียนทุกพันธุ์หรือหมอนทอง; มีพื้นที่ให้ผล/อายุต้น/การจัดการแยกพันธุ์หรือไม่?
4. ยอมรับ Static A403 ปี 2568 เป็น Retrospective Proxy พร้อมคำเตือนหรือจำเป็นต้องมี Historical Footprints?
5. POWER แยกอำเภอได้พอหรือควรขอสถานี/เซนเซอร์เพิ่มเติม? จะเลือก Physiological Windows อย่างไร?
6. ต้องขอ Consent/Data-sharing/License และกำหนด Anonymization ใดก่อนรับข้อมูลสวน?

เสนออนุมัติงานถัดไปหนึ่งงาน: **ขอ Data Availability + ตัวอย่าง Schema จากเกษตรและสหกรณ์จังหวัด/เกษตรจังหวัด/เกษตรอำเภอท่าใหม่** ตามรายการข้อ 2–3 ก่อนขอชุดเต็ม เริ่มจากทุกปีที่มีจริง หากไม่มี Production/Bearing Area ที่เทียบกันได้ ให้หยุดโจทย์ Yield พื้นที่ย่อยและคงงาน Descriptive หรือออกแบบ Prospective Farm Harvest Log แยก ไม่มีดาวน์โหลด/ติดต่อ/ขยาย GIS โดยอัตโนมัติ

## Evidence Paths และ Protection

- `C:/project/docs/research/spatial/DISTRICT_DATA_SOURCE_REVIEW_TH.md`
- `C:/project/research_data/five_province_history/production_source_review.json`
- `C:/project/docs/DURIAN_CHANTHABURI_SPATIAL_FEASIBILITY_TH.md`
- `C:/project/docs/DURIAN_FOUR_PROVINCE_INTERNAL_DATASET_TH.md`
- `C:/project/research_data/external/oae_2026-09-17/durian_province.xlsx`
- `C:/project/data/export_2026-09-13/farm_iot_source.xlsx`
- `C:/project/data/backups/2026-09-13/farm_iot_full_backup.xlsx`
- `C:/project/research_data/internal_research/tha_mai_spatial/phase10f_20261012_internal_accepted_proposal_v1/`

ตรวจ Read-only Headers ของ Workbook 3 ไฟล์ด้วย bundled Python; ใช้ Spreadsheets Skill เพื่อรักษาขอบเขตอ่านอย่างเดียว/ไม่ถือ Missing เป็นศูนย์ ไม่มีแก้ Workbook หรือ Source Records สร้างเฉพาะรายงานและ Hash Evidence ใหม่ ไม่รัน Tests/ML/Scenario/Overlay ไม่แก้ Production/API/Frontend/Dataset

Protected Verification เก็บที่ `C:/project/research_data/internal_research/chanthaburi_yield_feasibility/phase11a_20261012_v1/` พร้อม Source/Release Seals และ Production Hash หลังงาน **Public HOLD คงเดิม หยุดรอคำสั่ง**
