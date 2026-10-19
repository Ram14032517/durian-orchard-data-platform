# Phase 4B — ENSO Outlook Historical Archive Audit

วันที่ตรวจ: 11 ตุลาคม 2026 — Audit เท่านั้น ไม่มีการฝึกโมเดลหรือแก้ ML Pipeline

## ข้อสรุป

เอกสาร NOAA ENSO Diagnostic Discussion มีหลักฐานวันออกก่อนวันใช้ข้อมูลครบ 80 จังหวัด–ปี (2010–2025) และครบ 45 Outer evaluation keys เดิม มีข้อความระบุ Observed ENSO State ครบทุก key จึงรองรับการเสนอทดลอง **categorical observed-state ablation** ต่อไปได้ แต่ยังไม่อนุมัติให้สร้าง Feature หรือ Training ในงานนี้

**ENSO forecast probability แบบสม่ำเสมอยังไม่พร้อม**: ตัวเลขในข้อความมีเฉพาะบางฉบับและกล่าวถึงคนละ phase/ฤดู การพบเปอร์เซ็นต์ไม่เท่ากับการมี probability vector ครบ El Niño / Neutral / La Niña สำหรับ forecast horizon เดียวกัน ตาราง/ภาพ probabilities ยังไม่ได้ตรวจสอบ จึงไม่เติมตัวเลข ไม่อนุมานส่วนที่เหลือ และไม่อ้างว่าไม่มีข้อมูลในภาพ

การยืนยันวันออกเอกสารจาก archive ทางการ **ไม่ใช่การรับรอง historical byte-level vintage**: สำเนาทั้งหมดดาวน์โหลดในปี 2026 และยังไม่มีหลักฐานอิสระว่าเนื้อหาไม่เคยแก้ย้อนหลัง ทั้งระบบ ML จึงยังไม่เป็น PIT Certified รวมถึงข้อจำกัด vintage ของ OAE/POWER จากงานก่อน

## Protocol และแหล่งข้อมูล

