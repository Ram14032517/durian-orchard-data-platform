# Phase 7B Preflight

ตรวจ Phase 7A และ Sealed Phase 6A/6B โดยไม่เปลี่ยนไฟล์เดิม
Python 279/279 (266 เดิม + 13 ใหม่) และ JavaScript 30/30 ผ่าน ไม่มี skipped tests
Logs: `.build/rebaseline-backups/phase7b/python_preflight.log` และ `js_preflight.log`
Before-task Snapshot เก็บ Hashes และ Git Status ไม่รวมเนื้อหา Secrets; Protected เดิม 775 Entries ตรงทั้งหมด
Production SHA256: `b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

เพิ่มเฉพาะ `experiment_delta_target.py` และ `test_delta_target.py`; ไม่แก้ Shared Helper หรือ Model เดิม
คง 10 จังหวัด/Weather 7/Frozen Calendar/Lead 60/Outer 2017–2025/Inner 3 ปี/Grid Depth 2–3/Seed 42
Signed Delta = Current Yield − Lag Yield; ไม่ Clamp Delta; Reconstruction แล้ว Clamp Final Yield เป็นศูนย์ทั้งสองแขน
บันทึก Raw Target Prediction, Raw Reconstructed Yield และ Clipping Flag เพื่อไม่ซ่อนผลของกฎนี้
เลือก Depth ด้วย Inner MAE บน Final Yield แยกแขน; Exact Tie เลือก Depth 2

Preflight Replay Guard และเพิ่ม Target Pair Availability 3,555 คู่ / 7,110 Dependency Records
ตรวจ Current/Prior Year ทั้ง Training และ Selection Cutoffs; Source Hash ผูกกับ Annual จริงและ Lag ที่ Feature Builder ใช้
Publication/Vintage ยัง unverified อนุญาตแบบ Exploratory พร้อม Warnings เท่านั้น ไม่ถือว่ามี Historical PIT
Inner Gate ใช้ 135 Rows/แขน ใน 27 Contexts มี 55 Unique จังหวัด–ปี และนับซ้ำ 80 แถว
Gate: MAE ลดอย่างน้อย 5%, RMSE ไม่แย่, MAE จังหวัดเดิมทุกจังหวัดไม่แย่เกิน 10%
ถ้าไม่ผ่าน จะไม่ Fit/Evaluate Outer และหยุด Delta ไม่มีการจูนหรือรันซ้ำ

Output สร้างด้วย UTC run_id ใหม่และ Exclusive Creation; เก็บ Config/Source Snapshot/Hashes/Dependencies/Fold Cutoffs/Lineage/Fit Cache Audit
Tests ใช้ Fake Estimators ไม่มีการฝึก CatBoost ก่อน Preflight ผ่าน
อนุญาตให้รัน Training หนึ่งรอบหลังบันทึกนี้ โดยห้ามเปลี่ยนกฎเมื่อเห็นผล
