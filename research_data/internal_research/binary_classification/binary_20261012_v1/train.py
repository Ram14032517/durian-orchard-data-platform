"""One bounded offline binary experiment. Inner selection precedes own outer."""
import datetime,hashlib,json,time,warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder,StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression,Ridge
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import accuracy_score,balanced_accuracy_score,f1_score,precision_recall_fscore_support,confusion_matrix
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier,CatBoostRegressor
from prepare import ROOT,OUT,PREV,P9,OLD,NAMES,H,W,V,N,sha,read,js,csv,label,direction,verify_seals

ANOMALIES={'temp_anomaly':'nasa_temp_annual','rain_anomaly_pct':'nasa_rain_annual','rh_anomaly':'nasa_rh_annual','vpd_anomaly':'vpd_mean','ndvi_anomaly':'ndvi_median'}
FAMILIES=['Logistic','RandomForest','XGBoost','LightGBM','CatBoost','RidgePct','CatBoostPct']
COMPLEXITY={'Majority':0,'PreviousKnownDirection':1,'Logistic':2,'RidgePct':2,'RandomForest':3,'XGBoost':4,'LightGBM':4,'CatBoost':4,'CatBoostPct':4}
FIT_AUDIT=[];TRANSFORMS=[];INNER_CACHE={};COUNTS={'fits':0,'reuses':0};SOURCES={}
DEADLINE=0
def scores(actual,pred):
 actual=np.asarray(actual,int);pred=np.asarray(pred,int)
 assert len(actual)==len(pred)>0 and set(actual)<=set([0,1]) and set(pred)<=set([0,1])
 p,r,f,s=precision_recall_fscore_support(actual,pred,labels=[0,1],zero_division=0)
 with warnings.catch_warnings():
  warnings.simplefilter('ignore');ba=balanced_accuracy_score(actual,pred)
 return dict(accuracy=float(accuracy_score(actual,pred)),balanced_accuracy=float(ba),macro_f1=float(f1_score(actual,pred,labels=[0,1],average='macro',zero_division=0)),correct=int((actual==pred).sum()),n=len(actual),precision=p.tolist(),recall=r.tolist(),class_f1=f.tolist(),support=s.tolist(),confusion_matrix=confusion_matrix(actual,pred,labels=[0,1]).tolist())
def load_features():
 df=pd.read_csv(OUT/'unified_features.csv')
 for a,b in ANOMALIES.items(): df[a]=df[b]
 return df
def groups(study):
 return {'H':H,'W':H+W,'V':H+V,**({'N':H+N} if study=='ndvi_common' else {}),'ALL':H+W+V+(N if study=='ndvi_common' else [])}
def configs(study):
 return [dict(id=f'{g}__{f}__{v}',group=g,family=f,variant=v,balanced=(v==1 and f not in ['RidgePct','CatBoostPct']),features=cols) for g,cols in groups(study).items() for f in FAMILIES for v in [0,1]]+[dict(id=f'H__{f}__0',group='H',family=f,variant=0,balanced=False,features=H) for f in ['Majority','PreviousKnownDirection']]
def transform(train,test,cols):
 a=train[cols].copy();b=test[cols].copy();means={}
 for field,raw in ANOMALIES.items():
  if field not in cols: continue
  reference=train.groupby('province_code')[raw].mean();assert reference.notna().all()
  ma=train.province_code.map(reference);mb=test.province_code.map(reference)
  if field=='rain_anomaly_pct':
   assert (reference>0).all();a[field]=100*(a[field]/ma-1);b[field]=100*(b[field]/mb-1)
  else: a[field]=a[field]-ma;b[field]=b[field]-mb
  means[field]={str(k):float(v) for k,v in reference.items()}
 assert np.isfinite(a.to_numpy(float)).all() and np.isfinite(b.to_numpy(float)).all()
 return a,b,means
def signature(train,test,conf,year,study):
 cols=conf['features'];tcols=['province_code','year_ce','label','pct_change']+list(dict.fromkeys(x for x in cols if x!='province_code'))
 ecols=['province_code','year_ce']+list(dict.fromkeys(x for x in cols if x!='province_code'))
 payload={'study':study,'config':conf,'issue_year':year,'fit_cutoff':f'{year}-03-01','label_max_year':year-2,'source_hashes':SOURCES,'train':train[tcols].sort_values(['province_code','year_ce']).to_json(orient='split',double_precision=15),'eval_features_only':test[ecols].sort_values(['province_code','year_ce']).to_json(orient='split',double_precision=15)}
 return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
