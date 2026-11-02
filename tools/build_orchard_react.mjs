import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const root=new URL('../',import.meta.url);
const require=createRequire(new URL('web/react/package.json',root));
const {build}=require('esbuild');
await build({entryPoints:[fileURLToPath(new URL('web/react/src/main.jsx',root))],outfile:fileURLToPath(new URL('research_data/five_province_history/orchard_app.js',root)),bundle:true,minify:true,format:'iife',jsx:'automatic',jsxImportSource:'@orchard/i18n',alias:{'@orchard/i18n/jsx-runtime':fileURLToPath(new URL('web/react/src/i18n/jsx-runtime.js',root))},target:['es2020'],define:{'process.env.NODE_ENV':'"production"'},legalComments:'eof'});
// A changed dictionary must produce a new immutable asset URL as part of the same build.
const page=new URL('research_data/five_province_history/UNIFIED_MAP.html',root);
const version=createHash('sha256').update(await readFile(new URL('research_data/five_province_history/orchard_app.js',root))).digest('hex').slice(0,12);
const html=await readFile(page,'utf8');
const updated=html.replace(/orchard_app\.js\?v=[a-f0-9]+/g,'orchard_app.js?v='+version);
if(updated!==html)await writeFile(page,updated,'utf8');
