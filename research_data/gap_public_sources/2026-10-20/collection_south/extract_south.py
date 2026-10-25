"""Extract public southern GAP aggregates without exporting personal records.

Run with the bundled Python runtime (pdfplumber). Does not contact providers,
change upstream research data, or infer actual annual harvest from GAP fields.
"""
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

import pdfplumber

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
RETRIEVED = "2026-10-20"
URLS = {
    "CMP_GAP_DURIAN_2020_2024": "https://chumphon.gdcatalog.go.th/dataset/6d6f9607-025f-4956-bc3d-390d5875f4ae/resource/f1229d61-ff73-4c7b-a270-50f6dd2a727e/download/untitled.csv",
    "CMP_GAP_TRAINING_2017_2025": "https://chumphon.gdcatalog.go.th/dataset/a7eadd65-a571-4402-9aa8-f22cac837c77/resource/21d2f8bd-2cf8-416d-aff6-4c665495d5a5/download/untitled.csv",
    "SRT_GAP_DURIAN_2015": "https://www.opsmoac.go.th/suratthani-dwl-files-401091791958",
    "SRT_GAP_DURIAN_2021": "https://www.opsmoac.go.th/suratthani-dwl-files-431691791404",
    "SRT_GAP_DURIAN_REPORT_2025": "https://www.opsmoac.go.th/suratthani-dwl-files-471891791074",
    "SRT_GAP_DURIAN_REPORT_2026": "https://www.opsmoac.go.th/suratthani-dwl-files-481091791081",
}
FILES = {
    "CMP_GAP_DURIAN_2020_2024": "chumphon_durian_gap_plots.csv",
    "CMP_GAP_TRAINING_2017_2025": "chumphon_durian_gap_training.csv",
    "SRT_GAP_DURIAN_2015": "surat_durian_report_historical.pdf",
    "SRT_GAP_DURIAN_2021": "surat_durian_report_2021.pdf",
    "SRT_GAP_DURIAN_REPORT_2025": "surat_agriculture_2025.pdf",
    "SRT_GAP_DURIAN_REPORT_2026": "surat_agriculture_2026.pdf",
}
SOURCE_DATES = {
    "CMP_GAP_DURIAN_2020_2024": {"data_period":"BE 2563-2567 / CE 2020-2024", "resource_last_modified":"2025-10-24T08:38:26.053533", "as_of_date":None},
    "CMP_GAP_TRAINING_2017_2025": {"data_period":"BE 2560-2568 / CE 2017-2025", "resource_last_modified":"2026-07-02T02:28:11.756693", "as_of_date":None},
    "SRT_GAP_DURIAN_2015": {"data_period":"Snapshot August 2015", "as_of_date":"2015-08", "as_of_precision":"month", "pdf_created_metadata":"2015-08-28"},
    "SRT_GAP_DURIAN_2021": {"data_period":"Snapshot 8 March 2021", "as_of_date":"2021-03-08", "as_of_precision":"day", "pdf_created_metadata":"2021-09-29"},
    "SRT_GAP_DURIAN_REPORT_2025": {"data_period":"GAP reference date not stated", "as_of_date":None, "pdf_created_metadata":"2025-01-29"},
    "SRT_GAP_DURIAN_REPORT_2026": {"data_period":"GAP reference date not stated", "as_of_date":None, "pdf_created_metadata":"2026-03-31"},
}
SRT_DISTRICTS = [
    ("8401", "เมืองสุราษฎร์ธานี"), ("8402", "กาญจนดิษฐ์"), ("8403", "ดอนสัก"),
    ("8404", "เกาะสมุย"), ("8405", "เกาะพะงัน"), ("8406", "ไชยา"),
    ("8407", "ท่าชนะ"), ("8408", "คีรีรัฐนิคม"), ("8409", "บ้านตาขุน"),
    ("8410", "พนม"), ("8411", "ท่าฉาง"), ("8412", "บ้านนาสาร"),
    ("8413", "บ้านนาเดิม"), ("8414", "เคียนซา"), ("8415", "เวียงสระ"),
    ("8416", "พระแสง"), ("8417", "พุนพิน"), ("8418", "ชัยบุรี"), ("8419", "วิภาวดี"),
]
CMP_DISTRICTS = dict(zip(
    ["เมืองชุมพร", "ท่าแซะ", "ปะทิว", "หลังสวน", "ละแม", "พะโต๊ะ", "สวี", "ทุ่งตะโก"],
    ["8601", "8602", "8603", "8604", "8605", "8606", "8607", "8608"],
))


