"""Parse public DOA durian district report snapshots, excluding HTML comments."""
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

from lxml import html

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
REFERENCE = HERE.parent / "collection_national/gap_durian_group_live.html"
PROVINCES = {"22":"จันทบุรี", "86":"ชุมพร", "84":"สุราษฎร์ธานี", "33":"ศรีสะเกษ", "53":"อุตรดิตถ์"}
STATUS_KEYS = [
    "waiting_for_audit", "under_audit_new", "under_audit_surveillance", "under_audit_renewal",
    "certified_excluding_surveillance_and_renewal", "processing_total",
    "certified_unexpired", "certified_expired", "certified_all",
]
UNITS = ["ราย", "แปลง", "ไร่"]
METRICS = ["farmer_count", "plot_count", "area_rai"]


def text(element):
    return " ".join(" ".join(element.itertext()).split())


def number(element):
    value = text(element)
    assert re.fullmatch(r"[\d,]+(?:\.\d+)?", value), value
    value = float(value.replace(",", ""))
    return int(value) if value.is_integer() else value


def load(path):
    raw = path.read_bytes()
    content = raw.decode("utf-8")
    assert re.search(r"</html>\s*$", content, flags=re.I), f"Truncated HTML: {path}"
    # Commented-out legacy <th>/<td> columns must never become active cells.
    document = html.fromstring(content, parser=html.HTMLParser(remove_comments=True))
    assert not document.xpath("//comment()")
    table = document.xpath("//table[@id='editable-sample2']")[0]
    statuses = [text(x) for x in table.xpath("./thead/tr[1]/th")][1:]
    units = [text(x) for x in table.xpath("./thead/tr[2]/th")]
    assert len(statuses) == 9 and units == UNITS * 9, (statuses, units)
    date_label = text(document.xpath("//h2")[0])
    assert "20-ต.ค.-2569" in date_label, date_label
    crop_label = " ".join(text(x) for x in document.xpath("//h3"))
    assert re.search(r"ผลการดำเนินงานพืช\s*ทุเรียน", crop_label), crop_label
    return raw, table, statuses, date_label, crop_label


