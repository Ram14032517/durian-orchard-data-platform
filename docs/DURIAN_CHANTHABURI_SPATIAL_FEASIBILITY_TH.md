# Phase 10A จันทบุรี Spatial Deep Dive Feasibility Audit

วันที่ตรวจ 12 ตุลาคม 2026 · Audit Only · Internal Research · Public Release HOLD

## ข้อสรุปเพื่อหารืออาจารย์

**พร้อมออกแบบ Pilot พื้นที่ Pure A403 และองค์ประกอบดินรายอำเภอ แต่ยังไม่พร้อมวิเคราะห์ผลผลิตรายอำเภอหรือสภาพอากาศระดับสวน** Raw A403, Soil และขอบเขตปกครองมีจริงในเครื่อง แต่ยังไม่มีตาราง Intersection เต็มที่เชื่อม Polygon–Soil–District การสร้างข้อมูลเชิงพื้นที่ที่แม่นตรงต้องอนุมัติ Overlay แบบจำกัดพื้นที่ใหม่ ไม่ใช้ Geometry ลดรายละเอียดหรือแจก Yield จังหวัดลงอำเภอ

POWER Cache ยืนยันความซ้ำของอนุกรมได้ แต่ไม่เก็บ Native Cell ID/Cell Bounds จึง **ยังยืนยันจำนวน Unique Weather Grids จริงไม่ได้** ผลตรวจ 6 Meteorological Signatures และ 4 Solar Signatures ไม่ใช่การรับรอง 6/4 Native Grids และไม่ใช่จำนวนสถานีอิสระ

รอบนี้อ่าน Metadata, DBF, CSV, JSON, XML, โค้ดและเอกสารเดิม ไม่สร้าง Spatial Dataset ไม่คำนวณ Intersection/Union ขนาดใหญ่ ไม่ดาวน์โหลด ไม่รัน ML/Scenario และไม่เปลี่ยน Production/API/Frontend

## 1 ขอบเขตปกครองที่พบจริง

โฟลเดอร์ต้นทาง:

`C:/project/research_data/external/ldd_chanthaburi_2026-09-17/landuse/Landuse_cti/จันทบุรี2568/ขอบเขตการปกครอง/`

| ไฟล์ | จำนวน Records | หน่วยรหัสในไฟล์ | CRS จาก PRJ |
|---|---:|---|---|
| จันทบุรี_Amp.shp | 18 | 10 AMPHOE_IDN ได้แก่ 2201–2210 | EPSG:32647 |
| จันทบุรี_Tam.shp | 84 | 78 TAMBON_IDN ที่ไม่ซ้ำ | EPSG:32647 |
| จันทบุรี_Pro.shp | 9 | จังหวัด 22 หลายชิ้น | EPSG:32647 |

มี DBF/SHX/PRJ และ `.shp.xml` คู่ไฟล์ อ่าน DBF UTF-8 ได้ Amp รหัส 2202 มี 3 ชิ้น, 2203 มี 2 ชิ้น และ 2206 มี 6 ชิ้น ดังนั้น **18 Records ไม่ใช่ 18 อำเภอ** ต้อง dissolve ตาม AMPHOE_IDN ไม่รวม/Join ตามชื่อหรือ OBJECTID อย่างเดียว Tam มีรหัสส่วนเกาะ 220651/220652 และชื่อ/remark ประกอบ ต้องตรวจ Crosswalk ก่อนถือว่า 78 รหัสหมายถึงตำบลทางราชการ 78 แห่ง

XML ของ Amp/Pro มี CreaDate และ mdDateSt 2021-06-14; Tam มี CreaDate 2021-06-14 และ mdDateSt 2021-06-11 พร้อม Processing History procdate 2013-07-11 **วันที่เหล่านี้เป็น Metadata/Processing ไม่ใช่หลักฐานปีที่แนวเขตมีผลตามกฎหมายหรือวันสำรวจ** แม้ไฟล์อยู่ในโฟลเดอร์ Land-use 2568 ก็ห้ามตีความว่าแนวเขตเป็นรุ่นสำรวจ 2568 ขณะนี้ boundary_valid_date และ official_boundary_vintage ยัง Unverified

ยังไม่ตรวจ Topology, ช่องว่าง/การทับซ้อนระหว่างอำเภอ หรือตำบล–อำเภอ–จังหวัดด้วย Geometry ในรอบ Audit นี้ จึงยังไม่รับรอง Spatial Join ผลจริง

## 2 การแจกแจง A403 ตามอำเภอ