def fold_data(df,eligible,year):
 train=df[df.year_ce.isin([y for y in eligible if y<=year-2])].copy();test=df[df.year_ce==year].copy()
 assert len(train)>=8 and len(test)>0 and set(train.province_code)==set(NAMES) and set(test.province_code)<=set(NAMES)
 assert train.year_ce.max()<=year-2 and train.year_ce.max()<test.year_ce.min()
 assert (pd.to_datetime(train.max_observation_date)<pd.Timestamp(f'{year}-03-01')).all()
 assert (pd.to_datetime(test.max_observation_date)<pd.to_datetime(test.issue_date)).all()
 assert not set(zip(train.province_code,train.year_ce))&set(zip(test.province_code,test.year_ce))
 return train,test
def estimator(family,variant):
 # Direct models have fixed shallow capacity; two alternatives only change class weights.
 if family=='Logistic': return LogisticRegression(C=.1,max_iter=1500,random_state=42)
 if family=='RandomForest': return RandomForestClassifier(n_estimators=150,max_depth=2,min_samples_leaf=3,random_state=42,n_jobs=2)
 if family=='XGBoost': return XGBClassifier(n_estimators=160,max_depth=2,learning_rate=.05,reg_lambda=10,min_child_weight=3,random_state=42,n_jobs=2,objective='binary:logistic')
 if family=='LightGBM': return LGBMClassifier(n_estimators=160,max_depth=2,num_leaves=4,learning_rate=.05,reg_lambda=10,min_child_samples=5,random_state=42,n_jobs=2,verbosity=-1,deterministic=True,force_col_wise=True)
 if family=='CatBoost': return CatBoostClassifier(iterations=160,depth=2,learning_rate=.05,l2_leaf_reg=10,random_seed=42,thread_count=2,loss_function='Logloss',allow_writing_files=False,verbose=False)
 if family=='RidgePct': return Ridge(alpha=[10,100][variant])
 return CatBoostRegressor(iterations=160,depth=[2,3][variant],learning_rate=.05,l2_leaf_reg=10,random_seed=42,thread_count=2,loss_function='RMSE',allow_writing_files=False,verbose=False)
def fit_predict(train,test,conf,study,year,role):
 if time.monotonic()>DEADLINE: raise RuntimeError('Predeclared 55-minute training budget exceeded; preserve incomplete results, no score chasing')
 f=conf['family'];a,b,means=transform(train,test,conf['features']);trained=None;pct=None;weights=None;train_sc=None
 majority=int(train.label.mode().iloc[0]);zero_fallbacks=0
 if f=='Majority': pred=np.repeat(majority,len(test))
 elif f=='PreviousKnownDirection':
  pred=np.array([direction(x,majority) for x in test.last_known_pct_change]);zero_fallbacks=int((test.last_known_pct_change==0).sum())
 else:
  reg=f in ['RidgePct','CatBoostPct']
  if train.label.nunique()==1 and not reg: pred=np.repeat(majority,len(test))
  else:
   weights=compute_sample_weight('balanced',train.label) if conf['balanced'] else np.ones(len(train))
   numeric=[c for c in conf['features'] if c!='province_code'];steps=[('impute',SimpleImputer(strategy='median',add_indicator=True))]
   if f in ['Logistic','RidgePct']: steps.append(('scale',StandardScaler()))
   prep=ColumnTransformer([('province',OneHotEncoder(handle_unknown='ignore',sparse_output=False),['province_code']),('numeric',Pipeline(steps),numeric)])
   model=Pipeline([('prep',prep),('model',estimator(f,conf['variant']))])
   target=train['pct_change'].to_numpy() if reg else train.label.to_numpy()
   model.fit(a,target,model__sample_weight=weights);COUNTS['fits']+=1
   raw=np.asarray(model.predict(b)).reshape(-1);rawtrain=np.asarray(model.predict(a)).reshape(-1)
   if reg:
    pct=raw;pred=np.array([direction(x,majority) for x in raw]);train_pred=np.array([direction(x,majority) for x in rawtrain]);zero_fallbacks=int((raw==0).sum())
   else: pred=raw.astype(int);train_pred=rawtrain.astype(int)
   trained=(model,a,b,reg,majority);train_sc=scores(train.label,train_pred)
 key=signature(train,test,conf,year,study)
 FIT_AUDIT.append(dict(study=study,role=role,config_id=conf['id'],issue_year=year,max_train_label_year=int(train.year_ce.max()),train_rows=len(train),evaluation_rows=len(test),context_sha256=key,classes=train.label.value_counts().sort_index().to_dict(),sample_weights=None if weights is None else [float(x) for x in weights],training_macro_f1=None if train_sc is None else train_sc['macro_f1'],training_accuracy=None if train_sc is None else train_sc['accuracy'],anomaly_means=means,balanced=conf['balanced'],cache='fit',source_hashes=SOURCES,zero_prediction_fallbacks=zero_fallbacks,majority_tie_policy='smaller class0 if training counts equal',fit_cutoff=f'{year}-03-01'))
 for name,data,origin in [('train',a,train),('evaluation',b,test)]:
  TRANSFORMS.append(dict(study=study,role=role,issue_year=year,config_id=conf['id'],partition=name,keys=[[int(r.province_code),int(r.year_ce)] for r in origin.itertuples()],features=conf['features'],values=data.to_numpy().tolist(),reference_means=means,source_hashes=SOURCES,context_sha256=key))
 return np.asarray(pred),pct,trained,key
