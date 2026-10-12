# Phase 5B — Preflight หยุดก่อน Training

11 ตุลาคม 2026 — Status: blocked by new orchestration test; actual estimator fits = 0

## ผลตรวจ

- ก่อนเพิ่ม runner: Python 242/242 และ JavaScript 30/30 ผ่าน
- Tests ใหม่เฉพาะ Training orchestration: 2/3 ผ่าน, 1 failure
- ทั้ง Repository หลังเพิ่ม runner: Python 244/245 ผ่าน, failure เดียวกัน; JavaScript 30/30 ผ่าน ไม่มี failure อื่น
- Failure: `test_inner_only_selection_and_cache`, `tests/test_enso_training.py:54` คาด calls=48 แต่ stub ถูกเรียกจริง 46 ครั้ง
- ยังไม่เริ่ม CatBoost Training, ไม่สร้าง Training run, ไม่มีคะแนน Outer ใหม่ ไม่เปลี่ยน Features/Grid/Calendar/Production/API/Frontend

## สาเหตุเบื้องต้นและแผนแก้ที่ต้องอนุมัติ

Test นับว่าทุก fold year ต้อง Fit ทั้ง 4 candidates แต่ลูปจริงใช้ปี 2014–2024 เป็น Inner อย่างน้อยหนึ่งครั้ง จึงมี 11 × 4 = 44 unique fits; ปีสุดท้าย 2025 ไม่เป็น Inner ของปีถัดไปใน Protocol นี้ ใช้เพียง 2 candidates ที่ถูกเลือกจาก Inner แล้ว จึงรวม 46 unique fits ไม่ใช่ 48 และควรมี 23 cache keys ต่อแขน ไม่ใช่ 24

นี่เป็นผลจาก prediction stub เท่านั้น ไม่ใช่คะแนนโมเดลหรือข้อมูลสำหรับจูน การแก้ที่เสนอคือเปลี่ยน expected counts ของ Test ให้สะท้อนขอบเขต Inner/Outer ที่ล็อกไว้ พร้อม assert final-year fitting ว่าฝึกเฉพาะ winners จาก Inner; ไม่แก้ model logic/Features/Grid เพื่อไล่คะแนน **ยังไม่ได้แก้ assertion** ตามคำสั่งให้หยุดเมื่อ Tests ไม่ผ่าน

## ไฟล์ที่เพิ่มในรอบนี้

- `tools/durian_model/experiment_enso_training.py`: isolated runner สองแขน, audit consumed lineage/cutoff/hash ก่อน Fit, Inner-only depth selection, arm/source/fold cache separation, source snapshot allowlist เฉพาะ .py, Phase 3 Weather-prediction regression gate, paired summaries และ artifact isolation
- `tests/test_enso_training.py`: 3 stub-based tests สำหรับ selection/cache, Outer target poisoning และ paired summary/missing evaluation keys; ไม่ฝึก estimator
- รายงานนี้

ENSO encoding ใช้ fixed three-state one-hot schema ที่กำหนดใน Phase 5A ไม่มี learned encoder parameters จึงไม่ Fit vocabulary จาก Outer หรือทั้ง dataset; category ที่เป็นที่รู้จักแต่ไม่ปรากฏใน Training จะยังมีคอลัมน์เดิม, missing/unknown category ถูกปฏิเสธก่อน Fit ไม่เติมจากอนาคต

## Hash Protection

- Phase 5A saved artifacts 79 ไฟล์ตรวจ inventory แล้วตรง
- Source hashes ใน Phase 5A configuration 11 ไฟล์ตรงทั้งหมด
- Archive source/table hashes 85 รายการตรงทั้งหมด
- Protected baseline 645 ไฟล์จาก Phase 5A ตรงทั้งหมด
- Production model SHA256: `b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

Git working tree มีการเปลี่ยนแปลงก่อนงานนี้อยู่แล้ว ตรวจสถานะก่อนเริ่ม ไม่ stage/reset/delete หรือแก้ไฟล์เดิม และไม่ได้สร้าง snapshot ที่รวม Secrets

## ข้อจำกัด

ยังไม่ยืนยัน runner ใหม่ผ่าน Preflight ทั้งชุด จึงยังไม่รายงาน MAE/RMSE/Bias/ENSO Contribution จริง; historical PIT และ content vintage ยัง unverified เช่นเดิม ต้องได้รับอนุมัติแก้ Test และผ่าน Tests ก่อนเริ่ม Training
