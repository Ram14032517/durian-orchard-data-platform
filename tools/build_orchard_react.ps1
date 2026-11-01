$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$frontendRoot=Join-Path $projectRoot 'web/react'
if (!(Test-Path -LiteralPath (Join-Path $frontendRoot 'node_modules/react'))) {
  throw 'Install pinned frontend dependencies first: pnpm --dir web/react install --frozen-lockfile'
}
& node (Join-Path $projectRoot 'tools/build_orchard_react.mjs')
if ($LASTEXITCODE -ne 0) { throw 'React/Tailwind build failed; install the pinned frontend dependencies first.' }
