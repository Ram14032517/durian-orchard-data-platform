# Data Vintage และ Point-in-Time Correctness ของ Durian Yield Forecasting

วันที่ตรวจ 10 ตุลาคม 2026 ขอบเขต: อ่านข้อมูล/โค้ด/หลักฐานออนไลน์ และจัดทำรายงานเท่านั้น
ไม่ฝึกโมเดล ไม่แก้สคริปต์ทดลอง Production, Frontend หรือ API
ค้นหา AGENTS.md ใน C:\project ทั้งต้นไม้และ C:\ ซึ่งเป็นโฟลเดอร์แม่แล้วไม่พบ
อ่าน DURIAN_EXPANSION_AUDIT_TH.md ก่อนตรวจต่อ

## ข้อสรุป

**ยังรับรอง Point-in-Time correctness ของการทดลอง 2017–2025 ไม่ได้**
มีการตัด observation dates ของอากาศและแยกปีฝึก/ทดสอบ แต่ไม่มี historical publication/value vintages สำหรับ OAE และ POWER
MAE CatBoost 204.85 จึงยังเป็นผล exploratory บนข้อมูลฉบับย้อนหลังที่มีอยู่ตอนนี้ ไม่ใช่คะแนนพยากรณ์จริงที่ replay สิ่งซึ่งทราบในวันนั้น
ข้อสรุปนี้ไม่ได้กล่าวว่าค่าทั้งหมดถูกปรับแก้แน่นอน หรือว่าไม่เคยมีข้อมูลใดเผยแพร่มาก่อน
สิ่งที่ขาดคือหลักฐานว่าค่า/รุ่นที่ใช้ตรงกับค่า/รุ่นที่เข้าถึงได้ ณ issue date
ยังคำนวณขนาดผลของ revised-data leakage หรือ corrected MAE ไม่ได้จาก snapshot เดียว

## 1. Source, Version และวันที่ที่ตรวจพบ

### OAE รายปี

ผู้จัดทำ: ศูนย์สารสนเทศการเกษตร สำนักงานเศรษฐกิจการเกษตร

- Dataset: https://catalog.oae.go.th/dataset/durian_product
- Resource ID: `3f9531b0-dc97-415a-a8d5-aa7c89f0c7b3`
- Resource: https://catalog.oae.go.th/dataset/durian_product/resource/3f9531b0-dc97-415a-a8d5-aa7c89f0c7b3
- ไฟล์ที่ใช้อยู่: research_data/external/oae_2026-09-17/durian_province.xlsx, sheet `durian`
- SHA256: `6a3ae44026b5ef8037a8bb091852281d890168a8d795c9c44d5cde9a48613d4c`
- data_date ในทุกแถว: `2026-07-14`
- CKAN resource created: `2026-08-24T06:35:28.791110`
- CKAN resource last_modified: `2026-08-24T06:35:28.766670`
- CKAN dataset metadata_created: `2026-08-24T06:19:01.449510`
- CKAN dataset metadata_modified: `2026-08-24T06:42:10.016208`

ไม่มี official version number ที่ยืนยันได้ ไม่มีนิยาม data_date ที่ระบุว่าเป็นวัน revision ของค่าทุกแถว
จึงเรียกฉบับด้วย SHA256 เพื่อระบุ bytes ที่ตรวจ ไม่อ้างว่า hash เป็นหมายเลขรุ่นทางการ
Revision date ของข้อมูลแต่ละ observation และ publication date ครั้งแรก: **ไม่ทราบ**
หน้า resource เว้นว่างวันที่กำหนดเผยแพร่/ปรับปรุงข้อมูล แต่แสดงวันที่สร้าง/ปรับปรุงในระบบแคตตาล็อก
timestamps API ไม่ระบุ timezone ในข้อความที่คืนมา จึงเก็บรูปเดิม ไม่เติม Z หรือแปลงเอง

### OAE รายเดือน

- Dataset: https://catalog.oae.go.th/dataset/durian_product_month
- Resource ID: `93c0421b-ebc5-443b-b763-2be1b4a86c5b`
- Resource: https://catalog.oae.go.th/dataset/durian_product_month/resource/93c0421b-ebc5-443b-b763-2be1b4a86c5b
- ไฟล์ที่ใช้: research_data/external/oae_2026-09-17/durian_monthly_province.xlsx, sheet `durian_monthly`
- SHA256: `461dab6a68ff2aca9bceb81e9a35b0137e77aff7ed9afb29054910ddf53cb62f`
- data_date ในทุกแถว: `2026-07-22`
- CKAN resource created: `2026-08-25T02:41:15.281632`
- CKAN resource last_modified: `2026-08-25T02:41:15.261076`
- CKAN dataset metadata_created: `2026-08-25T01:58:42.801560`
- CKAN dataset metadata_modified: `2026-08-25T02:41:21.359804`

