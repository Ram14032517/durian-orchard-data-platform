"""Collect public Chanthaburi durian GAP aggregates and inspect public rosters.

No authentication, form submission, or personal farmer fields are used.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urljoin

import requests
import openpyxl

BASE = Path(__file__).resolve().parent
CATALOG = "https://chanthaburi.gdcatalog.go.th"
QUERY_URL = CATALOG + "/api/3/action/package_search"
SOURCES = []


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def fetch(url, relative, params=None):
    try:
        response = requests.get(url, params=params, timeout=(15, 55), headers={"User-Agent": "DurianAcademicPublicDataCollector/1.0"})
        response.raise_for_status()
        body, final_url = response.content, response.url
        requested_url, status, content_type = response.request.url, response.status_code, response.headers.get("Content-Type")
        client = "requests_tls_verified"
    except requests.exceptions.SSLError:
        # macOS curl uses its native trust store. Keep TLS verification enabled.
        if params:
            raise
        result = subprocess.run(["curl", "-fsSL", "--max-time", "55", "--write-out",
                                 "\n__SOURCE_METADATA__%{http_code}|%{url_effective}|%{content_type}", url],
                                capture_output=True, check=True)
        body, metadata = result.stdout.rsplit(b"\n__SOURCE_METADATA__", 1)
        status_text, final_url, content_type = metadata.decode().split("|", 2)
        requested_url, status, client = url, int(status_text), "curl_native_tls_verified"
    path = BASE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    record = dict(source_id=path.name.replace(".", "_"), path=relative, requested_url=requested_url,
                  final_url=final_url, retrieved_utc=datetime.now(timezone.utc).isoformat(),
                  sha256=hashlib.sha256(body).hexdigest(), bytes=len(body),
                  content_type=content_type, http_status=status, client=client)
    save_json(path.with_suffix(path.suffix + ".source.json"), record)
    return record, body


def collect_catalog():
    query_record, raw = fetch(QUERY_URL, "raw/chanthaburi_gap_search.json", {"q": "GAP ทุเรียน", "rows": 30})
    SOURCES.append(query_record)
    response = json.loads(raw)
    assert response["success"]
    packages = [p for p in response["result"]["results"] if p["name"] in {"dataset_10_11", "dataset_10_12", "dataset_10_13"}]
    assert len(packages) == 3, "Expected three separate certified farmer/plot/area datasets"
    jobs = [(p, r) for p in packages for r in p["resources"] if r["format"].upper() in {"CSV", "XLSX"}]

    def resource(job):
        package, item = job
        fmt = item["format"].lower()
        record, body = fetch(item["url"], "raw/" + package["name"] + "." + fmt)
        record.update(dataset_id=package["id"], dataset_name=package["name"], title=package["title"],
                      dataset_url=CATALOG + "/dataset/" + package["name"], resource_id=item["id"],
                      resource_last_modified=item.get("last_modified"), metadata_modified=package.get("metadata_modified"),
                      organization=package["organization"]["title"], unit=package.get("unit_of_measure"),
                      first_year_of_data_metadata=package.get("first_year_of_data"),
                      last_year_of_data_metadata=package.get("last_year_of_data"),
                      geographic_scope=package.get("geo_coverage"), crop_scope="durian_only",
                      measurement_scope="GAP_certification_not_export_quantity_or_harvest_yield",
                      license=package.get("license_title"), data_source=package.get("data_source"))
        records = []
        if fmt == "csv":
            for encoding in ("utf-8-sig", "cp874"):
                try:
                    text = body.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            records = list(csv.DictReader(io.StringIO(text)))
            record.update(parsed_row_count=len(records), fields=list(records[0]) if records else [], encoding=encoding)
        save_json(BASE / ("raw/" + package["name"] + "." + fmt + ".source.json"), record)
        return record, records

    tables = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for record, records in pool.map(resource, jobs):
            SOURCES.append(record)
            if records:
                tables.append(dict(source_id=record["source_id"], source_path=record["path"],
                                   dataset_name=record["dataset_name"], title=record["title"],
                                   unit=record["unit"], records=records))
    save_json(BASE / "parsed_tables.json", tables)
    return tables


def inspect_roster_pages():
    pages = [
        ("https://www.doa.go.th/psco/?page_id=988", "raw/psco_export_registration_landing.html"),
        ("https://online.customs.gov.cn/ociswebserver/pages/dzjxxcx/index.html", "raw/gacc_public_registration_landing.html"),
        ("https://scintl.chinaport.gov.cn/aprwebserver/pages/apr/public/html/companyList.html", "raw/gacc_public_company_list.html"),
    ]
    outcomes = []
    for url, relative in pages:
        try:
            record, body = fetch(url, relative)
            SOURCES.append(record)
            text = body.decode("utf-8", errors="replace")
            links = sorted(set(urljoin(url, match) for match in re.findall(r'''(?:href|src)=["']([^"']+)["']''', text, re.I)))
            candidates = [link for link in links if re.search(r"\.(?:pdf|xlsx?|csv)(?:[?#]|$)", link, re.I)]
            outcomes.append(dict(url=url, status="downloaded_public_landing", title=re.findall(r"<title[^>]*>(.*?)</title>", text, re.S),
                                 candidate_document_links=candidates, all_links=links))
        except (requests.RequestException, subprocess.CalledProcessError) as exc:
            outcomes.append(dict(url=url, status="unavailable", error=str(exc)))
    save_json(BASE / "roster_page_checks.json", outcomes)


def normalize_tables(tables):
    metrics = {"dataset_10_11": "gap_certified_farmers", "dataset_10_12": "gap_certified_plots",
               "dataset_10_13": "gap_certified_area"}
    rows, checks = [], []
    for table in tables:
        workbook = openpyxl.load_workbook(BASE / ("raw/" + table["dataset_name"] + ".xlsx"), read_only=True, data_only=True)
        sheet = workbook.worksheets[0]
        excel = [tuple(row[:3]) for row in sheet.values if row[0] is not None]
        header = list(table["records"][0])
        assert tuple(header) == excel[0]
        assert len(excel) - 1 == len(table["records"])
        source = next(item for item in SOURCES if item["source_id"] == table["source_id"])
        for number, (record, values) in enumerate(zip(table["records"], excel[1:]), 2):
            year_be = int(record[header[0]])
            value = float(record[header[1]].replace(",", ""))
            if table["unit"] != "ไร่":
                assert value.is_integer()
                value = int(value)
            assert year_be == values[0] and abs(value - values[1]) < 1e-9 and record[header[2]] == values[2]
            rows.append(dict(province_code="22", province_name_th="จันทบุรี", district_code=None,
                             geographic_level="province", crop="ทุเรียน", metric=metrics[table["dataset_name"]],
                             year_be=year_be, year_ce=year_be - 543, year_basis="source_label_year_unspecified_calendar_or_fiscal",
                             value=value, unit=table["unit"], source_id=table["source_id"],
                             source_url=source["final_url"], source_dataset_url=source["dataset_url"],
                             source_location=f"CSV row {number}; XLSX sheet {sheet.title} row {number}",
                             source_value=record[header[1]], measurement_scope="GAP_certification",
                             export_quantity=None, harvest_yield=None,
                             quality_flag="reported_as_published_not_recomputed"))
        checks.append(dict(dataset_name=table["dataset_name"], matched_csv_xlsx_rows=len(excel) - 1,
                           fields=header, workbook_sheet=sheet.title,
                           actual_years_be=[item[0] for item in excel[1:]], csv_xlsx_exact_numeric_parity=True))
        workbook.close()
    save_json(BASE / "rows.json", rows)
    save_json(BASE / "quality_report.json", dict(normalized_observations=len(rows), checks=checks,
        limitations=["Province aggregates; no individual orchard code, coordinates, harvest yield or export lot volume.",
                     "Dataset metadata updated in 2025; actual CSV/XLSX values end in Buddhist year 2566 (2023).",
                     "2566 certified farmers and plots both report 20,690; preserved unchanged and confirmed in CSV and XLSX.",
                     "The source year label does not specify calendar versus fiscal year or annual flow versus year-end stock."]))


def main():
    tables = collect_catalog()
    normalize_tables(tables)
    inspect_roster_pages()
    save_json(BASE / "source_manifest.json", dict(collection_date_bangkok="2026-10-20", sources=SOURCES))
    print(json.dumps([dict(dataset=t["dataset_name"], unit=t["unit"], rows=t["records"]) for t in tables], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
