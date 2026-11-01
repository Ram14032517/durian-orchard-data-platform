import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { readFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
const root=new URL('../',import.meta.url);
const require=createRequire(new URL('web/react/package.json',root));
const {build}=require('esbuild');
await build({entryPoints:[fileURLToPath(new URL('web/react/src/main.jsx',root))],outfile:fileURLToPath(new URL('research_data/five_province_history/orchard_app.js',root)),bundle:true,minify:true,format:'iife',jsx:'automatic',target:['es2020'],define:{'process.env.NODE_ENV':'"production"'},legalComments:'eof'});
// The same pinned CLI works on macOS, Windows and Linux; no global install.
const manifestUrl=new URL('web/react/node_modules/@tailwindcss/cli/package.json',root);
const manifest=JSON.parse(await readFile(manifestUrl,'utf8'));
const cli=new URL(typeof manifest.bin==='string'?manifest.bin:manifest.bin.tailwindcss,manifestUrl);
const css=spawnSync(process.execPath,[fileURLToPath(cli),'-i',fileURLToPath(new URL('web/react/src/style.css',root)),'-o',fileURLToPath(new URL('research_data/five_province_history/orchard_app.css',root)),'--minify'],{cwd:fileURLToPath(new URL('web/react/',root)),stdio:'inherit'});
if(css.error)throw css.error;
if(css.status!==0)throw Error('Tailwind build failed: '+css.status);