def dump(name, data):
    (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    rows, summaries, manifests = [], [], []
    country_reference = {}
    if REFERENCE.exists():
        raw, table, _, _, _ = load(REFERENCE)
        for tr in table.xpath("./tbody/tr"):
            cells = tr.xpath("./td")
            if len(cells) != 28 or not cells[0].xpath("./a/@href"):
                continue
            link = cells[0].xpath("./a/@href")[0]
            code = parse_qs(urlsplit(link).query).get("p", [None])[0]
            if code in PROVINCES:
                country_reference[code] = [number(x) for x in cells[1:]]
    for province_code, province_name in PROVINCES.items():
        filename = f"gap_durian_district_{province_code}.html"
        path = RAW / filename
        raw, table, statuses, date_label, crop_label = load(path)
        assert province_name in crop_label, (province_code, crop_label)
        url = f"https://gap.doa.go.th/reportbyplant?t=5&r=78&p={province_code}"
        source_id = f"DOA_GAP_DURIAN_DISTRICTS_{province_code}_20261020"
        district_rows = table.xpath("./tbody/tr")
        district_totals = [0.0] * 27
        observed_ids = set()
        for district_row_number, tr in enumerate(district_rows, start=1):
            cells = tr.xpath("./td")
            assert len(cells) == 28, (filename, district_row_number, len(cells))
            district_name = text(cells[0])
            href = cells[0].xpath("./a/@href")[0]
            district_id = parse_qs(urlsplit(href).query)["p"][0]
            assert district_id not in observed_ids
            observed_ids.add(district_id)
            values = [number(cell) for cell in cells[1:]]
            district_totals = [x + y for x, y in zip(district_totals, values)]
            common = dict(
                source_id=source_id, province_code=province_code, province_th=province_name,
                district_th=district_name, district_id_observed=district_id,
                district_id_scheme="GAP DOA internal report p parameter, not asserted to be DOPA code",
                district_drilldown_url=urljoin(url, href), crop="ทุเรียน", crop_report_id="78",
                as_of_date="2026-10-20", as_of_label=date_label, year_be=2569, year_ce=2026,
                period_type="current_report_snapshot", source_url=url,
                source_table_id="editable-sample2", source_row_number=district_row_number,
            )
            for status_index, (status_key, status_label) in enumerate(zip(STATUS_KEYS, statuses)):
                for metric_index, (metric, unit) in enumerate(zip(METRICS, UNITS)):
                    column_index = status_index * 3 + metric_index
                    row = dict(common, status_key=status_key, status_label=status_label,
                        metric=metric, value=values[column_index], unit=unit,
                        source_numeric_column=column_index + 1,
                        source_anchor=f"table#editable-sample2 tbody row {district_row_number}; {district_name}; {status_label}; {unit}",
                    )
                    rows.append(row)
            summary = dict(common,
                unexpired_farmers=values[18], unexpired_plots=values[19], unexpired_area_rai=values[20],
                expired_farmers=values[21], expired_plots=values[22], expired_area_rai=values[23],
                all_certified_farmers=values[24], all_certified_plots=values[25], all_certified_area_rai=values[26],
            )
            # Counts of people are NOT assumed additive across statuses or locations.
            for offset in (1, 2):
                assert abs(values[18+offset] + values[21+offset] - values[24+offset]) < 0.051, (province_code, district_name, offset)
            summaries.append(summary)
        comparison = []
        if province_code in country_reference:
            for i, (actual, expected) in enumerate(zip(district_totals, country_reference[province_code])):
                comparison.append(dict(status_key=STATUS_KEYS[i // 3], metric=METRICS[i % 3],
                    district_sum=round(actual, 2), province_report_value=expected,
                    difference=round(actual - expected, 2),
                    matched=abs(actual-expected)<0.051,
                    note="Farmer counts need not sum: province may deduplicate persons across districts/statuses; discrepancies retained for review, not corrected.",
                ))
        manifests.append(dict(
            source_id=source_id, source_url=url, local_file=f"raw/{filename}",
            sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw), html_closed=True,
            as_of_date="2026-10-20", as_of_label=date_label, page_title=crop_label, district_rows=len(district_rows),
            tidy_metric_rows=len(district_rows)*27, status_labels=statuses, units=UNITS,
            html_comments_removed_before_parsing=True, province_comparison=comparison,
        ))
    for index, row in enumerate(rows, start=1):
        row["record_id"] = f"LIVE_DISTRICT_{index:05d}"
    dump("rows.json", rows)
    dump("district_summary.json", summaries)
    dump("source_manifest.json", dict(
        retrieved_date="2026-10-20", sources=manifests,
        record_counts={"district_summary_rows":len(summaries), "tidy_metric_rows":len(rows)},
        methodology=["Only active HTML th/td cells parsed; comments removed", "Labels preserved verbatim", "Observed internal district href IDs retained; no DOPA codes inferred", "Missing districts are not manufactured as zero rows", "No owner names, national IDs, or phone numbers collected", "Report status totals may overlap; never sum all nine statuses", "Current report is not an annual harvest or export dataset"],
        national_reference_path=str(REFERENCE.relative_to(HERE.parent)) if REFERENCE.exists() else None,
        national_reference_sha256=hashlib.sha256(REFERENCE.read_bytes()).hexdigest() if REFERENCE.exists() else None,
    ))
    print(json.dumps({"district_rows":len(summaries), "metric_rows":len(rows),
        "coverage":{p:sum(s["province_code"]==p for s in summaries) for p in PROVINCES},
        "national_comparison_mismatches":sum(not x["matched"] for m in manifests for x in m["province_comparison"])},ensure_ascii=False))


if __name__ == "__main__":
    main()
