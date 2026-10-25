#!/usr/bin/env python3
"""Extract official district GAP crop statistics, retaining exact page anchors."""
import json
import re
from pypdf import PdfReader
from collect import ROOT

REPORTS = [
    ("uttaradit_2023_11", "2023-11-06", range(7, 13)),
    ("uttaradit_2024_01", "2024-01-09", range(8, 13)),
    ("uttaradit_2025_12", "2025-10-24", range(10, 13)),
]


def main():
    manifest = json.loads((ROOT / "source_manifest.json").read_text())
    by_id = {r["id"]: r for r in manifest}
    output = []
    for key, source_date, pages in REPORTS:
        source = by_id[key]
        reader = PdfReader(ROOT / source["file"])
        district = None
        table_rows = []
        page_texts = []
        for page in pages:
            text = reader.pages[page - 1].extract_text(extraction_mode="layout")
            page_texts.append({"page_pdf_1based": page, "text": text})
            lines = text.splitlines()
            for line_no, line in enumerate(lines, 1):
                stripped = line.strip()
                # Limit district summary extraction to the crop GAP table.
                if not (stripped.startswith("อำเภอ") or stripped.startswith("ทุเรียน")):
                    continue
                match = re.match(r"^(.*?)\s{2,}([\d,]+)\s{2,}(?:([\d,]+)\s{2,})?([\d,.]+)\s*$", stripped)
                if not match:
                    continue
                label, farmers, plots, area = match.groups()
                if label.startswith("อำเภอ"):
                    district = label.removeprefix("อำเภอ").strip()
                    crop = "พืชทุกชนิด"
                    scope = "GAPallcrops"
                else:
                    if district is None:
                        raise ValueError((key, page, stripped))
                    crop, scope = label, "GAPdurian"
                    # Wrapped variety lists checked against rendered page images.
                    if key == "uttaradit_2023_11" and page == 9 and farmers == "20":
                        crop = "ทุเรียนหมอนทอง,ทุเรียนหลงลับแล,หลินลับแล"
                    elif key == "uttaradit_2023_11" and page == 9 and farmers == "2":
                        crop = "ทุเรียนหมอนทอง,ทุเรียนหลงลับแล,หลินลับแล,มูซังคิง"
                    elif key == "uttaradit_2024_01" and page == 9 and farmers == "2" and label.endswith(","):
                        crop += "มูซังคิง"
                if scope == "GAPallcrops" and page == 7 and key == "uttaradit_2023_11" and district != "เมืองอุตรดิตถ์":
                    # Rice GAP section precedes the crop table on this page.
                    continue
                row = {
                    "record_id": f"{key}:pdfpage:{page}:line:{line_no}",
                    "province_code": "53", "province_name": "อุตรดิตถ์",
                    "district_name": district, "subdistrict_name": None,
                    "reference_year_be": int(source_date[:4]) + 543,
                    "reference_year_ce": int(source_date[:4]),
                    "source_as_of_date": source_date,
                    "certification_scope": scope, "crop_raw": crop,
                    "reported_farmers_count": int(farmers.replace(",", "")),
                    "reported_plots_count": int(plots.replace(",", "")) if plots else None,
                    "area_rai": float(area.replace(",", "")),
                    "count_unit": "ราย / แปลง / ไร่ ตามหัวตาราง",
                    "certificate_validity_as_of_2026_10_20": "unknown_no_certificate_dates",
                    "source_resource_id": key, "source_url": source["source_url"],
                    "source_file": source["file"], "source_sha256": source["sha256"],
                    "source_page_pdf_1based": page,
                    "source_page_printed": page - 1 if key == "uttaradit_2025_12" else page,
                    "source_text_line_1based": line_no,
                    "source_row_text": stripped,
                    "grain_limit": "District/crop aggregate as of source date; cannot recover individual plot IDs or sum farmer counts across varieties as unique farmers.",
                    "verification": "PDF table extraction; key durian rows and multi-line varieties visually verified using rendered official PDF pages.",
                }
                table_rows.append(row)
        (ROOT / (key + "_gap_pages.json")).write_text(json.dumps(page_texts, ensure_ascii=False, indent=2), encoding="utf-8")
        source["gap_pages_pdf_1based"] = list(pages)
        output += table_rows
    # There must be nine district totals in each provincial table.
    for key, _, _ in REPORTS:
        totals = [r for r in output if r["source_resource_id"] == key and r["certification_scope"] == "GAPallcrops"]
        assert len(totals) == 9, (key, len(totals))
    (ROOT / "pdf_district_crop_statistics.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"rows": len(output), "durian_rows": sum(r["certification_scope"] == "GAPdurian" for r in output), "rows_by_source": {key: sum(r["source_resource_id"] == key for r in output) for key, _, _ in REPORTS}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
