"""Build minimized, quality-gated GAP registry map points from a local snapshot.

No network access, model fitting or raw-source publication. Registry keys are not
asserted to identify unique orchards; point-in-polygon is not field verification.
The output deliberately omits plot codes, owner details and reported production.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DATE = "2026-10-20"
SOURCE_ROOT = ROOT / "research_data/gap_public_sources" / SNAPSHOT_DATE
OUTPUT = ROOT / "research_data/five_province_history/gap_orchards"
PROVINCES = {"22": "จันทบุรี", "33": "ศรีสะเกษ", "53": "อุตรดิตถ์",
             "84": "สุราษฎร์ธานี", "86": "ชุมพร"}
GAP_URL = "https://gap.doa.go.th/searchgap"
BOUNDARY_URL = ("https://gistdaportal.gistda.or.th/arcgis/rest/services/"
                "ข้อมูลเขตการปกครอง/MapServer/2")
EXPOSED_PROPERTIES = frozenset({"id", "province_code", "province_name", "district",
    "tambon", "crop", "status_reported", "issued", "expired", "date_status",
    "area_rai", "registry_rows", "quality", "quality_flags", "source_ids",
    "field_verified"})


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_text(value: Any, max_length: int = 160) -> str:
    """Only used for an allowlisted set of non-personal registry fields."""
    if value is None:
        return ""
    return " ".join(str(value).split())[:max_length]


def safe_source_url(value: Any) -> str:
    """No arbitrary scheme, credentials, source-local path or external host."""
    candidate = str(value or "")
    parsed = urlsplit(candidate)
    if (parsed.scheme != "https" or parsed.hostname != "gap.doa.go.th"
            or parsed.username or parsed.password or parsed.port not in (None, 443)
            or parsed.path.rstrip("/") != "/searchgap" or parsed.fragment):
        raise ValueError("Unexpected GAP public source URL")
    return candidate


class ExportLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            values = dict(attrs)
            if (values.get("href") and "action=10" in values["href"]
                    and "{querycondition}" not in values["href"]):
                self.links.append(values["href"])


def load_sources(source_root: Path, required_ids: set[str]) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for item in read_json(source_root / "collection_live_plots/query_manifest.json"):
        if item["source_id"] not in required_ids:
            continue
        if not item.get("complete"):
            raise ValueError("A retained row references an incomplete source")
        lookup[item["source_id"]] = {
            "url": safe_source_url(item.get("source_url")),
            "title": "กรมวิชาการเกษตร — ทะเบียน GAP ทุเรียน / "
                     + PROVINCES[str(item["province_code"])],
            "retrieved_utc": item.get("retrieved_utc"),
            "sha256": item.get("sha256"),
        }
    for source_id in sorted(required_ids - lookup.keys()):
        parts = source_id.split("_")
        if len(parts) != 5 or parts[:3] != ["DOA", "PLOT", "OLD"]:
            raise ValueError("No provenance for GAP source " + source_id)
        province, crop = parts[-2:]
        folder = source_root / "collection_north_northeast"
        source = folder / f"live_export_{province}_{crop}.xls"
        if not source.is_file():
            raise ValueError("Missing source evidence for " + source_id)
        search = folder / f"live_search_{province}_{crop}.html"
        if not search.exists():
            search = folder / f"live_search_get_{province}_{crop}.html"
        parser = ExportLinks()
        if search.exists():
            parser.feed(search.read_text(encoding="utf-8"))
        url = urljoin(GAP_URL, parser.links[0]) if parser.links else GAP_URL
        lookup[source_id] = {"url": safe_source_url(url),
            "title": "กรมวิชาการเกษตร — ทะเบียน GAP ทุเรียน / " + PROVINCES[province],
            "retrieved_date": SNAPSHOT_DATE, "sha256": digest(source.read_bytes())}
    return dict(sorted(lookup.items()))


def load_boundaries(boundary_path: Path | None, bundled_map: Path) -> tuple[dict, dict]:
    """Prefer a cached boundary file; otherwise extract the existing map's DATA.

    The bundled polygons were generated from GISTDA, then simplified for display.
    We do not download alternatives or pretend this is parcel/district verification.
    """
    if boundary_path is not None and boundary_path.is_file():
        boundaries = read_json(boundary_path)
        origin = "local_province_display_geojson"
    else:
        text = bundled_map.read_text(encoding="utf-8")
        marker = "const DATA="
        if marker not in text:
            raise ValueError("No cached province boundaries; supply --boundaries")
        payload, _ = json.JSONDecoder().raw_decode(text.split(marker, 1)[1].lstrip())
        boundaries = payload["boundaries"]
        origin = "existing_unified_map_embedded_display_boundaries"
    selected = {str(f["properties"]["province_code"]): f["geometry"]
                for f in boundaries["features"]
                if str(f["properties"]["province_code"]) in PROVINCES}
    if set(selected) != set(PROVINCES):
        raise ValueError("Need one province boundary for every target province")
    for geometry in selected.values():
        if geometry.get("type") not in ("Polygon", "MultiPolygon"):
            raise ValueError("Unsupported province geometry")
    return selected, {"method": "point_in_simplified_province_polygon",
        "source": origin, "source_url": BOUNDARY_URL,
        "sha256": digest(canonical_json(selected)), "field_verified": False,
        "caveat": "Display boundaries are simplified. Outside points are quarantined, "
                  "not proven incorrect; boundary-edge cases need higher-resolution review."}


def ring_relation(x: float, y: float, ring: list) -> int:
    """Return 1 inside, 0 on edge, -1 outside (orientation independent)."""
    inside = False
    for index, current in enumerate(ring):
        previous = ring[index - 1]
        x1, y1 = previous[:2]
        x2, y2 = current[:2]
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if (abs(cross) <= 1e-11 and min(x1, x2) - 1e-10 <= x <= max(x1, x2) + 1e-10
                and min(y1, y2) - 1e-10 <= y <= max(y1, y2) + 1e-10):
            return 0
        if (y1 > y) != (y2 > y):
            intersects = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < intersects:
                inside = not inside
    return 1 if inside else -1


def point_in_geometry(longitude: float, latitude: float, geometry: dict) -> bool:
    polygons = ([geometry["coordinates"]] if geometry["type"] == "Polygon"
                else geometry["coordinates"])
    for polygon in polygons:
        if ring_relation(longitude, latitude, polygon[0]) < 0:
            continue
        if not any(ring_relation(longitude, latitude, hole) > 0 for hole in polygon[1:]):
            return True
    return False


def numeric_coordinate(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def coordinate_pair(row: dict) -> tuple[float, float] | None:
    latitude, longitude = row.get("latitude"), row.get("longitude")
    if not numeric_coordinate(latitude) or not numeric_coordinate(longitude):
        return None
    return float(longitude), float(latitude)


def date_check(issued: Any, expired: Any, snapshot: str) -> tuple[str | None, str | None, str]:
    try:
        start, end, as_of = date.fromisoformat(str(issued)), date.fromisoformat(str(expired)), date.fromisoformat(snapshot)
        if end < start:
            return start.isoformat(), end.isoformat(), "invalid_dates"
        status = "future_issue" if start > as_of else "expired" if end < as_of else "within_dates"
        return start.isoformat(), end.isoformat(), status
    except ValueError:
        return None, None, "invalid_dates"


def missing_coordinate_reason(row: dict) -> str:
    flag = str(row.get("gps_flag") or "")
    if "CRS" in flag or "UTM" in flag:
        return "unknown_coordinate_reference_system"
    if "นอกช่วง" in flag or "ศูนย์" in flag:
        return "invalid_coordinate"
    if "รูปแบบไม่ชัดเจน" in flag:
        return "ambiguous_coordinate_format"
    return "missing_coordinate"


def build_layer(rows: list[dict], boundaries: dict[str, dict], sources: dict,
                snapshot: str = SNAPSHOT_DATE) -> tuple[dict, dict[str, dict]]:
    """Pure transformation; counts reconcile to source rows, never unique orchards."""
    date.fromisoformat(snapshot)
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    counters = {code: {"source_rows": 0, "coordinate_rows": 0,
                      "distinct_registry_keys": 0, "display_points": 0,
                      "duplicate_rows_collapsed": 0, "excluded_counts": Counter()}
                for code in PROVINCES}
    for row in rows:
        province = str(row.get("province_code", ""))
        if province not in PROVINCES:
            raise ValueError("Snapshot contains a non-target province")
        counters[province]["source_rows"] += 1
        if coordinate_pair(row) is not None:
            counters[province]["coordinate_rows"] += 1
        code = str(row.get("plot_code") or "").strip()
        if not code:
            counters[province]["excluded_counts"]["missing_registry_key"] += 1
            continue
        grouped[(province, code)].append(row)
    features: dict[str, list[dict]] = {code: [] for code in PROVINCES}
    for (province, code), members in sorted(grouped.items()):
        counter = counters[province]
        counter["distinct_registry_keys"] += 1
        all_pairs = {coordinate_pair(row) for row in members}
        reason = None
        if len(all_pairs) != 1:
            reason = "conflicting_coordinates_for_registry_key"
        else:
            pair = next(iter(all_pairs))
            if pair is None:
                reason = missing_coordinate_reason(members[0])
            elif any("สลับแกน" in str(row.get("gps_flag", "")) for row in members):
                reason = "axis_swapped_source_quarantined"
            elif any("ค่าที่สาม" in str(row.get("gps_flag", "")) for row in members):
                reason = "extra_coordinate_value_quarantined"
            elif not (97 <= pair[0] <= 107 and 5 <= pair[1] <= 21):
                reason = "outside_thailand_bounds"
            elif not point_in_geometry(*pair, boundaries[province]):
                reason = "outside_simplified_province_boundary"
        if reason:
            counter["excluded_counts"][reason] += len(members)
            continue
        source_ids = sorted({str(row.get("source_id", "")) for row in members})
        if not all(source_id in sources for source_id in source_ids):
            raise ValueError("Retained point has no safe source metadata")
        # A deterministic source-order choice is not a claim of the latest state.
        members = sorted(members, key=lambda row: (str(row.get("source_id", "")),
                                                  int(row.get("source_row") or 0)))
        row = members[0]
        flags = ["registry_gps_unverified"]
        metadata_fields = ("district", "tambon", "crop_raw", "status_raw", "issued", "expired", "area_rai")
        if any(any(member.get(key) != row.get(key) for key in metadata_fields) for member in members[1:]):
            flags.append("metadata_conflict")
        issued, expired, date_status = date_check(row.get("issued"), row.get("expired"), snapshot)
        if date_status != "within_dates":
            flags.append(date_status)
        area = row.get("area_rai")
        if not numeric_coordinate(area) or area < 0:
            area = None
            flags.append("area_unusable")
        point_id = "gap-" + digest(canonical_json([province, code]))[:20]
        properties = {"id": point_id, "province_code": province, "province_name": PROVINCES[province],
            "district": clean_text(row.get("district")), "tambon": clean_text(row.get("tambon")),
            "crop": clean_text(row.get("crop_raw")), "status_reported": clean_text(row.get("status_raw")),
            "issued": issued, "expired": expired, "date_status": date_status,
            "area_rai": area, "registry_rows": len(members), "quality": "province_checked",
            "quality_flags": flags, "source_ids": source_ids, "field_verified": False}
        assert set(properties) == EXPOSED_PROPERTIES
        features[province].append({"type": "Feature", "id": point_id,
            "geometry": {"type": "Point", "coordinates": list(pair)}, "properties": properties})
        counter["display_points"] += 1
        counter["duplicate_rows_collapsed"] += len(members) - 1
    # Coincident registry points remain separate keys, explicitly flagged, not
    # fabricated as separate field-verified orchards or silently spatially deduped.
    for items in features.values():
        occurrences = Counter(tuple(feature["geometry"]["coordinates"]) for feature in items)
        for feature in items:
            if occurrences[tuple(feature["geometry"]["coordinates"])] > 1:
                feature["properties"]["quality_flags"].append("shared_coordinate")
    manifests = []
    layers = {}
    for code, name in PROVINCES.items():
        items = features[code]
        points = [feature["geometry"]["coordinates"] for feature in items]
        bbox = ([min(p[0] for p in points), min(p[1] for p in points),
                 max(p[0] for p in points), max(p[1] for p in points)] if points else None)
        counter = counters[code]
        exclusions = dict(sorted(counter["excluded_counts"].items()))
        excluded = sum(exclusions.values())
        assert counter["source_rows"] == len(items) + counter["duplicate_rows_collapsed"] + excluded
        manifests.append({"code": code, "name": name, "province_code": code, "province_name": name,
            "file": f"province_{code}.geojson", "bbox": bbox, **counter,
            "excluded_counts": exclusions, "exclusions": exclusions, "excluded_rows": excluded,
            "parseable_coordinate_rows": counter["coordinate_rows"], "displayed_features": len(items),
            "quality_flag_counts": dict(sorted(Counter(flag for feature in items
                for flag in feature["properties"]["quality_flags"]).items())),
            "districts": sorted({feature["properties"]["district"] for feature in items})})
        layers[code] = {"type": "FeatureCollection", "schema_version": 1,
            "snapshot_date": snapshot, "province_code": code, "bbox": bbox, "features": items}
    exclusions = Counter()
    for counter in counters.values():
        exclusions.update(counter["excluded_counts"])
    totals = {key: sum(counter[key] for counter in counters.values())
              for key in ("source_rows", "coordinate_rows", "distinct_registry_keys", "display_points", "duplicate_rows_collapsed")}
    totals.update(excluded_rows=sum(exclusions.values()),
                  parseable_coordinate_rows=totals["coordinate_rows"], displayed_features=totals["display_points"])
    return {"schema_version": 1, "snapshot_date": snapshot, "totals": totals,
        "excluded_counts": dict(sorted(exclusions.items())), "exclusions": dict(sorted(exclusions.items())),
        "provinces": manifests, "sources": sources,
        "warnings": [
            "หมุดตามทะเบียน GAP ไม่ใช่สวนที่ตรวจพิกัดภาคสนามแล้ว และรหัสทะเบียนไม่ยืนยันสวนที่ไม่ซ้ำกัน",
            "แผนที่เป็นเฉพาะรายการที่รวบรวมได้และผ่านเกณฑ์พิกัด ไม่ใช่จำนวนสวนทั้งหมดของจังหวัด ความครอบคลุมพิกัดต่างกันมากระหว่างจังหวัด",
            "การอยู่ในขอบเขตจังหวัดแบบย่อเป็นการคัดกรองเบื้องต้น ไม่ยืนยันตำบล อำเภอ หรือแปลงที่ดิน",
            "พิกัดสลับแกน มีค่าที่สาม ขัดแย้ง หรืออยู่นอกขอบเขตจังหวัด ถูกพักไว้ ไม่แทนด้วยจุดกลางอำเภอ",
            "ทะเบียนปี 2026 ไม่ยืนยันสถานะหรือการมีอยู่ของสวนในอดีต ห้ามใช้ย้อนหลังแบบ point-in-time โดยไม่ตรวจหลักฐาน",
            "ข้อมูลนี้ไม่มีผลผลิตจริงรายปีหรือผลตรวจโรค ห้ามทำสำเนาคำตอบระดับจังหวัดให้แต่ละหมุดเป็นตัวอย่างฝึกใหม่",
            "พื้นที่ไร่เป็นค่าที่ทะเบียนรายงาน ไม่ยืนยันพื้นที่ให้ผล จึงไม่ใช่น้ำหนักผลผลิตโดยอัตโนมัติ",
            "วันที่รับรองกับสถานะที่แหล่งข้อมูลรายงานแสดงแยกกัน ไม่ใช่การตรวจรับรองซ้ำ",
            "พิกัดแปลงอาจระบุตัวบุคคลได้ทางอ้อม แม้ละชื่อและรหัสแปลงแล้ว ควรจำกัดการเผยแพร่และทบทวนสิทธิการใช้ข้อมูล",
        ]}, layers


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--boundaries", type=Path,
                        default=ROOT / "research_data/thailand_comparison/province_display.geojson")
    parser.add_argument("--bundled-map", type=Path,
                        default=ROOT / "research_data/five_province_history/UNIFIED_MAP.html")
    args = parser.parse_args()
    input_path = args.source_root / "collection_live_plots/records_sanitized.json"
    rows = read_json(input_path)
    sources = load_sources(args.source_root, {str(row["source_id"]) for row in rows})
    boundaries, boundary_check = load_boundaries(args.boundaries, args.bundled_map)
    manifest, layers = build_layer(rows, boundaries, sources)
    manifest["boundary_check"] = boundary_check
    manifest["input_sha256"] = digest(input_path.read_bytes())
    args.output.mkdir(parents=True, exist_ok=True)
    for province in manifest["provinces"]:
        body = canonical_json(layers[province["code"]]) + b"\n"
        province["sha256"] = digest(body)
        province["bytes"] = len(body)
        (args.output / province["file"]).write_bytes(body)
    (args.output / "manifest.json").write_bytes(canonical_json(manifest) + b"\n")
    print(json.dumps({"output": str(args.output), "totals": manifest["totals"],
                      "excluded_counts": manifest["excluded_counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
