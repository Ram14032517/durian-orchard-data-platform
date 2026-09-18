# Validation — 18 กันยายน 2569

## ผลตรวจที่ทำแล้ว

- การตรวจรอบแรก `tools/test_regional_orchards.py`: 7 tests ผ่าน; `tools/test_national_comparison.py`: 6 tests ผ่าน
- รัน notebook 03 ผ่าน kernel Jupyter จริงครบทุก code cell ไม่มี error output; notebook 02 สร้างใหม่หลังเพิ่มดิน 4 จังหวัด
- ตรวจ SHA-256 แหล่ง SHP/DBF/PRJ/readme และ response/archives ที่ดาวน์โหลด
- เปิด land-use SHP ซ้ำตรวจพิกัด API ที่ปัดทศนิยมแล้วทั้ง 59 จุดว่าอยู่ใน polygon A403 ตรงตัวจริง
- ผลรวมพื้นที่/ส่วนซ้อนดิน/ส่วนขาด/พื้นที่ทับซ้อนกระทบยอด; จันทบุรีตรงผล pipeline เดิม
- ศรีสะเกษ soil EPSG32647 → land-use EPSG32648; ไม่เอา coordinate ต่าง zone มาซ้อนตรง ๆ
- 14,160 sample-months, 960 province-months, 80 province-years ไม่มี key ซ้ำ; ผลผลิตมีครบ 80 แถวใน 4 จังหวัดนี้
- แยกเดือน13, days รวม leap year, rain=mm/day×days, ค่าเฉลี่ยถ่วงพื้นที่และจำนวนวันตรวจย้อนอิสระ
- ทดสอบลบหนึ่ง stratum จำลอง: ค่าเฉลี่ยจังหวัดเป็น missing พร้อม coverage ไม่ถูก renormalize ให้ดูครบ
- ตรวจ predictions baseline ทุกแถวว่าใช้เฉพาะค่าปีก่อนเป้าหมาย ไม่มี target leakage จาก shift/rolling
- baseline ทั้งสองใช้ช่วง2011–2025เหมือนกัน 60 แถว: previous-year MAE189.7833/RMSE246.2900; trailing5 MAE209.4367/RMSE259.4050 กก./ไร่

## Visual specification และการตรวจภาพ

- งานเปรียบเทียบส่วนประกอบ: แท่งแนวนอน 4 panels หน่วยดิน top5 แกน0–100%ร่วมกัน; ไม่ใช้พื้นที่ polygon ต่างจังหวัดเป็น ranking ความเหมาะสม
- งานเทียบวิธี: paired-dot อุณหภูมิ/ฝนแยกแกนและหน่วย; ค่าเดิม/ใหม่มีตัวเลข ไม่แสดงแต่ delta
- งานเวลา: เส้นอุณหภูมิและฝนแยก panels; 4 จังหวัดมีเส้นคนละรูปแบบเพื่ออ่านขาวดำได้; ไม่ fit causal trend
- ใช้ scientific-visual-table-style: พื้นขาว ตัวอักษรเข้ม สีเขียวหนึ่งสี เส้นเทาและคำอธิบายแหล่ง/ปี; PNG200dpi และSVG
- เปิดตรวจ PNGทั้ง3ภาพ: ภาษาไทยอ่านได้ แกน/หน่วย/แหล่งครบ ไม่มีlabelชน; ตรวจภาพเวลาฉบับขาวดำที่ขนาด1150×800
- เปิด HTMLอ่านผลจริงใน browser1280×900: สรุป/ตารางแหล่งอ้างอิงแสดงครบ ซ่อน code เฉพาะ export แต่เก็บ code ใน notebook
- แผนที่ UI: เลือกชุมพร/ศรีสะเกษ/อุตรดิตถ์เห็นดินและปีคนละปี; สตูลแสดงยังไม่ประมวลผล ไม่ใช้0แทนmissing
- ตรวจ mobile390×844: controls และแผนที่แสดงในคอลัมน์เดียว; รายละเอียดอยู่ด้านล่าง; คืน viewport ก่อนส่งงาน
- browser console ไม่พบ error ในแผนที่ที่ทดสอบ; ไม่มีการติดตั้งหรือ login ผ่าน browser

## ข้อจำกัดที่การตรวจไม่ได้แก้ให้หาย

4จังหวัดไม่แทนทั้งประเทศ, fixed footprint ต่างปี, mixed orchard สัดส่วนสูง, SC/ES/W ไม่ใช่ชุดดินละเอียด,
พื้นที่ LDD ไม่เท่ากับเนื้อที่ให้ผล OAE, NASAไม่ใช่สถานี, การเลือกกรอบ0.25°ยังไม่ทำ sensitivity test,
baseline ใช้สถิติฉบับปัจจุบันไม่ใช่ข้อมูล vintage ที่รู้ ณ วันพยากรณ์,
ยังไม่ทดสอบ weather model/ฤดูผลิต/causal effect/สุขภาพต้น/ลิตรน้ำ และยังไม่ยืนยันสิทธิ์เผยแพร่ derived data

การทดสอบผ่านหมายถึง pipeline ทำตามข้อกำหนดข้างต้น ไม่ใช่ยืนยันว่าแหล่งข้อมูลถูกทุกแปลงหรือโมเดลพร้อมใช้งานจริง

## เพิ่มรอบตรวจความพร้อม

- ผลล่าสุด: regional9tests + national6tests ผ่านรวม15tests; notebook03รันใหม่ครบหลังเพิ่มหัวข้อ
- เพิ่ม2 tests: matched-year OAE/planted-vs-bearing/formula/area-attribute และ soil-resolution tags/ผลรวมสัดส่วน/64ปีfootprint
- พบ3จังหวัดที่สมการpure+f×mixed=OAEplantedไม่มีคำตอบfใน[0,1]; เก็บค่าติดลบ/เกิน1จริง ไม่clipให้ดูถูกต้อง
- ตรวจdescriptorA403=ทุเรียนทั้ง4จังหวัด; sourceareaattributeกับgeometryต่างไม่เกิน0.036%; ความต่างขนาดใหญ่กับOAEยังไม่ทราบสาเหตุ
- ป้ายsoilresolutionเป็นderivedreviewlabels ไม่อ้างว่าแหล่งข้อมูลรับรองความละเอียดนั้นโดยตรง
