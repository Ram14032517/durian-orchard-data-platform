"""Thai Step0-6 report from frozen experiment outputs; never fits/selects models."""
import html,json
import numpy as np
import pandas as pd
from prepare import ROOT,OUT,PREV,P9,NAMES,H,W,V,N,read,sha,js,csv
from train import scores,FAMILIES
E=lambda x:html.escape(str(x))
def table(headers,rows):
 return '<table><thead><tr>'+''.join('<th>'+E(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+E(x)+'</td>' for x in r)+'</tr>' for r in rows)+'</tbody></table>'
def page(title,body,n):
 return f'<section class="page"><div class="eyebrow">SELECTED TOPICS IN AI · INTERNAL RESEARCH · 12 ตุลาคม 2569</div><h1>{title}</h1>{body}<footer>เพิ่ม/ลดผลผลิตทุเรียนระดับจังหวัด · Public HOLD · ไม่มีพยากรณ์ปีใหม่ <span>{n}/10</span></footer></section>'
def confusion_svg(m,title):
 s=[f'<svg viewBox="0 0 370 285" role="img" aria-label="{E(title)}"><text x="185" y="23" text-anchor="middle" class="plot-title">{E(title)}</text><text x="220" y="49" text-anchor="middle">ทำนาย</text><text x="159" y="76" text-anchor="middle">ลดลง</text><text x="267" y="76" text-anchor="middle">เพิ่มขึ้น</text><text x="26" y="164" transform="rotate(-90,26,164)" text-anchor="middle">จริง</text>']
 for i in range(2):
  s.append(f'<text x="92" y="{126+i*87}" text-anchor="end">{["ลดลง","เพิ่มขึ้น"][i]}</text>')
  for j in range(2):
   x=106+j*108;y=88+i*87;c='#d9ede6' if i==j else '#fae8db'
   s.append(f'<rect x="{x}" y="{y}" width="104" height="82" rx="5" fill="{c}"/><text x="{x+52}" y="{y+52}" text-anchor="middle" font-size="31">{m[i][j]}</text>')
 return ''.join(s)+'</svg>'
def timeline(g):
 years=sorted(g.year_ce.unique());s=['<svg viewBox="0 0 760 372" role="img" aria-label="ทิศทางจริงและทำนายแยกจังหวัด"><text x="20" y="24" class="plot-title">จริงเทียบค่าทำนาย · ปี 2020–2025</text>']
 for j,y in enumerate(years):s.append(f'<text x="{233+j*87}" y="56" text-anchor="middle">{y}</text>')
 for i,code in enumerate(NAMES):
  y=92+i*64;s.append(f'<text x="20" y="{y+9}" font-weight="600">{NAMES[code]}</text><text x="145" y="{y}">จริง</text><text x="145" y="{y+25}">ทาย</text>')
  for j,year in enumerate(years):
   r=g[(g.province_code==code)&(g.year_ce==year)].iloc[0];x=233+j*87
   for dy,l in [(0,r.actual_label),(25,r.predicted_label)]:
    text='เพิ่ม' if l==1 else 'ลด';color='#087e71' if l==1 else '#a65820'
    s.append(f'<rect x="{x-32}" y="{y+dy-16}" width="64" height="23" rx="4" fill="{color}"/><text x="{x}" y="{y+dy+1}" text-anchor="middle" fill="white">{text}</text>')
 s.append('<text x="20" y="365">สีช่วยแยกทิศทาง มีข้อความเพิ่ม/ลดกำกับทุกจุด ไม่ใช่กราฟปริมาณกก./ไร่</text></svg>');return ''.join(s)
def yearly_plot(d):
 colors={'candidate':'#087e71','Majority':'#71808b','PreviousKnownDirection':'#ac6922'};names={'candidate':'โมเดลที่ตรึงไว้','Majority':'ทายกลุ่มบ่อย','PreviousKnownDirection':'ทิศทางล่าสุด'}
 s=['<svg viewBox="0 0 760 290"><text x="60" y="24" class="plot-title">Accuracy รายปี · แต่ละปีมีเพียง 4 กรณี</text>']
 for v in [0,.25,.5,.75,1]:
  y=235-v*180;s.append(f'<line x1="62" y1="{y}" x2="706" y2="{y}" stroke="#dbe3e5"/><text x="49" y="{y+5}" text-anchor="end">{v*100:.0f}%</text>')
 for year in range(2020,2026):s.append(f'<text x="{62+(year-2020)*128.8}" y="257" text-anchor="middle">{year}</text>')
 for case in colors:
  g=d[d.case==case].sort_values('year_ce');pts=' '.join(f'{62+(r.year_ce-2020)*128.8:.2f},{235-r.accuracy*180:.2f}' for r in g.itertuples())
  s.append(f'<polyline points="{pts}" stroke="{colors[case]}" stroke-width="3" fill="none"/>')
 for i,c in enumerate(colors):s.append(f'<text x="{70+i*230}" y="283" fill="{colors[c]}">{names[c]}</text>')
 return ''.join(s)+'</svg>'