def inner_prediction(df,eligible,conf,year,study,outer):
 train,test=fold_data(df,eligible,year);key=signature(train,test,conf,year,study)
 if key in INNER_CACHE:
  assert INNER_CACHE[key][3]==key;COUNTS['reuses']+=1
  FIT_AUDIT.append(dict(study=study,role='inner',config_id=conf['id'],issue_year=year,outer_selection_year=outer,max_train_label_year=int(train.year_ce.max()),context_sha256=key,cache='exact_inner_context_reuse',source_hashes=SOURCES))
 else: INNER_CACHE[key]=fit_predict(train,test,conf,study,year,'inner')
 return test,INNER_CACHE[key]
def rank_select(records,confs):
 best=max(r['macro_f1'] for r in records);pool=[r for r in records if r['macro_f1']>=best-.02-1e-12];lookup={c['id']:c for c in confs}
 selected=sorted(pool,key=lambda r:(r['year_f1_sd'],len(lookup[r['config_id']]['features']),COMPLEXITY[lookup[r['config_id']]['family']],lookup[r['config_id']]['balanced'],r['config_id']))[0]
 return lookup[selected['config_id']],selected
def select_inner(df,eligible,confs,years,study,outer,all_inner):
 records=[]
 for conf in confs:
  actual=[];preds=[];year_f1=[]
  for year in years:
   test,(pred,pct,trained,key)=inner_prediction(df,eligible,conf,year,study,outer)
   actual.extend(test.label.tolist());preds.extend(pred.tolist());year_f1.append(scores(test.label,pred)['macro_f1'])
   for i,r in enumerate(test.itertuples()): all_inner.append(dict(study=study,outer_selection_year=outer,inner_year=year,config_id=conf['id'],province_code=r.province_code,actual_label=r.label,predicted_label=int(pred[i]),context_sha256=key))
  sc=scores(actual,preds);records.append(dict(study=study,outer_selection_year=outer,config_id=conf['id'],accuracy=sc['accuracy'],macro_f1=sc['macro_f1'],balanced_accuracy=sc['balanced_accuracy'],increase_recall=sc['recall'][1],year_f1_sd=float(np.std(year_f1)),validation_rows=len(actual),validation_years=years))
 return records
