#!/usr/bin/env python3
"""Collect public official GAP sources. Do not publish owner identity fields."""
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
SOURCES = [
    ("uttaradit_gap_durian", "https://uttaradit.gdcatalog.go.th", "gpa_durain"),
    ("sisaket_gap_plants", "https://sisaket.gdcatalog.go.th", "dataset_10_40"),
]


def fetch(url):
    # macOS curl uses the platform trust store; TLS validation stays enabled.
    result = subprocess.run(["curl", "-fsSL", "--max-time", "60", "-w",
                             "\n__CURL_METADATA__%{json}", url], check=True,
                            stdout=subprocess.PIPE)
    raw, details = result.stdout.rsplit(b"\n__CURL_METADATA__", 1)
    details = json.loads(details)
    return raw, details.get("content_type"), details.get("url_effective")


def main():
    manifest = []
    for key, host, dataset in SOURCES:
        metadata_url = host + "/api/3/action/package_show?id=" + dataset
        raw, ctype, final_url = fetch(metadata_url)
        metadata = json.loads(raw)["result"]
        path = ROOT / (key + "_metadata.json")
        path.write_bytes(raw)
        manifest.append({"id": key + "_metadata", "source_url": metadata_url,
                         "final_url": final_url, "file": path.name,
                         "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                         "content_type": ctype})
        print(json.dumps({"dataset": key, "title": metadata["title"],
                          "first_year": metadata.get("first_year_of_data"),
                          "last_year": metadata.get("last_year_of_data"),
                          "metadata_modified": metadata.get("metadata_modified")}, ensure_ascii=False))
        for resource in metadata["resources"]:
            if not resource["url"].endswith(".csv"):
                continue
            raw, ctype, final_url = fetch(resource["url"])
            file = key + "_" + resource["id"] + ".csv"
            (ROOT / file).write_bytes(raw)
            encoding = "utf-8-sig"
            try:
                decoded = raw.decode(encoding)
            except UnicodeDecodeError:
                encoding = "cp874"
                decoded = raw.decode(encoding)
            rows = list(csv.DictReader(io.StringIO(decoded)))
            manifest.append({"id": resource["id"], "dataset": key,
                             "dataset_page_url": host + "/dataset/" + dataset,
                             "source_url": resource["url"], "final_url": final_url,
                             "file": file, "sha256": hashlib.sha256(raw).hexdigest(),
                             "bytes": len(raw), "content_type": ctype, "encoding": encoding,
                             "resource_name": resource.get("name"),
                             "description": resource.get("description"),
                             "resource_last_updated_date": resource.get("resource_last_updated_date"),
                             "resource_first_year_of_data": resource.get("resource_first_year_of_data"),
                             "resource_last_year_of_data": resource.get("resource_last_year_of_data"),
                             "row_count": len(rows), "columns": list(rows[0]) if rows else []})
            print(json.dumps({"file": file, "rows": len(rows),
                              "columns": list(rows[0]) if rows else [],
                              "description": resource.get("description")}, ensure_ascii=False))
    (ROOT / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