def number(value):
    if value is None or not value.strip():
        return None
    numeric = float(value.replace(",", "").replace(" ", ""))
    return int(numeric) if numeric.is_integer() else numeric


def record(source_id, province_code="84", **fields):
    row = dict(
        source_id=source_id, dataset_role="durian_gap_certification_aggregate",
        province_code=province_code,
        province_th="ชุมพร" if province_code == "86" else "สุราษฎร์ธานี",
        district_code=None, district_th=None, crop="ทุเรียน", crop_category="รวมทุเรียนตามแหล่งข้อมูล",
        year_be=None, year_ce=None, period_type=None, reference_date=None,
        reference_date_precision=None, period_label=None, certified_plots=None,
        certified_farmers=None, certified_area_rai=None, reported_production_tonnes=None,
        production_actual_status="no_actual_harvest_proof_supplied", is_total=True,
        source_page_number=None, source_printed_page_number=None, source_row_number=None,
        source_anchor=None, source_url=URLS[source_id], retrieved_date=RETRIEVED,
        notes=None,
    )
    row.update(fields)
    return row


def load_csv(filename):
    with (RAW / filename).open(encoding="utf-8-sig", newline="") as stream:
        return [{k.strip(): v for k, v in row.items()} for row in csv.DictReader(stream)]


def collect_chumphon():
    rows = []
    for n, item in enumerate(load_csv(FILES["CMP_GAP_DURIAN_2020_2024"]), start=2):
        year = int(item["ปี"])
        rows.append(record(
            "CMP_GAP_DURIAN_2020_2024", "86", year_be=year, year_ce=year - 543,
            period_type="annual_label_stock_or_flow_not_defined", period_label=f"พ.ศ. {year}",
            certified_plots=number(item["ค่าของข้อมูล"]), source_row_number=n,
            source_anchor=f"CSV row {n}; ปี={year}; หน่วย=แปลง",
            notes="Source labels annual plot counts; active-stock versus new/renewed certificates is not specified. Not farmers, training participants, or harvested tonnes.",
        ))
    training = []
    for n, item in enumerate(load_csv(FILES["CMP_GAP_TRAINING_2017_2025"]), start=2):
        year = int(item["ปี"])
        training.append(dict(
            source_id="CMP_GAP_TRAINING_2017_2025", dataset_role="training_participants_only_not_certifications",
            province_code="86", province_th="ชุมพร", district_code=CMP_DISTRICTS[item["อำเภอ"]],
            district_th=item["อำเภอ"], year_be=year, year_ce=year - 543,
            crop="ทุเรียน", trained_participants=number(item["ค่าของข้อมูล"]), unit=item["หน่วย"],
            source_row_number=n, source_url=URLS["CMP_GAP_TRAINING_2017_2025"],
            source_anchor=f"CSV row {n}; ปี={year}; อำเภอ={item['อำเภอ']}",
            notes="Participants receiving GAP training; does not mean GAP certified and is not an orchard count.",
        ))
    return rows, training