Version number, observation-specific revision date และ first publication date: **ไม่ทราบ**
ทั้งสองไฟล์ที่ endpoint ส่งกลับในวันที่ตรวจมี SHA256 ตรงกับไฟล์ในเครื่อง
ตรวจ bytes ในหน่วยความจำ ไม่เขียนทับต้นฉบับ การตรงกันพิสูจน์เพียงฉบับปัจจุบันตรงกัน ไม่พิสูจน์ความพร้อมย้อนหลัง
วันที่ดาวน์โหลด 2026-09-17 เป็น retrieval evidence เท่านั้น ไม่ใช้แทน publication_date
วันที่สร้างแคตตาล็อกปี 2026 ก็ไม่ใช้แทนวันที่เผยแพร่เดิมทางหนังสือ เว็บไซต์เก่า หรือช่องทางอื่น

ข้อมูล OAE มีช่วงปี/คำอธิบายแคตตาล็อกไม่ตรงกันตามรายงานก่อนหน้า ต้องยึดปี observation จากไฟล์
ข้อมูลนี้เป็น all-cultivar ไม่ใช่ Monthong-only และสถานะ final/estimate ของทุกแถวยังไม่ยืนยัน

### NASA POWER

- Daily API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- raw caches 25 ไฟล์ (5 จังหวัด × 5 ช่วงเวลา) มี source sidecars และ SHA256 ตรงกับ raw bytes ทั้ง 25 ไฟล์
- sidecars retrieved_utc ช่วง `2026-09-26T07:23:27.722957+00:00` ถึง `2026-09-26T07:23:52.124727+00:00`
- header ของห้าช่วงเวลาจันทบุรีที่ตรวจระบุ API `v2.10.0`, time standard `LST`
- header sources มี SRB/MERRA2/POWER ในช่วงเก่า และ SYN1DEG/FLASHFLUX/GEOSIT/MERRA2/POWER ในช่วงใหม่

API version ไม่ใช่ data-vintage version และรายชื่อ sources รวมใน header ไม่พิสูจน์ว่าแต่ละวันใช้ product/release ใด
ไม่มี first_available_at หรือ revision history รายวันใน sidecars
date ใน weather_daily.csv เป็น observation date ไม่ใช่ publication date
LST ไม่ใช่ timezone Asia/Bangkok จึงไม่อนุมานเวลาเผยแพร่จากเวลา observation

NASA ระบุ latency โดยรวม meteorology 2–3 วัน และ solar 5–7 วันในเอกสารปัจจุบัน
จึงมีบริบทสนับสนุนการตั้ง lag เจ็ดวัน แต่ไม่ใช่ SLA หรือหลักฐานความพร้อมของทุกวัน/ทุก parameter ในปี 2014–2025
NASA ระบุด้วยว่า quick-look meteorology ถูกแทนด้วย climate-quality products หลังประมาณ 2–3 เดือน
และ archive มีการปรับ bias/model/error ภายหลัง นี่เป็นหลักฐานว่าต้องแยก observation date ออกจาก data vintage
อ้างอิง: https://power.larc.nasa.gov/docs/faqs/data/ และ https://power.larc.nasa.gov/docs/services/

## 2. แยกสามกลุ่มข้อมูล

| กลุ่ม | สิ่งที่จัดเข้าได้จากหลักฐานนี้ | ข้อจำกัด |
|---|---|---|
| พิสูจน์ว่าทราบ ณ วันพยากรณ์ | province keys และ calendar year ที่กำหนดในโจทย์ | เป็น known-by-construction ไม่ใช่หลักฐานเผยแพร่ค่าจาก OAE/POWER |
| ฉบับย้อนหลังใช้เป็น reference labels ภายหลัง | production_tonnes / bearing_rai และ yield ratio ปีเป้าหมายจาก OAE ฉบับที่มีอยู่ | ใช้ประเมินภายหลังได้ แต่ finality ยังไม่ยืนยัน จึงไม่เรียก confirmed final ground truth |
| ยังพิสูจน์วันเผยแพร่/ค่าตามวันจริงไม่ได้ | OAE lag yield, training labels, monthly season history, POWER observations และ inputs ของ climatology | ไม่ผ่าน strict input availability gate |

