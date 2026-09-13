# Farm IoT Receiver Gateway (ESP32-S3)

ไฟล์โค้ดหลัก: `receiver_gateway.ino`

สถานะอ้างอิง: เวอร์ชันที่ทดสอบใช้งานสำเร็จเมื่อ 13 กรกฎาคม 2026

- บอร์ด: ESP32-S3 Dev Module
- อ่านเซนเซอร์ดิน RS485/Modbus โดยตรง: ESP TX=GPIO17, ESP RX=GPIO18
- Gateway ส่งคำสั่ง `READ,A1,<epoch>` ทุก 15 นาทีตามเวลา NTP
- บันทึกเวลาเป็นนาทีลงตัว `:00`, `:15`, `:30`, `:45`
- ส่งข้อมูลไป Google Sheets และ Supabase
- อ่านข้อมูลอากาศ Tuya, พยากรณ์ TMD/Open-Meteo และ NDVI
- พิมพ์ `T` ใน Serial Monitor เพื่อทดสอบเซนเซอร์ดินโดยไม่บันทึกแถวทดสอบ

โค้ดบอร์ดส่งค่าดินที่ทำงานคู่กันอยู่ที่:

`../sender_1/sender_1.ino`

ค่าคอมไพล์ Receiver:

- Board: `ESP32S3 Dev Module`
- USB Mode: `Hardware CDC and JTAG`
- USB CDC On Boot: `Enabled`
- Serial baud rate: `115200`

อย่าเผยแพร่ไฟล์โค้ดต่อสาธารณะจนกว่าจะย้าย Wi-Fi password และ API tokens ออกจาก source code