Raw อยู่ที่:

`C:/project/research_data/external/ldd_chanthaburi_2026-09-17/landuse/Landuse_cti/จันทบุรี2568/การใช้ที่ดิน/LU_CTI_2568.shp`

โครงสร้าง DBF มี LU_CODE และ Area_Sqm/Area_Rai แต่ **ไม่มีรหัสอำเภอ/ตำบล** Phase 9D ยืนยัน Pure A403 8,512 รูป รวม 539,971.790558 ไร่ และ Mixed ที่มี A403 5,364 รูป รวม 139,426.573408 ไร่ ต้องเชื่อมขอบเขตด้วย Geometry ไม่เดาจากชื่อหรือกำหนดทั้ง Polygon ให้อำเภอที่ Centroid อยู่

วิธีที่เสนอหลังอนุมัติ: dissolve แนวเขตตามรหัส → ตรวจ CRS/Topology → spatial index คัด candidate → ตัด A403 กับอำเภอ → เก็บ fragment ที่ข้ามเขตแยกกัน โดยมี parent source_record และพื้นที่ของแต่ละ fragment หาก Polygon พาดหลายอำเภอ แต่ละอำเภอรับเฉพาะพื้นที่ intersection ของตน ไม่รับพื้นที่เต็มซ้ำ และต้องเก็บส่วนที่อยู่นอก/ไม่ตรงแนวเขตเป็น unassigned ไม่ Drop เงียบ ๆ

ใช้ source_record แบบ 0-based ผูกกับ SHA256 ของ SHP/DBF ต้นฉบับและ LU_CODE ไม่ใช้ลำดับแถวหลัง sort/filter เป็นตัวตนถาวร รหัส A403 เป็นการจำแนกการใช้ที่ดินทุเรียน ไม่ใช่ชั้นเหมาะสม S1 หรือขอบเขตสวนรายเจ้าของที่ยืนยันแล้ว

## 3 ความพร้อมของ Soil Intersections

| Asset | สิ่งที่เก็บจริง | ใช้แยกสัดส่วนดินรายอำเภอได้ทันทีหรือไม่ |
|---|---|---|
| `regional_orchards/cti_polygon_audit.csv` | source_record, kind, LU_CODE, geometry_rai, covered_rai, soil_overlap_rai | ไม่ได้ ไม่มี soil_code/พื้นที่ต่อคู่/Intersection Geometry |
| `regional_orchards/soil_series_comparison.csv` และ Phase 9D `soil_composition.csv` | ผลรวมตามหน่วยแผนที่ดินระดับจังหวัด | ไม่ได้ แตกยอดลงอำเภอจากผลรวมไม่ได้ |
| `soil_evidence_chanthaburi/polygon_audit.json` | Parent Record และพื้นที่/การครอบคลุมดิน | ไม่ได้ ไม่มีคู่ Polygon–Soil–District |
| `soil_evidence_chanthaburi/display_geometry.json` | รวม Intersection ตาม soil code และ pure/mixed แล้ว simplify 30 เมตร; Soil/District display simplify 100 เมตร | ใช้ดูภาพประกอบได้ แต่ไม่ใช้คำนวณสัดส่วนพื้นที่แบบแม่นตรง |
| Raw `Soil_จ.จันทบุรี.shp` | 555 Records, soilseries/ชื่อ/คุณสมบัติ/AMPHOE_IDN พร้อม Geometry เต็ม | เป็น Input สำหรับ Overlay ใหม่ ไม่ใช่ตารางดินภายใน A403 สำเร็จรูป |

โค้ด `C:/project/tools/build_soil_evidence.py` สร้าง cuts ในหน่วยความจำแล้วรวมและลดรายละเอียดก่อนบันทึกแผนที่; `C:/project/tools/prepare_regional_orchards.py` บันทึกผลรวมและ Polygon Audit ไม่เก็บ pair-level cuts รหัสดิน–อำเภอใน Raw Soil ไม่พิสูจน์ว่าแนวเขตตรงกับ Amp รุ่นที่เลือก ต้องตรวจเชิงพื้นที่ก่อน ไม่สรุป Soil ทั้งอำเภอเป็น Soil เฉพาะพื้นที่ทุเรียน

Raw Soil:

`C:/project/research_data/external/ldd_chanthaburi_2026-09-17/soil/จันทบุรี/Soil_จ.จันทบุรี/Soil_จ.จันทบุรี.shp`

