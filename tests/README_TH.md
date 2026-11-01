# ทดสอบโปรเจกต์โดยไม่ train ใหม่

จาก root ของ repository หลังติดตั้ง environment ตามคู่มือ Mac:

```sh
.build/national-analysis-venv/bin/python -B -m unittest discover -s tests -v
node --test tests/*.js
```

unit tests ใช้ข้อมูลสังเคราะห์และ fake estimator สำหรับตรวจขอบเขตเวลา การเลือกโมเดล cache และการปฏิเสธข้อมูลผิด ไม่มีการ fit โมเดล production หรือดาวน์โหลดหลักฐานเพิ่มเติมให้อัตโนมัติ ไฟล์ fixture ระบุว่า `synthetic_unit_only` ไม่ใช่ผลผลิตหรือ labels ที่นำไปทำวิจัยได้

## เทสต์หลักฐานภายในที่เป็น optional

ชุด `chanthaburi_internal_pilot`, `four_province_internal_dataset`, `chanthaburi_district_yield_extraction`, `tha_mai_spatial_review` และบางกรณี geometry/advisor/calendar ต้องใช้ไฟล์หลักฐานที่ไม่ได้เผยแพร่ใน Git เมื่อไม่มีไฟล์จะแสดง `skipped` พร้อมเหตุผล **ไม่ใช่ passed** ไม่สร้างไฟล์ขึ้นมาแทนและไม่ส่งข้อมูลส่วนบุคคลขึ้น Git เพื่อให้เทสต์ผ่าน

ถ้าต้องตรวจ release งานวิจัยแบบบังคับว่าหลักฐานต้องมีครบ:

```sh
ORCHARD_REQUIRE_RESEARCH_FIXTURES=1 .build/national-analysis-venv/bin/python -B -m unittest discover -s tests -v
```

โหมดนี้ทำให้ไฟล์ที่ขาดเป็น error แทน skip ส่วนไฟล์ที่มีอยู่แต่ hash/seal ผิดยังเป็น error เสมอ ไม่ถูกข้ามด้วยการจับข้อผิดพลาด หากต้องใช้ sealed experiment เก่าต้องใช้หลักฐาน โค้ด และ dependencies ฉบับที่ seal นั้นระบุ ไม่เขียนทับ hash เพื่ออ้างว่าโค้ดปัจจุบันเป็นฉบับเดียวกัน

บน sandbox ที่ไม่อนุญาตเปิด localhost เทสต์ HTTP จะขึ้น `PermissionError` ต้องอนุญาตการทดสอบ localhost ก่อน ไม่ควรเปลี่ยนเทสต์ให้ผ่านโดยไม่เปิด server จริง
