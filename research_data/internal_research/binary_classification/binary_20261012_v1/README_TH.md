# ผลทดลองทิศทางผลผลิตทุเรียน 2 กลุ่ม (Internal)

อ่าน binary_classification_report_th.pdf ก่อน Candidate หลัก RandomForest H ไม่ใช่โมเดลที่เลือกจากคะแนน Outer สูงสุด Public HOLD และยังไม่รับรอง Historical PIT ไม่มี Forecast ปี 2569

## ผลและไฟล์

model_comparison.csv คะแนน Accuracy, Balanced Accuracy, Macro F1 และจำนวนทายถูก; predictions_vs_actual.csv ค่าจริง/ค่าทำนายระดับจังหวัด–ปี; classification_report.csv คะแนนแต่ละ Class; confusion_matrix.csv จำนวนแต่ละช่อง 2×2; province_metrics/year_metrics.csv แยกพื้นที่/ปี; feature_group_contributions.csv เปรียบเทียบกลุ่มข้อมูลบน Keys เดียวกัน; feature_importance.csv Inner-only ของ Candidate

unified_features.csv 64 แถวปี2010–2025 แยก Target-only ออกจาก Predictors; all_OAE_direction_labels.csv 80 แถว/76คู่มีLag; exact_equal_excluded.csv มี 0 แถว ไม่ใช้ช่วงทรงตัว±5%

## ทำซ้ำแบบ Offline

Python: C:/project/.build/durian-automl-20261012-v1/Scripts/python.exe ใช้ -B -X utf8 ไม่ใช้ py launcher ไม่ติดตั้งเพิ่ม

คัดลอก prepare.py/train.py/report.py/verify.py/render_pdf.cjs/pdf_qa.py ไปโฟลเดอร์ version ใหม่ที่ยังไม่มี Outputs ภายใต้ C:/project ห้ามรันเขียนทับรุ่นนี้

1. python -B -X utf8 prepare.py ตรวจ sealed inputs และสร้าง Binary Labels
2. python -B -X utf8 train.py ล็อก Protocol ก่อน Outer รัน Tests และทดลองหนึ่งครั้ง เวลาไม่เกิน55นาที
3. python -B -X utf8 report.py สรุปผล ไม่ฝึกหรือเลือกโมเดลใหม่
4. python -B -X utf8 verify.py ตรวจ Metrics/Cutoff/Cache/Lineage/Hashes
5. node render_pdf.cjs แปลง HTML Offline เป็น PDF แล้ว render ด้วย Poppler และรัน pdf_qa.py

Environment/package versions อยู่ environment.json ใช้ CPU2 Seed42 ไม่ใช้ GPU/SMOTE แยก Cache ตาม Source/Train/Evaluation Features/Params/Cutoff/Study; Outer ไม่เข้า Inner Cache

## ตีความให้ถูกต้อง

Candidate family/features ตรึงจาก Inner ก่อน Outer แรก Later Inner เลือกเฉพาะ Preset ในตระกูลเดิม adaptive_nested รายงานแยก ทุกปีทุกจังหวัดใน Fold เดียวกัน หนึ่งปีมี4กรณีเท่านั้น

Full history: Outer2020–2025 24Keys; NDVI common: Outer2022–2025 16Keys ใช้ Training Cohort เดียวกันทุกแขนภายใน Study ไม่เทียบ F1 ข้าม Study NDVI cohort ขาด2018ตามข้อมูลจริง ไม่เติม Raw Months

Label เพิ่ม1ถ้าOAEY>Y−1 ลด0ถ้าน้อยกว่า เท่ากันแยกออก Regression ทำนาย SignedYoYpct แล้วแปลงที่0 ไม่มีการใช้Y−1จริงเป็นตัวหารตอนพยากรณ์ ค่า0ทำนาย/ทิศทางล่าสุด0 fallback Train Majority เท่านั้น

กฎIssue1มีนาคมY; Weatherทั้งปีY−1; Lagล่าสุดY−2 ไม่ใช่หลักฐานว่าวินเทจมีทันวันนั้น Publication Dates ยังไม่รับรอง Reanalysis/NDVI reprocessing/OAE revision มีข้อจำกัด ไม่ใช้ Soil/A403เป็นFeaturesย้อนหลัง ไม่อ้างรายสวนหรือเหตุและผล

Files ต้นทาง/Production ไม่เปลี่ยน การตรวจทุก Fold อยู่ final_verification.json/output_manifest.json ไม่มีการดาวน์โหลดหรือ Upload ภายนอก