def self_tests(df):
 checks=[]
 assert [label(100+x,100) for x in [-1,-.00001,0,.00001,1]]==[0,0,None,1,1];checks.append('exact_OAE_binary_label_and_equal_exclusion')
 assert [direction(x,0) for x in [-.01,0,.01]]==[0,0,1] and direction(0,1)==1;checks.append('fixed_zero_regression_and_last_direction_fallback')
 assert set(df.label)=={0,1};checks.append('no_old_stable_class_used')
 assert not set(['label','pct_change','yield_kg_per_rai','yield_previous_year_label_only'])&set(H+W+V+N);checks.append('target_and_lag1_predictor_isolation')
 tr,te=fold_data(df,sorted(df.year_ce.unique()),2020);a,b,m=transform(tr,te,H+W+V)
 mutated=te.copy();mutated['label']=1-mutated.label;mutated['pct_change']=999;mutated['yield_kg_per_rai']=99999;mutated['yield_previous_year_label_only']=99999
 aa,bb,mm=transform(tr,mutated,H+W+V);assert a.equals(aa) and b.equals(bb) and m==mm;checks.append('outer_target_mutation_does_not_change_features')
 assert tr.year_ce.max()==2018 and te.weather_year.max()==2019;checks.append('training_and_observation_cutoffs')
 assert np.allclose(a.groupby('province_code').temp_anomaly.mean(),0,atol=1e-10);checks.append('training_only_anomaly_reference')
 imp=SimpleImputer(strategy='median').fit([[1],[3],[np.nan]]);assert imp.transform([[np.nan]])[0,0]==2;checks.append('training_only_imputation')
 c=configs('full_history')[0];s=signature(tr,te,c,2020,'full_history');assert s==signature(tr,mutated,c,2020,'full_history');checks.append('cache_ignores_own_outer_targets')
 altered=te.copy();altered.loc[altered.index[0],'yield_lag2']+=1;assert s!=signature(tr,altered,c,2020,'full_history');checks.append('cache_checks_actual_evaluation_features')
 c2=dict(c,id=c['id']+'_new');assert s!=signature(tr,te,c2,2020,'full_history') and s!=signature(tr,te,c,2019,'full_history');checks.append('cache_config_and_cutoff_isolation')
 altered=tr.copy();altered.loc[altered.index[0],'label']=1-altered.label.iloc[0];assert s!=signature(altered,te,c,2020,'full_history');checks.append('cache_training_label_isolation')
 assert all(sha(ROOT/p)==h for p,h in read(OUT/'source_manifest.json')['files'].items());checks.append('all_source_hashes_unchanged')
 assert scores([0,1],[0,1])['accuracy']==1 and scores([0,1],[0,1])['macro_f1']==1;checks.append('binary_metric_definitions')
 js(OUT/'pretraining_tests.json',dict(passed=len(checks),checks=checks))
