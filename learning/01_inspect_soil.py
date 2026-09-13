"""บทฝึกแรก: อ่านข้อมูลสวนอย่างเดียว ไม่แก้ไฟล์ต้นฉบับ.

Run with a working Python interpreter; see docs/LEARNING_PATH_TH.md.
"""

from pathlib import Path

import pandas as pd


# Path ทำให้หาไฟล์จากตำแหน่งโปรเจกต์ได้ แม้เปิด Terminal คนละโฟลเดอร์
PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "data/backups/2026-09-13/sensor_training_unlabeled.csv"

# แบบฝึกเท่านั้น: ลองเปลี่ยนเป็น 25 หรือ 35 แล้วอธิบายผลที่เปลี่ยน
EXAMPLE_THRESHOLD = 30.0

df = pd.read_csv(SOURCE)
print("Rows, columns:", df.shape)
print(df[["device_id", "recorded_at", "soil_moisture_percent"]].head())

# errors='coerce' แปลงค่าที่อ่านไม่ได้เป็นค่าหาย ไม่เปลี่ยนเป็นศูนย์
timestamp = pd.to_datetime(df["recorded_at"], utc=True, errors="coerce")
soil = pd.to_numeric(df["soil_moisture_percent"], errors="coerce")
valid = soil.between(0, 100)
local_time = timestamp.dt.tz_convert("Asia/Bangkok")

print("\nTime range (Thailand):", local_time.min(), "to", local_time.max())
print("Missing/invalid timestamps:", timestamp.isna().sum())
print("Missing/non-numeric soil values:", soil.isna().sum())
print("Soil values outside 0-100:", (soil.notna() & ~valid).sum())
print("Duplicate event IDs:", df["event_id"].duplicated().sum())
print("\nSoil statistics (valid numeric range only):")
print(soil[valid].describe())

# เรียกว่า below_example_threshold เพราะยังไม่ได้สอบเทียบเกณฑ์ดินแห้ง
result = pd.DataFrame({
    "device_id": df["device_id"],
    "valid_soil": valid,
    "unknown_soil": ~valid,
    "below_example_threshold": valid & soil.lt(EXAMPLE_THRESHOLD),
})
print("\nEXERCISE threshold:", EXAMPLE_THRESHOLD, "(not a calibrated dry-soil threshold)")
print(result.groupby("device_id").sum())

# การนับจุดที่ต่ำกว่าเกณฑ์ยังไม่ใช่จำนวนชั่วโมง ต้องตรวจช่วงห่างเวลาก่อน
# แบบฝึกต่อไป: แสดง local_time.dt.hour และคิดว่าจะจัดช่วงเช้า/กลางวันอย่างไร
