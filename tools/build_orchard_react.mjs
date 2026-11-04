import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { readFile, writeFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
const root=new URL('../',import.meta.url);
const require=createRequire(new URL('web/react/package.json',root));
const {build}=require('esbuild');
await build({entryPoints:[fileURLToPath(new URL('web/i18n/english.js',root))],outfile:fileURLToPath(new URL('research_data/five_province_history/orchard_english.js',root)),bundle:true,minify:true,format:'iife',globalName:'OrchardEnglish',target:['es2020'],legalComments:'eof'});
await build({entryPoints:[fileURLToPath(new URL('web/react/src/main.jsx',root))],outfile:fileURLToPath(new URL('research_data/five_province_history/orchard_app.js',root)),bundle:true,minify:true,format:'iife',jsx:'automatic',jsxImportSource:'@orchard/i18n',alias:{'@orchard/i18n/jsx-runtime':fileURLToPath(new URL('web/react/src/i18n/jsx-runtime.js',root))},target:['es2020'],define:{'process.env.NODE_ENV':'"production"'},legalComments:'eof'});
// The same pinned CLI works on macOS, Windows and Linux; no global install.
const manifestUrl=new URL('web/react/node_modules/@tailwindcss/cli/package.json',root);
const manifest=JSON.parse(await readFile(manifestUrl,'utf8'));
const cli=new URL(typeof manifest.bin==='string'?manifest.bin:manifest.bin.tailwindcss,manifestUrl);
const css=spawnSync(process.execPath,[fileURLToPath(cli),'-i',fileURLToPath(new URL('web/react/src/style.css',root)),'-o',fileURLToPath(new URL('research_data/five_province_history/orchard_app.css',root)),'--minify'],{cwd:fileURLToPath(new URL('web/react/',root)),stdio:'inherit'});
if(css.error)throw css.error;
if(css.status!==0)throw Error('Tailwind build failed: '+css.status);
// A changed dictionary must produce a new immutable asset URL as part of the same build.
const page=new URL('research_data/five_province_history/UNIFIED_MAP.html',root);
const version=createHash('sha256').update(await readFile(new URL('research_data/five_province_history/orchard_app.js',root))).digest('hex').slice(0,12);
const html=await readFile(page,'utf8');
const updated=html.replace(/orchard_app\.js\?v=[a-f0-9]+/g,'orchard_app.js?v='+version);
if(updated!==html)await writeFile(page,updated,'utf8');
