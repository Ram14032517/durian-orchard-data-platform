# ดัชนีงานวิจัยทุเรียนภายใน

อัปเดต 12 ตุลาคม 2569 ใช้คู่กับ [คู่มือเริ่มต้น](../../00_START_HERE_TH.md) งานในโฟลเดอร์นี้แยกจาก Production ทั้งหมด คง **Public Release HOLD** ไม่อัปโหลด Dataset หรือ Derived GIS ภายนอกโดยอัตโนมัติ

## เลือกไฟล์อ่านตามงาน

| ต้องการทำอะไร | เปิดไฟล์นี้ก่อน |
| --- | --- |
| สรุปความคืบหน้าให้อาจารย์อย่างกระชับ | [สรุปความคืบหน้า 1–2 หน้า](advisor_progress/progress_20261012_v1/advisor_progress_summary_th.pdf) |
| อ่านผลทดลองเพิ่ม/ลดสองกลุ่มล่าสุด | [Binary Classification PDF](binary_classification/binary_20261012_v1/binary_classification_report_th.pdf) และ [คู่มือ/โค้ด/CSV](binary_classification/binary_20261012_v1/README_TH.md) |
| อ่านภาพรวมการวิเคราะห์และโมเดลจังหวัด | [Final Advisor Report](final_advisor/final_20261012_v1/final_advisor_report_th.pdf) |
| อ่านข้อจำกัดของการแบ่งผลผลิตเป็นรายอำเภอ | [Spatial Allocation Report](district_spatial_allocation/allocation_20261012_v1/spatial_allocation_report_th.pdf) |
| ตรวจข้อมูล GIS/อากาศ/ผลผลิต 4 จังหวัด | [รายงาน Phase 9D](../../docs/DURIAN_FOUR_PROVINCE_INTERNAL_DATASET_TH.md) และ [Source Manifest](four_provinces/phase9d_20261012_v1/source_manifest.json) |
| ดูข้อมูลรายอำเภอจันทบุรีที่ถอดจากต้นฉบับ | [Phase 11B รุ่น v2](chanthaburi_district_yield/phase11b_20261012_v2/dataset_preview.html) |
| ดูแผนที่/หน่วยดินท่าใหม่สำหรับอาจารย์ | [Tha Mai Advisor Brief รุ่น v2](tha_mai_spatial/phase10g_20261012_advisor_preview_v2/advisor_brief.pdf) |
| เตรียมขอข้อมูลจริงเพิ่มโดยยังไม่ส่งคำขอ | [Data Requirements Phase 11F](chanthaburi_district_yield/phase11f_20261012_v1/ONE_PAGE_DATA_REQUIREMENTS_TH.html) |

ลิงก์ชุดเก่าบางส่วนเป็นหลักฐานที่มีเฉพาะเครื่องนี้ ไม่ใช่ไฟล์ที่รวมใน Git commit ล่าสุด ถ้าคัดลอกเฉพาะ Repository ไปเครื่องใหม่ ต้องนำข้อมูลภายในที่ได้รับอนุญาตและ Manifest มาด้วยก่อนใช้งาน

## โครงสร้างที่เก็บไว้

| หมวด | โฟลเดอร์ | ข้อควรแยก |
| --- | --- | --- |
| รายงานอาจารย์ | `advisor_progress/`, `final_advisor/`, `chanthaburi_eda/` | อ่านผลเดิม ไม่จำเป็นต้องฝึกโมเดลซ้ำ |
| ทดลอง AI/ML | `automl/`, `integrated_ndvi_vpd/`, `optimized_classification/`, `binary_classification/` | Regression, สามกลุ่ม และสองกลุ่มเป็นคนละโจทย์ ห้ามเทียบคะแนนตรง ๆ |
| ข้อมูลจังหวัด | `chanthaburi_pilot/`, `four_provinces/` | Yield จังหวัด–ปี ไม่ใช่รายสวน |
| หลักฐานพื้นที่ย่อย | `tha_mai_spatial/`, `chanthaburi_yield_feasibility/`, `chanthaburi_district_yield/` | แยก Geometry, หน่วยดิน และ Yield รายอำเภอ ไม่ถือ Polygon เป็นสวนรายเจ้าของ |
| ค่าประมาณพื้นที่ย่อย | `district_spatial_allocation/` | ค่าประมาณไม่ใช่ผลผลิตรายงานจริง ห้ามนำไปเป็น Label จริง |

โฟลเดอร์ย่อยชื่อ `*_v1`, `*_v2` เป็นรุ่นหลักฐาน ไม่ย้าย/เปลี่ยนชื่อเพื่อลดความรก เพราะโค้ด, Manifest, Notebook และ HTML อ้างเส้นทางเหล่านี้อยู่ ไม่ลบรุ่น Failed/Quarantined หรือร่างเก่าเพื่อให้เหลือเฉพาะผลที่ดูดี

