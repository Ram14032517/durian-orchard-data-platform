"""Train an interpretable anomaly baseline for the Farm IoT sensor stream.

This is a data-quality/anomaly model, not a disease diagnosis model. It learns
robust median/MAD statistics only from rows that pass basic validity checks and
whose Tuya weather values are not stale.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


WEATHER_COLUMNS = [
    "outdoor_temperature_c",
    "outdoor_humidity_percent",
    "pressure_hpa",
]

MODEL_FEATURES = [
    "soil_moisture_percent",
    "soil_temperature_c",
    "soil_ec",
    "soil_ph",
    "outdoor_temperature_c",
    "outdoor_humidity_percent",
    "pressure_hpa",
    "rain_1h_mm",
    "uv_index",
    "light_lux",
]

VALID_RANGES = {
    "soil_moisture_percent": (0.0, 100.0),
    "soil_temperature_c": (-10.0, 60.0),
    "soil_ec": (0.0, None),
    "soil_ph": (0.0, 14.0),
    "outdoor_temperature_c": (-10.0, 60.0),
    "outdoor_humidity_percent": (0.0, 100.0),
    "pressure_hpa": (850.0, 1100.0),
    "rain_1h_mm": (0.0, None),
    "uv_index": (0.0, None),
    "light_lux": (0.0, None),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("model_json", type=Path)
    parser.add_argument("--stale-minutes", type=float, default=60.0)
    parser.add_argument("--anomaly-threshold", type=float, default=4.5)
    return parser.parse_args()


def add_weather_stale_flags(frame: pd.DataFrame, stale_minutes: float) -> pd.DataFrame:
    output = frame.copy()
    weather_missing = output[WEATHER_COLUMNS].isna().any(axis=1)
    changed = output[WEATHER_COLUMNS].ne(output[WEATHER_COLUMNS].shift()).any(axis=1)
    changed |= output["device_id"].ne(output["device_id"].shift())
    run_id = changed.cumsum()
    run_start = output.groupby(run_id)["recorded_at"].transform("min")
    stale_age = (output["recorded_at"] - run_start).dt.total_seconds().div(60)

    output["weather_missing"] = weather_missing
    output["weather_stale_minutes"] = stale_age.where(~weather_missing, np.nan)
    output["weather_stale"] = (~weather_missing) & (stale_age >= stale_minutes)
    return output


def add_range_flags(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    invalid = pd.Series(False, index=output.index)
    reasons: list[pd.Series] = []
    for column, (minimum, maximum) in VALID_RANGES.items():
        column_invalid = output[column].notna() & (output[column] < minimum)
        if maximum is not None:
            column_invalid |= output[column].notna() & (output[column] > maximum)
        invalid |= column_invalid
        reasons.append(pd.Series(np.where(column_invalid, column, ""), index=output.index))

    reason_frame = pd.concat(reasons, axis=1)
    output["invalid_range"] = invalid
    output["invalid_range_columns"] = reason_frame.apply(
        lambda row: ",".join(value for value in row if value), axis=1
    )
    return output


def robust_statistics(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    statistics: dict[str, dict[str, float]] = {}
    for feature in MODEL_FEATURES:
        values = pd.to_numeric(frame[feature], errors="coerce").dropna()
        median = float(values.median())
        mad = float((values - median).abs().median())
        q1 = float(values.quantile(0.25))
        q3 = float(values.quantile(0.75))
        statistics[feature] = {
            "median": median,
            "mad": mad,
            "q1": q1,
            "q3": q3,
            "usable": bool(mad > 0 and values.nunique() > 1),
        }
    return statistics


def score_anomalies(
    frame: pd.DataFrame,
    statistics: dict[str, dict[str, float]],
    threshold: float,
) -> pd.DataFrame:
    output = frame.copy()
    scores: list[pd.Series] = []
    for feature, stat in statistics.items():
        if not stat["usable"]:
            continue
        values = pd.to_numeric(output[feature], errors="coerce")
        robust_z = (values - stat["median"]).abs() / (1.4826 * stat["mad"])
        scores.append(robust_z.rename(feature))

    score_frame = pd.concat(scores, axis=1)
    output["anomaly_score"] = score_frame.max(axis=1, skipna=True)
    output["anomaly_feature"] = score_frame.idxmax(axis=1, skipna=True)
    quality_bad = output["weather_missing"] | output["weather_stale"] | output["invalid_range"]
    output["model_eligible"] = ~quality_bad
    output["is_anomaly"] = output["model_eligible"] & (output["anomaly_score"] >= threshold)
    return output


def add_environment_risk_flags(frame: pd.DataFrame, stats: dict[str, dict[str, float]]) -> pd.DataFrame:
    """Add data-relative flags; these are inspection priorities, not diagnoses."""
    output = frame.copy()
    soil_high = output["soil_moisture_percent"] >= stats["soil_moisture_percent"]["q3"]
    humidity_high = output["outdoor_humidity_percent"] >= stats["outdoor_humidity_percent"]["q3"]
    recent_rain = output["rain_1h_mm"].fillna(0) > 0
    output["wet_environment_score"] = soil_high.astype(int) + humidity_high.astype(int) + recent_rain.astype(int)
    output["wet_environment_alert"] = output["model_eligible"] & (output["wet_environment_score"] >= 2)
    return output


def main() -> None:
    args = parse_args()
    data = pd.read_csv(args.input_csv)
    missing = sorted(set(["recorded_at", "device_id", *MODEL_FEATURES]) - set(data.columns))
    if missing:
        raise ValueError(f"Input is missing columns: {', '.join(missing)}")

    data["recorded_at"] = pd.to_datetime(data["recorded_at"], utc=True, errors="coerce")
    data = data.dropna(subset=["recorded_at", "device_id"]).sort_values(["device_id", "recorded_at"])
    data = add_weather_stale_flags(data, args.stale_minutes)
    data = add_range_flags(data)

    training_rows = data[~(data["weather_missing"] | data["weather_stale"] | data["invalid_range"])]
    statistics = robust_statistics(training_rows)
    scored = score_anomalies(data, statistics, args.anomaly_threshold)
    scored = add_environment_risk_flags(scored, statistics)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.model_json.parent.mkdir(parents=True, exist_ok=True)
    scored.to_csv(args.output_csv, index=False, encoding="utf-8-sig")

    model = {
        "model_type": "robust_median_mad_baseline",
        "purpose": "sensor anomaly screening; not disease diagnosis",
        "stale_weather_rule": {
            "columns": WEATHER_COLUMNS,
            "unchanged_minutes_threshold": args.stale_minutes,
        },
        "anomaly_threshold_robust_z": args.anomaly_threshold,
        "valid_ranges": VALID_RANGES,
        "features": statistics,
        "training_rows": int(len(training_rows)),
        "excluded_weather_missing": int(data["weather_missing"].sum()),
        "excluded_weather_stale": int(data["weather_stale"].sum()),
        "excluded_invalid_range": int(data["invalid_range"].sum()),
        "flagged_anomalies": int(scored["is_anomaly"].sum()),
        "wet_environment_alerts": int(scored["wet_environment_alert"].sum()),
    }
    args.model_json.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
