# Durian Orchard Data Platform

An academic project connecting orchard IoT measurements with soil maps, historical weather, and provincial durian production data in Thailand.

**Focus:** sensor data quality, reproducible data preparation, interactive geospatial analysis, and baseline machine learning experiments.

[คู่มือภาษาไทยและการติดตั้ง IoT](README_TH.md) · [Training data guide](research_data/five_province_history/training/README_TH.md) · [Collaboration handoff](docs/FIVE_PROVINCE_HANDOFF_TH.md)

## What this project does

- Collects soil sensor readings through an ESP32/LoRa gateway workflow, with a 15-minute acquisition interval.
- Provides ingestion code for Google Sheets and Supabase.
- Checks missing readings and suspected stale weather values caused by gateway interruptions.
- Combines NASA POWER historical weather, Land Development Department soil layers, and Office of Agricultural Economics production records.
- Compares five provinces: Chanthaburi, Chumphon, Sisaket, Uttaradit, and Surat Thani.
- Displays soil layers, area A/B weather comparisons, selectable weather charts, and monthly evidence in one map.
- Exports source-labelled weather snapshots and prepares monthly and annual datasets for modeling.
- Evaluates baseline models using chronological training, validation, and test periods.

## Start here

### Interactive map

From the repository root, use your own Python environment. Do not copy another computer's `.venv` folder.

```powershell
py -m venv .venv-portfolio
& .\.venv-portfolio\Scripts\python.exe -m pip install requests
& .\.venv-portfolio\Scripts\python.exe tools\serve_orchard_analysis.py
```

No PowerShell activation script is needed. If `py` is unavailable, use the path to your installed Python executable for the first command.

Open [the local dashboard](http://127.0.0.1:8871/research_data/five_province_history/UNIFIED_MAP.html).

1. Choose a province or soil-map location for area A; optionally set area B.
2. Choose a month or date range and load the weather comparison.
3. Switch the chart variable to temperature, rainfall, humidity, solar radiation, or wind.
4. Review monthly production evidence and source notes.
5. Use the training-data section to access datasets, or export the displayed weather snapshot.

Keep the terminal running. Use `Ctrl+C` to stop the local server. Do not open the HTML template in `tools/` with `file://`: it is not the served dashboard. NASA API access needs an internet connection; available provincial fallback data is explicitly labelled and is not a measurement at the selected point.

### Jupyter / VS Code

Open [`00_OPEN_ME.ipynb`](00_OPEN_ME.ipynb) for the main notebook. To rerun it, install the analysis dependencies in your environment:

```powershell
& .\.venv-portfolio\Scripts\python.exe -m pip install -r tools\requirements-national-analysis.txt
```

Select that environment as the notebook kernel. Review the source and output caveats before interpreting the charts.

## Repository guide

| Location | Purpose |
| --- | --- |
| `00_OPEN_ME.ipynb` | Main notebook entry point |
| `research_data/five_province_history/UNIFIED_MAP.html` | Generated dashboard served by the local server |
| `research_data/five_province_history/training/` | Modeling panels, provenance, predictions, metrics, and documentation |
| `tools/` | Data preparation, dashboard builders, analysis scripts, and local server |
| `sender_1/`, `receiver_gateway/` | Device and gateway firmware |
| `google-apps-script/`, `supabase/` | Ingestion implementations |
| `docs/` | Sensor context, quality reviews, learning notes, and handoff documentation |

Large downloads, private device configuration, local environments, caches, and orchard exports are excluded from Git. Some rebuilds therefore require downloading source data separately; see the corresponding source manifests and guides. A clone is not a backup of all local orchard data.

## Modeling: current findings and limits

The monthly experiment compares seasonal and Ridge baselines. In the recorded test set, the province-month Ridge baseline achieved MAE **14,685.26 tonnes**, while adding previous-month weather produced MAE **15,283.82 tonnes**. This experiment does not establish a predictive improvement from those weather features. See [the experiment guide](research_data/five_province_history/training/README_TH.md) for splits, coverage, and limitations.

- Provincial production includes all reported durian varieties; it is not individual-tree or Monthong-only yield.
- NASA POWER values are gridded estimates, not orchard station observations. Nearby points may share the same grid.
- Soil polygons do not prove that durian is planted there or establish the fertility of an individual orchard.
- Regional harvest calendars are not observed flowering, fruit-set, or fruit-drop dates for a specific tree.
- Weather associations and model feature effects do not establish causes of yield changes.
- Outdoor station readings must be distinguished from indoor gateway temperature/humidity.
- These experiments do not diagnose tree health, establish flowering readiness, or prescribe irrigation litres per tree.

## Next research steps

1. Forecast orchard soil moisture using quality-checked sensor history, evaluated against simple persistence baselines.
2. Record real growth stages, irrigation events, and harvest outcomes for identified sample trees.
3. Calibrate sensors and validate soil-water thresholds at the orchard before recommending irrigation.
4. Evaluate models on genuinely unseen periods and, when available, independent orchards.

## Before making the repository public

Review [the publication checklist](docs/PORTFOLIO_PUBLICATION_TH.md). Ignoring a file does not remove it from past commits. Do not publish credentials or orchard/person identifiers without permission. No public-release security certification is implied by this README.
