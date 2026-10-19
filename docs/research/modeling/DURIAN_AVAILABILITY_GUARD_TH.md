# Experimental Availability Guard

ดำเนินการ 10 ตุลาคม 2026 อ่านรายงาน PIT และตาราง840แถวก่อนแก้ ค้น AGENTS.md ใน repository/โฟลเดอร์แม่แล้วไม่พบ
ใช้แนวทาง Ponytail เพิ่ม Guard ร่วมจุดเดียว ไม่รื้อ production loader
ไม่ฝึกโมเดล ไม่เปลี่ยน MAE, Production, API หรือ Frontend

## ไฟล์ที่แก้

- tools/durian_model/availability_guard.py: ตรวจ status, role, source version, publication evidence, cutoff และเวลา issue-rule creation
- tools/durian_model/availability_manifest.json: hashes ของ CSV ที่ใช้จริง; dependencies ครบ8features; publication ที่ไม่ทราบเป็นnull
- tools/durian_model/experiment_issue_date.py: Guardก่อนจุดฝึก; default preflight-only; outputsแยกตามmode; predictor whitelist
- tests/test_availability_guard.py:16 tests ไม่ฝึก estimator
- tools/durian_model/README_TH.md:อธิบายพฤติกรรมคำสั่งใหม่

## Issue Date

เดิมหา monthly peak จาก revised OAE แล้วลบlead ใหม่ใช้fixed-calendar scenarioโดยไม่อ่านผลผลิตรายเดือน:
จันทบุรี04-01, ศรีสะเกษ05-01, อุตรดิตถ์06-01, สุราษฎร์ธานี07-01, ชุมพร07-01
stage seasonเป็นสามเดือนจากanchor และissueคือanchorลบ60หรือ0วัน รองรับmonth-startมกราคมถึงตุลาคม
กฎนี้สร้างตอนนี้และบันทึกcreated_atจริง ไม่ใช่กฎที่พิสูจน์ว่าประกาศก่อน2017
Strictจึงปฏิเสธย้อนหลังทั้งกรณีunverifiedและcreated_atหลังissue ไม่backdateกฎ
การเปลี่ยนscheduleต้องผูกSHAใหม่กับทั้งissue_ruleและissue_rule_feature

Shared fit/selection cutoffคือเวลา00:00 Asia/Bangkokของissueแรกสุดในห้าจังหวัดในแต่ละปี/lead
Featuresของforecastตรวจที่issueของจังหวัดนั้น; training inputsและtraining/selection labelsตรวจที่shared fit cutoff
ปี2023lead60จึงใช้31มกราคมเป็นfit cutoff แม้ชุมพรออก2พฤษภาคม
นี่เป็นexperimental policy ไม่ใช่logการฝึกจริงในอดีต

## สถานะและการแยกบทบาท

| Status | Exploratory | Strict |
|---|---|---|
| verified_available | ตรวจversion/evidence/cutoffและบันทึกปัญหา | ผ่านเฉพาะวันเผยแพร่ทันcutoffและหลักฐานผูกversion/dateตรงกัน |
| verified_unavailable | warning ไม่เปลี่ยนป้ายเป็นverified | ปฏิเสธinput/label/rule |
| unverified | ไปต่อพร้อมwarning | ปฏิเสธinput/label/rule |
| not_applicable | เฉพาะcalendar keysที่ทราบจากนิยาม | เช่นเดียวกัน ห้ามใช้กับexternal data |

Missing publication dateไม่ใช่pass Datesที่ไม่มีtimezoneไม่ถูกเดาเวลาเผยแพร่
Version mismatch, role mismatch, dependencyหาย และfuture observed dateที่ส่งเข้าตัวตรวจถูกปฏิเสธทั้งสองโหมด
Evaluation targetอนุญาตlater referenceได้ แต่ย้ายroleไปเป็นfeature/train/selectionโดยไม่ตรวจใหม่ไม่ได้
Predictor frameรับเฉพาะprovince_code/year_ce/FEATURES ไม่ส่งtarget, bearing_raiหรือproduction_tonnesเข้าpredict
Trainingและselection labelsมีrecordsแยกแม้ปัจจุบันอ้างannual CSVเดียวกัน