def collect_surat_2015():
    # Transcription independently checked against rendered PDF p50 / printed p41.
    entries = [
        ("8404", "เกาะสมุย", 96, 1146.50), ("8408", "คีรีรัฐนิคม", 3, 9),
        ("8414", "เคียนซา", 17, 419), ("8406", "ไชยา", 12, 125),
        ("8403", "ดอนสัก", 3, 26), ("8411", "ท่าฉาง", 12, 97.50),
        ("8407", "ท่าชนะ", 31, 332), ("8409", "บ้านตาขุน", 6, 34),
        ("8412", "บ้านนาสาร", 39, 226), ("8410", "พนม", 6, 35),
        ("8401", "เมืองสุราษฎร์ธานี", 30, 468), (None, None, 255, 2918),
    ]
    assert sum(x[2] for x in entries[:-1]) == entries[-1][2]
    assert abs(sum(x[3] for x in entries[:-1]) - entries[-1][3]) < 1e-9
    return [record(
        "SRT_GAP_DURIAN_2015", district_code=code, district_th=name,
        year_be=2558, year_ce=2015, period_type="as_of_snapshot", reference_date="2015-08",
        reference_date_precision="month", period_label="ณ สิงหาคม 2558", is_total=code is None,
        certified_plots=plots, certified_area_rai=area,
        source_page_number=50, source_printed_page_number=41, source_row_number=i,
        source_anchor=f"Table 26, PDF p50, printed p41; district={name or 'รวม'}",
        notes="Only 11 districts are listed. Unlisted districts remain unavailable, not zero. Search-engine OCR incorrectly rendered the source year; checked original Thai numeral 2558 visually.",
    ) for i, (code, name, plots, area) in enumerate(entries, start=1)]


def collect_surat_2021():
    with pdfplumber.open(RAW / FILES["SRT_GAP_DURIAN_2021"]) as pdf:
        table = pdf.pages[30].extract_tables()[0]
    assert len(table) == 22 and len(table[2]) == 11
    output = []
    categories = [(2, "ทุเรียน"), (5, "ทุเรียนหมอนทอง"), (8, "รวม")]
    for i, values in enumerate(table[2:]):
        is_total = i == 19
        code, name = (None, None) if is_total else SRT_DISTRICTS[i]
        for offset, category in categories:
            plots, area, production = [number(v) for v in values[offset:offset + 3]]
            output.append(record(
                "SRT_GAP_DURIAN_2021", district_code=code, district_th=name,
                crop_category=category, year_be=2564, year_ce=2021,
                period_type="as_of_snapshot", reference_date="2021-03-08",
                reference_date_precision="day", period_label="ณ 8 มีนาคม 2564",
                certified_plots=plots, certified_area_rai=area, reported_production_tonnes=production,
                is_total=is_total, source_page_number=31, source_printed_page_number=23,
                source_row_number=i + 1,
                source_anchor=f"Table 17, PDF p31 / printed p23, data row {i+1}, {name or 'ผลรวมทั้งหมด'}, category={category}",
                notes="Source categories kept as printed; use category รวม for all-durian totals. Blank Monthong cells stay null. ผลผลิต(ตัน) is reported quantity: measurement method, harvest year, and actual-versus-estimated status are not stated, so it is not verified actual harvest or export quantity.",
            ))
    totals = [x for x in output if x["is_total"]]
    for total in totals:
        subset = [x for x in output if not x["is_total"] and x["crop_category"] == total["crop_category"]]
        for metric in ["certified_plots", "certified_area_rai", "reported_production_tonnes"]:
            assert abs(sum(x[metric] or 0 for x in subset) - total[metric]) < 0.051, (metric, total)
    combined = next(x for x in totals if x["crop_category"] == "รวม")
    assert combined["certified_plots"] == 2844
    assert combined["certified_area_rai"] == 22631
    assert combined["reported_production_tonnes"] == 13037.5
    return output