## งานล่าสุด: Binary Classification

รุ่น `binary_classification/binary_20261012_v1` ใช้ผลผลิต OAE จริง เพิ่มขึ้น = 1 ลดลง = 0 เท่ากันพอดีแยกออก ใช้ 4 จังหวัด และแบ่ง Train/Validation/Test ตามเวลา

- Candidate จาก Validation คือ Random Forest ใช้ผลผลิตย้อนหลัง ทายถูก 13/24 กรณี Accuracy 54.2% และ Macro F1 0.534
- Baseline ทายกลุ่มบ่อยถูก 14/24 กรณี Accuracy 58.3% แม้ Macro F1 ต่ำกว่า จึงยังไม่รับรองโมเดลพร้อมใช้งานจริง
- Weather ดีขึ้นบางตระกูล ส่วน NDVI/VPD ยังไม่ช่วยสม่ำเสมอ ไม่เปลี่ยน Candidate ตามคะแนน Test
- ปี 2020–2025 เคยใช้พัฒนาแล้ว ไม่ใช่ Independent Holdout ยังไม่รับรอง Historical PIT และไม่มีพยากรณ์ปี 2569
- Pretraining Checks 14 ข้อ และ Independent Checks 21 ข้อผ่าน Production และข้อมูลต้นทางไม่เปลี่ยนในรอบทดลอง

## ไฟล์ในรุ่นทดลองใช้ทำอะไร

| กลุ่ม | ไฟล์หลัก |
| --- | --- |
| อ่านรายงาน | `binary_classification_report_th.pdf`, `.html`, `README_TH.md` |
| อ่านคะแนน/ค่าทำนาย | `model_comparison.csv`, `predictions_vs_actual.csv`, `classification_report.csv`, `confusion_matrix.csv` |
| ตรวจจังหวัด/ปี/ปัจจัย | `province_metrics.csv`, `year_metrics.csv`, `feature_group_contributions.csv`, `feature_importance.csv` |
| ตรวจข้อมูล/หน่วย | `unified_features.csv`, `unified_feature_dictionary.csv`, `all_OAE_direction_labels.csv`, `data_dictionary.md` |
| ทำซ้ำ | `prepare.py`, `train.py`, `report.py`, `verify.py`, `render_pdf.cjs`, `pdf_qa.py`, `seal.py`, `environment.json` |
| ตรวจย้อนหลัง | `protocol_frozen.json`, `source_manifest.json`, `output_manifest.json`, `fit_cache_audit.json`, `transformed_feature_lineage.json`, `final_verification.json` |
| ดูหลักฐานการตรวจหน้า PDF | `pdf_qa/`, `pdf_layout_verification.json` |

ไม่แก้ CSV, รายงาน หรือ README ภายในรุ่นที่ Seal แล้ว หากทดลองใหม่ให้คัดลอกเฉพาะสคริปต์ไปโฟลเดอร์รุ่นใหม่ที่ยังไม่มี Outputs ตามคู่มือของรุ่นนั้น ใช้ Python Environment วิจัยที่ระบุไว้ ไม่ติดตั้งใน Production และไม่ดาวน์โหลด NDVI/VPD ซ้ำโดยไม่มีเหตุจำเป็น

## การเก็บใน Git และการส่งต่อ

ข้อมูลภายในอื่น ๆ ถูก ignore เป็นค่าเริ่มต้น เพื่อลดความเสี่ยงจาก `git add .` ชุดล่าสุดที่ผ่านการตรวจสามารถบันทึกเป็น **Local commit** ด้วยรายชื่อไฟล์ที่ตรวจแล้วเท่านั้น ร่าง `report_draft1/` ยังเก็บในเครื่อง แต่ไม่รวมใน Snapshot ล่าสุด

`.gitattributes` ปิดการแปลง LF/CRLF เฉพาะรุ่น Binary ที่ Seal แล้ว เพื่อให้ SHA256 ตรงแม้ Checkout บน Windows การ Commit ไม่ใช่การอนุญาต Publish หรือ Push ข้อมูลภายใน ต้องตรวจสิทธิ์และข้อจำกัดก่อนส่งออกทุกครั้ง

Raw GIS/Workbook/Cache เดิม, Environment ใน `.build/`, Credentials และรุ่นข้อมูลภายในเก่าไม่ได้รวมเป็นชุดข้อมูลเผยแพร่ ไม่ใช่ว่า Clone แล้วจะมีหลักฐานครบสำหรับรัน Training ทันที

ไม่รัน Training ใหม่ ไม่ย้าย Protected Assets และไม่แก้เว็บ/API/โมเดล Production ในงานจัดระเบียบนี้
