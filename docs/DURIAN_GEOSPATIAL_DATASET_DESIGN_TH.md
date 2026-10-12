# Phase 9B — Durian Geospatial Research Dataset Design

วันที่ตรวจ: 12 ตุลาคม 2026 • สถานะ: Audit & Schema Only • Public release: HOLD

## 1. ข้อสรุปและขอบเขต

ออกแบบชุดข้อมูล **ผลผลิตระดับจังหวัดรายปี เชื่อมกับอากาศย้อนหลังที่ถ่วงน้ำหนักบน footprint การใช้ที่ดิน A403 จากแผนที่รุ่นหนึ่ง** ไม่ใช่ชุดข้อมูลผลผลิตรายสวน และไม่ใช่ footprint ที่สำรวจใหม่ทุกปี เก็บองค์ประกอบดินแยกตามคู่รุ่นแผนที่ดิน–การใช้ที่ดิน ไม่ขยายดินรุ่นเดียวเป็นตัวอย่างอิสระ 20 ปี

มี assets ครบสำหรับ internal research 4 จังหวัด: จันทบุรี ชุมพร ศรีสะเกษ อุตรดิตถ์ ส่วนสุราษฎร์ธานีมีดิน แต่ยังไม่มี A403 และ weather profile แบบเดียวกัน ไม่มีการสร้าง dataset/geometry/observations ใหม่ รัน ML หรือเปลี่ยน Production/API/Frontend ในงานนี้

การตรวจสิทธิ์พบเงื่อนไข NC-ND ใน Catalog ของ LDD แต่ยังไม่มีหลักฐานสิทธิ์การแจกจ่าย derived dataset รายไฟล์ จึง **ยังไม่อนุมัติเผยแพร่** แม้ไม่แนบ polygon ก็ตาม รายงานนี้เป็นข้อเสนอทางเทคนิค ไม่ใช่ข้อวินิจฉัยทางกฎหมาย

## 2. Existing assets และ provenance

ไม่พบรายงาน GIS audit แยกชื่อใน `docs` จากการค้นชื่อแบบจำกัด ใช้ข้อสรุป audit เดิมร่วมกับเอกสารและ manifests ที่มีจริงดังต่อไปนี้:

- `C:/project/research_data/regional_orchards/SOURCE_TH.md`, `DATA_DICTIONARY_TH.md`, `VALIDATION_TH.md`
- `C:/project/research_data/regional_orchards/overlay_summaries.json` และ `cti_analysis.json`, `cpn_analysis.json`, `ssk_analysis.json`, `utt_analysis.json`
- `C:/project/research_data/soil_evidence_chanthaburi/analysis.json`
- `C:/project/notebooks/02_thailand_durian_comparison.ipynb`, `03_regional_orchards_soil_weather.ipynb`
- `C:/project/tools/build_soil_evidence.py`, `build_national_notebook.py`, `prepare_regional_orchards.py`, `fetch_orchard_weather.py`, `prepare_national_comparison.py`

| จังหวัด / code | Land-use file / ปี พ.ศ. (ค.ศ.) | Pure A403 polygons | จุดอากาศ | Pure A403 ไร่ | ดิน |
|---|---|---:|---:|---:|---|
| จันทบุรี / 22 | LU_CTI_2568.shp / 2568 (2025) | 8,512 | 16 | 539,971.790558 | ปีผลิต 2561 |
| ชุมพร / 86 | LU_CPN_2564.shp / 2564 (2021) | 3,897 | 17 | 86,755.515670 | ปีผลิต 2561 |
| ศรีสะเกษ / 33 | LU_SSK_2565.shp / 2565 (2022) | 1,234 | 17 | 16,529.896958 | ปีผลิต 2561 |
| อุตรดิตถ์ / 53 | LU_UTT_2563.shp / 2563 (2020) | 71 | 9 | 2,377.027338 | ปีผลิต 2561 |
| สุราษฎร์ธานี / 84 | ไม่พบ A403 asset ในชุดที่ตรวจ | — | — | — | ปีผลิต 2561 |