def collect_surat_recent():
    specs = [
        ("SRT_GAP_DURIAN_REPORT_2025", 2025, 18, 8397, 7338, 66637.48),
        ("SRT_GAP_DURIAN_REPORT_2026", 2026, 23, 11302, 7338, 88947.55),
    ]
    output = []
    for source, report_year, page, plots, farmers, area in specs:
        with pdfplumber.open(RAW / FILES[source]) as pdf:
            text = pdf.pages[page - 1].extract_text()
            assert f"{plots:,}" in text and f"{area:,.2f}" in text and f"{farmers:,}" in text
        output.append(record(
            source, period_type="report_compilation_snapshot_gap_reference_date_unspecified",
            period_label=f"รายงานจัดทำ ค.ศ. {report_year}; ยอด GAP ไม่ระบุวันที่อ้างอิง",
            certified_plots=plots, certified_farmers=farmers, certified_area_rai=area,
            source_page_number=page, source_printed_page_number=page,
            source_anchor=f"Section 5.1 item 3 ทุเรียน, PDF p{page}, paragraph continuation if applicable",
            notes="Report creation dates are metadata (2025-01-29 / 2026-03-31), not established as-of dates of GAP counts. Do not relabel these as annual actual yield or compare growth without harmonizing validity, crop coverage, and cutoffs.",
        ))
    return output


def dump(name, content):
    (HERE / name).write_text(json.dumps(content, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    chumphon, training = collect_chumphon()
    rows = chumphon + collect_surat_2015() + collect_surat_2021() + collect_surat_recent()
    for i, row in enumerate(rows, start=1):
        row["record_id"] = f"SOUTH_GAP_{i:04d}"
    for i, row in enumerate(training, start=1):
        row["record_id"] = f"SOUTH_TRAIN_{i:04d}"
    manifest = []
    for source_id, filename in FILES.items():
        data = (RAW / filename).read_bytes()
        manifest.append(dict(
            source_id=source_id, source_url=URLS[source_id], local_file=f"raw/{filename}",
            sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data), retrieved_date=RETRIEVED,
            public_download=True, source_type="CSV" if filename.endswith(".csv") else "PDF",
            source_dates=SOURCE_DATES[source_id],
        ))
    dump("rows.json", rows)
    dump("training_only_rows.json", training)
    dump("source_manifest.json", dict(
        collected_date=RETRIEVED, geography=["86", "84"], sources=manifest,
        record_counts={"certification_aggregate_rows":len(rows), "training_only_rows":len(training)},
        excluded_partial_downloads=[
            {"local_file":"raw/surat_durian_report_2021.failed-download.partial", "reason":"First download timed out at 60 seconds; full original successfully retrieved separately and used"},
            {"local_file":"raw/surat_all_package_search.failed-download.partial", "reason":"Large all-packages query returned incomplete JSON; excluded from evidence; smaller targeted queries were valid"},
        ],
        catalog_metadata_files=[
            "raw/chumphon_gap_package_search.json", "raw/surat_gap_package_search.json",
            "raw/surat_durian_package_search.json", "raw/surat_standard_package_search.json",
        ],
        exclusions=["No owner names, citizen IDs, or phone columns extracted", "No existing frozen research changed", "No actual annual harvest labels inferred", "No unlisted district set to zero"],
        known_gaps=["Chumphon certification source is provincial, not district level", "Surat district certification snapshots found for 2015 and 2021, not a continuous annual series", "Recent Surat report dates are not the GAP reference dates", "No public orchard-level measured harvest proof was obtained"],
    ))
    dump("collection_summary.json", dict(
        certification_rows=len(rows), training_only_rows=len(training),
        source_ids=list(FILES),
        certification_rows_by_source={source:sum(x["source_id"]==source for x in rows) for source in FILES},
        assertions="2015 plots/area and 2021 district/category totals reconcile; recent PDF paragraphs visually checked",
        missing_metric_cells=sum(x[k] is None for x in rows for k in ["certified_plots", "certified_area_rai", "reported_production_tonnes"]),
    ))
    print(json.dumps({"certification_rows":len(rows), "training_only_rows":len(training), "sources":len(manifest)}))


if __name__ == "__main__":
    main()
