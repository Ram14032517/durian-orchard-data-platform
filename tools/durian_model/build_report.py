"""Executed notebook and Thai PDF/Markdown report, generated from verified results."""
import argparse
import os
import re
from html import escape
from importlib import import_module
from pathlib import Path
import sys

from common import *
from run_all import STEPS

NAMES = {'22': 'จันทบุรี', '33': 'ศรีสะเกษ', '53': 'อุตรดิตถ์', '84': 'สุราษฎร์ธานี', '86': 'ชุมพร'}


def report_text(text, bold=False):
    """Keep Thai shaping intact while giving Latin text a consistent sans-serif face."""
    latin = 'EnglishBold' if bold else 'English'
    thai = 'ThaiBold' if bold else 'Thai'
    # The shaper uses a word's first font; keep parentheses and Thai units together.
    return ''.join(escape(run).replace('\n', '<br/>') if run.isspace() else
                   f'<font name="{thai if re.search(r"[\u0e00-\u0e7f]", run) else latin}">{escape(run)}</font>'
                   for run in re.split(r'(\s+)', str(text)) if run)


def build_notebook():
    import nbformat
    from nbclient import NotebookClient
    from jupyter_client.kernelspec import KernelSpecManager
    cells = [nbformat.v4.new_markdown_cell(
        '# ทำนายผลผลิตทุเรียนด้วย Ridge + VPD\nข้อมูลปี 2010-2025; ทดสอบปี 2017-2025 แบบ chronological rolling. '
        'กันปี test ออกจากการเทรนในแต่ละ fold แต่ไม่ใช่ชุดยืนยันอิสระจากการเลือกกลุ่มโมเดล. '
        'โค้ดเต็มแยกตามขั้นใน `tools/durian_model/`. รันทุก cell ตามลำดับ.'),
        nbformat.v4.new_code_cell(
            "from pathlib import Path\nimport sys\nimport pandas as pd\nfrom IPython.display import display, Image\n"
            "ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'tools/durian_model').is_dir())\n"
            "sys.path.insert(0, str(ROOT / 'tools/durian_model'))\nfrom common import OUT\n")]
    descriptions = [
        'ตรวจ key, target ต่อพื้นที่ให้ผล, ปี และ source hash ก่อนใช้ข้อมูล',
        'ทดสอบปีถัดไป และ tune ด้วย 3 ปีก่อนหน้าเท่านั้น ไม่สุ่มข้ามเวลา',
        'เลือกฤดูเฉพาะจากปี train สร้างช่วงอายุผลและ daily VPD proxy ไม่เติมค่าหายเป็นศูนย์',
        'เลือกอายุ 4 ค่าและ alpha 3 ค่าเฉพาะ inner validation แล้ว refit ด้วยปีอดีต',
        'ดู signed standardized coefficients ไม่ใช่หลักฐานเชิงสาเหตุ',
        'ประเมิน rolling-origin test predictions และ paired year-block bootstrap เชิงพรรณนา',
        'demo 2025 ใช้โมเดล train ถึง 2024; ยังไม่เชื่อม API พยากรณ์สด']
    for number, (module, text) in enumerate(zip(STEPS, descriptions)):
        cells.append(nbformat.v4.new_markdown_cell(f'## ขั้น {number}: {module}\n{text}'))
        code = f'import {module}\nresult_{number} = {module}.run()\n'
        if number == 4:
            code += "display(result_4)\ndisplay(Image(filename=str(OUT / 'ridge_vpd_coefficients.png')))"
        elif number == 5:
            code += "display(pd.DataFrame([result_5['overall'], result_5['previous_year']], index=['Ridge + VPD', 'Previous year']))\ndisplay(Image(filename=str(OUT / 'ridge_vpd_evaluation.png')))"
            code += "\ndisplay(pd.DataFrame([dict(comparator=name, **estimate) for name, estimates in result_5['paired_uncertainty'].items() for estimate in estimates]))\nprint(result_5['uncertainty_warning'])"
        elif number == 6:
            code += 'display(result_6)'
        else:
            code += f'result_{number}'
        cells.append(nbformat.v4.new_code_cell(code))
    nb = nbformat.v4.new_notebook(cells=cells)
    # A task-local kernelspec avoids changing the user's global Python/Jupyter setup.
    kernels = ROOT / '.build/durian-report-kernels'
    spec = kernels / 'durian-report'
    spec.mkdir(parents=True, exist_ok=True)
    (spec / 'kernel.json').write_text(json.dumps(dict(
        argv=[sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
        display_name='Durian project Python', language='python')), encoding='utf-8')
    client = NotebookClient(nb, timeout=300, kernel_name='durian-report',
                            resources={'metadata': {'path': str(ROOT)}})
    client.km = client.create_kernel_manager()
    client.km.kernel_spec_manager = KernelSpecManager(kernel_dirs=[str(kernels)])
    client.execute()
    assert all(c.get('execution_count') is not None for c in nb.cells if c.cell_type == 'code')
    assert not any(o.output_type == 'error' for c in nb.cells if c.cell_type == 'code' for o in c.outputs)
    nb.metadata.kernelspec = dict(name='python3', display_name='Python 3 (select project interpreter)', language='python')
    destination = ROOT / 'notebooks/DURIAN_RIDGE_VPD_STEPS.ipynb'
    nbformat.write(nb, destination)
    print('Executed notebook:', destination, flush=True)


def report_pages():
    evaluation = load_json('evaluation.json')
    final = load_json('final_model.json')
    models = load_json('models.json')
    by_year = load_csv('metrics_by_year_ce.csv')
    by_province = load_csv('metrics_by_province_code.csv')
    coefficients = load_csv('coefficients.csv')
    demo = load_csv('demo_2025_predictions.csv')
    primary = evaluation['overall']
    comparisons = {r['model']: r for r in evaluation.get('comparison_models', [])}
    uncertainty = evaluation['paired_uncertainty']
    gain_without_vpd = uncertainty['stage_ridge'][0]['mae_reduction_pct']
    worse_years = ', '.join(map(str, uncertainty['previous_year'][0]['worse_years']))
    pages = []

    def page(title, content):
        pages.append((title, content))

    page('ภาพรวมและวัตถุประสงค์', [
        ('h', 'รายงานโมเดลผลผลิตทุเรียน 5 จังหวัด'),
        ('p', 'Ridge Regression ใช้อากาศตามช่วงอายุผล พร้อมประเมินการเพิ่ม VPD\nข้อมูลปี 2010-2025 (พ.ศ. 2553-2568) | จัดทำ 9 ตุลาคม 2569'),
        ('p', 'วัตถุประสงค์: ทดลองประมาณผลผลิตต่อไร่จากผลผลิตปีก่อน แนวโน้มปี จังหวัด และอากาศย้อนหลังที่นับจากช่วงเก็บเกี่ยว เพื่อสร้าง workflow ที่รันซ้ำได้ และตรวจสอบว่าให้ผลดีกว่าการอ้างผลผลิตปีก่อนหรือไม่'),
        ('table', [['ผลหลัก', 'ค่าจากการรันซ้ำ'],
                   ['โมเดลที่เลือก', 'stage_ridge_vpd'],
                   ['ข้อมูลทั้งหมด', '80 จังหวัด-ปี ใน 5 จังหวัด'],
                   ['ทดสอบเดินหน้าตามเวลา', '2017-2025 รวม 45 จังหวัด-ปี'],
                   ['MAE (กก./ไร่)', f"{primary['mae_kg_rai']:.2f}"],
                   ['RMSE (กก./ไร่)', f"{primary['rmse_kg_rai']:.2f}"],
                   ['ลด MAE เทียบค่าปีก่อน', f"{evaluation['mae_reduction_vs_previous_year_pct']:.2f}%"]]),
        ('h', 'เหตุผลที่เลือกโมเดลนี้'),
        ('p', 'ใช้ MAE เป็นเกณฑ์หลัก จากผลเปรียบเทียบเดิม 26 วิธี/ชุดผลบน test rows เดียวกัน Ridge + VPD มี MAE ต่ำที่สุด ตารางประเมินรวม CatBoost, Extra Trees และ SVR และแสดงครบ 26 วิธีในภาคผนวก โมเดลที่เพิ่ม NDVI มี RMSE ดีกว่า แต่ MAE สูงกว่า จึงไม่มีผู้ชนะทั้งสองเกณฑ์พร้อมกัน'),
        ('p', 'ช่วง 2010-2025 เลือกตามปฏิทินเพื่อเน้นปีหลัง ไม่ลบปีที่ผลผลิตต่ำ ข้อความว่าอากาศแปรปรวนมากขึ้นเป็นคำถามวิจัย ไม่ใช่ข้อสรุปที่พิสูจน์แล้วจากการเลือกช่วงปีนี้'),
        ('p', 'สถานะ: งานทดลองย้อนหลัง กันปี test ออกจากการเทรนในแต่ละ fold แต่ใช้ผลชุดนี้เลือกกลุ่มโมเดลแล้ว จึงไม่ใช่ชุดยืนยันอิสระ ตัวเลขลด MAE 11.44% เป็นผลเชิงพรรณนา อาจมองดีเกินจริงจากการเลือกผู้ชนะ และยังไม่ได้พิสูจน์ความเหนือกว่าทางสถิติหรือใช้วินิจฉัยสุขภาพต้น')])

    page('ข้อมูลและหน่วยวิเคราะห์', [
        ('h', 'Data Understanding'),
        ('p', 'หนึ่งแถวเป้าหมายคือหนึ่งจังหวัดในหนึ่งปี ได้แก่ จันทบุรี (22) ศรีสะเกษ (33) อุตรดิตถ์ (53) สุราษฎร์ธานี (84) และชุมพร (86) รวม 5 × 16 = 80 แถว ไม่มีการสร้าง target รายอำเภอหรือรายชุดดินจากการแจกยอดจังหวัด'),
        ('code', 'yield_kg_per_rai = production_tonnes * 1000 / bearing_rai'),
        ('table', [['ข้อมูลใน repo', 'ใช้ทำอะไร'],
                   ['production_annual.csv', 'ยอดจังหวัด เนื้อที่ให้ผล และ target 2010-2025; lag ใช้ปี 2009-2024'],
                   ['harvest_monthly.csv', 'เลือกเดือน peak เฉพาะปี train; เดือนที่ไม่มีระเบียนไม่ใช่ศูนย์'],
                   ['weather_daily.csv', 'NASA POWER อุณหภูมิ ฝน RH และรังสีดวงอาทิตย์ ณ จุดอ้างอิง'],
                   ['OAE SOURCE.md / XLSX', 'หลักฐาน edition ต้นทาง; CSV เก็บ snapshot ไม่ได้ดึงใหม่รอบนี้']]),
        ('p', 'ใช้เนื้อที่ให้ผล (bearing area) เป็นตัวหาร ไม่ใช่เนื้อที่ยืนต้น/ปลูกทั้งหมด จึงไม่เอาพื้นที่ปลูกใหม่ที่ยังไม่ให้ผลมาลดค่าผลผลิตต่อไร่ แต่ยังอาจมีผลจากสัดส่วนอายุต้นและพันธุ์ที่ไม่ได้วัด'),
        ('h', 'ตรวจปีและสถานะข้อมูล'),
        ('p', 'ตรวจไฟล์ OAE ต้นฉบับในเครื่อง: ปี 2540-2568 และ data_date 14 ก.ค. 2026; แฟ้มรายเดือนมีปี 2547-2568 และ data_date 22 ก.ค. 2026 หน้าแคตตาล็อกยังระบุสิ้นสุด 2567 จึงอ้างปีจากไฟล์และเก็บความต่างนี้ไว้ data_date ไม่ใช่ปีผลผลิต [1][2]'),
        ('p', 'Target เป็นค่าที่มีบันทึกในแหล่งทางการ ไม่ใช่ค่าจำลอง อย่างไรก็ตามไฟล์ไม่ได้ใส่สถานะ final/forecast แยกทุกแถว รอบนี้ยังไม่ได้ยืนยันยอดปิดจริงทุกปีจากหน่วยงาน ผลจึงอ้าง snapshot ของโครงการ ไม่รับรอง finality ของทุกแถว'),
        ('p', 'อากาศเป็นวัน LST และกริด NASA POWER หนึ่งพิกัดต่อจังหวัด ไม่ใช่สถานีสวน ไม่ใช่ค่าเฉลี่ยถ่วงด้วยพื้นที่สวนที่ให้ผล การเพิ่มความละเอียดแผนที่ไม่ได้เพิ่มความละเอียด target [3]')])

    page('ขั้น 0 และ 1: ตรวจข้อมูลและแบ่งปี', [
        ('h', 'Step 0 - Audit Data'),
        ('p', 'ไฟล์: step0_audit_data.py ตรวจ key จังหวัด-ปีซ้ำ ค่าตัวเลข finite พื้นที่ให้ผล > 0 ผลผลิต >= 0 และสูตร target ให้ตรงกัน ตรวจให้ได้ 80 แถว แบ่งปีด้วยปฏิทิน และสร้างผลผลิตปีก่อนโดยเลื่อน key ปี +1'),
        ('code', "lag = annual[['province_code', 'year_ce', TARGET]].copy()\nlag = lag.rename(columns={TARGET: 'previous_yield_kg_rai'})\nlag['year_ce'] += 1\n# Merge on province/year, validate='one_to_one'"),
        ('p', 'ผลลัพธ์: ridge_vpd_panel.csv และ ridge_vpd_audit.json มี SHA256 ของ input ทั้งสามไฟล์ ขั้นถัดไปตรวจ snapshot ทุกครั้ง ถ้าต้นทางเปลี่ยนต้องรัน pipeline ใหม่ ไม่ปนโมเดลเก่ากับข้อมูลใหม่'),
        ('h', 'Step 1 - Chronological Split'),
        ('p', 'ไฟล์: step1_split_years.py ใช้ outer test ปี 2017-2025 ปีละ 5 จังหวัด สำหรับ test ปี t ใช้ train 2010 ถึง t-1 และ inner validation สามปี t-3, t-2, t-1 แต่ละ inner fold เทรนเฉพาะปีก่อน validation นั้น'),
        ('table', [['ตัวอย่าง test ปี 2025', 'ช่วงปี'],
                   ['Inner validate 2022', 'train 2010-2021'],
                   ['Inner validate 2023', 'train 2010-2022'],
                   ['Inner validate 2024', 'train 2010-2023'],
                   ['Refit ก่อน test', 'train 2010-2024 รวม 75 แถว'],
                   ['Outer test', '2025 รวม 5 แถว']]),
        ('p', 'แบ่งปีตามเวลาเพื่อหลีกเลี่ยงข้อมูลอนาคตย้อนเข้าสู่ train การ tune อายุ/alpha ของแต่ละ fold ใช้เฉพาะปีอดีต อย่างไรก็ตามผล outer test เคยใช้เลือกกลุ่มโมเดล จึงไม่ใช่ชุดยืนยันอิสระสำหรับการเลือกกลุ่มนั้น')])

    page('ขั้น 2: สร้างอากาศตามช่วงอายุผลและ VPD', [
        ('h', 'Step 2 - Process Data'),
        ('p', 'ไฟล์: step2_process_data.py หาผลรวมยอดรายเดือนเฉพาะปี train ของจังหวัดนั้น เลือกเดือน peak และช่วง 3 เดือนต่อเนื่องรอบ peak หากติดขอบปีจะเลื่อนช่วงให้ยังอยู่ในปีเดียว นี่เป็นฤดูอ้างอิง ไม่ใช่ฤดูที่วัดจริงทุกปี'),
        ('p', 'ให้ทุกวันที่เป็นไปได้ในช่วงเก็บเกี่ยวมีน้ำหนักเท่ากัน สำหรับ harvest day H และอายุสมมติ A วัน ให้วันดอกบานอ้างอิง B = H - A จากนั้นสร้าง exposure แต่ละ window ไม่ได้ให้น้ำหนักตามจำนวนผลจริงหรือยอดรายเดือนของ test ปีนั้น'),
        ('table', [['Feature / ช่วงเทียบ B', 'วิธีรวมและหน่วย'],
                   ['pre_bloom_90d_rain_mm: [-90, 0)', 'ค่าเฉลี่ยผลรวมฝน 90 วันต่อ harvest scenario (มม.)'],
                   ['fruit_0_29d_rain_mm: [0, 30)', 'ค่าเฉลี่ยผลรวมฝน 30 วัน (มม.)'],
                   ['fruit_30_59d_rain_mm: [30, 60)', 'ค่าเฉลี่ยผลรวมฝน 30 วัน (มม.)'],
                   ['fruit_60_89d_solar_mj_m2_day: [60, 90)', 'รังสีเฉลี่ยรายวัน (MJ/m²/day)'],
                   ['fruit_90_to_harvest_temperature_c: [90, A)', 'อุณหภูมิเฉลี่ย (°C)'],
                   ['vpd_pre_bloom_mean_kpa: [-90, 0)', 'VPD เฉลี่ยทุก day-scenario (kPa)'],
                   ['vpd_early_fruit_p90_kpa: [0, 30)', 'percentile 90 ทุก day-scenario (kPa)']]),
        ('code', 'e(T) = 0.6108 * exp(17.27*T / (T + 237.3))\nes = (e(Tmin) + e(Tmax)) / 2\nVPD = es * (1 - RHmean/100)  # kPa, approximate'),
        ('p', 'สูตรใช้แนวทาง FAO-56 แต่ RH เฉลี่ยรายวันของ NASA ไม่ใช่ค่าเฉลี่ย RHmax/RHmin ตามสมมติฐาน Eq.19 จึงเป็น proxy ไม่ใช่ VPD รายชั่วโมงหรือที่ใบ [4] ไม่มี threshold ลูกร่วงที่ยืนยันสำหรับทุเรียนใส่ลงไป'),
        ('p', 'ทดลอง A = 120, 130, 140, 150 วัน และ season cutoffs 2013-2025 ได้ 4,160 feature rows แต่ยังมี target อิสระเพียง 80 แถว หน้าต่างต้องมีข้อมูลครบ ไม่เติม missing ด้วย 0 ไม่ใช้ไฟล์ดิน/NDVI/ภัยพิบัติที่ยังไม่เข้าคู่ในโมเดลนี้')])

    page('ขั้น 3: เทรน Tune และบันทึกโมเดล', [
        ('h', 'Step 3 - Train Model'),
        ('p', 'ไฟล์: step3_train_model.py ใช้ Ridge Regression โดยนำฟังก์ชันเดิมของโปรเจกต์มาใช้ซ้ำ จัด province เป็น 5 one-hot columns รวม year, lag yield, weather 5 ตัว และ VPD 2 ตัว เป็น 14 design columns'),
        ('code', 'z = (X - mean_train) / std_train\nminimize sum((y - intercept - z @ beta)**2)\n         + alpha * sum(beta**2)\ny_hat = max(0, intercept + z @ beta)'),
        ('p', 'fit mean/std และ coefficient เฉพาะ train; std = 0 เปลี่ยนเป็น 1 ไม่มี scaling จาก test ไม่ใช้ผลผลิตปีปัจจุบันเป็น predictor Tune 4 อายุ × 3 alpha (1, 10, 100) = 12 configurations เลือก mean MAE ของสาม inner years แล้ว refit train ก่อน outer year [5]'),
        ('table', [['Outer test', 'Train ถึง', 'อายุ (วัน)', 'alpha']] +
                  [[year, str(int(year)-1), str(models[year]['age_days']), str(models[year]['parameters']['alpha'])]
                   for year in map(str, range(2017, 2026))]),
        ('p', f"โมเดลสุดท้าย refit ปี 2010-2025 รวม 80 แถว เพื่อรับ input ปีถัดไป: อายุสมมติ {final['age_days']} วัน, alpha {final['parameters']['alpha']:.0f} เลือกจาก validation 2023-2025 โมเดลสุดท้ายนี้ไม่ใช่โมเดลที่ใช้วัด test 2025"),
        ('p', 'เก็บ mean, scale, coefficients, intercept, feature order, train_end, age, season และ input hash ใน JSON ไม่ใช้ pickle ที่ต้อง execute ตอนโหลด บันทึก tuning.csv และ models.json เพื่อย้อนตรวจการเลือกในแต่ละปี อายุที่ได้คือค่าที่ช่วย prediction ไม่ใช่การพิสูจน์อายุผลจริง')])

    page('ขั้น 4: ตรวจการใช้งานตัวแปรในโมเดล', [
        ('h', 'Step 4 - Investigate Feature Importance'),
        ('p', 'ไฟล์: step4_investigate_feature_importance.py แสดง signed standardized Ridge coefficients จากโมเดลสุดท้าย train 2010-2025 ค่า coefficient คือ kg/rai ต่อการเพิ่มหนึ่ง training standard deviation เมื่อคงตัวแปรอื่นในสมการ'),
        ('image', ('ridge_vpd_coefficients.png', 480, 288)),
        ('p', 'เรียงค่าสัมบูรณ์เพื่อดูว่าโมเดลใช้ตัวแปรใดมาก แต่ weather/VPD/จังหวัดมีความสัมพันธ์กัน จึงอาจแบ่งอิทธิพลกันหรือเปลี่ยนเครื่องหมายเมื่อเปลี่ยนชุด train ห้ามตีความว่าฝนทำให้ผลร่วง หรือว่าจังหวัดหนึ่งเหมาะปลูกกว่าจาก coefficient เพียงอย่างเดียว'),
        ('table', [['ตัวแปรที่มี |coefficient| สูง 5 อันดับ', 'Signed coefficient']] +
                  [[r.feature, f'{r.coefficient_kg_rai_per_training_sd:.2f}'] for r in coefficients.head(5).itertuples()]),
        ('p', 'ค่า province dummy เป็นการอธิบายความต่างภายใต้ coding/regularization นี้ ไม่ใช่คุณสมบัติดินที่วัดได้ การวัด pH/NPK และ overlay ชุดดินจริงเป็นงานเพิ่มเติมที่ต้องมีหน่วยพื้นที่และหลักฐาน ไม่ใส่ค่าธาตุอาหารสมมติมาแทน')])

    comparison_names = ['stage_ridge_vpd', 'stage_ridge_ndvi_vpd', 'stage_ridge',
                        'stage_catboost_combined', 'stage_extra_trees_combined', 'stage_svr_combined', 'previous_year']
    comparison_table = [['วิธีเปรียบเทียบ', 'MAE', 'RMSE']]
    for name in sorted(comparison_names, key=lambda name: comparisons[name]['mae_kg_rai']):
        record = comparisons.get(name)
        if record:
            comparison_table.append([name, f"{record['mae_kg_rai']:.2f}", f"{record['rmse_kg_rai']:.2f}"])
    page('ขั้น 5: ประเมินผลย้อนหลัง', [
        ('h', 'Step 5 - Evaluate Result'),
        ('p', 'ไฟล์: step5_evaluate_result.py คำนวณจาก outer predictions 45 แถวที่ train ไม่เคยใช้ target ของปี test ใน fold นั้น เปรียบเทียบกับ yield ปีก่อนบนจังหวัด-ปีเดียวกัน รันใหม่แล้ว prediction ตรงกับ benchmark เดิมภายใน tolerance 1e-7'),
        ('code', 'MAE  = mean(abs(predicted - actual))\nRMSE = sqrt(mean((predicted - actual)**2))\nBias = mean(predicted - actual)'),
        ('table', comparison_table),
        ('p', f"หน่วยทุกค่าเป็น กก./ไร่ Bias = {primary['bias_kg_rai']:.2f} หมายถึงทำนายต่ำกว่าค่าต้นทางโดยเฉลี่ย MAE ลด {evaluation['mae_reduction_vs_previous_year_pct']:.2f}% เทียบค่าปีก่อน และ {gain_without_vpd:.2f}% เทียบ Ridge ไม่มี VPD ทั้งสองค่าเป็นผลเชิงพรรณนา ไม่ใช่หลักฐานยืนยันนัยสำคัญทางสถิติ คำนวณร้อยละจากค่าเต็มความละเอียดก่อนปัดเศษ"),
        ('image', ('ridge_vpd_evaluation.png', 480, 196)),
        ('p', f'กราฟซ้ายเทียบ actual กับ predicted เส้นประคือค่าตรงกัน กราฟขวาแสดง MAE รายปี โมเดลแย่กว่าค่าปีก่อนในปี {worse_years} แม้ค่าเฉลี่ยรวมดีกว่า วิธีอื่นเป็น benchmark ที่ตรวจ input hash ตรงกัน รันใหม่เฉพาะ Ridge + VPD ไม่ใช่ retrain ทุกกลุ่ม')])

    uncertainty_table = [['ตัวเทียบ / บล็อกปี', 'ช่วงลด MAE (กก./ไร่)', 'ช่วงลด MAE (%)']]
    for name, estimates in uncertainty.items():
        label = 'ค่าปีก่อน' if name == 'previous_year' else 'Ridge ไม่มี VPD'
        for estimate in estimates:
            absolute = estimate['gain_percentile_95_kg_rai']
            relative = estimate['reduction_percentile_95_pct']
            uncertainty_table.append([f"{label} / {estimate['block_length_years']} ปี",
                                      f'{absolute[0]:.2f} ถึง {absolute[1]:.2f}',
                                      f'{relative[0]:.2f} ถึง {relative[1]:.2f}'])
    page('ความไม่แน่นอนของผลเปรียบเทียบ', [
        ('h', 'Paired year-block bootstrap'),
        ('p', '45 แถวมีเพียง 9 ปีและ 5 จังหวัดเดิม ไม่ถือว่าแต่ละแถวอิสระ จับคู่ความคลาดเคลื่อนบนจังหวัด-ปีเดียวกัน สุ่มเป็นบล็อกปีต่อเนื่องโดยเก็บทั้ง 5 จังหวัดไว้ด้วยกัน บล็อกวนจากปลายกลับต้นชุดตาม circular block bootstrap [6]'),
        ('p', 'ในการวิเคราะห์เชิงสำรวจนี้ใช้บล็อก 3 ปีเป็นการประเมินหลัก และ 2 ปีเพื่อตรวจความไว รายงานนี้ไม่มีหลักฐานลงวันที่ยืนยันว่าขนาดบล็อกถูกกำหนดก่อนดูผล จึงไม่อ้างว่าเป็นการกำหนดล่วงหน้าที่ตรวจสอบได้ สุ่ม 20,000 ครั้งด้วย seed 42 แต่ละครั้งเฉลี่ย MAE ของทั้ง 9 ปี คำนวณผลต่างและร้อยละจาก MAE รวม ไม่เฉลี่ยร้อยละรายปี'),
        ('code', 'gain = MAE_baseline - MAE_model\nreduction_pct = 100 * (1 - MAE_model / MAE_baseline)'),
        ('table', uncertainty_table),
        ('p', 'ตารางเป็นช่วงเปอร์เซ็นไทล์ 95% ของ bootstrap เชิงพรรณนา ค่าบวกหมายถึงโมเดลดีกว่า ค่าลบหมายถึงแย่กว่า ทั้งสองตัวเทียบและทั้งสองขนาดบล็อกคร่อมศูนย์ จึงยังไม่สนับสนุนข้อสรุปว่าการลด MAE 11.44% หรือ 2.07% เป็นความเหนือกว่าที่แน่นอน'),
        ('h', 'ข้อจำกัดของช่วงที่คำนวณ'),
        ('p', 'มีเพียง 9 ปีต้นทางและ 5 จังหวัดคงที่ ไม่แทนประชากรทุกจังหวัด สมมติฐานความคงตัวของลำดับความคลาดเคลื่อนยังไม่ยืนยัน การวนปลายกลับต้นสร้างรอยต่อจำลอง บล็อก 2-3 ปีเก็บได้เพียงความสัมพันธ์ระยะสั้น ไม่รับประกันว่าครอบคลุมการพึ่งพากันทั้งหมด'),
        ('p', 'สุ่มจาก prediction ที่บันทึกไว้ ไม่เทรนและ tune ใหม่ในแต่ละรอบ และไม่ปรับความเอนเอียงจากการเลือกผู้ชนะ 26 วิธีบนผล test เดียวกัน จึงไม่ใช่ช่วงความเชื่อมั่นยืนยันหลังเลือกโมเดล และไม่ใช่ prediction interval สำหรับปีอนาคต'),
        ('p', 'หลักฐานที่ต้องเพิ่มคือผลจากปีหรือชุดข้อมูลใหม่ที่ไม่เคยใช้เลือกกลุ่มโมเดล โดยตรึงวิธีและเกณฑ์ล่วงหน้า ตารางจับคู่รายปีและโค้ด bootstrap เก็บในผลขั้น 5 เพื่อรันซ้ำได้')])

    recent = evaluation['recent_2020_2025']
    page('ผลรายจังหวัดและปีหลัง', [
        ('h', 'Evaluation Detail'),
        ('table', [['จังหวัด', 'n', 'MAE', 'RMSE', 'Bias']] +
                  [[NAMES[r.province_code], str(r.n), f'{r.mae_kg_rai:.2f}', f'{r.rmse_kg_rai:.2f}', f'{r.bias_kg_rai:.2f}']
                   for r in by_province.itertuples()]),
        ('p', 'จังหวัดละ 9 test years ค่า bias ต่างกันมาก จึงไม่ควรใช้ค่าผิดพลาดเฉลี่ยรวมแทนระดับความแม่นยำรายสวน โดยเฉพาะความคลาดเคลื่อนเชิงระบบในจันทบุรีและสุราษฎร์ธานี'),
        ('table', [['Test ปี', 'n', 'MAE', 'RMSE', 'Bias']] +
                  [[str(r.year_ce), str(r.n), f'{r.mae_kg_rai:.2f}', f'{r.rmse_kg_rai:.2f}', f'{r.bias_kg_rai:.2f}']
                   for r in by_year.itertuples()]),
        ('p', f"เฉพาะ test ปี 2020-2025: n = {recent['n']}, MAE = {recent['mae_kg_rai']:.2f}, RMSE = {recent['rmse_kg_rai']:.2f} กก./ไร่ นี่เป็น subgroup เชิงพรรณนาจากผลเดิม ไม่ใช่การเริ่มทดลองใหม่หรือเลือกผู้ชนะใหม่ตามช่วงนี้"),
        ('p', 'ปีที่ MAE ต่ำไม่ได้แปลว่าอากาศแปรปรวนน้อย และปีที่ MAE สูงไม่ได้ยืนยันภัยพิบัติ การเชื่อมเหตุการณ์ต้องมีวันเกิดเหตุ พื้นที่จริง และหลักฐานผลกระทบ ไม่อนุมานความเสียหายจาก residual เพียงอย่างเดียว')])

    page('ขั้น 6: ทำนายและรันใน VS Code', [
        ('h', 'Step 6 - Predict Live (conditional demo)'),
        ('p', 'ไฟล์: step6_predict_live.py ค่าเริ่มต้นเป็น demo ย้อนหลังปี 2025 ใช้ model ที่ train ถึง 2024 พร้อมอากาศที่เกิดแล้ว ไม่มีการเชื่อม API พยากรณ์สดในชุดนี้'),
        ('table', [['จังหวัด', 'Demo ปี', 'Predicted kg/rai']] +
                  [[NAMES[r.province_code], str(r.year_ce), f'{r.predicted_kg_rai:.2f}'] for r in demo.itertuples()]),
        ('p', 'สำหรับ CSV ใหม่: ใช้ final_model.json ที่ train ถึง 2025 รับเฉพาะปี >2025 และห้าจังหวัดเดิม ต้องมี year_ce, province_code, lag yield และ stage features ทั้ง 7 ตัวตาม contract ปฏิเสธ target/production columns, ค่าหาย/ติดลบผิดหน่วย, key ซ้ำ และลำดับ model schema ไม่ตรง'),
        ('code', '# At repo root, select project Python interpreter\npython tools/durian_model/run_all.py\npython tools/durian_model/step6_predict_live.py \\\n  --input new_stage_features.csv --output new_predictions.csv'),
        ('p', 'กรอก template ตามอายุ 140 วันและฤดูของแต่ละจังหวัดใน prediction_contract.json ถ้าหน้าต่างยังไม่จบ ต้องใช้พยากรณ์ที่มี ณ วันออกผล หรือ scenario ที่ติดป้ายชัด ไม่เติมอากาศปีอนาคตเอง ยังไม่ได้ทดสอบ forecast error แบบ operational'),
        ('code', 'predicted_tonnes = predicted_kg_rai * bearing_rai / 1000'),
        ('p', 'bearing_rai เป็น optional input สำหรับแปลงหน่วยเท่านั้น ไม่ได้เข้า model ต้องเป็นเนื้อที่ให้ผลของปีที่ทำนาย หากยังเป็นค่าคาดการณ์ ผลตันก็เป็นค่าที่ขึ้นกับสมมติฐานนั้น โมเดลไม่มี calibrated prediction intervals'),
        ('p', 'เปิด tools/durian_model/README_TH.md เพื่อดูหน้าที่ทุกไฟล์ เปิดไฟล์ step0 ถึง step6 แล้วกด Run Python File ตามลำดับ หรือใช้ VS Code Tasks ที่เพิ่มไว้ Notebook รวมรันทุกขั้นและเก็บ output จริงไว้แล้ว')])

    vpd_range = uncertainty['stage_ridge'][0]['reduction_percentile_95_pct']
    page('อภิปรายและข้อจำกัด', [
        ('h', 'Discussion and Analysis'),
        ('p', f"ในผลเปรียบเทียบเชิงสำรวจชุดนี้ Ridge ที่ใช้อากาศตามช่วงอายุผลร่วมกับ VPD ให้ MAE ต่ำที่สุดในกลุ่มที่เทียบ แต่ลดจาก Ridge ไม่มี VPD เพียง {gain_without_vpd:.2f}% ช่วง bootstrap บล็อก 3 ปีอยู่ที่ {vpd_range[0]:.2f}% ถึง {vpd_range[1]:.2f}% และคร่อมศูนย์ จึงยังไม่มีหลักฐานชัดว่าการเพิ่ม VPD ช่วยเพิ่มความแม่นยำ ตัวเลขนี้เปรียบเทียบ pipeline ที่ tune แยกกัน ไม่ใช่ผลของ VPD ที่แยกจากการปรับค่าอื่น"),
        ('p', 'Inner fold แรกของ outer test ปี 2017 ใช้ train ปี 2010-2013 เพียง 20 แถว เทียบกับ 14 design columns ข้อมูลทั้ง 5 จังหวัดสัมพันธ์ตามพื้นที่และเวลา Ridge ใช้ L2 ลดความแปรปรวนของ coefficient แต่ไม่รับประกันว่าไม่มี overfitting หรือเลือกอายุผลได้อย่างเสถียร'),
        ('p', 'สิ่งที่ยังไม่มี: อากาศถ่วงด้วย polygon สวนที่ให้ผล วันดอกบานจริงรายปี ข้อมูลการจัดการน้ำ/ปุ๋ย อายุและพันธุ์ต้น แปลงตรวจ pH/NPK และภัยพิบัติที่เชื่อมหน่วยพื้นที่/เวลาได้ จึงยังคำนวณการสังเคราะห์อาหาร ความต้องการน้ำจริง หรือความพร้อมออกผลของต้นจากผลชุดนี้ไม่ได้'),
        ('p', 'แนวทางต่อ: ยืนยัน data finality และ publication vintage; เตรียม bearing-orchard mask; เชื่อมข้อมูลวันเกิดภัยที่ตรวจแล้ว; ทดลอง feature ทีละกลุ่มบน split เดิม; เก็บปีใหม่สำหรับ confirmatory test พร้อม weather forecast vintages ก่อนใช้เป็นคำแนะนำการจัดการสวน'),
        ('h', 'Reproducibility'),
        ('p', f"NumPy {np.__version__}; pandas {pd.__version__}. Input hashes เต็มใน ridge_vpd_audit.json; code และผลแต่ละขั้นอยู่ใน repo ไม่เปลี่ยน input ดิบ โมเดลเป็น JSON ที่เก็บ feature order/scaler อย่างชัดเจน"),
        ('p', 'รายงาน PDF และ Markdown สร้างจากผลเดียวกัน Notebook execute ทุก code cell แยกการประเมินจากโมเดล refit สุดท้าย ตารางผลเปรียบเทียบและ bootstrap เก็บเป็น CSV/JSON เพื่อคำนวณซ้ำโดยไม่ใช้ค่าที่ปัดในรายงาน')])
    page('แหล่งอ้างอิง', [
        ('h', 'References'),
        ('p', 'แหล่งอ้างอิงออนไลน์ [1]-[6] เข้าถึงเมื่อ 9 ตุลาคม 2569 (9 October 2026) วันที่นี้เป็นวันที่ตรวจหน้าเว็บ ไม่ใช่วันดาวน์โหลดไฟล์หรือปีข้อมูล'),
        ('reference', ('[1] สศก. ปริมาณการผลิตทุเรียน', 'https://catalog.oae.go.th/dataset/durian_product')),
        ('reference', ('[2] สศก. ร้อยละปริมาณผลผลิตทุเรียนรายเดือน', 'https://catalog.oae.go.th/dataset/durian_product_month')),
        ('reference', ('[3] NASA POWER Daily API', 'https://power.larc.nasa.gov/docs/services/api/temporal/daily/')),
        ('reference', ('[4] FAO-56 Chapter 3 (VPD approximation)', 'https://www.fao.org/4/X0490E/x0490e07.htm')),
        ('reference', ('[5] Ridge objective, L2 penalty', 'https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html')),
        ('reference', ('[6] Circular block bootstrap', 'https://arch.readthedocs.io/en/latest/bootstrap/generated/arch.bootstrap.CircularBlockBootstrap.html')),
        ('p', 'สำหรับ [1][2] หน้าแคตตาล็อกที่ตรวจในวันที่ข้างต้นยังระบุปีล่าสุด 2567 ส่วนไฟล์ snapshot ที่ใช้ในโครงการระบุถึง 2568 ความต่างนี้ยังคงเป็นข้อจำกัดของหลักฐานต้นทาง ไม่แก้ปีไฟล์ให้ตรงกับหน้าเว็บหรือถือว่าวันเข้าถึงยืนยันสถานะยอดปิดจริง')])
    ordered_comparisons = evaluation['comparison_models']
    if len(ordered_comparisons) != 26 or any(r['n'] != 45 for r in ordered_comparisons):
        raise ValueError('Expected all 26 comparison methods on 45 paired test rows')
    for start in (0, 13):
        page(f'ภาคผนวก: ผลเปรียบเทียบ {start + 1}-{start + 13}', [
            ('h', 'ผลครบ 26 วิธีและชุดตัวแปร'),
            ('p', 'เรียงตาม MAE บน outer test ปี 2017-2025 รวม 45 จังหวัด-ปีเดียวกัน หน่วย กก./ไร่ ตัวเลขเป็น benchmark เดิมที่ตรวจ hash ต้นทางตรงกับ snapshot ของโครงการ การเลือกวิธีจากตารางนี้เป็น exploratory ไม่ใช่ผลยืนยันอิสระ'),
            ('table', [['วิธี / ชุดตัวแปร', 'MAE', 'RMSE']] +
                       [[r['model'], f"{r['mae_kg_rai']:.2f}", f"{r['rmse_kg_rai']:.2f}"]
                        for r in ordered_comparisons[start:start + 13]]),
            ('p', '26 วิธีรวม baseline และหลายชุดตัวแปรของโมเดลเดียวกัน ไม่ใช่ 26 algorithm อิสระ ชื่อ inner_selected เป็นกลยุทธ์เลือกวิธีด้วย inner validation ไม่ใช่โมเดลชนิดใหม่'),
            ('p', 'ไม่ควรใช้ลำดับจากค่าที่ปัดสองตำแหน่งเพื่อตีความความต่างเล็กน้อยว่าแน่นอน ตารางเต็มพร้อม bias และค่าไม่ปัดอยู่ใน ridge_vpd_comparison_models.csv')])
    return pages


def build_report():
    check_snapshot()
    if load_json('workflow_state.json')['completed_steps'] != list(range(7)):
        raise ValueError('Complete steps 0-6 before building the report')
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, Preformatted
    import uharfbuzz  # Thai glyph shaping; fail explicitly rather than produce broken text.
    font = Path('C:/Windows/Fonts/tahoma.ttf')
    bold = Path('C:/Windows/Fonts/tahomabd.ttf')
    english = Path('C:/Windows/Fonts/arial.ttf')
    english_bold = Path('C:/Windows/Fonts/arialbd.ttf')
    code_font = Path('C:/Windows/Fonts/consola.ttf')
    if not all(p.exists() for p in (font, bold, english, english_bold, code_font)):
        raise FileNotFoundError('Tahoma, Arial and Consolas fonts required; change font paths for another platform')
    pdfmetrics.registerFont(TTFont('Thai', str(font), shapable=True))
    pdfmetrics.registerFont(TTFont('ThaiBold', str(bold), shapable=True))
    pdfmetrics.registerFont(TTFont('English', str(english)))
    pdfmetrics.registerFont(TTFont('EnglishBold', str(english_bold)))
    pdfmetrics.registerFont(TTFont('Code', str(code_font)))
    navy, muted = colors.HexColor('#123047'), colors.HexColor('#475569')
    body = ParagraphStyle('body', fontName='Thai', fontSize=10.2, leading=16,
                          textColor=navy, shaping=1, spaceAfter=10)
    heading = ParagraphStyle('heading', parent=body, fontName='ThaiBold', fontSize=13,
                             leading=19, spaceBefore=5, spaceAfter=9)
    title = ParagraphStyle('title', parent=heading, fontSize=19, leading=27, spaceAfter=18)
    cell = ParagraphStyle('cell', parent=body, fontSize=8.7, leading=13, spaceAfter=0)
    code_style = ParagraphStyle('code', fontName='Code', fontSize=9.2, leading=13, textColor=navy,
                                backColor=colors.HexColor('#f1f5f9'), borderPadding=9,
                                spaceBefore=4, spaceAfter=12)
    output = ROOT / 'output/pdf/DURIAN_RIDGE_VPD_REPORT_TH.pdf'
    output.parent.mkdir(parents=True, exist_ok=True)
    story, markdown = [], ['# รายงานการทำนายผลผลิตทุเรียนด้วย Ridge และอากาศตามช่วงอายุผล\n']
    for index, (page_title, items) in enumerate(report_pages()):
        if index:
            story.append(PageBreak())
        story.append(Paragraph(report_text(page_title, bold=True), title))
        markdown.append('\n## ' + page_title + '\n')
        for kind, content in items:
            if kind in ('p', 'h'):
                story.append(Paragraph(report_text(content, bold=kind == 'h'), heading if kind == 'h' else body))
                markdown.append(('### ' if kind == 'h' else '') + content + '\n')
            elif kind == 'reference':
                label, url = content
                # Keep the complete URL visible without running past the page margin.
                visible_url = escape(url)
                if len(url) > 85:
                    parent, filename = url.rsplit('/', 1)
                    visible_url = escape(parent + '/') + '<br/>' + escape(filename)
                story.append(Paragraph(report_text(label) + '<br/>' +
                                       f'<font name="English" size="9.2"><link href="{escape(url, quote=True)}" '
                                       f'color="#1d4ed8"><u>{visible_url}</u></link></font>', body))
                markdown.append(f'[{label}]({url})\n')
            elif kind == 'table':
                # Keep wide feature labels readable without squeezing the numerical columns.
                widths = {2: [260, 220], 3: [280, 100, 100], 4: [170, 125, 100, 85],
                          5: [160, 60, 85, 85, 90]}[len(content[0])]
                rows = [[Paragraph(report_text(v), cell) for v in row] for row in content]
                table = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dceaf1')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f8fa')]),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8), ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LINEBELOW', (0, 0), (-1, 0), .6, colors.HexColor('#94a3b8'))]))
                story.extend([table, Spacer(1, 12)])
                markdown += ['| ' + ' | '.join(map(str, content[0])) + ' |',
                             '| ' + ' | '.join(['---'] * len(content[0])) + ' |']
                markdown += ['| ' + ' | '.join(map(str, row)) + ' |' for row in content[1:]]
                markdown.append('')
            elif kind == 'code':
                story.append(Preformatted(content, code_style))
                markdown.append('```python\n' + content + '\n```\n')
            elif kind == 'image':
                filename, width, height = content
                story.extend([Image(str(OUT / filename), width=width, height=height), Spacer(1, 10)])
                markdown.append(f'![{filename}](../research_data/five_province_history/training/{filename})\n')

    def footer(canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(navy)
        canvas.rect(0, height - 12, width, 12, fill=1, stroke=0)
        canvas.setFont('English', 8)
        canvas.setFillColor(muted)
        canvas.drawString(52, 30, 'DURIAN RESEARCH | Ridge + VPD | Retrospective experiment')
        canvas.drawRightString(width - 52, 30, str(doc.page))
        canvas.restoreState()

    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=52, rightMargin=52,
                            topMargin=42, bottomMargin=52, title='Durian Yield Regression with Stage Weather Features',
                            author='Durian orchard research project')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    (ROOT / 'docs/DURIAN_RIDGE_VPD_REPORT_TH.md').write_text('\n'.join(markdown), encoding='utf-8')
    print('Report:', output, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-notebook', action='store_true', help='Rebuild only report from existing results')
    args = parser.parse_args()
    if not args.skip_notebook:
        build_notebook()
    build_report()