ใน dependency records ของตาราง ยังไม่มีค่าจากผู้ให้บริการที่จัดเป็น verified-as-of ได้
ไม่ตีความว่าจังหวัดหรือปีเหล่านั้นไม่มีข้อมูลสาธารณะใดเลย
ข้อมูลแถวเดียวกันอาจอยู่คนละกลุ่มตามบทบาท: yield ปี 2024 ใช้เป็น reference label หลังฤดูได้ แต่จะใช้เป็น lag เพื่อพยากรณ์ปี 2025 ต้องพิสูจน์ availability ใหม่

## 3. Trace features และ Revised Data Leakage

ตรวจ `common.load_panel()`, `compare_harvest_stage_yield.design()/training_seasons()/fit_predict()`
และ `experiment_issue_date.IssueWeather()/frame_for()/predict_year()`

| Feature / dependency | วิธีใช้จริง | ความเสี่ยง |
|---|---|---|
| previous_yield_kg_rai | ใช้ target ratio ปี y−1 จาก annual snapshot โดยเลื่อน year +1 | ทั้ง numerator ผลผลิตและ denominator พื้นที่ให้ผลอาจต่างจากฉบับที่ทราบในวันนั้น |
| province dummies, year_ce | keys และ calendar | ไม่มี revised agricultural values โดยตรง |
| pre_bloom_90d_rain_mm | POWER ฝนตาม stage ก่อนดอก + normal เมื่อเลย cutoff | เสี่ยง POWER revisions และ monthly season revisions |
| fruit_0_29d_rain_mm | เช่นเดียวกันในวัน 0–29 | ความเสี่ยงเดียวกัน |
| fruit_30_59d_rain_mm | เช่นเดียวกันในวัน 30–59 | ความเสี่ยงเดียวกัน |
| fruit_60_89d_solar_mj_m2_day | ค่าเฉลี่ย solar ในหน่วย MJ/m²/วัน | ความเสี่ยง solar vintage/latency และ stage timing |
| fruit_90_to_harvest_temperature_c | ค่าเฉลี่ย T2M ช่วงปลายผล | ความเสี่ยง meteorology vintage และ stage timing |
| vpd_pre_bloom_mean_kpa | คำนวณ TMIN/TMAX/RH ก่อนดอก | รับความเสี่ยงจาก inputs ทั้งสาม ไม่ปลอดภัยเพราะเป็น derived feature |
| vpd_early_fruit_p90_kpa | p90 VPD ช่วงผลอ่อน | ความเสี่ยงเดียวกัน และ normal ไม่ใช่ forecast distribution ของปีนั้น |
| main-season months และ issue date | peak ของรายเดือนปี <= fold_year−1 แล้วใช้สามเดือนรอบ peak | revised monthly values อาจเปลี่ยนทั้ง windows และวันพยากรณ์เอง |
| climatology | calendar-day mean จากสิบปีก่อนปีของแต่ละแถว | ตัด observation years อนาคตได้ แต่ข้อมูลอดีตฉบับที่สร้าง normal ถูกโหลดในปี 2026 |

production_tonnes / bearing_rai ปีเป้าหมาย **ไม่ใช่ predictor โดยตรง** ของ CatBoost ชุดนี้
แต่ ratio ปีก่อนเป็น predictor และ labels ที่ใช้ฝึก/เลือกโมเดลทั้งหมดมาจาก snapshot เดียว
province_median baseline ใช้ training labels ฉบับเดียว จึงมีความเสี่ยงด้วย
production_yoy_pct / yield_yoy_pct มีใน annual table แต่ไม่อยู่ใน design columns ของ issue-date experiment
ไม่มี lag bearing area, planted area หรือ cultivar share เป็น predictor แยกในชุดนี้
อย่านำคำว่า table มี target columns มาสรุปว่า target ถูกส่งเข้า estimator: ตรวจ design whitelist แล้วใช้เฉพาะ year, province และ features ที่ระบุ

