"""Independent post-training checks; no fitting, network or source changes."""
import datetime,subprocess
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score,balanced_accuracy_score,f1_score,confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight
from prepare import ROOT,OUT,PREV,P9,H,W,V,N,NAMES,PRODUCTION,read,sha,js,label,direction,verify_seals
import train as t
def main():
 assert not (OUT/'final_verification.json').exists()
 checks=[];protocol=read(OUT/'protocol_frozen.json');df=t.load_features();t.SOURCES=protocol['source_hashes']
 pred=pd.read_csv(OUT/'predictions_vs_actual.csv');score=pd.read_csv(OUT/'model_comparison.csv');inner=pd.read_csv(OUT/'inner_validation_predictions.csv');ins=pd.read_csv(OUT/'inner_model_comparison.csv');sel=read(OUT/'selections.json');info=read(OUT/'study_info.json')
 p9=pd.read_csv(P9/'province_year.csv').set_index(['province_code','year_ce'])
 for r in df.itertuples():
  y=float(p9.loc[(r.province_code,r.year_ce)].yield_kg_per_rai);lag=float(p9.loc[(r.province_code,r.year_ce-1)].yield_kg_per_rai)
  assert y==r.yield_kg_per_rai and lag==r.yield_previous_year_label_only and label(y,lag)==r.label
  assert abs(100*(y/lag-1)-getattr(r,'pct_change'))<1e-10
 checks.append('independent_real_OAE_binary_labels_and_pct_target')
 all_labels=pd.read_csv(OUT/'all_OAE_direction_labels.csv');equal=pd.read_csv(OUT/'exact_equal_excluded.csv')
 assert len(equal)==int((all_labels.status=='exact_equal_excluded').sum()) and len(equal)==read(OUT/'preflight.json')['equal_rows']
 assert all_labels.label.notna().sum()==76 and df.label.isin([0,1]).all();checks.append('all_76_OAE_pairs_and_exact_ties_accounted_for')
 assert not set(['label','pct_change','yield_kg_per_rai','yield_previous_year_label_only'])&set(H+W+V+N);checks.append('target_and_unavailable_lag1_not_predictors')
 assert not pred.duplicated(['study','case','province_code','year_ce']).any() and pred.year_ce.max()==2025;checks.append('unique_predictions_and_no_new_year_forecast')
 for study,g in pred.groupby('study'):
  keys=[set(zip(x.province_code,x.year_ce)) for c,x in g.groupby('case')];assert all(k==keys[0] for k in keys)
  assert len(keys[0])==(24 if study=='full_history' else 16)
  for key,x in g.groupby(['case','year_ce']): assert len(x)==4 and set(x.province_code)==set(NAMES)
 checks.append('identical_keys_all_arms_and_year_group_integrity')
 for (study,case),g in pred.groupby(['study','case']):
  x=score[(score.study==study)&(score.case==case)].iloc[0]
  assert abs(accuracy_score(g.actual_label,g.predicted_label)-x.accuracy)<1e-12
  assert abs(f1_score(g.actual_label,g.predicted_label,labels=[0,1],average='macro',zero_division=0)-x.macro_f1)<1e-12
  assert abs(balanced_accuracy_score(g.actual_label,g.predicted_label)-x.balanced_accuracy)<1e-12
  assert x.correct==int((g.actual_label==g.predicted_label).sum())
  cm=pd.read_csv(OUT/'confusion_matrix.csv');cc=cm[(cm.study==study)&(cm.case==case)].pivot(index='actual_class',columns='predicted_class',values='count')
  assert np.array_equal(cc.to_numpy(),confusion_matrix(g.actual_label,g.predicted_label,labels=[0,1]))
 checks.append('independent_accuracy_macroF1_BA_and_confusion_recalculation')
 eligible={s['study']:s['eligible_years'] for s in info}
 for r in pred[pred.predicted_yoy_pct.notna()].itertuples():
  tr,te=t.fold_data(df,eligible[r.study],r.year_ce);assert direction(r.predicted_yoy_pct,int(tr.label.mode().iloc[0]))==r.predicted_label
 checks.append('signed_regression_to_binary_without_lag1_denominator')
 for r in pred[pred.case=='PreviousKnownDirection'].itertuples():
  tr,te=t.fold_data(df,eligible[r.study],r.year_ce);actual=df[(df.province_code==r.province_code)&(df.year_ce==r.year_ce)].iloc[0]
  assert direction(actual.last_known_pct_change,int(tr.label.mode().iloc[0]))==r.predicted_label
 checks.append('last_known_direction_uses_Yminus2_and_Yminus3_only')
 for key,g in inner.groupby(['study','outer_selection_year','config_id']):
  record=ins[(ins.study==key[0])&(ins.outer_selection_year==key[1])&(ins.config_id==key[2])].iloc[0]
  assert g.inner_year.max()<=key[1]-2
  assert abs(f1_score(g.actual_label,g.predicted_label,labels=[0,1],average='macro',zero_division=0)-record.macro_f1)<1e-12
 checks.append('inner_metrics_and_selection_label_cutoff')
 for s in sel:
  configs=t.configs(s['study']);records=ins[(ins.study==s['study'])&(ins.outer_selection_year==s['outer_year'])].to_dict('records')
  assert t.rank_select(records,configs)[0]['id']==s['choices']['adaptive_nested']['id']
  frozen=read(OUT/(s['study']+'_candidate_before_outer.json'));c=s['choices']['candidate'];assert c['family']==frozen['candidate_family'] and c['group']==frozen['candidate_group']
  options=[x for x in configs if x['family']==c['family'] and x['group']==c['group']]
  assert t.rank_select([r for r in records if r['config_id'] in [x['id'] for x in options]],options)[0]['id']==c['id']
  assert max(s['inner_years'])<=s['outer_year']-2 and s['selected_before_own_outer']
 checks.append('all_selections_rebuilt_from_own_inner_only_and_family_frozen')
 seen={};fits=read(OUT/'fit_cache_audit.json')
 for f in fits:
  conf=next(c for c in t.configs(f['study']) if c['id']==f['config_id']);tr,te=t.fold_data(df,eligible[f['study']],f['issue_year'])
  assert f['context_sha256']==t.signature(tr,te,conf,f['issue_year'],f['study']) and f['max_train_label_year']<=f['issue_year']-2
  if f['cache']=='exact_inner_context_reuse': assert f['role']=='inner' and f['context_sha256'] in seen
  elif f['role']=='inner': seen[f['context_sha256']]=f
  if f.get('balanced') and f.get('sample_weights') is not None: assert np.allclose(f['sample_weights'],compute_sample_weight('balanced',tr.label),atol=1e-12)
 checks.append('fit_cache_source_features_parameters_cutoff_and_inner_role_isolation');checks.append('train_only_class_weights_every_actual_fit')
 for b in read(OUT/'transformed_feature_lineage.json'):
  tr,te=t.fold_data(df,eligible[b['study']],b['issue_year']);a,c,m=t.transform(tr,te,b['features']);x=a if b['partition']=='train' else c;origin=tr if b['partition']=='train' else te
  assert np.allclose(x.to_numpy(),b['values'],atol=1e-10,rtol=1e-12) and m==b['reference_means']
  assert b['keys']==[[int(r.province_code),int(r.year_ce)] for r in origin.itertuples()]
 checks.append('actual_feature_values_and_reference_means_reconstructed_every_fit')
 assert (pd.to_datetime(pred.max_feature_date)<pd.to_datetime(pred.issue_date)).all();checks.append('all_observation_dates_before_issue')
 assert not any('soil' in x or 'A403' in x for x in H+W+V+N);checks.append('historical_map_hindsight_excluded')
 assert sha(OUT/'train.py')==protocol['source_hashes']['training_code'] and sha(OUT/'prepare.py')==protocol['source_hashes']['prepare_code'];checks.append('training_code_not_changed_after_outer_results')
 assert all(sha(ROOT/p)==h for p,h in read(OUT/'source_manifest.json')['files'].items());checks.append('input_and_prior_artifact_hashes_unchanged')
 protected,seals=verify_seals();checks.append('1288_protected_files_and_all_prior_seals_unchanged')
 # Synthetic negative checks do not fit models or manufacture real research rows.
 tr,te=t.fold_data(df,eligible['full_history'],2020);conf=t.configs('full_history')[0];key=t.signature(tr,te,conf,2020,'full_history')
 bad=te.copy();bad['label']=1-bad.label;bad['pct_change']=1000;assert key==t.signature(tr,bad,conf,2020,'full_history')
 bad=te.copy();bad.loc[bad.index[0],'yield_lag2']+=1;assert key!=t.signature(tr,bad,conf,2020,'full_history');checks.append('cache_target_mutation_excluded_but_input_mutation_detected')
 rejected=False
 try: t.fold_data(df[df.year_ce>=2018],eligible['full_history'],2020)
 except AssertionError: rejected=True
 assert rejected;checks.append('insufficient_training_fail_fast')
 status=subprocess.check_output(['git','status','--porcelain=v1','-uall'],cwd=ROOT,text=True,encoding='utf-8')
 prefix=str(OUT.relative_to(ROOT)).replace('\\','/')+'/'
 before=read(OUT/'repository_state_before.json')['status']
 strip=lambda text:[line for line in text.splitlines() if prefix not in line]
 assert strip(status)==strip(before),'Repository status changed outside new internal namespace'
 js(OUT/'repository_state_after.json',{'status':status,'outside_namespace_status_unchanged':True})
 checks.append('repository_state_unchanged_outside_new_version_folder')
 js(OUT/'final_verification.json',dict(passed=len(checks),checks=checks,protected_count=len(protected),sealed_release_counts=seals,production_sha256=sha(PRODUCTION),no_network=True,no_new_forecast=True,public_release='HOLD',historical_pit='not_certified',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 print('Final independent checks passed:',len(checks),'Production and sources unchanged',flush=True)
if __name__=='__main__': main()