def main():
 global SOURCES,DEADLINE
 assert not (OUT/'protocol_frozen.json').exists(),'Refuse overwrite or rerun after outer'
 source=read(OUT/'source_manifest.json')['files'];SOURCES=dict(source,training_code=sha(Path(__file__)),prepare_code=sha(OUT/'prepare.py'),unified_inputs=sha(OUT/'unified_features.csv'))
 DEADLINE=time.monotonic()+55*60;start=time.time();df=load_features()
 protocol=dict(labels='1 if OAE Yield(Y)>Yield(Y-1);0 if less; exact equality excluded',issue='March1',observations='Y-1 only, before issue; no current-year weather',training_labels='<= prediction_year-2; conservative proxy, not certified publication evidence',feature_groups={s:groups(s) for s in ['full_history','ndvi_common']},configurations={s:configs(s) for s in ['full_history','ndvi_common']},first_outer_family_freeze='Family and feature group from first own Inner only, before any binary Outer scores. Later Inner chooses preset inside frozen family/group.',adaptive_nested='separate exploratory all-family own-inner selector',inner='latest up to3 complete eligible years<=outer-2 with >=8 training rows; minimum2 inner years',outer={'full_history':list(range(2020,2026)),'ndvi_common':list(range(2022,2026))},tie_policy='within0.02 best aggregate MacroF1: lower year F1 SD, fewer features, simpler family, unweighted, ID',majority_tie='class0 if counts equal',zero_regression_or_previous_direction='training-fold majority, never target-year actual',class_weights='train-only N/(2*class_count), weight toggle only; no SMOTE',regression='signed YoY pct predicted directly, sign threshold0 fixed, no clamp and no inference use of YieldY-1',capacity='direct depth2/160trees (RF150),LogisticC0.1; two weight presets. Ridgealpha10/100; CatRegdepth2/3; seed42 CPU2',ndvi='Landsat8 only >=6 real months; matched four-province complete-year cohort. Missing raw months not filled.',soil_gis='context only excluded due historical map hindsight',anomaly='train-only per-province historical means; rain percent anomaly',source_hashes=SOURCES,public_release='HOLD',historical_pit='not_certified',forecast_2026=False,time_budget_minutes=55,readiness_gate='descriptive only: candidate MacroF1 and accuracy beat both baselines; at least3/4 province F1 wins and >=4/6 year accuracy wins vs previous direction; never sufficient for operational/PIT approval')
 js(OUT/'protocol_frozen.json',protocol);self_tests(df)
 predictions=[];inner_rows=[];selections=[];inner_scores=[];importance=[];study_info=[]
 for study in ['full_history','ndvi_common']:
  confs=configs(study);cols=list(dict.fromkeys(sum(groups(study).values(),[])));eligible=[]
  for year,g in df.groupby('year_ce'):
   # Equal actual labels were excluded once in preparation, never per model.
   if set(g.province_code)==set(NAMES) and g[cols].notna().all().all(): eligible.append(int(year))
  outers=[y for y in protocol['outer'][study] if y in eligible]
  assert outers==protocol['outer'][study],f'Missing predeclared outer cohort: {study}'
  frozen=None;study_info.append(dict(study=study,eligible_years=eligible,outer_years=outers))
  for outer in outers:
   inner=[y for y in eligible if y<=outer-2 and len(df[df.year_ce.isin([z for z in eligible if z<=y-2])])>=8][-3:]
   assert len(inner)>=2,'Insufficient Inner support; do not relax after seeing results'
   records=select_inner(df,eligible,confs,inner,study,outer,inner_rows);inner_scores+=records
   adaptive,adrec=rank_select(records,confs)
   if frozen is None:
    frozen=adaptive;js(OUT/(study+'_candidate_before_outer.json'),dict(candidate_family=frozen['family'],candidate_group=frozen['group'],initial_config=frozen,inner_score=adrec,outer_year=outer,code_sha256=SOURCES['training_code'],role='family/features frozen before any own outer'))
   frozen_options=[c for c in confs if c['family']==frozen['family'] and c['group']==frozen['group']]
   candidate,candrec=rank_select([r for r in records if r['config_id'] in [c['id'] for c in frozen_options]],frozen_options)
   choices={'candidate':candidate,'adaptive_nested':adaptive}
   for group in groups(study):
    for family in FAMILIES:
     options=[c for c in confs if c['family']==family and c['group']==group]
     choices[group+'__'+family]=rank_select([r for r in records if r['config_id'] in [c['id'] for c in options]],options)[0]
   for f in ['Majority','PreviousKnownDirection']: choices[f]=next(c for c in confs if c['family']==f)
   selection=dict(study=study,outer_year=outer,inner_years=inner,choices=choices,candidate_inner=candrec,adaptive_inner=adrec,selected_before_own_outer=True)
   js(OUT/f'{study}_{outer}_selection_before_outer.json',selection);selections.append(selection)
   train,test=fold_data(df,eligible,outer);memo={}
   for case,conf in choices.items():
    if conf['id'] not in memo: memo[conf['id']]=fit_predict(train,test,conf,study,outer,'outer')
    pred,pct,fit,key=memo[conf['id']]
    for i,r in enumerate(test.itertuples()): predictions.append(dict(study=study,case=case,config_id=conf['id'],family=conf['family'],feature_group=conf['group'],balanced=conf['balanced'],province_code=r.province_code,province_name=r.province_name,year_ce=outer,issue_date=r.issue_date,actual_label=r.label,predicted_label=int(pred[i]),actual_yoy_pct=getattr(r,'pct_change'),predicted_yoy_pct=None if pct is None else float(pct[i]),actual_yield_kg_per_rai=r.yield_kg_per_rai,fit_label_max_year=int(train.year_ce.max()),max_feature_date=r.max_observation_date,availability='unverified_historical_vintage',context_sha256=key))
   # No new fits: grouped permutation on retained Inner candidate fits, descriptive only.
   actual=[];original=[];perturbed={};rng=np.random.default_rng(42)
   for year in inner:
    te,(pr,pct,fit,key)=inner_prediction(df,eligible,candidate,year,study,outer)
    if fit is None: continue
    model,a,b,reg,majority=fit;actual.extend(te.label.tolist());original.extend(pr.tolist())
    for group,gcols in [('Yield',H[2:]),('Weather',W),('VPD',V),('NDVI',N),('Province',['province_code'])]:
     used=[x for x in gcols if x in candidate['features']]
     if not used: continue
     for rep in range(5):
      perm=rng.permutation(len(b));bb=b.copy();bb[used]=b.iloc[perm][used].to_numpy();raw=np.asarray(model.predict(bb)).reshape(-1)
      pp=[direction(x,majority) for x in raw] if reg else raw.astype(int).tolist();perturbed.setdefault((group,rep),[]).extend(pp)
   if actual:
    orig=scores(actual,original)['macro_f1']
    for group in sorted({g for g,r in perturbed}):
     impacts=[orig-scores(actual,perturbed[(group,r)])['macro_f1'] for r in range(5)]
     importance.append(dict(study=study,outer_selection_year=outer,config_id=candidate['id'],group=group,inner_macro_f1_drop_mean=float(np.mean(impacts)),repeat_sd=float(np.std(impacts)),meaning='Inner-only postselection description, not causal or significance'))
   print('Completed',study,outer,'candidate',candidate['id'],'InnerF1',round(candrec['macro_f1'],3),flush=True)
 pp=pd.DataFrame(predictions);csv(OUT/'predictions_vs_actual.csv',pp);csv(OUT/'inner_validation_predictions.csv',pd.DataFrame(inner_rows));csv(OUT/'inner_model_comparison.csv',pd.DataFrame(inner_scores));js(OUT/'selections.json',selections);js(OUT/'study_info.json',study_info);js(OUT/'fit_cache_audit.json',FIT_AUDIT);js(OUT/'transformed_feature_lineage.json',TRANSFORMS);csv(OUT/'feature_importance.csv',pd.DataFrame(importance))
 comparison=[];classes=[];confusions=[];byprovince=[];byyear=[]
 for (study,case),g in pp.groupby(['study','case']):
  sc=scores(g.actual_label,g.predicted_label);base=dict(study=study,case=case)
  comparison.append(dict(**base,**{k:sc[k] for k in ['accuracy','macro_f1','balanced_accuracy','correct','n']},families='|'.join(sorted(g.family.unique())),configurations_used='|'.join(sorted(g.config_id.unique()))))
  for i in range(2): classes.append(dict(**base,class_id=i,precision=sc['precision'][i],recall=sc['recall'][i],f1=sc['class_f1'][i],support=sc['support'][i]))
  for i in range(2):
   for j in range(2): confusions.append(dict(**base,actual_class=i,predicted_class=j,count=sc['confusion_matrix'][i][j]))
  for code,s in g.groupby('province_code'):
   q=scores(s.actual_label,s.predicted_label);byprovince.append(dict(**base,province_code=code,province_name=NAMES[code],**{k:q[k] for k in ['accuracy','macro_f1','balanced_accuracy','correct','n']}))
  for year,s in g.groupby('year_ce'):
   q=scores(s.actual_label,s.predicted_label);byyear.append(dict(**base,year_ce=year,**{k:q[k] for k in ['accuracy','macro_f1','balanced_accuracy','correct','n']}))
 for name,rows in [('model_comparison',comparison),('classification_report',classes),('confusion_matrix',confusions),('province_metrics',byprovince),('year_metrics',byyear)]: csv(OUT/(name+'.csv'),pd.DataFrame(rows))
 js(OUT/'training_completion.json',dict(counts=COUNTS,elapsed_seconds=time.time()-start,source_hashes=SOURCES,training_code_unchanged=sha(Path(__file__))==SOURCES['training_code'],new_year_forecast_issued=False,public_release='HOLD',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 verify_seals();print('Training complete, no retraining after scores',COUNTS,flush=True)
if __name__=='__main__': main()
