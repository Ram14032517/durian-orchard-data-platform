# บันทึกตรวจผลวิเคราะห์ — 17 กันยายน 2569

## ผ่านแล้ว

- Native Jupyter kernel `durian-national`: รัน7code cells ตามลำดับ1–7 ไม่มี error
  ไม่ใช่การจำลอง stdout; nbformat validate ผ่าน และบันทึกผล/กราฟใน notebook
- `tools/test_national_comparison.py`: 6tests ผ่าน
  ตรวจ82source sidecar hashes, province-year key, missingness เทียบต้นทาง,
 77ขอบเขตรวมสตูล, 4,620monthly rows, สูตรฝน/ค่าเฉลี่ยถ่วงวัน,
  missingเดือนต้องไม่กลายเป็นศูนย์, ยอดประเทศ, native execution และ map ไม่มี external JS/CSS
- ผลผลิตมีข้อมูล2021=49,2022=59,2023=59,2024=67,2025=67จังหวัด ไม่แสร้งว่าครบ67ทุกปี
- Browserตรวจจริง: เปิดเริ่มต้นเป็นสีผลผลิตต่อไร่; คลิกรูปจังหวัดชุมพรแล้วรายละเอียดเปลี่ยน;
  เลือกสตูลปี2567, สลับปี2568, เปรียบเทียบสมุทรปราการกับศรีสะเกษ;
  จังหวัดที่ไม่มีระเบียนแสดง“—” ไม่ใช่0; เลือกภาคใต้ได้14/14จังหวัดผลรวม569,241ตัน;
  เปลี่ยนตัวชี้วัดเป็นฝนได้ ไม่มี console error ในการทดสอบ
- ดูการแสดงที่หน้าจอปกติ1280×720 และเปิดครั้งแรกที่640×900:
  หน้าจอเล็กแผนที่อยู่ด้านบน ตารางอยู่ด้านล่าง คืนค่า viewport แล้ว
- รูปจังหวัดมีปุ่มที่ระบุชื่อสำหรับ keyboard; มีเมนูเลือกจังหวัดแทนพื้นที่เล็ก
- PNGกราฟตรวจที่ขนาดจริง: long Thai labels และตัวเลขไม่ทับกัน แกนแท่งเริ่ม0
  source/caveat อยู่ใต้ภาพ; รูปเก็บเป็นPNGไม่ใช่ screenshot

## Visual specification

- Scientific-visual-table-style และ geospatial skill ใช้เลือกแผนที่choropleth
  สำหรับผลผลิตต่อไร่ แท่งแนวนอนสำหรับชื่อจังหวัดยาว และ scatter สำหรับสำรวจความสัมพันธ์
- ระบบภาพ: white/near-black/teal #1F6F5F, missingสีเทาพร้อมข้อความ,
  ขอบบาง ไม่มี3D ไม่มีdual-axis ไม่มีผลพยากรณ์ประกอบที่ไม่ได้คำนวณ
- Sequential5bins มีlegendหน่วยชัด ช่วงสีคงที่ทั้ง5ปีต่อหนึ่งตัวชี้วัด
  ตัวเลขในตารางและตำแหน่ง/ชื่อทำให้ไม่ต้องอาศัยสีเพียงอย่างเดียว
- ใช้ Astra-style sparse comparison/table hierarchy; form references inspected:
  Professional benchmark table, Chain-of-thought monitorability scatter,
  source corpus form selection; scientific truth takes priority over styling
- Thai Tahoma จากWindowsสำหรับrenderในเครื่อง ไม่แจกfontfile

## ข้อจำกัดที่ยังเปิดอยู่

1. ไม่ได้ตรวจGISทุกจังหวัดกับแผนที่ล่าสุดอิสระ; GISTDAอ้างDOPA source date2013
   raw query geometryถูกgeneralize0.002องศาและdisplay0.005องศา; ไม่ใช้คำนวณพื้นที่เกษตร
2. NASAเป็นจุดอ้างอิงจังหวัด ไม่ใช่profileสวนทุเรียน และไม่ใช่ค่าเฉลี่ยพื้นที่ทั้งจังหวัด
   ยังไม่เทียบสถานีสวน/กรมอุตุฯ และยังไม่แบ่งช่วงฤดูผลผลิต
3. ดินมีเพียงจันทบุรี ไม่ใช่nationalsoilmodel; มีข้อควรสอบทานการซ่อมgeometry,
   A403ซ้อนหน่วยน้ำ และความต่างปีในรายงานดินเดิม
4. OAEผลผลิตต่อไร่ต้นทางและคำนวณอาจไม่ตรงกัน: เก็บแยกทั้งสองคอลัมน์
5. แผนที่HTMLเปิดออฟไลน์ได้เพราะinlineLeaflet; ลิงก์แหล่งข้อมูลต้องใช้อินเทอร์เน็ต
   HTMLอ่านnotebookอาจใช้ทรัพยากรธีมจากnbconvertบางส่วน; ไม่อ้างว่าHTMLทั้งเล่มทดสอบnetwork-blocked
6. ไม่ได้ทดสอบทุกbrowser/VSCodeextensionของผู้ใช้; ตรวจnativekernelและin-appbrowserแล้ว
7. ไม่มีข้อสรุปเชิงเหตุผลอุณหภูมิ±1°C ไม่มีการทำนายสุขภาพหรือให้น้ำ ไม่มีการเผยแพร่สู่ภายนอก

## Runtime ที่ทดสอบ

Python environment `.build/national-analysis-venv` แยกใหม่:
pandas3.0.1, numpy2.3.5, shapely2.1.2, folium0.20.0,
matplotlib3.11.2, nbclient0.11.0, ipykernel7.3.0
JupyterบนWindowsแจ้งเตือนProactor/ZeroMQ TCPขณะรัน แต่รันผ่าน7cells;
kernelใช้loopbackตามค่าเริ่มต้นและจบเมื่อexecuteเสร็จ ไม่เปิดJupyterserverสู่ภายนอก
