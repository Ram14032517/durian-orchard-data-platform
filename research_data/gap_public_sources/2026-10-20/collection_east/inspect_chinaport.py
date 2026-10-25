"""Inspect the publicly linked GACC registration interface without authentication."""
import json
from concurrent.futures import ThreadPoolExecutor

from collect_east import BASE, fetch, save_json


def main():
    base = "https://scintl.chinaport.gov.cn/aprwebserver/"
    jobs = [(base + "pages/apr/public/js/company.list.js", "raw/chinaport_company_list.js"),
            (base + "static/js/util/util.js", "raw/chinaport_public_util.js"),
            (base + "common/countryList", "raw/chinaport_country_list.json"),
            (base + "common/prodParamList?level=type", "raw/chinaport_product_types.json"),
            (base + "common/prodParamList?level=corp", "raw/chinaport_enterprise_types.json")]
    manifest = json.loads((BASE / "source_manifest.json").read_text(encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=3) as pool:
        for record, body in pool.map(lambda job: fetch(*job), jobs):
            manifest["sources"] = [item for item in manifest["sources"] if item["source_id"] != record["source_id"]] + [record]
            if record["path"].endswith(".json"):
                data = json.loads(body)
                if record["path"].endswith("country_list.json"):
                    data = [row for row in data.get("data", []) if "thai" in str(row).lower()]
                print(record["path"], json.dumps(data, ensure_ascii=False))
    save_json(BASE / "source_manifest.json", manifest)


if __name__ == "__main__":
    main()
