"""Read-only analysis of the 2026-09-19 Sheets snapshot; no live writes.

Thresholds 50 and 40 identify the user's reported pattern, not crop water stress.
Weather flatlines are suspected, not confirmed gateway outage intervals.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from clean_stale_weather import clean, SIGNATURE, WEATHER

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/analysis_soil_2026-09-19/live_readings_snapshot.json"


def inspect_snapshot(path=DEFAULT_INPUT):
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = pd.DataFrame(payload["records"])
    raw["timestamp"] = pd.to_datetime(raw.recorded_at, utc=True, errors="raise")
    raw = raw.sort_values(["device_id", "timestamp"]).reset_index(drop=True)
    assert raw.device_id.nunique() == 1, "Analyze each device separately"
    assert not raw.event_id.duplicated().any(), "Resolve duplicate event IDs first"
    assert not raw.duplicated(["device_id", "timestamp"]).any(), "Resolve duplicate times first"
    for col in ["soil_moisture_percent", "soil_temperature_c", *WEATHER]:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    df, flatlines = clean(raw)
    df["timestamp_th"] = df.timestamp.dt.tz_convert("Asia/Bangkok")
    df["gap_minutes"] = df.timestamp.diff().dt.total_seconds().div(60)
    df["soil_delta_pp"] = df.soil_moisture_percent.diff().where(df.gap_minutes.le(30))
    df["date_th"] = df.timestamp_th.dt.strftime("%Y-%m-%d")
    assert df.soil_moisture_percent.between(0, 100).all()
    pd.testing.assert_series_equal(raw.soil_moisture_percent, df.soil_moisture_percent)
    serial_th = pd.to_datetime(raw.recorded_at_th, unit="D", origin="1899-12-30")
    date_error_seconds = (serial_th - df.timestamp_th.dt.tz_localize(None)).dt.total_seconds().abs()
    expected = pd.date_range(df.timestamp.min(), df.timestamp.max(), freq="15min")
    missing_grid = expected.difference(pd.DatetimeIndex(df.timestamp))
    original_missing = raw[SIGNATURE].isna().any(axis=1)
    weather_usable = ~df.weather_stale_suspected & ~original_missing
    profile = {
        "rows": len(df), "columns_source": len(raw.columns) - 2,
        "first_th": df.timestamp_th.min().isoformat(), "last_th": df.timestamp_th.max().isoformat(),
        "expected_15min_slots": len(expected), "missing_15min_slots": len(missing_grid),
        "off_grid_rows": int((~df.timestamp.isin(expected)).sum()),
        "gaps_over_30min": int(df.gap_minutes.gt(30).sum()),
        "largest_gap_hours": float(df.gap_minutes.max() / 60),
        "original_weather_signature_missing": int(original_missing.sum()),
        "additional_weather_flatline_rows": int(df.weather_stale_suspected.sum()),
        "additional_weather_flatline_runs": len(flatlines),
        "weather_signature_usable_rows": int(weather_usable.sum()),
        "soil_min": float(df.soil_moisture_percent.min()),
        "soil_max": float(df.soil_moisture_percent.max()),
        "soil_latest": float(df.soil_moisture_percent.iloc[-1]),
        "timestamp_th_max_error_seconds": float(date_error_seconds.max()),
        "snapshot_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source": payload["source"],
    }
    assert date_error_seconds.max() < 1, "UTC and displayed Thai timestamps disagree"

    daily = df.groupby("date_th").agg(
        rows=("sheet_row", "size"), soil_min=("soil_moisture_percent", "min"),
        soil_max=("soil_moisture_percent", "max"), soil_first=("soil_moisture_percent", "first"),
        soil_last=("soil_moisture_percent", "last"),
        weather_flatline_rows=("weather_stale_suspected", "sum"),
        rain_1h_available_rows=("rain_1h_mm", "count"),
        rain_1h_positive_rows=("rain_1h_mm", lambda s: int(s.gt(0).sum())),
    ).reset_index()
    # Rolling one-hour/24-hour rain readings are never summed into daily rainfall.
    high = df.soil_moisture_percent.ge(50)
    group = ((high != high.shift(fill_value=False)) | df.gap_minutes.gt(30)).cumsum()
    events = []
    for _, indices in df.loc[high].groupby(group[high]).groups.items():
        peak_index = df.loc[indices, "soil_moisture_percent"].idxmax()
        peak = df.loc[peak_index]
        later = df.loc[peak_index:]
        later = later[later.timestamp.le(peak.timestamp + pd.Timedelta(hours=48))]
        rain_window = df[df.timestamp.between(peak.timestamp-pd.Timedelta(hours=1),
                                              peak.timestamp+pd.Timedelta(hours=1))]
        rain_positive = rain_window.rain_1h_mm.gt(0) | rain_window.rain_rate_mm_h.gt(0)
        observed_positive = bool(rain_positive.any())
        row = {
            "peak_time_th": peak.timestamp_th.isoformat(), "peak_sheet_row": int(peak.sheet_row),
            "peak_moisture": float(peak.soil_moisture_percent),
            "rain_positive_near_peak": observed_positive,
            "rain_1h_usable_near_peak": int(rain_window.rain_1h_mm.notna().sum()),
            "rain_window_expected_rows": 9,
            "rain_window_observed_rows": len(rain_window),
            "rain_1h_max_near_peak": float(rain_window.rain_1h_mm.max()) if rain_window.rain_1h_mm.notna().any() else None,
            "rain_attribution": "rain_signal_present" if observed_positive else "rain_not_established",
        }
        crossing = later[later.soil_moisture_percent.le(40)]
        row["first_observed_le40_th"] = None
        row["hours_to_first_observed_le40"] = None
        row["le40_path_has_gap"] = None
        if len(crossing):
            first = crossing.iloc[0]
            row["first_observed_le40_th"] = first.timestamp_th.isoformat()
            row["hours_to_first_observed_le40"] = (first.timestamp-peak.timestamp).total_seconds()/3600
            row["le40_path_has_gap"] = bool(df.loc[peak_index+1:first.name, "gap_minutes"].gt(30).any())
        for h in [1, 2, 3, 6, 12, 24, 48]:
            exact = df[df.timestamp.eq(peak.timestamp+pd.Timedelta(hours=h))]
            row[f"moisture_{h}h"] = float(exact.soil_moisture_percent.iloc[0]) if len(exact) else None
        events.append(row)
    events = pd.DataFrame(events)
    gaps = df.loc[df.gap_minutes.gt(30), ["sheet_row", "timestamp_th", "gap_minutes"]].copy()
    return df, profile, daily, events, gaps, flatlines


def save_results(path=DEFAULT_INPUT):
    df, profile, daily, events, gaps, flatlines = inspect_snapshot(path)
    out = Path(path).parent
    (out / "profile.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, frame in [("daily", daily), ("high_moisture_events", events), ("data_gaps", gaps),
                        ("suspected_weather_flatlines", flatlines), ("readings_analysis", df)]:
        frame.to_csv(out / f"{name}.csv", index=False, encoding="utf-8-sig")
    return profile, daily, events


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    profile, daily, events = save_results(args.input)
    print(json.dumps(profile, ensure_ascii=False, indent=2))
    print(events.to_string(index=False))
    print(daily.tail(12).to_string(index=False))
