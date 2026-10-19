# งานดูแล repository

สคริปต์เหล่านี้ใช้เมื่อต้องจัดการ configuration ส่วนตัว ไม่เกี่ยวกับการเปิดแผนที่หรือเทรนโมเดล

- `audit_staged_secrets.py` ตรวจชื่อไฟล์ staged ที่มีค่าตรงกับ local headers โดยไม่พิมพ์ค่าออกมา รันจาก root ด้วย `python tools/maintenance/audit_staged_secrets.py`
- `move_gateway_ingest_secrets.ps1` ย้ายค่า ingest จาก firmware ไป local header
- `sanitize_firmware_secrets.ps1` ย้ายค่าอุปกรณ์ไป local headers และสร้างไฟล์ตัวอย่าง

สองไฟล์ PowerShell แก้ local configuration เมื่อเรียกใช้ ควรอ่านโค้ดก่อนรัน ส่วนไฟล์ `*.example.h` ใน `iot/` เป็นจุดเริ่มตั้งค่าอุปกรณ์
