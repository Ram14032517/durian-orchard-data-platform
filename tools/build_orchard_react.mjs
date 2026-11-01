import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const root=new URL('../',import.meta.url);
const require=createRequire(new URL('web/react/package.json',root));
const {build}=require('esbuild');
await build({entryPoints:[fileURLToPath(new URL('web/react/src/main.jsx',root))],outfile:fileURLToPath(new URL('research_data/five_province_history/orchard_app.js',root)),bundle:true,minify:true,format:'iife',jsx:'automatic',target:['es2020'],define:{'process.env.NODE_ENV':'"production"'},legalComments:'eof'});
