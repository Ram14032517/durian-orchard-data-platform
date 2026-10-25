"""Read the public ChinaPort registry using its displayed table-query contract.

POST here is a read-only table search, not an application or data request.
Only administrative geography, registration codes, dates and product are emitted.
"""
import hashlib
import json
from datetime import datetime, timezone

import requests
from concurrent.futures import ThreadPoolExecutor
import sys

from collect_east import BASE, fetch, save_json

ROOT = "https://scintl.chinaport.gov.cn/aprwebserver/"
ALLOWED = {"countryCode", "countryNameEn", "provinceCode", "provinceNameEn", "provinceNameCn",
           "prodTypeCode", "prodTypeNameEn", "prodCategoryCode", "prodCategoryNameEn",
           "prodNameCn", "prodNameEn", "prodNameLa", "overseasOfficialRegNo", "chinaRegNo",
           "corpTypeCode", "corpTypeNameEn", "validFrom", "validTo", "regState"}


def register(record):
    manifest = json.loads((BASE / "source_manifest.json").read_text(encoding="utf-8"))
    manifest["sources"] = [row for row in manifest["sources"] if row["source_id"] != record["source_id"]] + [record]
    save_json(BASE / "source_manifest.json", manifest)


def main():
    for url, name in [(ROOT + "common/provinceList?code=764", "chinaport_thailand_provinces.json"),
                      (ROOT + "common/prodParamList?level=category&code=14", "chinaport_fruit_categories.json")]:
        record, body = fetch(url, "raw/" + name)
        register(record)
        print(name, body.decode("utf-8"))

    payload = dict(countryCode="764", prodTypeCode="14", corpTypeCode="01", prodName="%durian%", pageSize=10, pageNum=1)
    url = ROOT + "publicity/list"
    response = requests.post(url, json=payload, timeout=(15, 55), headers={
        "Referer": ROOT + "pages/apr/public/html/companyList.html", "Content-Type": "application/json;charset=UTF-8"})
    response.raise_for_status()
    data = response.json()
    # Retain only the fields needed for the user's workbook in the derived JSON.
    allowed = {"countryCode", "countryNameEn", "provinceCode", "provinceNameEn", "provinceNameCn",
               "prodTypeCode", "prodTypeNameEn", "prodCategoryCode", "prodCategoryNameEn",
               "prodNameCn", "prodNameEn", "prodNameLa", "overseasOfficialRegNo", "chinaRegNo",
               "corpTypeCode", "corpTypeNameEn", "validFrom", "validTo", "regState"}
    result = data.get("data", data)
    rows = result.get("rows", []) if isinstance(result, dict) else []
    sanitized = [{k: v for k, v in row.items() if k in allowed} for row in rows]
    save_json(BASE / "chinaport_probe.json", dict(payload=payload, response_code=data.get("code"),
               message=data.get("message"), response_structure=list(data),
               result_structure=list(result) if isinstance(result, dict) else type(result).__name__,
               total=result.get("total") if isinstance(result, dict) else None, sanitized_rows=sanitized))
    record = dict(source_id="chinaport_probe", requested_url=url, final_url=response.url,
                  method="POST_read_only_public_table_query", query=payload,
                  retrieved_utc=datetime.now(timezone.utc).isoformat(),
                  original_response_sha256=hashlib.sha256(response.content).hexdigest(),
                  original_response_bytes=len(response.content), original_body_retained=False,
                  derived_path="chinaport_probe.json", excluded_fields="owner_names_addresses_contacts_other_nonessential_fields")
    save_json(BASE / "chinaport_probe.source.json", record)
    register(record)
    print(json.dumps(dict(code=data.get("code"), message=data.get("message"), result_structure=record,
                          row_count=len(rows), total=result.get("total") if isinstance(result, dict) else None,
                          fields=list(rows[0]) if rows else []), ensure_ascii=False, indent=2))


def filtered_probes():
    variants = [
        ("thailand_plants_fruit_orchards", dict(countryCode="764", mode="P", prodTypeCode="14", corpTypeCode="01"), "json"),
        ("thailand_durian_uppercase", dict(countryCode="764", mode="P", prodTypeCode="14", prodName="%Durian%"), "json"),
        ("thailand_durian_form_table_contract", dict(countryCode="764", mode="P", prodTypeCode="14", prodName="%Durian%"), "form"),
        ("thailand_plants", dict(countryCode="764", mode="P"), "json"),
    ]
    url = ROOT + "publicity/list"

    def query(variant):
        label, params, encoding = variant
        params = dict(params, pageSize=10, pageNum=1)
        response = requests.post(url, timeout=(15, 55), headers={"Referer": ROOT + "pages/apr/public/html/companyList.html"},
                                 **({"json": params} if encoding == "json" else {"data": params}))
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or {}
        rows = data.get("rows") or []
        safe = [{key: value for key, value in row.items() if key in ALLOWED} for row in rows]
        path = BASE / ("chinaport_" + label + ".json")
        outcome = dict(query=params, encoding=encoding, code=payload.get("code"), message=payload.get("message"),
                       total=data.get("total"), sanitized_rows=safe,
                       original_response_sha256=hashlib.sha256(response.content).hexdigest(),
                       retrieved_utc=datetime.now(timezone.utc).isoformat())
        save_json(path, outcome)
        record = dict(source_id="chinaport_" + label, path=path.name, requested_url=url, final_url=response.url,
                      method="POST_read_only_public_table_query", query=params, encoding=encoding,
                      retrieved_utc=outcome["retrieved_utc"], sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      bytes=path.stat().st_size, original_response_sha256=outcome["original_response_sha256"],
                      original_body_retained=False, derived_path=path.name,
                      excluded_fields="owner_names_addresses_contacts_other_nonessential_fields")
        return record, outcome

    results = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for record, outcome in pool.map(query, variants):
            register(record)
            results.append(dict(label=record["source_id"], code=outcome["code"], total=outcome["total"],
                                returned=len(outcome["sanitized_rows"]),
                                product_names=sorted(set(str(row.get("prodNameEn")) for row in outcome["sanitized_rows"]))))
    save_json(BASE / "chinaport_probe_summary.json", results)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    filtered_probes() if "--filtered-probes" in sys.argv else main()
