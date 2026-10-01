# Durian Orchard Data Platform

An academic project connecting orchard IoT measurements with soil maps, historical weather, and provincial durian production data in Thailand.

**Focus:** sensor data quality, reproducible data preparation, interactive geospatial analysis, and baseline machine learning experiments.

**เริ่มใช้งานตามลำดับ:** [00_START_HERE_TH.md](00_START_HERE_TH.md) — จุดเปิดแผนที่/Notebook โฟลเดอร์ข้อมูล และลำดับเตรียมโมเดลในไฟล์เดียว

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

ใน VS Code เลือก **Terminal → Run Task → Durian: 01 เปิดแผนที่ (เริ่มตรงนี้)** หรือดับเบิลคลิก `00_OPEN_REPORT.cmd` ตัวเปิดจะใช้ข้อมูลของ repo นี้เท่านั้น และเลือกพอร์ตว่างหากมีสำเนา portfolio เปิดอยู่ ไม่ต้อง activate Python ด้วย PowerShell

งานอื่นอยู่ใน Run Task เช่นกัน: อ่านรายงานรายเดือน (เลือกจังหวัด/ปี/เดือน), เตรียม ZIP ข้อมูลเทรน, ทดสอบ Python และรันโมเดล baseline งานรันโมเดลจะเขียนผลทดลองใหม่ ส่วนงาน ZIP จะรักษา snapshot เดิม ไม่แก้ CSV ต้นฉบับ

โฟลเดอร์ environment/cache ซ่อนจาก Explorer เพื่อลดความรกเท่านั้น ไม่ได้ลบไฟล์ และไม่ใช่การป้องกัน secrets จาก Git

### Interactive map

From the repository root, use your own Python environment. Do not copy another computer's `.venv` folder.

```powershell
py -3 -m venv .build\national-analysis-venv
& .\.build\national-analysis-venv\Scripts\python.exe -m pip install -r tools\requirements-national-analysis.txt
& .\.build\national-analysis-venv\Scripts\python.exe tools\open_orchard_report.py
```

No PowerShell activation script is needed. If `py` is unavailable, use the path to your installed Python executable for the first command.

Use Python 3.10 or newer. This repo uses `.build/national-analysis-venv` consistently in VS Code tasks, the launcher, and these instructions. If that environment already works, skip the creation command. Do not overwrite a broken copied environment; create an environment on your own machine instead.

The launcher opens [the local dashboard](http://127.0.0.1:8871/research_data/five_province_history/UNIFIED_MAP.html). If that port belongs to another checkout/application, it uses a free port up to 8879 and prints the actual URL.

1. Choose a province or soil-map location for area A; optionally set area B.
2. Choose a month or date range and load the weather comparison.
3. Switch the chart variable to temperature, rainfall, humidity, solar radiation, or wind.
4. Review monthly production evidence and source notes.
5. Use the training-data section to access datasets, or export the displayed weather snapshot.

The launcher runs the local server in the background; closing its task terminal does not stop it. For a foreground server you can stop with `Ctrl+C`, use **Durian: 90 เปิดเซิร์ฟเวอร์แผนที่ (ขั้นสูง)** instead. Do not open the HTML template in `tools/` with `file://`: it is not the served dashboard. NASA API access needs an internet connection; available provincial fallback data is explicitly labelled and is not a measurement at the selected point.

Training CSVs are in `research_data/five_province_history/training/`. If the ignored ZIP is absent after cloning, run the ZIP task before downloading it from the dashboard. It packages saved regional files only, does not refresh model results, and preserves an existing valid ZIP. Individual CSVs remain available without the ZIP.

### Jupyter / VS Code

Open [`00_OPEN_ME.ipynb`](00_OPEN_ME.ipynb) for the main notebook. To rerun it, install the analysis dependencies in your environment:

```powershell
& .\.build\national-analysis-venv\Scripts\python.exe -m pip install -r tools\requirements-national-analysis.txt
```

Select that environment as the notebook kernel. If VS Code remembers the old `.venv`, use **Python: Select Interpreter** and **Select Kernel → Python Environments** to choose `.build/national-analysis-venv/Scripts/python.exe` once. Default settings do not replace a previously selected interpreter/kernel. Review the source and output caveats before interpreting the charts.

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
