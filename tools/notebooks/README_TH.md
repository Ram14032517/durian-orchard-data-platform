# สคริปต์สร้าง Notebook

โฟลเดอร์นี้เก็บโค้ดที่ใช้สร้างและรัน Notebook ส่วนไฟล์สำหรับเปิดอ่านอยู่ที่
[notebooks/](../../notebooks/) และ [00_OPEN_ME.ipynb](../../00_OPEN_ME.ipynb)
ไม่ต้องรันสคริปต์เหล่านี้เพื่ออ่านผลที่บันทึกไว้แล้ว

หากต้องการสร้างใหม่ ให้เปิด Terminal ที่โฟลเดอร์รากของโปรเจกต์
เลือก Python environment ของโปรเจกต์ แล้วใช้รูปแบบ `python -m` เช่น:

```sh
python -m tools.notebooks.build_monthly_notebook
```

- `build_monthly_notebook.py` สร้าง `00_OPEN_ME.ipynb` พร้อมรายงานรายเดือนและผลรัน
- `build_history_notebook.py` สร้าง `research_data/five_province_history/HISTORY_ANALYSIS.ipynb` และ HTML
- `build_national_notebook.py` สร้าง `notebooks/02_thailand_durian_comparison.ipynb` และรายงานระดับประเทศ
- `build_regional_notebook.py` สร้าง `notebooks/03_regional_orchards_soil_weather.ipynb` และรายงานภูมิภาค
- `build_soil_notebook.py` สร้าง `notebooks/01_soil_durian_comparison.ipynb` โดยรันเซลล์ Python ตามลำดับ
- `build_soil_drydown_notebook.py` สร้าง `notebooks/04_soil_drydown_review.ipynb` จากสำเนาข้อมูลเซนเซอร์ในเครื่อง

สคริปต์เหล่านี้อาจรันเซลล์ ดาวน์โหลดข้อมูล หรือเขียนทับผลรายงานเดิม
อ่านโค้ดและตรวจข้อมูลต้นทางก่อนรัน โดยเฉพาะเมื่ออ้างอิงผลวิจัยที่บันทึกไว้แล้ว
`build_national_notebook.py` และ `build_regional_notebook.py` มีฟังก์ชัน `main()`
ส่วนอีกสี่สคริปต์เริ่มสร้าง Notebook ทันทีเมื่อเรียกไฟล์หรือ import โมดูลนั้น
จึงใช้ `python -m` สำหรับการสร้างผล และไม่ import สคริปต์เหล่านั้นเพียงเพื่อสำรวจโค้ด
