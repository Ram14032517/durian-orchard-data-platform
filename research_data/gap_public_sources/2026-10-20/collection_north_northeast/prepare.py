#!/usr/bin/env python3
"""Build privacy-safe source records without inventing unique orchard IDs."""
from collections import Counter, defaultdict
import csv
from datetime import date
from decimal import Decimal
import hashlib
import json
import re
from collect import ROOT

AS_OF = date(2026, 10, 20)
UTT = "1238c69e-37ce-4827-89e4-54394fec2322"
SSK = "63bbef32-a3f1-4dab-8780-a96b75abbd92"
SSK_DUP = "4ff81856-9a98-4de8-89a2-b38eb2bdf688"
GI = "3e064d05-8f9d-4754-ab39-c1875f3f032f"


def parsed_date(raw):
    if not raw:
        return None
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if not match:
        return None
    year, month, day = map(int, match.groups())
    if year >= 2400:
        year -= 543
    return date(year, month, day)


def number(raw):
    if raw is None or raw.strip() in ("", "-", "NA", "N/A"):
        return None
    return float(Decimal(raw.replace(",", "").strip()))


def main():
    manifest = json.loads((ROOT / "source_manifest.json").read_text())
    source = {entry["id"]: entry for entry in manifest}
    records = []
    stats = {}
    for rid, province_code, province_name in [(UTT, "53", "อุตรดิตถ์"), (SSK, "33", "ศรีสะเกษ")]:
        meta = source[rid]
        file = ROOT / meta["file"]
        with file.open(encoding=meta["encoding"], newline="") as stream:
            reader = csv.DictReader(stream)
            for i, row in enumerate(reader, 1):
                year = int(row["ปี"])
                issue_raw = row.get("วันได้รับ")
                expiry_raw = row.get("วันที่สิ้นสุด")
                issue, expiry = parsed_date(issue_raw), parsed_date(expiry_raw)
                records.append({
                    "record_id": f"{rid}:row:{i}",
                    "province_code": province_code, "province_name": province_name,
                    "district_name": row.get("อำเภอ") or None,
                    "subdistrict_name": row.get("ตำบล") or None,
                    "village_no": row.get("หมู่") or None,
                    "reference_year_be": year, "reference_year_ce": year - 543,
                    "certification_scope": "GAPdurian",
                    "crop_raw": row.get("ชื่อพืช") or "ทุเรียน",
                    "source_item_raw": row.get("รายการ") or meta["resource_name"],
                    "area_rai": number(row.get("พื้นที่ปลูก(ไร่)")),
                    "count_unit": "source_record",
                    "unique_orchard_count": None, "unique_plot_count": None,
                    "unique_farmer_count": None, "public_certificate_code": None,
                    "issue_date_raw": issue_raw, "expiry_date_raw": expiry_raw,
                    "issue_date_ce": issue.isoformat() if issue else None,
                    "expiry_date_ce": expiry.isoformat() if expiry else None,
                    "source_status": "ได้รับการรับรอง (ตามชื่อชุดข้อมูล); ไม่ระบุสถานะรายแถว",
                    "expiry_precedes_reference_year": expiry < date(year - 543, 1, 1) if expiry else None,
                    "derived_status_as_of_2026_10_20": ("expired_by_listed_date" if expiry < AS_OF else "within_listed_dates" if issue and issue <= AS_OF else "not_yet_issued_by_listed_date") if expiry else "unknown_dates_not_provided",
                    "grain_limit": "No stable plot/farmer/certificate ID; repeated rows retained. Do not equate source rows with unique orchards.",
                    "source_resource_id": rid, "source_url": meta["source_url"],
                    "source_dataset_url": meta["dataset_page_url"],
                    "source_file": meta["file"], "source_sha256": meta["sha256"],
                    "source_data_row_1based": i, "source_csv_line_end_1based": reader.line_num,
                })
        this = [r for r in records if r["source_resource_id"] == rid]
        stats[province_name] = {
            "source_records": len(this), "year_counts": dict(Counter(r["reference_year_be"] for r in this)),
            "derived_status_counts": dict(Counter(r["derived_status_as_of_2026_10_20"] for r in this)),
            "expiry_precedes_reference_year_count": sum(r["expiry_precedes_reference_year"] is True for r in this),
            "missing_area_count": sum(r["area_rai"] is None for r in this),
            "zero_area_count": sum(r["area_rai"] == 0 for r in this),
            "raw_rows_identical_after_removing_year": None,
        }
        if rid == SSK:
            sig = lambda r: tuple((k, v) for k, v in r.items() if k not in {"ปี"})
            # Compare original source records including owner for QC internally;
            # never retain owner values or hashes in safe extracted outputs.
            raw_rows = list(csv.DictReader(file.open(encoding=meta["encoding"])))
            by_year = defaultdict(list)
            for r in raw_rows:
                by_year[r["ปี"]].append(sig(r))
            years = sorted(by_year)
            stats[province_name]["raw_rows_identical_after_removing_year"] = by_year[years[0]] == by_year[years[1]]
    groups = defaultdict(list)
    for r in records:
        groups[(r["province_code"], r["province_name"], r["district_name"], r["reference_year_be"], r["source_resource_id"])].append(r)
    aggregates = []
    for (pcode, pname, district, year, rid), rows in groups.items():
        aggregates.append({
            "province_code": pcode, "province_name": pname, "district_name": district,
            "reference_year_be": year, "reference_year_ce": year - 543,
            "certification_scope": "GAPdurian", "source_record_count": len(rows),
            "area_sum_source_rows_rai": float(sum(Decimal(str(r["area_rai"])) for r in rows if r["area_rai"] is not None)),
            "certified_farmers": None, "certified_plots": None,
            "count_limit": "Area and row-count sums only; not deduplicated orchards. Sisaket dates often predate reference years; do not treat as current-certified area.",
            "source_resource_id": rid, "source_url": source[rid]["source_url"],
            "locator": "Grouped source CSV data rows for this district and reference year",
        })
    gi = []
    meta = source[GI]
    for i, row in enumerate(csv.DictReader((ROOT / meta["file"]).open(encoding=meta["encoding"])), 1):
        gi.append({"province_code": "33", "province_name": "ศรีสะเกษ",
                   "district_name": row["อำเภอ"], "reference_year_be": int(row["ปี"]),
                   "certification_scope": "GI_durian_not_GAP",
                   "farmers_gi": number(row["ผู้ปลูกทุเรียนGI(ราย)"]),
                   "area_rai": number(row["พื้นที่ปลูก"]),
                   "source_resource_id": GI, "source_url": meta["source_url"],
                   "source_data_row_1based": i,
                   "limit": "Resource title says GAP but actual data header says GI; excluded from GAP totals."})
    stats["duplicate_resource"] = {"resource_id": SSK_DUP, "same_as": SSK,
                                   "same_sha256": source[SSK_DUP]["sha256"] == source[SSK]["sha256"],
                                   "excluded_from_records": True}
    stats["data_limitations"] = [
        "Officially public sources; owner names are omitted from records and aggregate outputs.",
        "All record IDs are source row references, not public certificate/plot codes.",
        "Area unit is rai. Null dates/counts mean unavailable, not zero.",
        "BE reference years are source labels; issue/expiry years converted by subtracting543.",
        "Expiry-derived status is a date calculation, not a live check of revocation/suspension/renewal.",
        "Do not sum records across years or combine repeated/overlapping sources into unique orchard totals.",
    ]
    for file, data in [("records.json", records), ("district_statistics.json", aggregates),
                       ("gi_mislabeled_resource.json", gi), ("quality_summary.json", stats)]:
        (ROOT / file).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"records": len(records), "district_statistics": len(aggregates), "quality": stats}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
