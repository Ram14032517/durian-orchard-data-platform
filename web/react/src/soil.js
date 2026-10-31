// Categorical map-unit colors only; colors carry no agronomic rating.
export function soilPalette(codes){
  const palette=new Map([['SC','#a4a29a'],['W','#398ac2']]);
  [...new Set(codes.filter(c=>typeof c==='string'&&c.trim()).map(c=>c.trim()))].sort().filter(c=>!palette.has(c)).forEach((code,i)=>palette.set(code,`hsl(${Math.round(i*137.508)%360} ${i%2?58:72}% ${i%3===0?65:48}%)`));
  return code=>palette.get(String(code||'').trim())||'#cbd5e1';
}
export function soilLegend(features,color){
  const units=new Map();
  for(const f of features||[]){const p=f.properties||{},code=String(p.soil_code||'').trim();if(!code)continue;if(!units.has(code))units.set(code,{code,name:p.soil_name||'',color:color(code),count:0});units.get(code).count++;}
  return [...units.values()].sort((a,b)=>a.code.localeCompare(b.code,'en'));
}
