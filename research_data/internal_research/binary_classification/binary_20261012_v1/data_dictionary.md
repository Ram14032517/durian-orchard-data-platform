# Data Dictionary (Binary provincial direction)

หนึ่งแถวต่อจังหวัด–ปี ค่าที่รายงาน OAE ไม่ใช่ผลผลิตประมาณรายอำเภอ รายละเอียดทุก Field/Unit/Source/Calculation อยู่ unified_feature_dictionary.csv

Label1เพิ่ม,0ลด,exact equalsแยกออก Target-only ได้แก่ label,pct_change,yield_kg_per_rai,yield_previous_year_label_only ห้ามเป็นPredictor

H/W/V/N กำหนดไว้ใน protocol_frozen.json ค่าที่ใช้จริงหลังAnomalyแต่ละFoldอยู่ transformed_feature_lineage.json เชื่อมด้วย context_sha256 กับ fit_cache_audit.json และ source_manifest.json

NDVI/VPD/Weather เป็น exposureปีก่อน ไม่ใช่อากาศฤดูเป้าหมาย; Missingไม่เท่ากับ0; หน่วยกก./ไร่,°C,mm,%,kPa,0–1 แยกชัด Soil/GISใช้บริบทเท่านั้น ไม่ทำOverlayใหม่