13,714 คือจำนวน polygon **รหัส A403 เดี่ยว** ไม่ใช่จำนวนสวน เจ้าของ หรือต้นทุเรียน รหัสผสมที่มี A403 ถูกแยกไว้ ไม่มีการประมาณสัดส่วนทุเรียนใน polygon ผสม

Raw paths:

- จันทบุรี: `C:/project/research_data/external/ldd_chanthaburi_2026-09-17/` มี `Landuse_cti.zip`, `sr_cti.rar`; geometry อยู่ใต้ `landuse/Landuse_cti/จันทบุรี2568/การใช้ที่ดิน/LU_CTI_2568.shp`
- อีกสามจังหวัด: `C:/project/research_data/external/ldd_regions_2026-09-18/{cpn,ssk,utt}/` มี `Landuse_{code}.zip`, `sr_{code}.rar` ใช้ path ภายในจริงจาก manifest เพราะบาง directory มีปัญหา encoding
- สุราษฎร์ธานี: `C:/project/research_data/external/ldd_surat_2026-09-23/sr_sni.rar` และ `soil/สุราษฎร์ธานี/Soil_จ.สุราษฎร์ธานี/Soil_จ.สุราษฎร์ธานี.shp`
- OAE: `C:/project/research_data/external/oae_2026-09-17/durian_province.xlsx`
- POWER: `C:/project/research_data/external/power_orchards_2026-09-18/` มี cached responses 59 ชุดและ `.source.json` 59 ชุด

ชุด derived เดิมอยู่ `C:/project/research_data/regional_orchards/`:

| Asset | บทบาท / coverage ตาม inventory และ validation เดิม |
|---|---|
| orchard_sample_points.geojson / orchard_weather_samples.csv | 59 จุด พร้อมพิกัด น้ำหนัก พื้นที่ A403 และรุ่นแผนที่ |
| sample_weather_monthly.csv | 59 × 20 × 12 = 14,160 point-months |
| orchard_weather_monthly.csv | 4 × 20 × 12 = 960 province-months |
| orchard_weather_annual.csv | 4 × 20 = 80 province-years |
| regional_province_year_panel.csv | OAE–weather join เดิม 80 province-years |
| soil_series_comparison.csv | องค์ประกอบหน่วยแผนที่ดินและพื้นที่ pure/mixed |
| *_polygon_audit.csv / landuse_code_inventory.csv | Source record, รหัสการใช้ที่ดิน, พื้นที่และ QC |
| sample_response_signatures.csv / model_readiness.csv / soil_resolution_review.csv | กริดอากาศซ้ำ ข้อจำกัดพื้นที่ และระดับความละเอียดดิน |

ตรวจ SHA256 ปัจจุบันของไฟล์ที่ผูกใน manifests GIS 4 จังหวัด **28/28 ตรง** และ cached POWER response **59/59 ตรง** กับ sidecars ไม่ใช่การรับรองความถูกต้องเชิงสำรวจหรือ PIT ไม่ได้รัน GIS overlay ใหม่หรือนับ CSV ทั้งชุดใหม่

## 3. Schema ที่เสนอ — ยังไม่ instantiate ตาราง

ทุกตารางมี `release_id` เพื่อแยก snapshot; source/content revision ต้องสร้าง ID ใหม่ ไม่เขียนทับรุ่นเดิม เก็บ province code เป็น string ไม่ใช้ชื่อภาษาไทยเป็น join key

