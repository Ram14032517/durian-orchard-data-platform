"""Export existing rolling Ridge predictions; no fitting or production-model changes."""
import hashlib
import json
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'research_data/five_province_history'
TRAIN = DATA / 'training'
OUT = ROOT / 'research_data/internal_research/yield_level_replay/replay_20261102_v1'


def level(value):
    if value is None or not np.isfinite(value) or value < 0:
        return None
    return 'น้อย' if value <= 1300 else 'ปานกลาง' if value <= 1700 else 'มาก'


def main():
    sources = [DATA/'production_annual.csv', TRAIN/'ridge_vpd_predictions.csv',
               TRAIN/'ridge_vpd_models.json', TRAIN/'ridge_vpd_final_model.json']
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    annual = pd.read_csv(sources[0], dtype={'province_code': str})
    frame = pd.read_csv(sources[1], dtype={'province_code': str})
    models = json.loads(sources[2].read_text(encoding='utf-8'))
    assert len(frame) == 45 and not frame.duplicated(['province_code', 'year_ce']).any()
    assert set(frame.year_ce) == set(range(2017, 2026))
    assert (frame.groupby('year_ce').size() == 5).all()
    for r in frame.itertuples():
        m = models[str(r.year_ce)]
        assert m['train_end'] == r.year_ce-1 and m['train_start'] == 2010
        assert m['age_days'] == r.age_days and m['parameters']['alpha'] == r.alpha
        a = annual[(annual.province_code == r.province_code) & (annual.year_ce == r.year_ce)].iloc[0]
        prior = annual[(annual.province_code == r.province_code) & (annual.year_ce == r.year_ce-1)].iloc[0]
        assert np.isclose(a.production_tonnes*1000/a.bearing_rai, r.actual_kg_rai)
        assert np.isclose(prior.yield_kg_per_rai_calculated, r.previous_year_kg_rai)
    assert np.isfinite(frame[['actual_kg_rai','predicted_kg_rai','previous_year_kg_rai']]).all().all()
    for key, column in [('actual','actual_kg_rai'),('predicted','predicted_kg_rai'),('baseline','previous_year_kg_rai')]:
        frame[key+'_level'] = frame[column].map(level)
    frame['absolute_error_kg_rai'] = abs(frame.predicted_kg_rai-frame.actual_kg_rai)
    frame['absolute_error_pct'] = np.where(frame.actual_kg_rai>0, frame.absolute_error_kg_rai/frame.actual_kg_rai*100, np.nan)
    frame['baseline_absolute_error_pct'] = np.where(frame.actual_kg_rai>0, abs(frame.previous_year_kg_rai-frame.actual_kg_rai)/frame.actual_kg_rai*100, np.nan)
    frame['level_correct'] = frame.predicted_level.eq(frame.actual_level) & frame.predicted_level.notna()
    frame['train_end'] = frame.year_ce-1
    summaries = []
    for year, g in frame.groupby('year_ce'):
        m = models[str(year)]
        summaries.append(dict(year_ce=int(year), model='Ridge + VPD', train_start=m['train_start'],
            train_end=m['train_end'], training_rows=m['training_rows'], age_days=m['age_days'],
            alpha=m['parameters']['alpha'], inner_mae_kg_rai=m['inner_mae_kg_rai'], count=len(g),
            mae_kg_rai=float(g.absolute_error_kg_rai.mean()), mape_pct=float(g.absolute_error_pct.mean()),
            baseline_mape_pct=float(g.baseline_absolute_error_pct.mean()),
            class_correct=int(g.level_correct.sum()), class_accuracy_pct=float(g.level_correct.mean()*100)))
    result = dict(schema_version=1, mode='saved_rolling_retrospective_exploratory',
        source_pdf='415_2564.pdf ตาราง 4 หน้า PDF 19',
        threshold_note='น้อย ≤1,300; ปานกลาง >1,300 ถึง 1,700; มาก >1,700 กก./ไร่ ใช้ค่าทศนิยมไม่ปัดก่อนแบ่งระดับ (ขยายช่วง 1,301–1,700 ในเอกสารให้ต่อเนื่อง)',
        limits='เกณฑ์วิจัยรายแปลงภาคตะวันออก นำมาทดลองระดับจังหวัด ไม่ใช่โมเดล Logistic ของบทความ ไม่ใช่พยากรณ์ก่อนฤดูหรือรายสวน ปีทดสอบเคยใช้พัฒนาและ Historical Publication Vintage ยังไม่ยืนยัน',
        rows=json.loads(frame.to_json(orient='records',force_ascii=False)), years=summaries,
        source_sha256=hashes)
    OUT.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT/'predictions_with_levels.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(summaries).to_csv(OUT/'yearly_metrics.csv',index=False,encoding='utf-8-sig')
    (ROOT/'web/react/src/yieldReplay.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    lines=['# ผลย้อนหลัง Ridge + VPD และระดับผลผลิต','',result['threshold_note'], '',result['limits'],'',
        'APE = |ทำนาย − จริง| ÷ จริง × 100; MAPE = ค่าเฉลี่ย APE ของจังหวัดในปีนั้น ไม่ใช่ Accuracy; ค่า Actual=0 ไม่คำนวณเปอร์เซ็นต์',
        'Baseline = กก./ไร่จริงปีก่อน; ทุกคู่เทียบจังหวัด–ปีเดียวกัน ไม่มีการจูนหรือฝึกใหม่', '',
        '| ปี พ.ศ. | ฝึกถึง | Alpha | อายุผล | MAE กก./ไร่ | MAPE % | Baseline MAPE % | ระดับถูก / 5 |',
        '|---|---|---|---|---|---|---|---|']
    for s in summaries:
        lines.append(f"| {s['year_ce']+543} | {s['train_end']+543} | {s['alpha']} | {s['age_days']} | {s['mae_kg_rai']:.2f} | {s['mape_pct']:.2f} | {s['baseline_mape_pct']:.2f} | {s['class_correct']} |")
    lines += ['', 'เกณฑ์มาจากตารางที่ 4 หน้า PDF 19 ของ 415_2564.pdf ตรวจจากภาพต้นฉบับ: ≤1,300 / 1,301–1,700 / >1,700; ค่าติดลบ/ไม่มีค่าไม่จัดระดับ',
              'ตรวจ code step3_train_model.py: เลือกอายุและ alpha จากสามปี validation ก่อนปีทดสอบ แล้วฝึกถึง Y−1; อากาศเป็น observed ครบหน้าต่าง จึงยังไม่ใช่พยากรณ์ล่วงหน้า',
              'Public HOLD · ไม่เปลี่ยนโมเดล Production หรือ Dataset ต้นทาง']
    (OUT/'README_TH.md').write_text('\n'.join(lines),encoding='utf-8')
    assert hashes == {str(p.relative_to(ROOT)): sha(p) for p in sources}
    (OUT/'manifest.json').write_text(json.dumps(dict(source_sha256=hashes,source_unchanged=True,training_performed=False),indent=2),encoding='utf-8')
    print(pd.DataFrame(summaries)[['year_ce','alpha','age_days','mape_pct','baseline_mape_pct','class_correct']].to_string(index=False))


if __name__ == '__main__':
    main()
