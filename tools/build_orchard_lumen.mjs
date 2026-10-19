// Run after installing pinned build packages in .build/lumen; no Node needed on Render.
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const root = new URL('../', import.meta.url);
const require = createRequire(new URL('.build/lumen/package.json', root));
const { build } = require('esbuild');
await build({
  entryPoints: [fileURLToPath(new URL('web/assets/js/orchard_lumen.js', root))],
  nodePaths: [fileURLToPath(new URL('.build/lumen/node_modules', root))],
  outfile: fileURLToPath(new URL('research_data/five_province_history/orchard_lumen.js', root)),
  bundle: true, minify: true, format: 'esm', target: ['es2020'], legalComments: 'eof',
  banner: { js: `/*! Lumen UI — MIT License. Copyright (c) 2026 Santiago Molina.
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. */` },
});