| ตาราง | Primary key ภายใน release | Fields สำคัญ / การเชื่อม |
|---|---|---|
| province_year | province_code, year_ce | oae_observation_id, weather_profile_id, soil_map_pair_id, yield_kg_per_rai, bearing_area_rai, production_tonnes, weather aggregates, quality flags |
| weather_profile_year | weather_profile_id, year_ce | province_code, footprint_source_id, sampling_manifest_id, aggregation_method_id, 4 annual weather values, completeness |
| soil_map_vintage | soil_map_pair_id | province_code, soil_source_id, landuse_source_id, soil_production_year_be, landuse_map_year_be, survey_date/status, CRS, total/covered/uncovered pure area, SC/W diagnostics, mixed excluded area |
| soil_composition | soil_map_pair_id, soil_map_code | source map-unit descriptor, interpreted unit class/status, pure_intersection_rai, mixed_intersection_rai, share_of_pure_A403_pct |
| mixed_use_exclusions | soil_map_pair_id, landuse_code | source descriptor, polygon_count, full_polygon_area_rai, exclusion_reason; ไม่มี allocated durian area |
| source_manifest | source_id | provider, resource ID/URL, filename, SHA256, source version, publication/retrieval time, valid period/status, license evidence |
| field_lineage | table_name, row_key, field_name, source_id, transform_id | Raw field/source record หรือ input collection, transformation/code hash, weighting source, revision |
| quality_flags | table_name, row_key, flag_code | severity, evidence source/record, explanation, review_status |

`oae_observation_id` อ้าง source workbook + sheet/row/column + province/year + content hash; `weather_profile_id` ผูก province + land-use hash + sampling manifest hash + method version ไม่ใช้จังหวัดอย่างเดียวเป็น profile key; `soil_map_pair_id` ผูก hashes ของทั้งสองแผนที่และวิธี overlay

Province-year เป็น analytical view หนึ่ง snapshot ต่อจังหวัด–ปี ไม่ใช้ soil code เป็นคีย์ของ target และไม่ทำให้ yield ถูกนับซ้ำเมื่อมีหลายหน่วยดิน การเปลี่ยน OAE revision ต้องแยก release/observation ใหม่ พร้อม revision linkage

ไม่ join สุราษฎร์ธานีให้มี weather profile A403 ที่ไม่มีจริง หากต้องเก็บ registry ของ 5 จังหวัด ให้ระบุสถานะ missing แต่ research panel รุ่นนี้มี 4 จังหวัดเท่านั้น

## 4. Soil composition และตัวหาร

นิยามจาก builder เดิม:

- Pure mask: `LU_CODE.strip() == 'A403'`
- Mixed: มี token `A403` ใน `LU_CODE.split('/')` แต่ไม่ใช่รหัสเดี่ยว; เก็บรหัสจริงทุกค่าใน exclusion table ไม่จำกัดรายการด้วยการเดา
- Numerator: พื้นที่ intersection ระหว่าง pure A403 กับหน่วยแผนที่ดินนั้น
- Denominator: **พื้นที่ pure A403 ทั้งหมด รวมส่วนที่ไม่มี soil coverage**
- `share_of_pure_A403_pct = 100 × pure_intersection_rai / pure_A403_total_rai`
- `share_of_all_A403_pct` ใน notebook จันทบุรี และ `share_of_A403_pct` ใน regional builder เป็นชื่อ legacy ของนิยามนี้ ไม่หมายถึง pure + mixed
- SC และ W ยังคงเป็นแถวองค์ประกอบและอยู่ในตัวหาร ไม่ตัดออกหรือ renormalize โดยอัตโนมัติ; SC เป็นหน่วยพื้นที่ลาดชันซับซ้อน ไม่ใช่ soil series ที่มีคุณสมบัติดินเดียว W เป็นหน่วยน้ำ ต้องมี flag ตรวจความสอดคล้องกับ crop overlay
- Uncovered เป็น residual ใน summary ไม่ปลอมเป็นรหัสชุดดิน LDD; sum(shares) + uncovered_pct ควรเท่ากับ 100 ภายใต้ QC tolerance
- SC/W totals ใน summary เป็น diagnostics ที่รวมอยู่ใน covered area แล้ว **ห้ามบวกซ้ำ**

จันทบุรีจาก analysis เดิม: total 539,971.790558 ไร่; covered 539,963.639789; uncovered 8.150769 (0.00150948%); SC 32,588.748646; W 290.555444; mixed 139,426.573408 ไร่ไม่อยู่ในตัวหาร ผลรวมแถว soil share ประมาณ 99.99849052% ไม่ใช่ข้อผิดพลาดที่ต้องปรับให้เป็น 100 โดยลบ uncovered