ถ้านำ bearing_rai ปีพยากรณ์ไปแปลง predicted kg/rai เป็น tonnes ต้องใช้ area estimate ที่ประกาศแล้ว
actual bearing area หลังฤดูให้ได้เพียง conditional/ex-post tonnage ไม่ใช่ forecast total ที่ทราบในวันนั้น
รอบนี้ไม่ตรวจหรือแก้ live API; ข้อความดังกล่าวเป็นเงื่อนไขการนำผลไปใช้งาน ไม่ใช่คำรับรอง API

### Training / Nested selection

การฝึก `train.year_ce < test_year` ป้องกันการใส่ปีเป้าหมายตรง ๆ แต่ไม่ป้องกัน revision ของ labels/features
inner scores สามปีก่อน outer ใช้ actual yields ฉบับปัจจุบัน
เพื่อเลือก depth สำหรับ outer ปี y ต้องพิสูจน์ว่า labels ของ inner years รวมถึง y−1 ประกาศแล้ว ณ fit/selection time
แค่ inner forecast เกิดก่อน outer year ยังไม่พอถ้าตัวเลขจริงของ inner ปีล่าสุดเพิ่งประกาศหลัง outer issue

วันที่ issue ต่างกันตามจังหวัด แต่ model selection/fit ในโค้ดแชร์ตาม year/candidate และไม่มี fit_timestamp ที่บันทึกไว้
การ replay ต้องกำหนดว่า fit ครั้งเดียวก่อน issue แรกของทุกจังหวัด หรือ refit ตาม issue รายจังหวัด แล้วบันทึกเวลาจริง
ห้ามให้ผลเลือกโมเดลจากข้อมูลที่ทราบตอน issue ของจังหวัดหลังไปใช้กับจังหวัดที่ออก forecast ก่อน
ยังไม่พิสูจน์ว่าเกิดกรณีนี้จริง เพราะไม่มี release records แต่เป็น dependency ที่ต้อง guard

historical training features ที่คำนวณใหม่ใน fold ใช้ได้ถ้าส่วนประกอบทั้งหมดทราบ ณ fit cutoff นั้น
ไม่จำเป็นต้องล็อกทุก training row ไว้ที่ issue เดิมของ row เสมอ แต่ต้องประกาศว่าจะใช้ frozen historical features หรือ regenerate-as-of-fit และทำเหมือนกันทุก fold
validation forecast แต่ละปีต้องสร้างจาก issue ของปีนั้น; label สำหรับ scoring ต้องมี ณ เวลาที่นำ score ไปเลือกโมเดล

## 4. ตรวจ Baseline ผลผลิตปีก่อน

ตรวจคู่ keys ของ lead 60 CatBoost ทั้ง 45 จังหวัด–ปี ปี 2017–2025
previous_year_kg_rai ตรงกับ `production_tonnes[y−1] * 1000 / bearing_rai[y−1]` จาก annual snapshot ปัจจุบันทุกแถว (tolerance 1e−8)
fit_predict(kind=previous_year) คืนค่า previous_yield_kg_rai ตรง ๆ ไม่เลือก vintage ตาม issue_date
ทั้ง baseline และ CatBoost จึงมี dependency ที่ยังไม่ยืนยันเดียวกัน
การชนะ baseline ไม่พิสูจน์ว่า baseline เป็น baseline ที่ผู้ใช้ทำได้จริงในวันนั้น
ยังไม่พบหลักฐานเปรียบเทียบค่าทั้ง 45 แถวกับฉบับเผยแพร่ก่อนวัน forecast

## 5. ตาราง Data Availability

ไฟล์ประกอบ: [DURIAN_DATA_AVAILABILITY.csv](DURIAN_DATA_AVAILABILITY.csv)

840 dependency records = 120 จุด forecast × 7 บทบาท
120 จุด forecast มาจาก 5 จังหวัด × ปี 2014–2025 × lead 60/0
ปี 2014–2016 เป็น inner-only, 2017–2024 ใช้ทั้ง outer และ inner, 2025 outer-only
เฉพาะ outer 2017–2025 มี 90 จุด forecast / 630 dependency records; lead 60 ที่ถามมี 45 จุด
ไม่ได้อ้างว่า 840 เป็นข้อมูลฝึกอิสระหรือเป็นผลทดลองใหม่

