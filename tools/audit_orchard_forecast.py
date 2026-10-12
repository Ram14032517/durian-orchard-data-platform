"""Read local forecast metadata without exporting keys, coordinates or readings."""
import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        rows = list(reader)
    dates = {}
    for field in ('recorded_at', 'issued_date', 'issued_at', 'forecast_date', 'forecast_time', 'received_at'):
        values = sorted(r[field] for r in rows if r.get(field))
        if values:
            dates[field] = {'first': values[0], 'last': values[-1], 'present': len(values)}
    return dict(rows=len(rows), columns=columns, dates=dates,
                sources=dict(Counter(r.get('source') or 'unspecified' for r in rows)),
                provider_model_issue_time_present='model_issued_at' in columns,
                timing_note='issued_at/date are upload timestamps in the current Apps Script, not provider model run times')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-dir', type=Path, default=ROOT / 'data/export_2026-09-13')
    parser.add_argument('--out', type=Path, default=ROOT / '.build/orchard_forecast_audit.json')
    args = parser.parse_args()
    report = {'audited_utc': datetime.now(timezone.utc).isoformat(), 'mode': 'local_snapshot_not_live', 'files': {}}
    for name in ('readings_15min.csv', 'forecast_daily.csv', 'forecast_hourly.csv'):
        path = args.export_dir / name
        report['files'][name] = audit_csv(path) if path.is_file() else {'missing': True}
    report['limits'] = [
        'No external API was called; latest dates describe the saved export only.',
        'Daily upserts overwrite forecasts within the same upload date; not a full model-run archive.',
        'Retention currently removes old forecasts; keep an immutable private archive before backtesting.',
        'shortwave lacks a provider-specific unit contract; do not use it as net radiation or PAR.',
        'No tree yield, flowering dates, irrigation or calibrated root-zone moisture verified by this audit.'
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
