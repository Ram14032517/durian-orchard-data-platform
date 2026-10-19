"""Render the saved issue-date experiment; does not train or replace any model."""
from common import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LABELS = {'lag': 'Previous year', 'median': 'Province median', 'lag_ridge': 'Ridge: lag only',
          'stage_ridge': 'Ridge: stage weather', 'stage_rf': 'Random Forest',
          'stage_catboost': 'CatBoost', 'inner_selected': 'Inner-selected policy'}


def run():
    result = json.loads((OUT / 'issue_date_results.json').read_text(encoding='utf-8'))
    summary = pd.DataFrame(result['overall'])
    figures, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    lines = ['# ผลทดลองพยากรณ์ตามวันออกประมาณการ — 10 ต.ค. 2569', '',
        'ตรวจข้อมูลจริงก่อนปรับระบบ: 5 จังหวัด ปี 2010–2025 จำนวน 80 จังหวัด–ปี '
        'อากาศเป็นรายวัน เป้าหมายคือผลผลิตรวม × 1,000 / พื้นที่ให้ผลผลิต หน่วยกก./ไร่ '
        'ตรวจ hash และนิยาม target จาก snapshot เดิมก่อนรัน ไม่สร้างตัวอย่างรายเดือนซ้ำ target รายปี', '',
        'ปัญหาที่ตรวจพบ: คะแนนโมเดลเดิม MAE 190.87 กก./ไร่ใช้อากาศครบช่วงฤดู '
        'เป็นการประมาณการเมื่อทราบอากาศแล้ว จึงไม่ใช่ค่าความแม่นยำ ณ วันออกพยากรณ์', '',
        '## กติกาการทดลอง', '',
        '- กำหนดวันออกพยากรณ์ก่อนวันแรกของฤดูหลัก 60 วัน และวันแรกของฤดูหลัก '
        'ฤดู 3 เดือนเรียนรู้จากผลผลิตรายเดือนในปีฝึกของแต่ละจังหวัดเท่านั้น',
        '- ตรึงอายุผลสมมติ 140 วันจากโมเดลเดิม เพื่อทดสอบผลของวันออกพยากรณ์และชนิดโมเดล '
        'ยังเป็น proxy ไม่ใช่วันดอกบานจริง หรือข้อมูลหมอนทองแยกพันธุ์',
        '- สมมติว่าอากาศย้อนหลังพร้อมใช้ช้ากว่า 7 วัน อากาศหลังขอบนี้ถูกกันออก '
        'ใช้ค่าปกติวันปฏิทินจาก 10 ปีก่อนของแถวนั้นแทนในฐานะสถานการณ์คาดหมาย '
        'รวม VPD จากค่า VPD รายวันในอดีต ไม่ใช้ค่าจริงอนาคต',
        '- Baselines: ผลผลิตต่อไร่ปีก่อน และ median จังหวัดจากปีฝึก; ablation: Ridge ใช้ lag อย่างเดียว '
        'เทียบ Ridge ที่เพิ่มฟีเจอร์ระยะผล + VPD; เพิ่ม Random Forest และ CatBoost',
        '- Inner validation 3 ปีก่อน test เลือกทั้งตระกูลและพารามิเตอร์ด้วย MAE '
        'outer 2017–2025 กันปี test ออกจากทุกจังหวัด คะแนน outer ใช้รายงานเท่านั้น '
        'scaling และการฝึกโมเดลทำจาก train; ไม่ใช้ outer test สำหรับ early stopping',
        '- 12 configurations ต่อ horizon เมื่อมี CatBoost: 2 baselines, 6 Ridge, '
        '2 Random Forest และ 2 CatBoost; XGBoost ไม่ได้ติดตั้ง จึงยังไม่ได้ทดลอง',
        '- ผลรวมเป็นตันยังไม่คำนวณด้วยพื้นที่ให้ผลจริงของปี test เพราะยังไม่มีวันที่ประกาศ '
        'พื้นที่พร้อมใช้ ณ วันพยากรณ์ สูตรแปลงเมื่อมีพื้นที่ที่ทราบแล้วคือ กก./ไร่ × ไร่ / 1,000', '',
        '## ผลเปรียบเทียบ', '',
        'แต่ละแถวมี 45 จังหวัด–ปีเดียวกัน การดูแถวที่ MAE ต่ำสุดย้อนหลังเป็นผลสำรวจ '
        'สำหรับนโยบายที่เลือกโดยไม่อ่าน test ให้ดู `inner_selected`', '']
    for ax, lead in zip(axes, (60, 0)):
        group = summary[summary.lead_days.eq(lead)].sort_values('mae_kg_rai')
        ax.barh([LABELS[p] for p in group.policy], group.mae_kg_rai,
                color=['#087f8c' if p == 'inner_selected' else '#2563eb' for p in group.policy])
        ax.invert_yaxis()
        ax.set_title(f'{lead} days before main-season start')
        ax.set_xlabel('MAE (kg per rai); exploratory 2017-2025')
        ax.spines[['top', 'right']].set_visible(False)
        lines += [f'### ก่อนเริ่มฤดูหลัก {lead} วัน', '',
                  '| วิธี | MAE กก./ไร่ | RMSE กก./ไร่ | WAPE % | R² |',
                  '|---|---:|---:|---:|---:|']
        for row in group.itertuples():
            lines.append(f'| {LABELS[row.policy]} | {row.mae_kg_rai:.2f} | {row.rmse_kg_rai:.2f} '
                         f'| {row.wape_pct:.2f} | {row.r2:.3f} |')
        u = result['paired_uncertainty'][str(lead)]
        lower, upper = u['reduction_percentile_95_pct']
        lines += ['', f'นโยบาย inner-selected เทียบค่าปีก่อน: MAE เปลี่ยนดีขึ้น '
                  f'{u["mae_reduction_pct"]:.2f}%; descriptive year-block bootstrap 95% '
                  f'{lower:.2f}% ถึง {upper:.2f}% นโยบายแย่กว่า baseline ในปี '
                  + ', '.join(str(y) for y in u['worse_years']), '']
        by_province = [r for r in result['by_province'] if r['lead_days'] == lead and r['policy'] == 'inner_selected']
        lines += ['| รหัสจังหวัด | MAE กก./ไร่ | Bias กก./ไร่ |', '|---|---:|---:|']
        for row in by_province:
            lines.append(f'| {row["province_code"]} | {row["mae_kg_rai"]:.2f} | {row["bias_kg_rai"]:.2f} |')
        lines.append('')
    figures.savefig(OUT / 'issue_date_comparison.png', dpi=150)
    plt.close(figures)
    bands = pd.read_csv(OUT / 'issue_date_intervals.csv')
    width = float((bands.upper_kg_rai - bands.lower_kg_rai).mean())
    lines += ['## การตัดสินจากผลรอบนี้', '',
        'ยังไม่เปลี่ยนโมเดลหลัก: นโยบาย inner-selected ก่อนฤดู 60 วันได้ MAE 233.62 '
        'เทียบ baseline ปีก่อน 215.51 (แย่ลง 8.40%) และวันเริ่มฤดูได้ 248.43 '
        '(แย่ลง 15.27%) การเลือกโมเดลจาก validation เพียง 3 ปีก่อนยังไม่เสถียร '
        'ไม่ใช่หลักฐานว่าตระกูลที่ชนะย้อนหลังจะชนะในปีใหม่', '',
        'CatBoost ก่อนฤดู 60 วันมี MAE 204.85 ต่ำที่สุดในตารางรอบนี้ '
        'แต่หากเลือกไปใช้เพราะอ่านคะแนน outer แล้ว จะเป็นการเลือกจาก test อีกครั้ง '
        'จึงเก็บเป็น candidate สำหรับทดสอบในข้อมูลใหม่ ไม่ประกาศเป็นผู้ชนะพร้อม deploy', '',
        'Ridge ใช้ lag + จังหวัด + ปีอย่างเดียวมี MAE 211.76 ให้ข้อสังเกตว่า '
        'การใส่อากาศคาดหมายไม่ได้ช่วยสม่ำเสมอ ต้องปรับข้อมูลอนาคตและกติกาการเลือกก่อน '
        'ไม่เพิ่มความซับซ้อนจากชื่อโมเดลอย่างเดียว', '',
        'นโยบายก่อนฤดู 60 วันผิดมากที่สุดที่จันทบุรี MAE 307.16 กก./ไร่ '
        'bias −164.77 กก./ไร่ (เฉลี่ยทายต่ำ) ส่วนสุราษฎร์ธานี bias +107.45 '
        '(เฉลี่ยทายสูง) R² รวมเป็นบวก แต่ R² แยกทั้งห้าจังหวัดของนโยบายนี้เป็นลบ '
        'การแยกความต่างระดับจังหวัดได้จึงไม่พอที่จะติดตามความแกว่งรายปีภายในจังหวัด '
        'ยังไม่มีหลักฐานให้อ้างว่า error เกิดจากน้ำใต้ดินหรือภัยแล้งเฉพาะพื้นที่', '']
    lines += ['## ความไม่แน่นอนและข้อจำกัด', '',
        'ทดลองแถบความคลาดเคลื่อนระดับ nominal 80% จากค่าสูงสุดของ absolute error '
        'ทั้ง 5 จังหวัดในแต่ละปี ใช้เฉพาะ 5 ปีก่อนวันทดสอบ การคำนวณไม่ใช้ error ของปีปัจจุบัน '
        'เริ่มรายงานได้ในปี 2022 มี ' + str(result['interval_rows']) + ' แถว '
        f'coverage ที่สังเกต {result["interval_coverage_pct"]:.2f}% ความกว้างเฉลี่ย {width:.2f} กก./ไร่ '
        'coverage สูงต้องพิจารณาร่วมกับแถบที่กว้าง ไม่ใช่คะแนนความแม่นของตัวเลขทำนาย '
        'แถบนี้เป็นการตรวจเบื้องต้น '
        'ยังไม่รับรอง coverage ในอนาคต เพราะข้อมูลรายปีสัมพันธ์กันและสภาพอากาศเปลี่ยน', '',
        'Bootstrap เก็บจังหวัดในปีเดียวกันไว้ด้วยกัน บล็อกปี 3 ปี 20,000 ครั้ง seed 42 '
        'เป็นช่วงเชิงพรรณนาจาก 9 ปีที่เคยสำรวจแล้ว ไม่ใช่ independent holdout ใหม่ '
        'หรือหลักฐานพิสูจน์กลไกผลร่วง', '',
        'ข้อมูลผลผลิตและผลผลิตปีก่อนเป็นฉบับแก้ไขย้อนหลัง ยังไม่มี publication vintages '
        'ค่าฝน/อากาศก่อนวันพยากรณ์มี temporal cutoff แต่ยังไม่จำลองว่าค่า reanalysis '
        'ฉบับนั้นเผยแพร่ในวันนั้นจริงหรือไม่ จึงเรียกผลนี้ว่า issue-date-constrained experiment '
        'ที่มีเงื่อนไข ไม่ใช่ operational hindcast', '',
        'ค่าปกติในส่วนอนาคตทำให้ extrema ถูกเฉลี่ยและไม่เห็นภัยเฉพาะวันที่ยังไม่เกิด '
        'ไม่ได้ใช้ forecast archive จึงยังตอบไม่ได้ว่าพยากรณ์กรมอุตุ/Windy จะช่วยมากเท่าไร '
        'อากาศยังหนึ่งกริดต่อจังหวัด ไม่มีการถ่วงพื้นที่สวนที่ให้ผล หรือ target หมอนทองแยกพันธุ์', '',
        '## สิ่งที่ต้องทำก่อนนำไปแทนโมเดลบนเว็บ', '',
        '1. เก็บวันเผยแพร่ผลผลิตปีก่อนและพื้นที่ให้ผล รวมฉบับปรับปรุง เพื่อเช็คข้อมูลที่รู้จริง ณ วันพยากรณ์',
        '2. เก็บ forecast archive พร้อมเวลาออกพยากรณ์และระยะล่วงหน้า แทนส่วน climatology แล้วทดสอบ cutoff เดิม',
        '3. ประเมินปีที่ยังไม่เคยใช้เลือกวิธี และตรวจ coverage/ความผิดพลาดรายจังหวัด '
        'รวมปีแล้ง/ฝนชุก ก่อนเปลี่ยนโมเดล API',
        '4. รวมพิกัดและพื้นที่สวนที่ให้ผลจริงเมื่อมีหลักฐาน ใช้เซนเซอร์สวนติดตามสวน '
        'โมเดลจังหวัดใช้ให้บริบท ไม่แปลงผลจังหวัดเป็นผลผลิตสวนโดยไม่มี label รายสวน', '',
        'โมเดลหลักและ prediction API เดิมยังอยู่ การทดลองนี้เขียนผลแยกไว้เพื่อให้ตรวจซ้ำได้', '',
        '## โค้ดและผลลัพธ์', '',
        '- [สคริปต์ทดลอง](../tools/durian_model/experiment_issue_date.py)',
        '- [ตารางคะแนน](../research_data/five_province_history/training/issue_date_summary.csv)',
        '- [Predictions](../research_data/five_province_history/training/issue_date_predictions.csv)',
        '- [ค่าพารามิเตอร์ที่เลือก](../research_data/five_province_history/training/issue_date_choices.csv)',
        '- [สัดส่วนอากาศจริง/ค่าปกติแต่ละฟีเจอร์](../research_data/five_province_history/training/issue_date_weather_context.csv)',
        '- [ผลเต็มและข้อจำกัด](../research_data/five_province_history/training/issue_date_results.json)', '',
        '## เอกสารวิธีประเมิน', '',
        '- [scikit-learn: cross-validation และข้อจำกัดการเลือกโมเดล](https://scikit-learn.org/stable/modules/cross_validation.html)',
        '- [CatBoost: validation dataset และการตรวจ overfitting](https://catboost.ai/docs/en/concepts/overfitting-detector)',
        'ตรวจเอกสาร 10 ต.ค. 2569']
    path = ROOT / 'docs/research/modeling/ML_ISSUE_DATE_EXPERIMENT_TH.md'
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(path)


if __name__ == '__main__':
    run()