columns ที่ร้องขอครบ: province, target_year, data_version, publication_date, issue_date, availability_status
เพิ่ม province_code, fold_usage, lead_days, data_role, observation_period, source_id, publication_evidence เพื่อไม่ปน labels กับ inputs
publication_date เว้นว่างทุกแถวเพราะไม่มี first-release evidence ไม่แทนด้วย data_date, catalog date หรือ retrieval date
known-by-construction ของ calendar keys ไม่ต้องมี publication date จาก provider
data_version แบบ SHA prefix เป็น audit identifier โดย SHA เต็มอยู่ในรายงานนี้ ไม่ใช่เลข version ทางการ

issue_date คำนวณซ้ำจาก monthly history <= year−1 ที่โค้ดใช้อยู่และตรวจพบตรงกับ saved weather context ครบ 120 จุด
นี่เป็น **reconstructed issue date จาก pipeline** ไม่ใช่หลักฐานว่าเคยออก forecast ในวันนั้น และยังขึ้นกับ vintage ของ monthly season
ตัวตารางบันทึก dependency-period แบบสรุป ไม่แจกแจง observation ทุกวันหรือ label ทุกปี
หากจะบังคับ gate จริงต้องเพิ่มตาราง granular records ตาม schema ในข้อ 6

## 6. แผน Point-in-Time Backtesting (ยังไม่แก้โค้ด)

1. เก็บ raw vintage แบบ append-only พร้อม hash ไม่เขียนทับค่าที่เคยเผยแพร่ รวมเอกสารสำรวจ/หนังสือสถิติ/ประกาศรุ่นประมาณการและรุ่นแก้ไข
2. ใช้สองเวลา: observation_date/year และ published_at; เก็บ retrieved_at แยก รวมเวลาที่ correction ถูกประกาศ
3. ตาราง granular: province_code, indicator, observation_period, value, unit, source_url, data_version,
   published_at, publication_evidence_url/page, evidence_type, revision_status, finality, retrieved_at, sha256
4. as-of join ต้องเลือกค่าฉบับล่าสุดที่มีหลักฐาน `published_at <= cutoff`; unknown ไม่ผ่าน gate
   การตรวจวันในชื่อไฟล์หรือ HTTP Last-Modified เพียงอย่างเดียวไม่พิสูจน์การประกาศ/ค่าฉบับเก่า
5. ตรึง forecast schedule ล่วงหน้าหรือใช้ season prior ที่ประกาศทันวันนั้น อย่าให้ revised monthly target distribution เปลี่ยน issue date โดยไม่ระบุ
6. ณ fit cutoff เลือก training labels และ raw features ที่ประกาศแล้ว; การ fit preprocessing และ season fitting ทำภายใน fold
7. สำหรับ inner validation replay issue ของแต่ละปี และใช้เฉพาะ inner labels ที่ทราบ ณ outer selection cutoff
8. สร้าง POWER daily features จาก as-of observations; แยก quick-look/climate-quality และ parameter-level first availability
   ถ้าไม่มี provider vintage ให้ใช้ log/snapshots ที่เริ่มเก็บจริงต่อไป หรือ archive ที่พิสูจน์รุ่นและเวลาได้
9. สร้าง climatology จากข้อมูลที่ทราบจริง ณ cutoff; ส่วนอนาคตใช้ scenario normals ที่ประกาศว่าเป็น climatology
   ถ้าใช้ historical forecast ต้องมี forecast_issued_at <= issue, valid_at, forecast model/run version และ archive value
10. ทำนายแล้ว freeze outputs/inputs/hash/fit time ตลอดจน selected depth; หลังฤดูจึง join evaluation reference labels
11. รายงาน dropped keys/เหตุผล, coverage, เวอร์ชัน labels, original-five metrics และ new-province metrics แยกกัน
    ก่อนเทียบแขนต้องใช้ common eligible keys; ถ้าหายจนไม่ครบ45ให้ระบุว่าไม่ใช่ชุดเทียบเดิม

Ground truth policy: ประเมินกับ fixed later reference version เดียวกันทุกแขน และถ้ามีให้รายงาน first-release target เทียบ revised target เพิ่ม
การใช้ later reference เพื่อ evaluation ไม่ใช่ leakage โดยตัวมันเอง แต่ถ้าตัวเลขนั้นย้อนกลับเข้า training/tuning/lag ก่อนเผยแพร่คือ PIT violation

### เมื่อไม่มี Historical Vintage

