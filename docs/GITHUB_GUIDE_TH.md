# เริ่มใช้ Git และ GitHub กับโปรเจกต์นี้

## สิ่งที่ทำแล้ว

โฟลเดอร์ `C:\project` ถูกสร้างเป็น local Git repository ด้วย `git init` แล้ว
แต่ยังไม่ควร commit จนกว่าจะแยกค่าลับออกจาก source code

## แนวคิดสั้น ๆ

- Git เก็บประวัติการเปลี่ยนแปลงบนเครื่อง
- GitHub เก็บสำเนา repository บนอินเทอร์เน็ตและใช้เป็น Portfolio
- commit คือจุดบันทึกหนึ่งจุด
- push คือส่ง commit จากเครื่องขึ้น GitHub

## ตรวจไฟล์ก่อน commit

```powershell
git status
git diff
```

ตรวจว่าไม่มีรหัส Wi-Fi, API token, Tuya key, service-role key หรือข้อมูลส่วนตัว
ถ้าความลับเคยถูก commit แล้ว การลบจากไฟล์ปัจจุบันอย่างเดียวไม่พอ ต้องเปลี่ยนคีย์และ
ล้างออกจากประวัติด้วย

## Commit แรกหลังตรวจ secrets

```powershell
git add .
git status
git commit -m "Initial Farm IoT data pipeline"
```

อ่านรายการใน `git status` ก่อนสั่ง commit ทุกครั้ง

## สร้าง repository บน GitHub

1. สร้าง repository ใหม่ใน GitHub
2. แนะนำให้เริ่มเป็น Private จนกว่าจะตรวจข้อมูลและความลับครบ
3. ไม่ต้องให้ GitHub สร้าง README หรือ `.gitignore` เพราะโปรเจกต์มีอยู่แล้ว
4. คัดลอก URL ของ repository แล้วรัน:

```powershell
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git branch -M main
git push -u origin main
```

หลังจากครั้งแรก รอบต่อไปใช้เพียง:

```powershell
git add .
git commit -m "อธิบายสิ่งที่เปลี่ยน"
git push
```

## ไฟล์ที่ไม่ควรขึ้น GitHub

- `.secrets/`
- ไฟล์ header ที่มี Tuya/Wi-Fi credentials
- `data/export_*` และ `data/processed/`
- raw Google Sheets export
- ภาพหรือข้อมูลที่ระบุตัวบุคคล/ตำแหน่งสวนได้ หากไม่ได้ตั้งใจเผยแพร่