- แหล่งหลัก: [NOAA ENSO Diagnostic Discussion Archive](https://www.cpc.ncep.noaa.gov/products/expert_assessment/ENSO_DD_archive.php)
- จังหวัดเดิม: จันทบุรี (22), ศรีสะเกษ (33), อุตรดิตถ์ (53), สุราษฎร์ธานี (84), ชุมพร (86)
- Fixed-calendar anchors: 1 เม.ย., 1 พ.ค., 1 มิ.ย., 1 ก.ค., 1 ก.ค.; Lead 60 วันตามปฏิทินเดิม ไม่เปลี่ยนเพื่อตามข้อมูล ENSO
- จันทบุรี issue 31 ม.ค. หรือ 1 ก.พ. ในปี leap; ศรีสะเกษ 2 มี.ค.; อุตรดิตถ์ 2 เม.ย.; สองจังหวัดภาคใต้ 2 พ.ค.
- Outer 2017–2025; Inner 3 ปีก่อน Outer; training history เริ่ม 2010; shared fit cutoff เป็นวัน issue แรกสุดของจังหวัดใน fold
- เลือก bulletin ล่าสุดที่ออก **ก่อน** วัน issue ของแถว และสำหรับ training ต้องก่อน fit cutoff ด้วย ไม่มีการย้าย forecast feature ของจังหวัดที่ issue ช้ากว่าเข้า training ณ shared fit cutoff
- เมื่อรู้เพียงวันที่ออก ไม่รู้เวลา/เขตเวลา ใช้กฎ conservative: publication day ต้องน้อยกว่า cutoff day; ไม่รับเอกสารวันเดียวกัน เกณฑ์ freshness ไม่เกิน 45 วันเป็นกฎ audit ไม่ได้เปลี่ยน protocol ML

สคริปต์ตามลิงก์ที่ archive ระบุจริง ตรวจ issuance header ให้ตรง edition เดือน–ปี และเก็บ raw bytes/URL/SHA256 เอกสาร HTML บางแห่ง HTTP 200 แต่เป็นหน้าถูกย้าย จึงใช้ English PDF ทางการจาก landing page แทน ไม่ถือ HTTP 200 ว่ายืนยันหลักฐานแล้ว

## Pilot

| ปี | ฉบับ ม.ค. | ฉบับ ก.พ. | ฉบับ มี.ค. | ฉบับ เม.ย. | Keys ผ่านเกณฑ์วันออก |
|---|---|---|---|---|---|
| 2017 | 12 ม.ค. | 9 ก.พ. | 9 มี.ค. | 13 เม.ย. | 5/5 |
| 2020 | 9 ม.ค. | 13 ก.พ. | 12 มี.ค. | 9 เม.ย. | 5/5 |
| 2023 | 12 ม.ค. | 9 ก.พ. | 9 มี.ค. | 13 เม.ย. | 5/5 |
| 2025 | 9 ม.ค. | 13 ก.พ. | 13 มี.ค. | 10 เม.ย. | 5/5 |

Pilot ผ่านเฉพาะ document availability และ observed-state extraction จึงขยาย coverage audit ไม่ได้หมายความว่า forecast probabilities ผ่านพร้อมกัน ฉบับ พ.ค. เก็บเป็น negative control: ออกหลัง issue 2 พ.ค. จึงไม่ถูกเลือกใช้

## Coverage และความหมายของสถานะ

| ขอบเขต | จำนวน | วันออก verified | unverified | unavailable | Observed state พบข้อความ |
|---|---:|---:|---:|---:|---:|
| Pilot | 20 keys | 20 (100%) | 0 | 0 | 20 |
| Input history 2010–2025 | 80 keys | 80 (100%) | 0 | 0 | 80 |
| Outer 2017–2025 | 45 keys | 45 (100%) | 0 | 0 | 45 |
| Outer/Inner consumption records | 1,890 | 1,890 (100%) | 0 | 0 | 1,890 |

1,890 records เป็นการใช้ข้อมูลซ้ำใน 36 fold contexts ไม่ใช่ 1,890 ตัวอย่างอิสระ: training inputs 1,710 และ forecast inputs 180 มีเอกสารที่เลือกใช้จริงไม่ซ้ำ 64 ฉบับ จาก 80 ฉบับที่เก็บ (HTML 42 / PDF 38)

| สิ่งที่ตรวจ | verified | unverified | unavailable / ข้อจำกัด |
|---|---:|---:|---|
| Historical content authentication ของ 80 keys | 0% | 100% | ไม่มี independent immutable snapshot ในงานนี้ |
| Complete probability vectors ของ 80 keys | 0% | 100% | ภาพ/ตารางยังไม่ audit; ไม่ตีความว่าไม่มี |
| Numeric probability mentions ในข้อความ | พบ 50/80 keys (62.5%) | phase/horizon mapping ยังต้อง review | 30/80 (37.5%) ไม่พบในข้อความ; อาจมีในภาพ |
| Numeric probability mentions เฉพาะ Outer | พบ 41/45 keys (91.1%) | ยังไม่ใช่ feature ที่เทียบกันได้ | 4/45 ไม่พบในข้อความ |
| Explicit horizon mentions ที่ parser รองรับ | พบ 66/80 keys | อีก 14 keys ต้องอ่าน raw synopsis | ไม่ถือว่าไม่มี horizon เพราะ regex ไม่พบ |

ตาราง CSV แยก `availability_status`, `state_status`, `content_authentication`, `probability_vector_status` อย่านำ status แรกมาใช้รับรองทั้งแถว Forecast probability mentions เก็บช่วง low/high, approximate flag และข้อความหลักฐาน แต่ตั้ง phase/valid_start/valid_end เป็น null พร้อม `requires_phase_horizon_review` จนกว่าจะ map ได้จริง ข้อความซ้ำใน Synopsis และ body ไม่ใช่หลาย observation

Observed state อิงข้อความระบบมหาสมุทร–บรรยากาศ ไม่ใช้ ENSO Watch/Advisory แทน state และไม่เอาข้อความอนาคตมาเป็น observed state. Forecast horizons เก็บตามถ้อยคำต้นฉบับ ไม่แปลงฤดูกาลหรือเติมปีจากการเดา Numeric Niño 3.4 ยังไม่ได้สกัด/ทำให้มีนิยามเดียวกัน; Revised ONI ไม่ได้โหลดและไม่ได้ใช้ (`revised_oni_used=False`)

## หลักฐานและ Artifacts

ผลอ้างอิงใช้ run `research_data/enso_outlook_archive_audit/phase4b_20261011_noaa_reviewed/` เท่านั้น:

- `documents.csv`: 80 editions; product family, เดือน–ปี, publication header/evidence, URL, retrieval time, snapshot path, SHA256, observed-state evidence, raw synopsis, sparse probability/horizon mentions และ missing reasons
- `pilot.csv`: 20 pilot keys
- `availability.csv`: 80 จังหวัด–ปี พร้อม issue/shared fit/use cutoff และแหล่งข้อมูลที่เลือก
- `fold_availability.csv`: 1,890 consumption records พร้อม outer/inner fold, input role, cutoffs และ evidence
- `summary.json` และ `sources/`: summary และสำเนาดิบ; SHA256 เป็น identifier ของ content snapshot ไม่ใช่หลักฐานวันเผยแพร่; ไม่ใช้ download time หรือ HTTP Last-Modified แทน publication date
- script: `tools/audit_enso_outlook_archive.py`; tests: `tests/test_enso_outlook_archive_audit.py`

Archive index SHA256: `e281bbabb9671c1e50435580b068e4a91d4d294c0d4a20d8feb4f4d0f195f464`

Script SHA256: `7074e170a61842fa15c2687da458af539fa2f26d429074fb84bd6f965943298a`

run ก่อนหน้าเก็บไว้ทั้งหมด: ครั้งแรกพบ HTML เสีย, v2 เพิ่ม PDF fallback, final/reviewed reparse สำเนาที่ตรวจ hash แล้วเพื่อแก้รูปแบบข้อความ ไม่ดาวน์โหลดทับหรือเลือก run จากคะแนนโมเดล ไม่มีคะแนนโมเดลในงานนี้ เอกสาร พ.ค. 2025 ยังสกัด observed state ไม่ได้ แต่ไม่ถูกเลือกใน key หรือ fold ใด

## การตรวจสอบและ Production Protection

Automated audit tests **7/7 ผ่าน**: future/same-day rejection, issuance edition, Watch ≠ observed state, sparse probabilities ≠ vector, PDF line breaks/modifiers, leap-calendar/5 provinces, observed continuation ≠ future statement

Data integrity checks ผ่าน: SHA256 ครบ 80 สำเนา; 80 keys ไม่ซ้ำ; 36 contexts / 1,890 records ครบ; ทุก selected publication ก่อน issue/use cutoff; training publication ก่อน fold fit cutoff; ฉบับ พ.ค. ไม่ถูกใช้ ไม่มีการลดตัวอย่างเพื่อให้ผ่าน

ตรวจ protected hashes **293 ไฟล์เดิมตรงทั้งหมด** รวม Production/Experimental pipeline และ artifacts เดิม ไม่แตะการเปลี่ยนแปลงที่มีอยู่ก่อนใน dirty repository. Production model `research_data/five_province_history/training/ridge_vpd_final_model.json` SHA256:

`b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

ไม่ได้รัน full repository suite ใน audit นี้ ไม่อ้างว่าผล 225 Python / 30 JS เดิมถูกตรวจใหม่ งานนี้เพิ่มเพียงสคริปต์ audit, tests, หลักฐานและรายงาน ไม่เปลี่ยน Production/API/Frontend/ML Pipeline และจำนวนโมเดลที่ฝึก = 0

## แผนที่เสนอ — รออนุมัติ

1. ทางเลือกต้นทุนต่ำ: categorical observed-state ablation โดยเสนอแผน experimental implementation ก่อน ไม่เรียกว่า ENSO Outlook Probability Feature และยังติดป้าย Exploratory
2. หากต้องการ Outlook จริง: audit probability figures / linked official forecast tables ต่อ ตรวจสามสถานะกับ valid season เดียวกันครบปี training/inner/outer; แยก consensus outlook จาก model plume ไม่ผสมโดยถือว่าเป็นผลิตภัณฑ์เดียวกัน ให้บันทึก mapping/missingness และหลักฐานฉบับต้นทางก่อนทดลอง
3. เพิ่มหลักฐาน independent historical snapshots หากต้องการยืนยัน content vintage มากกว่าหลักฐานวันออกเอกสาร และคงข้อจำกัด OAE/POWER ไว้จนมีหลักฐานของแต่ละแหล่ง

ยังไม่เริ่ม Feature Ablation, Province Expansion หรือ Training และไม่สรุปว่า ENSO จะเพิ่มความแม่นจาก coverage นี้