- ห้าม backdate snapshot ปี 2026 เป็น available ปี 2017
- ใช้ retrospective revised-data study เพื่อศึกษาสัญญาณ พร้อม label ชัดและไม่เรียก operational performance
- ใช้ conservative label lag ได้เป็น sensitivity scenario แต่ไม่ทำให้ค่าฉบับปรับปรุงกลายเป็น PIT-certified
- ค่าในหนังสือเก่าที่ลงวันที่/ฉบับชัดอาจช่วยกู้ vintage บางช่วง ต้องตรวจทั้งค่าผลผลิตและพื้นที่ให้ผล; การพบรายงานเก่าอย่างเดียวไม่ยืนยันค่าปัจจุบัน
- ถ้า reconstructed subset ผ่านจริง ให้รายงานผลเฉพาะ subset ไม่โยงเป็นความแม่นครบทั้ง 45 กรณี
- prospective evaluation ตั้งแต่เริ่ม log เป็นเส้นทางหลักที่ตรวจสอบได้ แต่ต้องรอ labels หลังฤดู ไม่ทดแทนประวัติด้วยข้อมูลสมมุติ

## 7. สถานะ A/B/C/D

| แขน | Exploratory ที่ทำได้หลังอนุญาตให้ฝึก | Operational claim ตอนนี้ |
|---|---|---|
| A: 5 จังหวัด, 2010 | revised-snapshot climatology study พร้อมเปิดเผยความเสี่ยงและ recompute หลังเปลี่ยน vintage | ไม่ผ่าน OAE/POWER/selection availability |
| B: เพิ่ม 6 จังหวัด, 2010 | เช่น A และต้องเตรียม weather/provenance ใหม่ | ไม่ผ่าน และจังหวัดใหม่ยังไม่ได้ตรวจ daily weather vintages |
| C: 5 จังหวัด, 2004 | เช่น A พร้อมแก้ season prior ช่วงเริ่มและประกาศ missing folds | ไม่ผ่าน และ season history ตอนเริ่มปี2004ยังมีข้อจำกัด |
| D: เพิ่มจังหวัด, 2004 | แยกจังหวัด/เวลาเป็น factorial study โดยไม่อ้างผลที่ยังไม่ได้รัน | ไม่ผ่าน dependency ทั้ง B/C |

Weather ablation ทำได้เชิง exploratory หากตรึง model family/splits/keys/selection criterion เท่ากัน
ไม่พิสูจน์คุณค่าพยากรณ์ operational เพราะ lag/labels/season ก็ยังเป็น revised snapshots
Oracle future-weather study ทำได้เฉพาะ research upper-bound scenario แยก; ไม่ใช่คะแนน deploy
รอบนี้ไม่ได้ฝึก A/B/C/D หรือ ablation ใด ๆ ตามข้อห้าม

## 8. หลักฐานและขอบเขตการตรวจ

- อ่าน code paths ที่สร้าง design matrix, lag ratio, monthly season, issue-date observations/normals และ nested selection
- อ่าน OAE workbook/source notes และ CKAN package_show/resource metadata ณ วันที่ตรวจ
- ตรวจ HTTP response bytes ของ XLSX สองไฟล์ตรงกับ local SHA256
- ตรวจ raw POWER SHA256 ทั้ง25ไฟล์ พร้อม provenance metadata
- ตรวจ baseline ratio 45 keys และ reconstructed issue dates120จุดด้วยการคำนวณอ่านอย่างเดียว
- ไม่รัน training script ไม่ทดสอบผลปรับโมเดล และไม่ใช้ unit-test pass เป็นหลักฐานว่าไม่มี leakage
- ไม่ได้พิสูจน์ finality OAE ทุกปี, ตรวจเอกสารเผยแพร่ครั้งแรกครบทุกปี หรือกู้ historical POWER snapshots ที่ยังไม่มี

CKAN endpoints ที่อ่าน:

- https://catalog.oae.go.th/api/3/action/package_show?id=durian_product
- https://catalog.oae.go.th/api/3/action/package_show?id=durian_product_month

ข้อเสนอแก้โค้ดครั้งถัดไป: เพิ่ม vintage loader/as-of join และ release manifest ใน experimental pipeline,
บันทึก fit_timestamp/selection cutoff, เปลี่ยน season schedule ให้มี as-of provenance และแยก evaluation label loader
ยังไม่ลงมือแก้ ต้องผ่านการพิจารณาแผนนี้ก่อนตามคำสั่งผู้ใช้