ข้อเสนอคือ Overlay เฉพาะ A403 fragments ใน Pilot กับ Raw Soil เต็ม เพื่อเก็บ area ต่อ fragment–soil unit รวม SC, W และ Uncovered ตัวหารสัดส่วนเป็น Pure A403 ของอำเภอนั้นทั้งหมด ไม่ใช่พื้นที่ดินทั้งอำเภอหรือเฉพาะส่วน Covered และแยก Mixed-use ออก

## 4 Weather Resolution และสิ่งที่ตรวจยืนยันได้

ตรวจ Cache 16 จุดจันทบุรี เทียบ SHA256 กับ `.source.json` ทุกไฟล์ผ่าน ใช้ข้อมูลเดือน 01–12 ช่วง 2006–2025 รวม 240 เดือนต่อจุด; Header มี MERRA2/SYN1DEG/POWER, API v2.10.0 และ LST

| วิธีนับจาก Cache | จำนวนที่พบ | ความหมาย |
|---|---:|---|
| จุดตัวอย่าง/พิกัด Response | 16 | ตำแหน่ง Request ที่ปัดพิกัด ไม่ใช่ Grid Center |
| Signature T2M | 6 | อนุกรมรายเดือนที่ต่างกัน |
| Signature RH2M | 6 | อนุกรมรายเดือนที่ต่างกัน |
| Signature PRECTOTCORR | 6 | อนุกรมรายเดือนที่ต่างกัน |
| Signature Meteorology 3 ตัวร่วมกัน | 6 | กลุ่ม Exposure ที่แยกได้จากค่าที่ Cache เก็บ |
| Signature ALLSKY_SFC_SW_DWN | 4 | อนุกรมรังสีที่ต่างกัน |
| Signature ทั้ง 4 Parameters | 11 | คู่ Meteorology/Solar ที่แตกต่าง ไม่ใช่ 11 สถานีหรือ 11 Native Grids |
| Native Weather Grid IDs/Bounds | ไม่พบ | จำนวนกริดจริงยัง Unverified |

Signature ใช้ SHA256 ของ JSON Parameter Series ที่เรียง key โดยไม่นับ annual month 13; กลุ่ม Meteorology มีสมาชิก 5/4/3/2/1/1 จุด และ Solar 7/5/2/2 จุด การเท่ากันของค่าที่ปัดไว้ 240 เดือนเป็นหลักฐานความซ้ำของ Response แต่ไม่พิสูจน์ Cell ID ที่ไม่ปรากฏในไฟล์

หลักฐานวิธีเดิมใน `C:/project/research_data/regional_orchards/SOURCE_TH.md` ระบุ Meteorology ประมาณ 0.5° × 0.625° และ Solar ต่าง Resolution ส่วนกรอบ 0.25° เป็น **Sampling Stratum ของโครงการ** ไม่ใช่ NASA Native Grid ดังนั้นอาจใช้เปรียบเทียบ Exposure กว้าง ๆ แต่ยังไม่รองรับความแตกต่างระดับสวน/หุบเขาหรือทุกอำเภออย่างอิสระ

ห้ามเลือกจุดที่อยู่ในอำเภอแล้วนำ Weight จังหวัดมาถ่วงใหม่เรียกว่า District Weather เพราะ Weight ผูกพื้นที่ A403 ทั้ง Stratum ซึ่งอาจข้ามอำเภอ ต้องมีตาราง district–stratum area allocation และวิธีตัวแทนที่อนุมัติก่อน Native Grid Comparison ต้องมี Grid Definition/Lookup Evidence เพิ่มเติมโดยแยก Meteorology/Solar รอบนี้ไม่อนุมาน Native IDs จากสูตร snap ที่ไม่ได้ตรวจ

## 5 DEM และผลผลิตระดับอำเภอ

พบ `C:/project/research_data/five_province_history/terrain_srtm30_samples.json` และ `terrain_selected_points.csv` เป็น Cached OpenTopoData SRTM30m 90 Samples รอบจุดเลือก 10 บริเวณใน 5 จังหวัด จันทบุรีมี 2 บริเวณคือท่าใหม่ (12.723, 101.983) และเขาคิชฌกูฏ (12.825, 102.135) บริเวณละ 3×3 จุด รวม 18 Samples ไม่ใช่ DEM Raster ต่อเนื่องหรือค่าเฉลี่ยอำเภอ/พื้นที่ A403