SHAเป็นidentifierของprepared CSVที่pipelineใช้ ไม่ใช่official OAE/NASA version
หลักฐานต้องครอบคลุมค่าที่ใช้ทั้งbatchและlineage raw vintage→prepared CSV
Guardตรวจความสอดคล้องของmetadata ไม่authenticateเอกสาร/URLหรือความจริงของสิ่งที่คนกรอก

## ผลตรวจและการใช้งาน

Exploratory preflightสร้าง5880dependency checksจาก120contexts(2014–2025×5จังหวัด×2lead)
ต่อcontextตรวจ5roles และ22feature dependencies×2cutoffs รวม49checks
ไม่ใช่5880ตัวอย่างอิสระ และไม่ใช่ผลMAEใหม่
Strict preflightออกด้วยfailureก่อนfitและก่อนเขียนoutputตามที่ต้องการ:
issue_ruleยังunverified ไม่มีpublication/evidence และcreated_atหลังhistorical issue
Strictหยุดที่ข้อผิดพลาดแรก; ปัญหาdependencyอื่นดูได้จากExploratory artifact

Outputsใหม่อยู่ที่training/issue_date_guarded/exploratory/หรือstrict/ ไม่ทับissue_date_*เดิม
ตารางdocs/research/modeling/DURIAN_DATA_AVAILABILITY.csvเดิมคงไว้เป็นlegacy lineage ไม่แก้ให้ดูเหมือนverified

```powershell
.build/national-analysis-venv/Scripts/python.exe -X utf8 tools/durian_model/experiment_issue_date.py --mode exploratory
.build/national-analysis-venv/Scripts/python.exe -X utf8 tools/durian_model/experiment_issue_date.py --mode strict
.build/national-analysis-venv/Scripts/python.exe -X utf8 -m unittest discover -s tests -p test_availability_guard.py
.build/national-analysis-venv/Scripts/python.exe -X utf8 -m unittest discover -s tests -p test_issue_date_experiment.py
.build/national-analysis-venv/Scripts/python.exe -X utf8 -m unittest discover -s tests -p test_expansion_audit.py
```

16testsใหม่และ7testsเดิมผ่าน รวม23tests ครอบคลุมfuture publication/observations, revised bytes/old evidence,
labelsหลังfit, evaluation role boundary, calendar not_applicable, ruleสร้างภายหลัง, timezone/lineageหาย,
schedule hashเปลี่ยน, predictor whitelist, Strictก่อนfit และ defaultไม่ฝึก
TestsยืนยันตรรกะGuard ไม่ยืนยันว่าแหล่งข้อมูลย้อนหลังไม่มีleakage

## ข้อจำกัดที่ยังคงอยู่

ไม่มีexternal verified_availableในManifestปัจจุบัน OAE/POWERและhistorical scheduleยังไม่มีหลักฐานvintage
ไม่ได้สร้างhistorical vintage loader/as-of value selection: Guardตรวจbatchที่ให้มาเท่านั้น
หลายvintagesต้องมีloaderเลือกข้อมูลตรงหลักฐานและผูกhashก่อน ไม่ใช่แก้statusอย่างเดียว
check_snapshot()/load_panelเดิมยังจำกัดsnapshotห้าจังหวัด ต้องเตรียมข้อมูลทดลองใหม่ก่อนรองรับvintages/จังหวัดใหม่
Strictที่ผ่านmetadataยังไม่ใช่การตรวจหลักฐานภายนอกเสร็จ จึงคงpit_certified=falseพร้อมข้อจำกัดนี้
การฝึกภายหลังต้องopt-inด้วย--train แต่ไม่ได้รันในงานนี้
ถ้าฝึกด้วยfixed calendarใหม่ คะแนนต้องติดป้ายexperimental ไม่อ้างว่าreproduce204.85โดยอัตโนมัติ