พื้นที่ใช้ geometry เต็มใน projected CRS แปลง m² / 1,600 ไม่ใช้ simplified display geometry หรือพิกัดองศาคำนวณพื้นที่ ดินเป็น EPSG:32647; land use ศรีสะเกษ EPSG:32648 ต้องตาม transformation เดิม พร้อมบันทึก geometry repair และผลต่างพื้นที่ ไม่ rerun ในงานนี้

## 5. Data Dictionary Outline / Units / null semantics

| Field group | Type / หน่วย | คำจำกัดความและข้อกำหนด |
|---|---|---|
| province_code / year_ce | string / integer ค.ศ. | รหัสจังหวัดและปีปฏิทินที่ใช้ join; เก็บ original OAE year label และ conversion ไว้ด้วย ไม่อ้างว่าเป็นฤดูชีววิทยาเดียวกัน |
| yield_kg_per_rai | nullable float กก./ไร่ | ค่าระดับจังหวัดจาก OAE; ระบุ source field หรือสูตร conversion จริง ไม่แทนด้วย yield ของ A403 mask |
| bearing_area_rai / production_tonnes | nullable float ไร่ / ตัน | พื้นที่ให้ผลและผลผลิตจังหวัดตาม source; planted area ต้องเป็นอีก field ไม่สลับกัน |
| weather_t2m_mean_c | nullable float °C | annual mean ถ่วงจำนวนวันจาก monthly profile เมื่อครบ 12 เดือน |
| weather_rh2m_mean_pct | nullable float % | annual mean RH ถ่วงจำนวนวัน; ไม่ใช่ความชื้นดิน |
| weather_precip_total_mm | nullable float mm/ปี | monthly PRECTOTCORR (mm/day) × วันในเดือน แล้วรวม 12 เดือน |
| weather_solar_mean_mj_m2_day | nullable float MJ/m²/day | annual mean ของรังสีเฉลี่ยรายวันถ่วงวัน; ไม่เรียกชั่วโมงแสงแดดหรือพลังงานรวมรายปี |
| pure/covered/uncovered/mixed area | float ไร่ | แต่ละชื่อเป็นพื้นที่ geometry ไม่ใช่ OAE bearing area |
| soil_map_code / map_unit_class | string / enum | raw LDD code เก็บตามต้นฉบับ; classification ที่แปลความต้องมี status และวิธีแยกต่างหาก |
| share_of_pure_A403_pct | float 0–100 % | ตัวหารตามหัวข้อ 4; ห้ามเปลี่ยนเป็น share of covered only |
| sample weight / coverage fraction | float 0–1 | น้ำหนักพื้นที่ pure A403 ใน sampling stratum; coverage มีนิยาม per variable/month |
| longitude / latitude | float degree WGS84 | จุดตัวแทนการสุ่มเชิงพื้นที่ ไม่ใช่พิกัดสวนเจ้าของหรือสถานีตรวจวัด |
| map_year_be / production_year_be | integer พ.ศ. | ปีแผนที่การใช้ที่ดินและปีผลิตแผนที่ดินแยกกัน ไม่เท่ากับวันสำรวจ |
| survey_date / publication_time | nullable date/timestamp + status | ไม่มีหลักฐานให้ null + unverified ห้ามใช้วันที่ดาวน์โหลดแทน |
| retrieval_time / valid_period | timestamp / date interval | เวลารับไฟล์กับช่วงเวลาที่ข้อมูลอธิบายเป็นคนละมิติ; timezone ต้องชัด |
| hashes / source version | SHA256 string / nullable string | hash ของ bytes จริง; unknown version ไม่สร้างหมายเลขรุ่นสมมติ |

Dictionary ฉบับเต็มใน pilot ต้องมี field name, definition, type, unit, allowed values, null meaning, original column, source IDs, transform, QC และ example จาก asset ที่อนุญาตเท่านั้น ไม่มี missing→0, ไม่มีเติมฝนหรือ yield ที่หายเอง ค่า -999 ของ POWER ต้องถือ missing ไม่ใช่ค่าจริง