CSV แยก supplied_elevation/slope ซึ่งยังไม่ยืนยันออกจาก srtm values ชัดเจน ข้อมูล third coordinate ใน POWER ไม่ใช้แทน DEM30m ไม่พบ Continuous DEM Raster ในการค้น filename ของ `C:/project/data` และ `C:/project/research_data` แบบรวม ignored files; ข้อนี้ไม่ใช่การรับรองว่าไม่มีไฟล์ในทุกโฟลเดอร์ของเครื่อง

ผลผลิต: Phase 9D และ OAE workbook เป็น **จังหวัด–ปี** ไม่พบ Chanthaburi district-year target ที่ผ่านตรวจใน Asset Inventory ที่ใช้รอบนี้ `C:/project/docs/DISTRICT_DATA_SOURCE_REVIEW_TH.md` และ `production_source_review.json` ระบุว่าเอกสารจันทบุรีที่มีให้ยอดจังหวัด ไม่ใช่รายอำเภอ ตรวจข้อความของ `C:/project/research_data/five_province_history/evidence/source_review_2026-10-08/chanthaburi_april_2026.pdf` เพิ่มเติม พบยอดจังหวัดปี 2568 และรายละเอียดพื้นที่/ภัย/โครงการ แต่ไม่ได้เป็นตาราง Yield/Bearing Area รายอำเภอที่ใช้สร้าง Target ได้ เอกสารยังมีข้อมูลเหมาะสม S1/S2 ซึ่งต้องไม่ปะปนกับ A403

`district_reference_points.csv`, `district_soil_exploration.csv`, `soil_properties_by_district.csv` เป็นตำแหน่งอ้างอิง/ข้อมูลดิน ไม่ใช่ผลผลิตอำเภอ ห้ามกระจาย Yield จังหวัดตามพื้นที่ A403 หรือสัดส่วนดิน

## 6 หน่วยวิเคราะห์และช่องว่าง

| หน่วย | Key ที่เสนอ | สิ่งที่ตอบได้ | สิ่งที่ห้ามตีความ |
|---|---|---|---|
| Land-use Polygon | archive hash + source_record + map vintage | พื้นที่รหัส A403 ของรุ่นแผนที่ | สวนรายเจ้าของ/พื้นที่ให้ผลจริง |
| District fragment | parent polygon + admin ID + boundary version | ส่วนพื้นที่ที่ถูกตัดตามแนวเขต | Target Yield ใหม่ |
| District–soil map pair | district ID + LU/Soil/Admin vintage + soil code | Soil composition ใน Pure A403 | Soil Measurement รายสวน หรือ 20 Observations อิสระ |
| Weather exposure group | parameter family + response/source hash + period | กลุ่มอนุกรมที่ซ้ำ/ต่างกัน | สถานีอิสระหรือ Native Grid ID ที่ยืนยันแล้ว |
| District–year ในอนาคต | district ID + year + source vintage | ใช้ได้เมื่อมี Actual ที่ตรวจแล้ว | การยก OAE Province เป็น District Target |

ช่องว่างที่ต้องปิด: Boundary Effective Date/Code Crosswalk/Topology; pair-level Soil cuts; Native Grid Evidence และการจัดสรรน้ำหนักรายอำเภอ; Continuous DEM หากต้องศึกษา Terrain; Target/Bearing Area รายอำเภอ; Cultivar/Management/Phenology; Historical Footprints และสัดส่วน A403 ใน Mixed-use

ความเสี่ยงร่วม: Land-use ปี 2568 ไม่พิสูจน์สถานะพื้นที่ปลูกย้อนหลัง 2006–2025; Soil ปีผลิต 2561 และ Boundary XML ปี 2021 เป็นเวลาคนละความหมาย; รหัส Pure ไม่แปลว่าพื้นที่ทั้งหมดให้ผลแล้ว; Geometry ซ่อม/ช่องว่างต้องมี QC; LDD/OAE Derived Distribution Rights ยัง Pending และต้องตรวจสิทธิ์ Administrative Resource เพิ่ม ไม่ถือว่าอยู่ใน ZIP เดียวแล้วเผยแพร่ได้ Historical PIT ไม่เปลี่ยนสถานะ

## 7 Pilot แบบเดียวที่เสนอหลังอนุมัติ

**ท่าใหม่ AMPHOE_IDN 2203 Soil Composition ใน Pure A403 ปีแผนที่ 2568** เลือกจากความพร้อม Raw/Admin และขอบเขตงาน ไม่เลือกจาก Yield/Outer Scores Amp รหัสนี้มี 2 Records ต้อง dissolve ก่อน ไม่ทำ Forecast/Scenario หรือ Yield Analysis

