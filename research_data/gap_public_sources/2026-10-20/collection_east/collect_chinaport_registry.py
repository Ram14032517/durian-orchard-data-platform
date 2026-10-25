"""Collect the public GACC table, retaining only five-province orchard fields.

The official UI supports 500 records/page and a read-only POST search. Names,
street addresses, national IDs, contacts and telephone numbers are discarded
before anything is persisted. Original response SHA-256 is retained for evidence.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import sys
import time

import requests

from collect_east import BASE, save_json

URL = "https://scintl.chinaport.gov.cn/aprwebserver/publicity/list"
LANDING = "https://scintl.chinaport.gov.cn/aprwebserver/pages/apr/public/html/companyList.html"
QUERY = dict(countryCode="764", mode="P", prodTypeCode="14", corpTypeCode="01", prodName="%Durian%", pageSize=500)
TARGETS = {"22": "จันทบุรี", "86": "ชุมพร", "84": "สุราษฎร์ธานี", "33": "ศรีสะเกษ", "53": "อุตรดิตถ์"}
PROVINCE_CODES = {"764016": "22", "764028": "86", "764184": "84", "764175": "33", "764208": "53"}


def split(value):
    # The public table uses both newlines and commas for multi-product fields.
    return [item.strip() for item in re.split(r"[,\r\n]+", str(value or "")) if item.strip()]


def normalize(row, page, index, retrieved):
    assert row.get("countryCode") == "764", "Country filter not respected"
    assert "Durian" in split(row.get("prodNameEn")), "Durian filter not respected"
    assert row.get("prodTypeCode") == "14", "Fresh fruit filter not respected"
    assert "01" in split(row.get("corpTypeCode")), "Production/orchard filter not respected"
    code = str(row.get("overseasOfficialRegNo") or "").strip()
    public_provinces = split(row.get("provinceCode"))
    mapped = {PROVINCE_CODES[item] for item in public_provinces if item in PROVINCE_CODES}
    if len(mapped) == 1:
        province = mapped.pop()
        basis = "GACC_explicit_public_province_field"
    else:
        return None, "province_unresolved" if not public_provinces else "non_target"
    if province not in TARGETS:
        return None, "non_target"
    status = str(row.get("regState") or "")
    valid_to = row.get("validTo")
    return dict(province_code=province, province_name_th=TARGETS[province], orchard_code=code,
                gacc_registration_code=row.get("chinaRegNo"), crop="ทุเรียน", product_names=split(row.get("prodNameEn")),
                commodity_scope="Fresh fruits; registered for Durian; may also include other fruits",
                entity_type="Production_orchard", gacc_entity_type_codes=split(row.get("corpTypeCode")),
                registration_status_code=status, registration_status={"1": "Normal", "2": "Suspension", "3": "Cancellation", "4": "Invalid"}.get(status, "Unknown"),
                valid_from=row.get("validFrom"), valid_to_source_value=valid_to,
                valid_to_interpretation="2999_sentinel_not_actual_GAP_certificate_expiry" if str(valid_to).startswith("2999-") else "as_reported",
                province_basis=basis, gacc_province_codes=public_provinces, gacc_province_names=split(row.get("provinceNameEn")),
                source_id=f"gacc_current_page_{page:04}", source_url=URL, public_query_page=LANDING,
                source_location=f"public table query page {page}, result row {index}", retrieved_utc=retrieved,
                measurement_scope="export_registration_status_not_actual_exports_or_harvest",
                export_quantity=None, harvest_yield=None, latitude=None, longitude=None), "target"


def page_query(page):
    path = BASE / f"gacc_pages/page_{page:04}.json"
    payload = dict(QUERY, pageNum=page)
    if path.exists():
        result = json.loads(path.read_text(encoding="utf-8"))
        assert result["query"] == payload
        return result
    for attempt in range(3):
        try:
            response = requests.post(URL, json=payload, timeout=(15, 45), headers={"Referer": LANDING})
            response.raise_for_status()
            body = response.json()
            assert body.get("code") == 200, "Public query did not return success"
            data = body["data"]
            retrieved = datetime.now(timezone.utc).isoformat()
            records, reasons = [], Counter()
            for number, row in enumerate(data["rows"], 1):
                normalized, reason = normalize(row, page, number, retrieved)
                reasons[reason] += 1
                if normalized:
                    records.append(normalized)
            result = dict(query=payload, retrieved_utc=retrieved, total=data["total"],
                          received_count=len(data["rows"]), classification_counts=dict(reasons), target_rows=records,
                          original_response_sha256=hashlib.sha256(response.content).hexdigest(),
                          original_response_bytes=len(response.content), original_body_retained=False,
                          excluded_fields="names_street_addresses_contacts_national_ids_all_other_unneeded_fields")
            save_json(path, result)
            return result
        except (requests.RequestException, ValueError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def main(finalize_only=False):
    first = page_query(1)
    total = first["total"]
    pages = math.ceil(total / QUERY["pageSize"])
    assert total > 0, "Empty search is not proof that there are no registered orchards"
    print(json.dumps(dict(national_orchard_durian_matches=total, pages=pages, page_size=QUERY["pageSize"])), flush=True)
    results = {1: first}
    errors = []
    if finalize_only:
        for path in (BASE / "gacc_pages").glob("page_*.json"):
            value = json.loads(path.read_text(encoding="utf-8"))
            results[value["query"]["pageNum"]] = value
    else:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(page_query, page): page for page in range(2, pages + 1)}
            for future in as_completed(futures):
                page = futures[future]
                try:
                    results[page] = future.result()
                except Exception as exc:
                    errors.append(dict(page=page, error=str(exc)))
                if (len(results) + len(errors)) % 20 == 0:
                    print(json.dumps(dict(completed_pages=len(results), errors=len(errors), target_rows=sum(len(v["target_rows"]) for v in results.values()))), flush=True)
    rows, duplicate_keys = [], []
    seen = set()
    excluded_no_explicit_province = 0
    for page in sorted(results):
        for record in results[page]["target_rows"]:
            # Older in-flight cached pages can contain code-based candidate rows.
            # Deliver only records with an explicit, uniquely matching source province.
            mapped = {PROVINCE_CODES[code] for code in record["gacc_province_codes"] if code in PROVINCE_CODES}
            if len(mapped) != 1:
                excluded_no_explicit_province += 1
                continue
            province = mapped.pop()
            record = dict(record, province_code=province, province_name_th=TARGETS[province],
                          province_basis="GACC_explicit_public_province_field")
            key = (record["orchard_code"], record["gacc_registration_code"], tuple(record["product_names"]))
            if key in seen:
                duplicate_keys.append(key)
            else:
                seen.add(key)
                rows.append(record)
    counts = Counter(record["province_code"] for record in rows)
    statuses = Counter((record["province_code"], record["registration_status"]) for record in rows)
    save_json(BASE / "current_export_orchards_rows.json", rows)
    save_json(BASE / "current_export_orchards_quality.json", dict(
        source_url=URL, public_query_page=LANDING, query=QUERY, expected_total_rows=total,
        completed_pages=len(results), expected_pages=pages, page_errors=errors,
        observed_total_values=sorted(set(item["total"] for item in results.values())),
        received_national_rows=sum(item["received_count"] for item in results.values()),
        target_province_rows=dict(counts), target_status_counts=[dict(province_code=p, status=s, count=c) for (p, s), c in sorted(statuses.items())],
        duplicate_keys_count=len(duplicate_keys), complete_query_snapshot=not errors and len(results) == pages and len({item["total"] for item in results.values()}) == 1,
        excluded_candidate_rows_without_explicit_source_province=excluded_no_explicit_province,
        privacy="No owner names, street addresses, IDs, contact names, phones or emails retained",
        limitations=["Live export registration snapshot; dates are registration dates, not annual production years.",
                     "No crop yield, orchard area, exact coordinates or exported lot quantities in selected registry fields.",
                     "Rows without an explicit, uniquely matching GACC province are excluded; GAP code prefixes are not treated as geographic evidence.",
                     "validTo=2999 is a source sentinel, not an actual GAP certificate expiry date.",
                     "Normal is GACC reported status as retrieved, not proof of shipment or a full current GAP certificate audit."]))
    manifest = json.loads((BASE / "source_manifest.json").read_text(encoding="utf-8"))
    manifest["sources"] = [source for source in manifest["sources"] if not source["source_id"].startswith("gacc_current_page_")]
    for page, value in sorted(results.items()):
        path = BASE / f"gacc_pages/page_{page:04}.json"
        manifest["sources"].append(dict(source_id=f"gacc_current_page_{page:04}", path=str(path.relative_to(BASE)),
            requested_url=URL, final_url=URL, method="POST_read_only_public_table_query", query=value["query"],
            retrieved_utc=value["retrieved_utc"], sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size,
            original_response_sha256=value["original_response_sha256"], original_response_bytes=value["original_response_bytes"],
            original_body_retained=False, artifact_type="sanitized_derivative_public_registry_query", privacy_fields_removed=True))
    save_json(BASE / "source_manifest.json", manifest)
    print(json.dumps(dict(target_rows=len(rows), province_counts=dict(counts), completed_pages=len(results), errors=errors, duplicate_keys=len(duplicate_keys)), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main(finalize_only="--finalize-only" in sys.argv)
