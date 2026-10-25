#!/usr/bin/env python3
"""Archive official provincial summary PDFs and privacy-safe GAP table text."""
import hashlib
import json
from pypdf import PdfReader
from collect import ROOT, fetch

PDFS = [
    ("uttaradit_2023_11", "https://www.opsmoac.go.th/uttaradit-dwl-files-452891791958", [7, 8, 9, 10]),
    ("uttaradit_2024_01", "https://www.opsmoac.go.th/uttaradit-dwl-files-461891791951", [7, 8, 9, 10]),
    ("uttaradit_2025_12", "https://www.opsmoac.go.th/uttaradit-dwl-files-472991791106", [10, 11, 12]),
]


def main():
    manifest = json.loads((ROOT / "source_manifest.json").read_text())
    summaries = []
    for key, url, pages in PDFS:
        raw, ctype, final = fetch(url)
        file = key + ".pdf"
        (ROOT / file).write_bytes(raw)
        reader = PdfReader(ROOT / file)
        texts = [{"page_pdf_1based": page,
                  "text": reader.pages[page - 1].extract_text(extraction_mode="layout")}
                 for page in pages]
        # These selected pages are aggregate GAP tables; no owner-level extracts.
        (ROOT / (key + "_gap_pages.json")).write_text(json.dumps(texts, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest.append({"id": key, "source_url": url, "final_url": final,
                         "file": file, "content_type": ctype, "bytes": len(raw),
                         "sha256": hashlib.sha256(raw).hexdigest(),
                         "page_count": len(reader.pages), "gap_pages_pdf_1based": pages})
        summaries.append({"id": key, "pages": len(reader.pages), "gap_pages": pages})
    (ROOT / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summaries, ensure_ascii=False))


if __name__ == "__main__":
    main()