ขอบเขต: Overlay เฉพาะ Pure A403 ที่ตัดกับท่าใหม่และ Raw Soil ที่เกี่ยวข้อง ไม่ Overlay ประเทศ/4 จังหวัดใหม่ เก็บ full-resolution cuts ใน Internal Version ใหม่ พร้อม source hash/parent IDs/units และ unassigned area; Mixed-use แสดงต่าง Layer โดยไม่แบ่ง Yield หรือเดาสัดส่วนทุเรียน Weather 16 จุดแสดงเป็น Exposure Diagnostic ของจังหวัดเท่านั้น ไม่สร้าง District Weather Profile รอบ Pilot นี้ ไม่ใช้ DEM จุดสองจุดแทนดิน/ภูมิประเทศทั้งอำเภอ

แผนที่เสนอ 3 แผง: (1) ขอบเขตท่าใหม่และ Pure A403 พร้อมส่วนที่ตัดข้ามเขต (2) Pure A403 จำแนก Soil Units พร้อม SC/W/Uncovered และ Legend ปีแผนที่ (3) Pure เทียบ Mixed-use ใน Footprint โดยแยกชัด สามารถลด Geometry สำหรับแสดงผลหลังคำนวณพื้นที่เต็มแล้วเท่านั้น กราฟสัดส่วนใช้ตัวหาร Pure A403 ทั้งอำเภอ ไม่ใช่ดินทั้งอำเภอ

QC/Acceptance ที่ล็อกก่อนสร้าง:

1. Input/Seal Hash ตรง; CRS ถูก; admin ID=2203 ครบทั้ง 2 Records; Boundary Date ที่ยังไม่รู้ติด Flag ไม่เติมเป็นปี 2568
2. ตรวจ Geometry valid/repair-area change และขอบเขตทับซ้อน; หยุดเมื่อพบ material overlap/gap ที่ทำให้ allocation ไม่ชัด ไม่ปรับ Threshold เพื่อให้ผ่าน
3. Parent Polygon area = pilot intersection + remaining/outside area ภายใน tolerance 0.1 ไร่ตาม Contract เดิม; ข้ามขอบเขตต้องมี Parent Link ไม่ centroid allocation; ไม่ตัดส่วนที่มีปัญหาออกเงียบ ๆ
4. Pure area = Covered + Uncovered; ผลรวม Soil intersections ตรง Covered ภายใน 0.1 ไร่; SC/W รวมครั้งเดียว; Shares รวม Uncovered ตรง 100% ตาม tolerance ของตัวหารใน Phase 9C; เก็บ numerical residual ไม่แก้ Raw
5. Unique Keys/Referential Integrity/Source Lineage ครบทุก fragment และ summary; label Mixed แยก; ไม่สร้าง OAE District Target; เมื่อมีเพียงหนึ่งอำเภอห้ามอ้างว่าผลรวมของ 10 อำเภอ reconcile แล้ว
6. เก็บ Raw/Pilot Phase 9C/Phase 9D/Production Hash ก่อน–หลัง ห้ามเขียนทับ; Public HOLD และไม่มีการส่ง Geometry ภายนอก

## 8 การตรวจความคงเดิมและสถานะหยุด

Phase 9D Output Seal ผ่าน; ตรวจ SHA256 POWER Cache จันทบุรี 16/16 ผ่าน Protected Snapshot ก่อน–หลังงาน **1,157 ไฟล์คงเดิมทั้งหมด** รวม Production, Raw/Admin, Dataset และเอกสารที่ใช้ตรวจ และตรวจเทียบ Protected Hash ที่ Phase 9D บันทึกไว้เดิมอีก **1,123 ไฟล์ตรงกันทั้งหมด** ไม่มีการรัน Training, GIS Overlay ใหม่, Scenario หรือ Live API

Production Model SHA256 คงเดิม: `b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680` สร้างเฉพาะรายงานนี้ ไม่แก้ Pipeline/API/Frontend/Tests หรือ Artifacts เดิม จึงไม่รัน Repository Training Tests ในงาน Audit นี้

ผลนี้อนุมัติได้เพียงความเป็นไปได้ทางเทคนิคของ Pilot ไม่ใช่การยืนยัน Spatial Dataset หรือ Native Grid Count รออนุมัติ Overlay จำกัดท่าใหม่ก่อนสร้าง Dataset จริง และรอข้อมูลเพิ่มหากจะวิเคราะห์ผลผลิตรายอำเภอ/อากาศละเอียด