def main():
 assert not (OUT/'binary_classification_report_th.html').exists()
 sc=pd.read_csv(OUT/'model_comparison.csv');pred=pd.read_csv(OUT/'predictions_vs_actual.csv');byprov=pd.read_csv(OUT/'province_metrics.csv');byyear=pd.read_csv(OUT/'year_metrics.csv');classes=pd.read_csv(OUT/'classification_report.csv');ins=pd.read_csv(OUT/'inner_model_comparison.csv');features=pd.read_csv(OUT/'unified_features.csv');pre=read(OUT/'preflight.json');sel=read(OUT/'selections.json');fit=read(OUT/'fit_cache_audit.json');complete=read(OUT/'training_completion.json')
 def metric(study,case):return sc[(sc.study==study)&(sc.case==case)].iloc[0]
 candidate=metric('full_history','candidate');maj=metric('full_history','Majority');last=metric('full_history','PreviousKnownDirection');nd=metric('ndvi_common','candidate');ndlast=metric('ndvi_common','PreviousKnownDirection');ndmaj=metric('ndvi_common','Majority')
 frozen=read(OUT/'full_history_candidate_before_outer.json');ndfrozen=read(OUT/'ndvi_common_candidate_before_outer.json')
 cp=pred[(pred.study=='full_history')&(pred.case=='candidate')];candclass=scores(cp.actual_label,cp.predicted_label)
 # Paired gains are descriptions of predeclared arms, never a new selector.
 contributions=[]
 for study in ['full_history','ndvi_common']:
  for f in FAMILIES:
   base=metric(study,'H__'+f)
   for group in (['W','V','ALL'] if study=='full_history' else ['W','V','N','ALL']):
    m=metric(study,group+'__'+f)
    a=pred[(pred.study==study)&(pred.case=='H__'+f)][['province_code','year_ce','actual_label','predicted_label']]
    b=pred[(pred.study==study)&(pred.case==group+'__'+f)][['province_code','year_ce','predicted_label']]
    j=a.merge(b,on=['province_code','year_ce'],suffixes=('_H','_added'),validate='one_to_one');h=j.actual_label==j.predicted_label_H;add=j.actual_label==j.predicted_label_added
    contributions.append(dict(study=study,family=f,added_group=group,n=len(j),history_macro_f1=base.macro_f1,added_macro_f1=m.macro_f1,macro_f1_gain=m.macro_f1-base.macro_f1,accuracy_gain=m.accuracy-base.accuracy,paired_wins=int((add&~h).sum()),paired_ties=int((add==h).sum()),paired_losses=int((h&~add).sum())))
 cont=pd.DataFrame(contributions);csv(OUT/'feature_group_contributions.csv',cont)
 pr=byprov[(byprov.study=='full_history')&byprov.case.isin(['candidate','PreviousKnownDirection'])].pivot(index='province_code',columns='case',values='macro_f1')
 yr=byyear[(byyear.study=='full_history')&byyear.case.isin(['candidate','PreviousKnownDirection'])].pivot(index='year_ce',columns='case',values='accuracy')
 province_wins=int((pr.candidate>pr.PreviousKnownDirection+1e-12).sum());year_wins=int((yr.candidate>yr.PreviousKnownDirection+1e-12).sum())
 beats_both=bool(candidate.macro_f1>max(maj.macro_f1,last.macro_f1) and candidate.accuracy>max(maj.accuracy,last.accuracy))
 gate=bool(beats_both and province_wins>=3 and year_wins>=4)
 js(OUT/'conclusion.json',{'candidate_family':frozen['candidate_family'],'candidate_group':frozen['candidate_group'],'candidate_score':candidate.to_dict(),'majority_score':maj.to_dict(),'previous_known_direction_score':last.to_dict(),'class_metrics':candclass,'beats_both_baselines_aggregate':beats_both,'consistency_gate':{'passed':gate,'province_F1_wins':province_wins,'year_accuracy_wins':year_wins,'criterion':'>=3 of4 provinces, >=4 of6 years vs last direction; aggregate Accuracy and MacroF1 beat both baselines'},'ndvi_candidate_family':ndfrozen['candidate_family'],'ndvi_candidate_group':ndfrozen['candidate_group'],'ndvi_candidate_score':nd.to_dict(),'ndvi_baselines':[ndmaj.to_dict(),ndlast.to_dict()],'exact_equal_excluded':pre['equal_rows'],'operational_readiness':'not_ready; test years already used, publication vintages unverified, no prospective validation','forecast_2026':False,'no_outer_reselection':True,'public_release':'HOLD','historical_pit':'not_certified'})
 label_counts=features.label.value_counts();outer_counts=cp.actual_label.value_counts()
 weather_wins=int(((cont.study=='full_history')&(cont.added_group=='W')&(cont.macro_f1_gain>1e-12)).sum());vpd_wins=int(((cont.study=='full_history')&(cont.added_group=='V')&(cont.macro_f1_gain>1e-12)).sum());ndvi_wins=int(((cont.study=='ndvi_common')&(cont.added_group=='N')&(cont.macro_f1_gain>1e-12)).sum())
 verdict='ดีกว่าสอง Baseline ในคะแนนรวม' if beats_both else 'ยังไม่ดีกว่าสอง Baseline พร้อมกันในคะแนนรวม'
 bodies=[]
 bodies.append(page('Step 0 · เปลี่ยนคำถามเป็น “เพิ่มหรือลด”',f'''
 <p class="lead">ทำนายทิศทางผลผลิตต่อไร่ระดับจังหวัด โดยเทียบปีเป้าหมายกับปีก่อนจากค่า OAE ที่รายงานจริง ไม่มีการใช้ผลผลิตรายอำเภอที่ประมาณขึ้นหรือข้อมูลผลผลิตรายสวน</p>
 <div class="callout"><h2>ผลสรุปของชุดหลัก</h2><p>{E(frozen['candidate_family'])} ใช้ข้อมูลผลผลิตย้อนหลัง (H) เลือกจาก Validation ก่อนผลทดสอบใหม่ ทายถูก <strong>{candidate.correct}/{candidate.n} กรณี ({candidate.accuracy*100:.1f}%)</strong> และ Macro F1 = <strong>{candidate.macro_f1:.3f}</strong></p><p>{verdict} แต่ยังไม่ใช่หลักฐานเพียงพอสำหรับออกพยากรณ์ปีใหม่จริง</p></div>
 {table(['วิธี','ถูก/ทั้งหมด','Accuracy','Macro F1','Balanced Acc.'],[[frozen['candidate_family']+' H',f'{candidate.correct}/{candidate.n}',f'{candidate.accuracy*100:.1f}%',f'{candidate.macro_f1:.3f}',f'{candidate.balanced_accuracy:.3f}'],['ทายกลุ่มที่พบบ่อย',f'{maj.correct}/{maj.n}',f'{maj.accuracy*100:.1f}%',f'{maj.macro_f1:.3f}',f'{maj.balanced_accuracy:.3f}'],['ทายทิศทางล่าสุดที่ทราบ',f'{last.correct}/{last.n}',f'{last.accuracy*100:.1f}%',f'{last.macro_f1:.3f}',f'{last.balanced_accuracy:.3f}']])}
 <h2>สิ่งที่เปลี่ยนและสิ่งที่ไม่เปลี่ยน</h2><p>Label เพิ่มขึ้น = 1 เมื่อ Yield ปี Y มากกว่าปี Y−1 และลดลง = 0 เมื่อน้อยกว่า ถ้าเท่ากันพอดีจะแยกออก พบเท่ากัน <strong>{pre['equal_rows']} กรณี</strong> ใน 76 คู่ปีที่ตรวจได้ ไม่ใช้เกณฑ์ ±5% ของงาน 3 กลุ่มอีกต่อไป</p>
 <p>ใช้ข้อมูลและ Environment เดิมทั้งหมด ไม่ดาวน์โหลด NDVI/VPD ไม่แตะ Production ไม่ออกพยากรณ์ปี 2569 ข้อมูล GIS ดัดแปลงยังคง Public HOLD</p>
 <p class="note">ปี 2020–2025 ถูกเปิดดูในการพัฒนามาก่อน ผลนี้เป็นการทดลองย้อนหลังเชิงสำรวจ ไม่ใช่ชุดทดสอบอิสระและไม่รับรอง Historical Point-in-Time</p>''',1))
 soil=pd.read_csv(PREV/'soil_gis_context.csv')
 bodies.append(page('Step 1 · ข้อมูลจริงที่มีและขอบเขต',f'''
 {table(['ข้อมูล','ช่วง/ความละเอียด','ใช้ในงานนี้อย่างไร'],[['OAE Yield','4 จังหวัด × 2006–2025 = 80 แถว','ค่า กก./ไร่ ที่รายงานระดับจังหวัด'],['NASA POWER','20 ปี; spatial weather profile','อุณหภูมิ ฝน ความชื้นของปีก่อน'],['ERA5-Land ผ่าน Open-Meteo','2006–2025; 8 จุด / 7 เซลล์กริดไม่ซ้ำ','อุณหภูมิ จุดน้ำค้าง และ VPD'],['NDVI Landsat/Sentinel','2 จุดตัวอย่างต่อจังหวัด','ใช้ Landsat 8 แยกชุดปีร่วม'],['LDD A403 และดิน','แผนที่ปีต่างกัน; ดิน 2561','ประกอบบริบทเท่านั้น ไม่เข้าโมเดล']])}
 <h2>4 จังหวัดที่นำมาฝึก</h2>
 {table(['จังหวัด','OAE / อากาศ','ปี A403 (พ.ศ.)','Pure A403 (ไร่)'],[[NAMES[int(r.province_code)],'2006–2025',r.landuse_map_year_be,f'{r.pure_A403_total_rai:,.1f}'] for r in soil.itertuples()])}
 <p>76 คู่จังหวัด–ปีมีผลผลิตปีก่อนสำหรับสร้างทิศทาง ตารางโมเดลมี 64 แถวปี 2010–2025 เพราะ Feature แนวโน้มต้องย้อนหลังถึง Y−4 ปี 2006 ไม่มีค่าปีก่อน และ 2007–2009 ใช้ไม่ได้ครบตามนิยาม Feature เดียวกัน</p>
 <p>NASA POWER เป็นข้อมูลกริด/แบบจำลองบนจุดตัวอย่าง ไม่ใช่สถานีตรวจวัดในทุกสวน ERA5 ที่ดึงมาให้บริการมีกริด 0.1° ประมาณ 11 กม. จึงแยกสภาพจุลภูมิอากาศรายสวนไม่ได้ NDVI มีเพียง 2 พิกเซลตัวอย่างต่อจังหวัด ไม่ใช่ค่าเฉลี่ยทั้งพื้นที่ทุเรียน</p>
 <p class="note">แผนที่ A403 ปีหลังไม่พิสูจน์ว่าพื้นที่ปลูกเหมือนเดิมทุกปีย้อนหลัง A403 เป็นหน่วยการใช้ที่ดิน ไม่ใช่สวนรายเจ้าของที่ยืนยันแล้ว และไม่มีผลผลิตรายสวนให้เป็น Target</p>''',2))
 bodies.append(page('Step 2 · ประเภทข้อมูลและการเตรียม',f'''
 {table(['ประเภท','ตัวอย่าง','วิธีเตรียม'],[['ตัวเลขต่อเนื่อง','ผลผลิต กก./ไร่; อุณหภูมิ °C','รักษาหน่วยเดิม ตรวจค่าที่ขาด'],['สัดส่วน/เปอร์เซ็นต์','ความชื้น %; VPD สูง 0–1','ไม่ปะปนเปอร์เซ็นต์กับสัดส่วน'],['หมวดหมู่','รหัสจังหวัด; Label 0/1','จังหวัด One-hot เฉพาะ Training'],['เวลา','ปีข้อมูล; Issue Date','แบ่งตามปี ไม่สุ่มจังหวัด–ปี'],['ค่าที่ขาด','NDVI บางเดือน/บางปี','ไม่สร้างภาพหรือเติมเดือนที่ขาด']])}
 <h2>ขั้นตอนก่อนฝึก</h2><ol><li>ตรวจ Hash ของข้อมูลต้นทางและรุ่นงานเดิม สร้าง Namespace ใหม่ที่ไม่เขียนทับ</li><li>เทียบค่า Yield ปี Y และ Y−1 กับ Phase 9D และคำนวณ Label ใหม่จากการมากกว่า/น้อยกว่าจริง ไม่แปลง Label 3 กลุ่มเดิม</li><li>ตรวจรหัสจังหวัด–ปีซ้ำ หน่วย วันที่ และความครบของ Features ก่อนกำหนดปีร่วม</li><li>สร้างค่าอากาศผิดปกติจากค่าเฉลี่ยจังหวัดใน Training เท่านั้น</li><li>ตัวแปลงหมวดหมู่ ค่าเฉลี่ย/ค่ามัธยฐานสำหรับเติมข้อมูล และการปรับสเกลเรียนรู้จาก Training เท่านั้น</li></ol>
 {table(['จำนวน Label ในตารางโมเดล','ลดลง = 0','เพิ่มขึ้น = 1'],[['รวม 64 แถว',int(label_counts.get(0,0)),int(label_counts.get(1,0))],['Outer หลัก 24 แถว',int(outer_counts.get(0,0)),int(outer_counts.get(1,0))]])}
 <p>จัดการ Class Imbalance ด้วยน้ำหนักปกติเทียบกับน้ำหนักผกผันความถี่ของ Class ที่คำนวณจาก Training ของแต่ละ Fold เท่านั้น ไม่ใช้ SMOTE ไม่เพิ่มจังหวัด–ปีสังเคราะห์ และไม่ปรับ Threshold หลังดู Test</p>
 <p class="note">ข้อมูลต้นทางปัดผลผลิตเป็นหน่วยที่รายงาน การเพิ่ม/ลดเล็กมากอาจไม่สะท้อนการเปลี่ยนแปลงสำคัญทางเกษตร แต่รอบนี้ใช้เกณฑ์สองกลุ่มตามโจทย์โดยไม่ปรับเส้นแบ่ง</p>''',3))
 bodies.append(page('Step 3 · Features และข้อมูลตามเวลา',f'''
 {table(['กลุ่ม','Inputs','ช่วงข้อมูลที่ใช้'],[['H ผลผลิตย้อนหลัง','Yield Y−2, ทิศทาง Y−2/Y−3, แนวโน้มถึง Y−4, จังหวัด, ปี','OAE ย้อนหลังอย่างน้อย 2 ปี'],['W อากาศ (13 ตัว)','T/Rain/RH รายปีและ ต.ค.–ธ.ค.; ความแปรปรวน/Anomaly; ดัชนีฝน','ม.ค.–ธ.ค. Y−1 และ ต.ค.–ธ.ค. Y−1'],['V VPD (8 ตัว)','เฉลี่ย, p95, ชั่วโมงสูง, ช่วงต่อเนื่อง, ช่วงต้นปี/กลางคืน, Anomaly','รายชั่วโมง Y−1; ม.ค.–เม.ย. หรือ ต.ค.–ธ.ค.'],['N NDVI (4 ตัว)','Median, variability, slope, anomaly','Landsat 8 ปี Y−1 ≥6 เดือนจริง'],['ดิน/GIS','ปีแผนที่, องค์ประกอบหน่วยดิน','บริบทเท่านั้น ไม่ใช้ฝึก']])}
 <p>ทุกแขนมี H เหมือนกัน: W = H+Weather, V = H+VPD, ALL ชุดหลัก = H+Weather+VPD ส่วน ALL ชุด NDVI เพิ่ม NDVI ด้วย N = H+NDVI ไม่ได้เปลี่ยนข้อมูลผลผลิตย้อนหลังระหว่างแขน</p>
 <h2>ไม่ใช้ข้อมูลหลังวันออกพยากรณ์จำลอง</h2><p>ตรึงวันจำลอง <strong>1 มีนาคม ปี Y</strong> ตามงานเดิม ใช้ข้อมูลอากาศสิ้นสุด <strong>31 ธันวาคม Y−1</strong> ไม่ใช้อากาศปี Y ผลผลิต Y−1 ใช้สร้าง Label ย้อนหลังเท่านั้น ไม่เป็น Feature หรือเป็นตัวหารแปลงค่าทำนาย</p>
 <p>ใช้ Yield Y−2 เป็นข้อมูลล่าสุดภายใต้กฎเว้นหนึ่งปี เพราะวันเผยแพร่ OAE Y−1 ยังพิสูจน์ไม่ได้ กฎนี้ลดการใช้ข้อมูลใกล้เหตุการณ์ แต่ไม่ได้พิสูจน์ว่าทุกรุ่นข้อมูลมีอยู่จริง ณ วันนั้น ข้อมูล OAE ฉบับปรับปรุงและ Reanalysis ยังเป็นข้อจำกัด</p>
 <p>ค่า Anomaly คือค่าปีก่อนลบค่าเฉลี่ยเฉพาะ Training ของจังหวัด ฝนใช้เปอร์เซ็นต์ต่างจากค่าเฉลี่ย ฝนแห้งนับเป็น <strong>เดือน</strong> ไม่ใช่วัน เพราะ Cache NASA เป็นรายเดือน ส่วนเกณฑ์ VPD&gt;1.5 kPa เป็นดัชนีทดลอง ไม่ใช่เกณฑ์ความเสียหายที่ยืนยันสำหรับทุเรียน</p>
 <p class="note">Landsat 7 / Landsat 8 / Sentinel-2 ไม่ถูกผสมโดยถือว่าเหมือนกัน ชุด NDVI ใช้ L8 เท่านั้น และปีข้อมูลไม่ครบถูกระบุใน Coverage ไม่เติมค่าด้วยอนาคต</p>''',4))
 foldrows=[]
 for s in sel:
  if s['study']!='full_history':continue
  foldrows.append([s['outer_year'],','.join(map(str,s['inner_years'])),s['outer_year']-2,s['choices']['candidate']['id'].replace('H__',''),f'{s["candidate_inner"]["macro_f1"]:.3f}'])
 bodies.append(page('Step 4 · แบ่งเวลาและเลือกโมเดล',f'''
 <p>ใช้ Expanding Validation: เพิ่มข้อมูลฝึกเมื่อเวลาเดินหน้า ทุกจังหวัดของปีเดียวกันอยู่ฝั่งเดียวกัน กฎข้อมูล Train และ Labels ของ Inner สิ้นสุดอย่างน้อย 2 ปีก่อนปีที่ประเมิน ไม่ใช้ Outer Targets ในการเลือก Features หรือน้ำหนัก</p>
 {table(['Outer ปี','Inner ปีที่ประเมิน','Train สูงสุดสำหรับ Outer','RF preset','Inner Macro F1'],foldrows)}
 <p>Inner ใช้ล่าสุดไม่เกิน 3 ปีที่ผ่าน Coverage และมีข้อมูลฝึกอย่างน้อย 8 แถว ตระกูล/กลุ่มข้อมูล Candidate ตรึงจาก Inner แรกก่อนดูคะแนน Outer ปี 2020 จากนั้นแต่ละปีเลือกเฉพาะ Preset ภายในตระกูลเดิมด้วย Inner ของตัวเอง</p>
 {table(['โมเดล','ขอบเขตที่กำหนดก่อนดู Test'],[['Logistic Regression','C=0.1; น้ำหนักปกติ/สมดุล'],['Random Forest','150 ต้น; depth2; leaf≥3; น้ำหนัก 2 แบบ'],['XGBoost / LightGBM / CatBoost','160 ต้น; depth2; learning rate0.05; regularization10; น้ำหนัก 2 แบบ'],['Regression → Binary','Ridge α10/100; CatBoost Regression depth2/3'],['ทุกแบบ','Seed42; CPU2; ไม่ใช้ GPU; ไม่มีการไล่คะแนน Test']])}
 <p>Regression ทำนายเปอร์เซ็นต์เปลี่ยนแปลงโดยตรงแล้วใช้เครื่องหมายบวก/ลบ Threshold 0 ถ้าทำนาย 0 พอดีให้ใช้ Class ที่พบบ่อยเฉพาะ Training เช่นเดียวกับ Baseline ทิศทางล่าสุดเมื่ออดีตเท่ากัน ไม่แอบใช้ Yield Y−1 ที่ยังไม่มีหลักฐานทันวันออกพยากรณ์</p>
 <p class="note">ระบบ adaptive_nested ที่เลือกตระกูลใหม่จาก Inner แต่ละปีรายงานแยกใน CSV ไม่ใช้คะแนน Outer ของระบบนี้เปลี่ยน Candidate หลัก ข้อมูลปีเก่าใน Inner มีการนำกลับมาใช้หลาย Context ไม่ใช่ตัวอย่างอิสระเพิ่มขึ้น</p>''',5))
 rows=[]
 for f in FAMILIES:
  h=metric('full_history','H__'+f);a=metric('full_history','ALL__'+f);w=metric('full_history','W__'+f);v=metric('full_history','V__'+f)
  rows.append([f,f'{h.accuracy*100:.1f}%',f'{h.macro_f1:.3f}',f'{w.macro_f1:.3f}',f'{v.macro_f1:.3f}',f'{a.macro_f1:.3f}'])
 bodies.append(page('Step 5 · เปรียบเทียบโมเดลบน 24 กรณี',f'''
 <p>ผล Outer เชิงสำรวจปี 2020–2025 ทุกวิธีใช้ 4 จังหวัดและ 24 Keys เดียวกัน Hyperparameters ของแต่ละตระกูล/กลุ่มข้อมูลเลือกจาก Inner ของ Fold นั้น ไม่เลือกผู้ชนะจากคอลัมน์คะแนน Test</p>
 {table(['โมเดล','H Acc.','H F1','W F1','V F1','ALL F1'],rows)}
 <p>H = ผลผลิตย้อนหลัง; W = H+Weather; V = H+VPD; ALL = H+Weather+VPD <strong>ไม่มี NDVI</strong> ทุกกลุ่มมีจังหวัดและปีเหมือนกัน ตารางคะแนนเต็มอยู่ใน model_comparison.csv</p>
 <h2>โมเดลที่เลือกก่อนผลทดสอบ</h2><p>{frozen['candidate_family']} H มี Inner แรก Macro F1 {frozen['inner_score']['macro_f1']:.3f} จาก {frozen['inner_score']['validation_rows']} กรณี ผล Outer = {candidate.macro_f1:.3f} ไม่อ้างว่าเป็นโมเดลดีที่สุดสำหรับอนาคต และไม่ย้ายไปโมเดลอื่นแม้บางช่องคะแนน Test สูงกว่า</p>
 <h2>เทียบวิธีพื้นฐาน</h2><p>Majority ทาย Class ที่บ่อยที่สุดใน Training ส่วน Previous Known Direction ใช้ Yield Y−2 เทียบ Y−3 Candidate {verdict} แม้ CatBoost H และ RF+Weather ทายถูก 16/24 (66.7%, F1 0.644) ก็ไม่เปลี่ยน Candidate จากคะแนน Outer ระบบ adaptive_nested ที่เลือกจาก Inner ทุกปีทายถูก 11/24 (F1 0.457) รายงานแยก ไม่ใช่ผู้ชนะที่เลือกใหม่</p>
 <div class="callout"><p><strong>Accuracy</strong> = จำนวนทายถูก / ทั้งหมด <strong>Balanced Accuracy</strong> = ค่าเฉลี่ย Recall ของ Class จริงที่พบ <strong>Macro F1</strong> = ค่าเฉลี่ย F1 สอง Class เพื่อไม่ให้ Class ที่พบมากกลบอีก Class</p></div>
 <p class="note">ไม่เปรียบเทียบ F1 สองกลุ่มนี้ตรง ๆ กับ F1 สามกลุ่มเดิมหรือ MAE ของ Ridge งานก่อน เพราะคำถาม Target และหน่วยคะแนนต่างกัน</p>''',6))
 cc=classes[(classes.study=='full_history')&(classes.case=='candidate')]
 province_rows=[]
 for code in NAMES:
  a=byprov[(byprov.study=='full_history')&(byprov.case=='candidate')&(byprov.province_code==code)].iloc[0]
  b=byprov[(byprov.study=='full_history')&(byprov.case=='PreviousKnownDirection')&(byprov.province_code==code)].iloc[0]
  province_rows.append([NAMES[code],f'{a.correct}/{a.n}',f'{a.accuracy*100:.1f}%',f'{a.macro_f1:.3f}',f'{b.macro_f1:.3f}'])
 bodies.append(page('Step 5 · เพิ่ม/ลดที่ทายถูก และแต่ละจังหวัด',f'''
 <div class="two">{confusion_svg(candclass['confusion_matrix'],frozen['candidate_family']+' H')}{confusion_svg(scores(pred[(pred.study=='full_history')&(pred.case=='PreviousKnownDirection')].actual_label,pred[(pred.study=='full_history')&(pred.case=='PreviousKnownDirection')].predicted_label)['confusion_matrix'],'Baseline ทิศทางล่าสุด')}</div>
 {table(['Class','Precision','Recall','F1','จริงกี่กรณี'],[['เพิ่มขึ้น' if r.class_id==1 else 'ลดลง',f'{r.precision:.3f}',f'{r.recall:.3f}',f'{r.f1:.3f}',r.support] for r in cc.itertuples()])}
 <p>Recall ตอบว่าจากปีที่เพิ่มจริง/ลดจริง ทายทิศทางนั้นได้กี่ส่วน Precision ตอบว่าจากที่โมเดลทายเพิ่ม/ลด มีจริงเท่าไร เมื่อตารางช่องบนขวาหรือล่างซ้ายมาก แปลว่าทายทิศทางผิด ไม่ได้บอกขนาดความผิดพลาดของ Yield</p>
 {table(['จังหวัด','ทายถูก','Accuracy','Candidate F1','ทิศทางล่าสุด F1'],province_rows)}
 <p class="note">จังหวัดละ 6 ปีเท่านั้น และสภาพภูมิอากาศ/ตลาดในปีเดียวกันอาจสัมพันธ์ข้ามจังหวัด จึงไม่ถือว่า 24 แถวเป็น 24 ตัวอย่างอิสระสำหรับอ้างนัยสำคัญทางสถิติ</p>''',7))
 bodies.append(page('Step 5 · จริงเทียบค่าทำนายและความเสถียร',f'''
 {timeline(cp)}{yearly_plot(byyear[(byyear.study=='full_history')&byyear.case.isin(['candidate','Majority','PreviousKnownDirection'])])}
 <p>Candidate มี Accuracy รายปีดีกว่า Baseline ทิศทางล่าสุด {year_wins}/6 ปี และ Macro F1 รายจังหวัดดีกว่า {province_wins}/4 จังหวัด เกณฑ์ความสม่ำเสมอที่ตรึงก่อนฝึก {"ผ่านเฉพาะเชิงพรรณนา" if gate else "ยังไม่ผ่าน"} แต่ไม่ใช่ใบรับรองการใช้งานจริง</p>
 <p class="note">ปีที่มีจริงเพียง Class เดียว เช่น 2025 Macro F1 แบบตรึงสอง Class อาจมีเพดาน 0.5 แม้ทายถูกทั้งหมด ส่วน Accuracy และ Balanced Accuracy อาจเท่ากับ 1 อ่านจำนวนกรณีและ Class Support ประกอบ ไม่ปรับนิยามคะแนนตามปีเพื่อให้ดูดีขึ้น</p>''',8))
 gains=[]
 for f in FAMILIES:
  gg=cont[(cont.study=='full_history')&(cont.family==f)].set_index('added_group');gn=cont[(cont.study=='ndvi_common')&(cont.family==f)].set_index('added_group')
  gains.append([f,f'{gg.loc["W","macro_f1_gain"]:+.3f}',f'{gg.loc["V","macro_f1_gain"]:+.3f}',f'{gg.loc["ALL","macro_f1_gain"]:+.3f}',f'{gn.loc["N","macro_f1_gain"]:+.3f}'])
 importance=pd.read_csv(OUT/'feature_importance.csv');pi=importance[importance.study=='full_history'].groupby('group').inner_macro_f1_drop_mean.mean()
 bodies.append(page('Step 6 · Weather / VPD / NDVI ช่วยไหม',f'''
 <p>ตัวเลขด้านล่างคือ Macro F1 ของกลุ่มที่เพิ่มข้อมูล − Macro F1 ของ H ในตระกูลเดียวกัน ค่าบวก = ดีขึ้น กลุ่ม Main เทียบปี 2020–2025 ส่วน NDVI เทียบปี 2022–2025 ภายในชุดร่วมเท่านั้น ไม่เทียบคะแนนข้ามชุด</p>
 {table(['ตระกูล','+Weather','+VPD','+Weather+VPD','+NDVI (ชุดร่วม)'],gains)}
 <p>Weather ดีขึ้น {weather_wins}/7 ตระกูล VPD ดีขึ้น {vpd_wins}/7 ตระกูล และ NDVI ดีขึ้น {ndvi_wins}/7 ตระกูล เป็นสัญญาณบางโมเดล ไม่ใช่ผลที่สม่ำเสมอหรือหลักฐานเหตุและผล การปรับ Preset แยกกลุ่มทำให้ผลต่างรวมทั้งข้อมูลที่เพิ่มและการเลือกน้ำหนัก ไม่ใช่การแยกผล Weather อย่างเดียว</p>
 <h2>ชุด NDVI: ผลบนปีร่วม 16 กรณี</h2>
 {table(['วิธี','ถูก/ทั้งหมด','Accuracy','Macro F1'],[[ndfrozen['candidate_family']+' '+ndfrozen['candidate_group'],f'{nd.correct}/{nd.n}',f'{nd.accuracy*100:.1f}%',f'{nd.macro_f1:.3f}'],['ทายทิศทางล่าสุด',f'{ndlast.correct}/{ndlast.n}',f'{ndlast.accuracy*100:.1f}%',f'{ndlast.macro_f1:.3f}'],['ทายกลุ่มบ่อย',f'{ndmaj.correct}/{ndmaj.n}',f'{ndmaj.accuracy*100:.1f}%',f'{ndmaj.macro_f1:.3f}']])}
 <p>Candidate NDVI ตรึงจาก Inner เพียง 8 กรณี ปี 2019/2020 (F1 {ndfrozen['inner_score']['macro_f1']:.3f}) จึงมีโอกาสเลือกจากความบังเอิญสูง ชุดฝึกมีปี 2015–2017, 2019–2025 โดย 2018 ไม่ผ่าน NDVI ครบ 4 จังหวัด ไม่เติมข้อมูลอนาคต</p>
 <h2>Feature Importance ที่รายงานได้</h2><p>ใช้การสลับกลุ่มค่าเฉพาะ Inner ของ Candidate แล้วดู F1 ที่ลดลง ไม่ฝึกใหม่ ไม่ใช้เลือก Features จาก Outer ค่าเฉลี่ย: {E(', '.join(f'{k} {v:+.3f}' for k,v in pi.items()))} กลุ่มที่ไม่มีใน Candidate ไม่มีค่า Importance ให้ตีความเป็นศูนย์ การสลับทำเฉพาะปีเดียวกัน 4 จังหวัดและมีความสัมพันธ์ระหว่างตัวแปร จึงเป็นคำอธิบายการพึ่งพาโมเดล ไม่ใช่เหตุและผล</p>''',9))
 trainf1=[a['training_macro_f1'] for a in fit if a.get('training_macro_f1') is not None and a['role']=='outer' and a['study']=='full_history' and a['config_id'].startswith(frozen['candidate_group']+'__'+frozen['candidate_family']+'__')]
 bodies.append(page('Step 6 · ข้อสรุปและความพร้อมปีใหม่',f'''
 <h2>ข้อสรุปที่ข้อมูลรองรับ</h2><ol><li>Candidate หลักคือ {frozen['candidate_family']} H ตาม Validation ที่ตรึงไว้ ทายเพิ่มถูก {candclass['confusion_matrix'][1][1]}/{candclass['support'][1]} และลดถูก {candclass['confusion_matrix'][0][0]}/{candclass['support'][0]} รวม {candidate.correct}/{candidate.n}</li><li>คะแนนอากาศ/NDVI/VPD เปลี่ยนตามโมเดลและช่วงเวลา ยังไม่ควรประกาศว่าเพิ่มข้อมูลแล้วทำให้ระบบแม่นขึ้นอย่างน่าเชื่อถือทุกกรณี</li><li>คะแนน Train F1 ของ Candidate อยู่ช่วง {min(trainf1):.3f}–{max(trainf1):.3f} เทียบ Outer {candidate.macro_f1:.3f} อ่านร่วมกับ Inner ที่ลดลงตามปี โมเดลจับข้อมูลฝึกได้ไม่เท่ากับพร้อมใช้งานจริง</li></ol>
 <h2>ยังไม่พร้อมพยากรณ์ปี 2569/ปีใหม่จริง</h2><p>ไม่ได้สร้าง Forecast ในงานนี้ วันที่ 1 มีนาคม 2569 ตามกฎจำลองผ่านไปแล้ว จึงห้ามนำผลที่คำนวณวันนี้มาเรียกพยากรณ์ล่วงหน้าของวันนั้น ต้องกำหนดวันออกจริงและตรวจ Inputs ที่เผยแพร่ทันวันนั้นก่อน รวมทั้งรุ่น OAE, NASA, NDVI และ ERA5 ที่ใช้งานจริง</p>
 <p>Historical Publication Vintage ยังไม่ยืนยัน กฎเว้นปีไม่ทดแทนหลักฐานเวลาเผยแพร่ จุดตัวอย่างอากาศ/NDVI บางชุดผูกกับแผนที่ A403 รุ่นหลัง เป็นการวิเคราะห์ย้อนหลังบนจุดคงที่ ไม่พิสูจน์ว่าเลือกจุดหรือพื้นที่ปลูกชุดนี้ได้ในอดีต ปี 2020–2025 ถูกใช้พัฒนามาแล้ว ต้องมีปีอนาคตที่ไม่เคยใช้ตัดสินใจพัฒนาเพื่อประเมินจริง</p>
 <h2>แหล่งข้อมูลและวิธีทำซ้ำ</h2><p>Label และ Weather Profile จาก Phase 9D; Raw OAE Workbook เดิม; NDVI/VPD และ hourly lineage จาก integrated_ndvi_vpd และ optimized_classification รุ่นเดิม ตารางผลใหม่ พร้อม Code/Source/Input Hashes และค่าที่ Feature Builder ใช้จริงในแต่ละ Fold อยู่ในโฟลเดอร์รายงานเดียวกัน ดู README_TH.md และ source_manifest.json</p>
 <p>ฝึกจริง {complete['counts']['fits']:,} Fits และใช้ Cache ของ Inner Context เดิม {complete['counts']['reuses']:,} ครั้ง ใช้เวลา {complete['elapsed_seconds']/60:.1f} นาที มี Pretraining Tests {read(OUT/'pretraining_tests.json')['passed']} ข้อ ไม่รัน Repository Tests ที่ไม่เกี่ยวข้อง และไม่ปรับ Features/ตระกูล/Threshold หลังดู Outer</p>
 <p class="note">ไม่อ้างผลเชิงสาเหตุ ไม่ทำนายสวนรายเจ้าของ ไม่กระจาย Yield จังหวัดลง Polygon ไม่เผยแพร่ Dataset/GIS ภายนอก และไม่เปลี่ยน Production/API/Frontend</p>''',10))
 css='''@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;color:#173641;background:#e4ebec;font-family:"Leelawadee UI",Tahoma,sans-serif;font-size:11.2pt;line-height:1.52}.page{position:relative;width:210mm;height:297mm;background:white;padding:16mm 17mm 21mm;break-after:page;overflow:visible}.page:last-child{break-after:auto}.eyebrow{font-family:Arial,sans-serif;color:#6b808a;font-size:8.2pt;letter-spacing:.8px;padding-bottom:10px;border-bottom:2px solid #168278;margin-bottom:17px}h1{font-size:22pt;line-height:1.3;margin:0 0 18px}h2{font-size:14pt;margin:17px 0 6px}p{margin:10px 0}.lead{font-size:13pt}.note{color:#596b74;font-size:10pt;border-top:1px solid #d9e3e5;padding-top:10px}.callout{background:#edf5f2;border-left:4px solid #168278;padding:8px 14px;margin:16px 0}.callout h2{margin-top:6px}table{width:100%;border-collapse:collapse;margin:12px 0;font-size:10.2pt;line-height:1.45;table-layout:auto}th{background:#173641;color:white;text-align:left;font-weight:600;padding:9px 8px}td{padding:8px;border-bottom:1px solid #dce5e7;vertical-align:top}tbody tr:nth-child(even){background:#f4f7f8}ol{padding-left:24px;margin:12px 0}li{margin:8px 0}footer{position:absolute;left:17mm;right:17mm;bottom:10mm;border-top:1px solid #d8e2e4;padding-top:9px;color:#667c84;font-size:8.5pt}footer span{float:right}svg{width:100%;height:auto;display:block;margin:10px 0;font-family:"Leelawadee UI",Tahoma,sans-serif;font-size:16px}.plot-title{font-size:19px;font-weight:600}.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}strong{font-weight:700}@media print{body{background:white}}'''
 with (OUT/'binary_classification_report_th.html').open('x',encoding='utf-8') as f:f.write('<!doctype html><html lang="th"><head><meta charset="utf-8"><title>ทิศทางผลผลิตทุเรียนสองกลุ่ม</title><style>'+css+'</style></head><body>'+''.join(bodies)+'</body></html>')
 with (OUT/'README_TH.md').open('x',encoding='utf-8') as f:f.write(f'''# ผลทดลองทิศทางผลผลิตทุเรียน 2 กลุ่ม (Internal)

อ่าน binary_classification_report_th.pdf ก่อน Candidate หลัก {frozen['candidate_family']} {frozen['candidate_group']} ไม่ใช่โมเดลที่เลือกจากคะแนน Outer สูงสุด Public HOLD และยังไม่รับรอง Historical PIT ไม่มี Forecast ปี 2569

## ผลและไฟล์

model_comparison.csv คะแนน Accuracy, Balanced Accuracy, Macro F1 และจำนวนทายถูก; predictions_vs_actual.csv ค่าจริง/ค่าทำนายระดับจังหวัด–ปี; classification_report.csv คะแนนแต่ละ Class; confusion_matrix.csv จำนวนแต่ละช่อง 2×2; province_metrics/year_metrics.csv แยกพื้นที่/ปี; feature_group_contributions.csv เปรียบเทียบกลุ่มข้อมูลบน Keys เดียวกัน; feature_importance.csv Inner-only ของ Candidate

unified_features.csv 64 แถวปี2010–2025 แยก Target-only ออกจาก Predictors; all_OAE_direction_labels.csv 80 แถว/76คู่มีLag; exact_equal_excluded.csv มี {pre['equal_rows']} แถว ไม่ใช้ช่วงทรงตัว±5%

## ทำซ้ำแบบ Offline

Python: C:/project/.build/durian-automl-20261012-v1/Scripts/python.exe ใช้ -B -X utf8 ไม่ใช้ py launcher ไม่ติดตั้งเพิ่ม

คัดลอก prepare.py/train.py/report.py/verify.py/render_pdf.cjs/pdf_qa.py ไปโฟลเดอร์ version ใหม่ที่ยังไม่มี Outputs ภายใต้ C:/project ห้ามรันเขียนทับรุ่นนี้

1. python -B -X utf8 prepare.py ตรวจ sealed inputs และสร้าง Binary Labels
2. python -B -X utf8 train.py ล็อก Protocol ก่อน Outer รัน Tests และทดลองหนึ่งครั้ง เวลาไม่เกิน55นาที
3. python -B -X utf8 report.py สรุปผล ไม่ฝึกหรือเลือกโมเดลใหม่
4. python -B -X utf8 verify.py ตรวจ Metrics/Cutoff/Cache/Lineage/Hashes
5. node render_pdf.cjs แปลง HTML Offline เป็น PDF แล้ว render ด้วย Poppler และรัน pdf_qa.py

Environment/package versions อยู่ environment.json ใช้ CPU2 Seed42 ไม่ใช้ GPU/SMOTE แยก Cache ตาม Source/Train/Evaluation Features/Params/Cutoff/Study; Outer ไม่เข้า Inner Cache

## ตีความให้ถูกต้อง

Candidate family/features ตรึงจาก Inner ก่อน Outer แรก Later Inner เลือกเฉพาะ Preset ในตระกูลเดิม adaptive_nested รายงานแยก ทุกปีทุกจังหวัดใน Fold เดียวกัน หนึ่งปีมี4กรณีเท่านั้น

Full history: Outer2020–2025 24Keys; NDVI common: Outer2022–2025 16Keys ใช้ Training Cohort เดียวกันทุกแขนภายใน Study ไม่เทียบ F1 ข้าม Study NDVI cohort ขาด2018ตามข้อมูลจริง ไม่เติม Raw Months

Label เพิ่ม1ถ้าOAEY>Y−1 ลด0ถ้าน้อยกว่า เท่ากันแยกออก Regression ทำนาย SignedYoYpct แล้วแปลงที่0 ไม่มีการใช้Y−1จริงเป็นตัวหารตอนพยากรณ์ ค่า0ทำนาย/ทิศทางล่าสุด0 fallback Train Majority เท่านั้น

กฎIssue1มีนาคมY; Weatherทั้งปีY−1; Lagล่าสุดY−2 ไม่ใช่หลักฐานว่าวินเทจมีทันวันนั้น Publication Dates ยังไม่รับรอง Reanalysis/NDVI reprocessing/OAE revision มีข้อจำกัด ไม่ใช้ Soil/A403เป็นFeaturesย้อนหลัง ไม่อ้างรายสวนหรือเหตุและผล

Files ต้นทาง/Production ไม่เปลี่ยน การตรวจทุก Fold อยู่ final_verification.json/output_manifest.json ไม่มีการดาวน์โหลดหรือ Upload ภายนอก
''')
 with (OUT/'data_dictionary.md').open('x',encoding='utf-8') as f:
  f.write('# Data Dictionary (Binary provincial direction)\n\nหนึ่งแถวต่อจังหวัด–ปี ค่าที่รายงาน OAE ไม่ใช่ผลผลิตประมาณรายอำเภอ รายละเอียดทุก Field/Unit/Source/Calculation อยู่ unified_feature_dictionary.csv\n\nLabel1เพิ่ม,0ลด,exact equalsแยกออก Target-only ได้แก่ label,pct_change,yield_kg_per_rai,yield_previous_year_label_only ห้ามเป็นPredictor\n\nH/W/V/N กำหนดไว้ใน protocol_frozen.json ค่าที่ใช้จริงหลังAnomalyแต่ละFoldอยู่ transformed_feature_lineage.json เชื่อมด้วย context_sha256 กับ fit_cache_audit.json และ source_manifest.json\n\nNDVI/VPD/Weather เป็น exposureปีก่อน ไม่ใช่อากาศฤดูเป้าหมาย; Missingไม่เท่ากับ0; หน่วยกก./ไร่,°C,mm,%,kPa,0–1 แยกชัด Soil/GISใช้บริบทเท่านั้น ไม่ทำOverlayใหม่\n')
 with (OUT/'source_manifest.md').open('x',encoding='utf-8') as f:
  f.write('# Source / Provenance\n\nทุกไฟล์ที่ใช้พร้อมSHA256อยู่ source_manifest.json อ้างต่อ manifestsealedรุ่นเดิม ไม่ดาวน์โหลดใหม่\n\n- OAE: research_data/external/oae_2026-09-17/durian_province.xlsx ผ่านPhase9D province_year.csv พร้อมoae_observation_id ปีข้อมูล2006–2025 สถานะRevision/PublicationDateยังไม่ยืนยัน ไม่ถือdownloaddateเป็นpublication\n- NASA POWER: Phase9D weather_profile_month.csv และ sampling_points/manifestเดิม ข้อมูลT/RHday-weighted,ฝนsumรายเดือน ไม่ใช่WeatherForecastVintage\n- ERA5-Land: raw_vpd/*.json.gz ในintegrated release เก็บresponseSHAและunits VPDคำนวณจากT/Tdew เป็นReanalysisผ่านOpen-Meteo ไม่ใช่HistoricalForecast\n- NDVI: Landsat8ในresults/ndvi_monthly_profile.csv และrecordlineageเดิม >=6actualmonthsสองpixels/province ไม่blendSensors ไม่อ้างprovincearea mean\n- LDD: Soil/GIScontextจากPhase9D mapvintages ไม่เป็นHistoricalFootprint ไม่มีPublishDerivedGIS สิทธิ์ยังPublicHOLDตามRegistryเดิม\n\npreflight.json/final_verification.jsonยืนยันProtected1288filesและsealsเดิม ก่อน/หลัง ไม่รับรองHistoricalPIT ไม่มี2026Forecast\n')
 print('Report HTML and interpretation files created; no fitting or outer reselection',flush=True)
if __name__=='__main__': main()