## 6. Spatial/temporal coverage และคุณภาพ

Weather 2006–2025 คือ **retrospective spatial profile บน footprint ที่ตรึงตามปีแผนที่** 64/80 province-years มี weather year ก่อน land-use map year ตาม inventory ไม่ใช่ footprint ประวัติศาสตร์ที่ยืนยันแล้ว ปีหลังแผนที่ก็ไม่ได้พิสูจน์ว่า footprint ไม่เปลี่ยน

Sampling เดิมใช้ strata 0.25° และ representative point ในชิ้น A403 ใหญ่สุด แต่ weight ใช้พื้นที่ pure A403 ทุกชิ้นใน stratum เป็น approximate point quadrature ไม่ใช่ NASA native grid overlay จุดหลายจุดอาจให้ค่าอากาศเดียวกัน ต้องใช้ response signatures อธิบายความซ้ำ ไม่ถือ 59 จุดเป็น 59 สถานีอิสระ

Weather มี T2M, RH2M, PRECTOTCORR, ALLSKY_SFC_SW_DWN เท่านั้น ไม่ใช่ daily Weather 7 Features ของ ML และไม่มี VPD ในชุด monthly นี้ ห้ามเติม feature ตามงาน ML เดิมโดยไม่มีการอนุมัติ

Builder เดิมตรวจ valid-area weight ต่อ variable/month และไม่ renormalize เมื่อ coverage ไม่ครบ (tolerance 1e-7); annual aggregation ต้องครบ 12 เดือน ใช้เดือน 01–12 ไม่ใช้เดือน 13 ของ POWER ซ้ำ Source header ที่ตรวจมี API v2.10.0, MERRA2/SYN1DEG/POWER และระบุ LST; ให้เก็บค่าตาม header พร้อม discrepancy flag เพราะ [POWER FAQ](https://power.larc.nasa.gov/docs/faqs/other/) อธิบาย default ของ monthly ต่างจาก hourly/daily ต้องตรวจรายละเอียดก่อนอ้างเวลารายชั่วโมงจาก monthly profile

Quality flags ที่เสนอ: `retrospective_fixed_footprint`, `survey_date_unverified`, `soil_production_year_not_survey_date`, `mixed_A403_excluded`, `mixed_use_dominant`, `uncovered_soil_area`, `SC_complex_unit`, `W_crop_overlay_review`, `geometry_repaired`, `shared_weather_grid`, `incomplete_weather`, `oae_revised_reference`, `publication_date_unverified`, `annual_calendar_not_phenology`, `license_pending`, `time_standard_review`

อุตรดิตถ์ pure area เล็กเมื่อเทียบ mixed area (mixed ประมาณ 95.96% ของ pure+mixed ตาม audit เดิม) ต้องเตือน representativeness ไม่ลบจังหวัดหรือเดาสัดส่วนใหม่ ความต่างระหว่างพื้นที่ LDD กับ OAE ไม่แก้ด้วย rescale เพราะนิยามและปีข้อมูลต่างกัน

## 7. Source Manifest และ License Matrix

Manifest ต้องแยก `publication_time`, `retrieval_time`, `source_last_modified`, `observation_period`, `map_year`, `source_version` และ `availability_status` การ hash bytes ปัจจุบันยืนยันตัวไฟล์ที่ถืออยู่ ไม่พิสูจน์ว่าไฟล์เหมือนที่เผยแพร่ในอดีต Historical PIT ยังคงไม่รับรอง

License evidence ที่ตรวจวันที่ 12 ตุลาคม 2026:

- **L1 — LDD Land-use**: [Catalog API ldd_21_01](https://lddcatalog.ldd.go.th/api/3/action/package_show?id=ldd_21_01) ระบุ “Creative Commons Attribution Non-Commercial No-Derivs”; resource SHP ID `c62118eb-c88d-4639-8593-3e60c48d09cc` ชี้ [Land-use index](https://tswc.ldd.go.th/DownloadGIS/Index_Lu.html) แต่ resource license/version และ license URL ไม่ระบุ ห้ามใช้ generic Catalog update date เป็น publication date ของแต่ละไฟล์จังหวัด
- **L2 — LDD Soil**: [Catalog API ldd_11_01](https://lddcatalog.ldd.go.th/api/3/action/package_show?id=ldd_11_01) ระบุ NC-ND ข้อความเดียวกัน; resource SHP ID `2ae21ea1-06af-4a8e-baea-9d629a722d85` ชี้ [Soil index](https://tswc.ldd.go.th/DownloadGIS/Index_Soil.html) ไม่มี resource-specific grant/version ที่ยืนยันได้จาก metadata ที่ตรวจ
- **O1 — OAE**: [Catalog API durian_product](https://catalog.oae.go.th/api/3/action/package_show?id=durian_product) ระบุ license “อื่นๆ” และ `license_id_other` เป็น “Creative Commons Attributions Non-Commercial”; [annual provincial resource](https://catalog.oae.go.th/dataset/durian_product/resource/3f9531b0-dc97-415a-a8d5-aa7c89f0c7b3) ไม่มี version/license URL ที่ตรวจยืนยัน ไม่กำหนดเองว่าเป็น CC BY-NC 4.0
- **P1 — POWER**: [POWER referencing](https://power.larc.nasa.gov/docs/referencing/) ขอ acknowledgment/citation และการแจ้ง redistribution; [บริการ NASA POWER](https://power.larc.nasa.gov/docs/services/aws/) อธิบายการเข้าถึงข้อมูลได้ฟรี แต่ไม่ใช่เหตุให้ตั้ง license ของชุดผสมเป็น CC0 โดยอัตโนมัติ [NASA license guidance](https://science.data.nasa.gov/about/license) ให้เงื่อนไขของไฟล์/เว็บมาก่อน และแยกข้อมูลที่ NASA ไม่ใช่เจ้าของต้นทาง ต้องตรวจ collection/upstream terms ของ MERRA2/SYN1DEG และเงื่อนไข footprint LDD ด้วย

| Local file/resource | Evidence | สิทธิ์ที่ระบุ / จุดค้าง | Public release status |
|---|---|---|---|
| ldd_chanthaburi_2026-09-17/Landuse_cti.zip | L1 | Dataset-level NC-ND; file-specific derived redistribution ยังไม่ยืนยัน | HOLD |
| ldd_regions_2026-09-18/cpn/Landuse_cpn.zip | L1 | เช่นเดียวกัน; ปีไฟล์ 2564 ไม่ใช่วันที่ Catalog | HOLD |
| ldd_regions_2026-09-18/ssk/Landuse_ssk.zip | L1 | Dataset-level NC-ND; version/grant รายไฟล์ค้าง | HOLD |
| ldd_regions_2026-09-18/utt/Landuse_utt.zip | L1 | Dataset-level NC-ND; version/grant รายไฟล์ค้าง | HOLD |
| ldd_chanthaburi_2026-09-17/sr_cti.rar | L2 | Dataset-level NC-ND; license ของ archive/derived shares ค้าง | HOLD |
| ldd_regions_2026-09-18/cpn/sr_cpn.rar | L2 | เช่นเดียวกัน | HOLD |
| ldd_regions_2026-09-18/ssk/sr_ssk.rar | L2 | เช่นเดียวกัน | HOLD |
| ldd_regions_2026-09-18/utt/sr_utt.rar | L2 | เช่นเดียวกัน | HOLD |
| ldd_surat_2026-09-23/sr_sni.rar | L2 | เช่นเดียวกัน; ไม่ให้สิทธิ์แทน land-use ที่ยังไม่มี | HOLD |
| oae_2026-09-17/durian_province.xlsx | O1 | Other-license field ระบุ Attribution/NC; standard version และ grant ราย resource ค้าง | HOLD pending clarification |
| power_orchards_2026-09-18/ cached responses 59 ชุด | P1 | Open access/citation guidance; formal collection terms และสิทธิ์ชุดผสมต้องตรวจต่อ | Conditional; combined dataset HOLD |

Paths ใน matrix อยู่ใต้ `C:/project/research_data/external/` ทุกไฟล์ ต้องมี manifest row รายไฟล์จริง ไม่ใช้หนึ่งแถวครอบทั้งหมดเมื่อทำ release จริง หลักฐาน Catalog ที่ตรวจออนไลน์รอบนี้ยังไม่ได้บันทึกเป็น immutable evidence file/hash จึงต้องเก็บสำเนาหลักฐานอย่างถูกต้องในงานถัดไปหลังอนุมัติ ห้ามแต่ง evidence hash

ต้องขอคำยืนยันผู้ให้ข้อมูลเรื่อง redistribution ของ original/derived geometry, soil area shares, sampling coordinates/weights และ weather profiles ที่พึ่ง footprint รวมทั้งข้อจำกัด non-commercial และความเข้ากันได้กับ repository/journal policy ไม่ถือการตัด geometry ออกว่าแก้ ND ได้แล้ว และไม่ใช้ license ของ NASA ครอบข้อมูล LDD/OAE

## 8. Internal artifacts vs Public candidate

Internal: raw archives, polygon audits, exact sampling geometry, cached responses, full lineage และผลวิเคราะห์เดิม จัดเก็บแบบไม่ overwrite พร้อม hash registry สถานะ internal ไม่ใช่การรับรองสิทธิ์โดยอัตโนมัติ

Public candidate หลังได้รับอนุญาต: province-year view, weather profile/method, soil vintage summary/composition, exclusions, dictionary, flags, source/evidence manifest และ reproduction specification เท่าที่ grant อนุญาต แยก raw geometry/coordinates ออกจนสิทธิ์ชัดเจน ไม่ใส่ private paths/secrets ในแพ็กเกจเผยแพร่ ไม่กำหนด blanket CC license ให้ joined dataset

ข้อจำกัดที่ผู้ใช้ dataset ต้องเห็น: ไม่มี yield รายสวน; ไม่มี geometry สวนรายเจ้าของที่ยืนยัน; A403 เป็นหน่วยแผนที่การใช้ที่ดินตาม source ไม่ใช่ suitability class; ไม่ครอบรหัสปลูกผสมใน mask; แผนที่ต่างปี; weather coarse spatial profile ไม่ใช่เซนเซอร์สวน; OAE อาจ revised และ annual reporting period ไม่ตรง physiological windows; ห้ามตีความ spatial soil/weather เป็น yield รายแปลงหรือ causal effects

## 9. Pilot Plan — จันทบุรีจังหวัดเดียว

ใช้ assets เดิมเท่านั้น: 8,512 pure polygons, 16 weather points, ช่วง 2006–2025; ออกแบบ pilot 20 province-years พร้อม soil map pair หนึ่งรุ่น โดยไม่สร้างข้อมูลใน Phase นี้ จังหวัดเลือกจากความครบของ provenance ไม่ใช่คะแนน ML

QC / Acceptance criteria สำหรับงานที่ขออนุมัติถัดไป:

1. ตรวจ hashes ทุก input, source-record references และ code version; input เปลี่ยนต้องสร้าง release ใหม่ ไม่ทับ raw/derived เดิม
2. Join OAE/weather ต้อง unique และครบ 20 keys ตาม coverage ที่ตกลง ไม่มีลดปีเอง; 240 province-months และ 3,840 sample-months ตาม inventory ต้องไม่มี duplicated/missing keys
3. ค่า source/units แปลงถูกต้อง; annual weather ต้องครบ 12 เดือนต่อ variable; incomplete ต้อง fail หรือส่ง missing+flag ตาม specification ไม่เติม/renormalize
4. Sampling weights รวม 1 ภายใน 1e-7; ตรวจ trace ของ area weights กับ pure mask และระบุ repeated weather response signatures ไม่เพิ่มจำนวน independent observations
5. ตรวจ overlay summaries เดิม: covered+uncovered เท่ากับ pure total ใน tolerance 0.1 ไร่; soil shares+uncovered share เท่ากับ 100 โดย tolerance แปลงจาก 0.1 ไร่และ precision การ export; SC/W รวมครั้งเดียว; mixed exclusions ไม่เข้าตัวหาร
6. ตรวจเดิมเรื่อง overlap/repair/CRS จาก audits ไม่ใช้ simplified map geometry คำนวณใหม่ ไม่รัน GIS ขนาดใหญ่ใน pilot QC โดยปริยาย
7. Survey/publication dates ที่ไม่มีหลักฐานต้อง null+unverified; flag footprint ย้อนเวลาและ soil vintage ปรากฏใน dictionary/view ไม่อ้าง PIT
8. Public acceptance ต้องมี grant/evidence/license version ราย resource ครบ รวม derived tables และ reproduction distribution; หากค้างแม้หนึ่ง source ให้ HOLD release แต่รายงาน internal QC ต่อได้ตามสิทธิ์ที่มี

Publication checklist: สิทธิ์และ attribution → versioned manifest/hashes → dictionary+units → coverage/missingness/QC → temporal-footprint warning → no-farm-yield statement → immutable output location → reproducibility review → journal/repository terms compatibility → ผู้ใช้อนุมัติ release แยกต่างหาก ไม่มีการ upload/เผยแพร่ในงานนี้

## 10. Missing Data — สุราษฎร์ธานี

ขาด land-use archive/A403 geometry และ code inventory, land-use map vintage/survey-date evidence, pure/mixed area audits, A403–soil intersections, sampling points/weights และ POWER profile แบบเดียวกับสี่จังหวัด มี soil archive ไม่พอสร้าง crop mask

ทางเลือกโดยยังไม่ดาวน์โหลด: (1) คง cohort public candidate ที่ 4 จังหวัดและบันทึก missing อย่างตรงไปตรงมา; (2) ขออนุมัติค้นเฉพาะ archive/manifest ที่มีอยู่ในเครื่องเพิ่มเติม; (3) เสนอ acquisition และ license audit แยกภายหลัง หากจะใช้จุดอ้างอิงจังหวัดที่มีอยู่ ต้องเป็นชุด proxy แยก ไม่เรียก A403 profile ไม่เติมลง panel นี้ด้วยวิธีต่างกันโดยไม่เปลี่ยน specification อย่างมีอนุมัติ

## 11. Reproducibility method และ verification รอบนี้

แผน reproduction: freeze inputs+hashes → ตรวจ source schemas/CRS/units → ใช้ overlay/sampling artifacts เดิม → aggregate จาก cached POWER เท่านั้น → join OAE snapshot → QC → เขียน release_id ใหม่ → สร้าง lineage/report แยก ไม่มี network fallback หรือ silent overwrite เก็บ environment/dependency versions จริงจากผู้สร้าง และ code hash; หากไม่มี version ให้ระบุ unknown ไม่เดา

Script เดิมบางตัวดาวน์โหลดและเขียน artifacts จึง **ไม่ควรรันตรงเพื่อ reproduce release** ต้องขออนุมัติ cache-only isolated export/QC ก่อน ไม่เปลี่ยน script หรือ pipeline ใน Phase 9B

OAE workbook SHA256: `6a3ae44026b5ef8037a8bb091852281d890168a8d795c9c44d5cde9a48613d4c`.

Production `C:/project/research_data/five_province_history/training/ridge_vpd_final_model.json` SHA256 ที่ตรวจ: `b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`.

รอบนี้แก้เฉพาะรายงาน Markdown ใหม่ ไม่รัน tests/training/GIS generation เพราะไม่มี executable changes ไม่รับรอง source accuracy, legal redistribution หรือ Historical PIT จากการที่ hashes ตรง หยุดรออนุมัติ pilot/internal QC และการรวบรวม license evidence ก่อนดำเนินการต่อ
