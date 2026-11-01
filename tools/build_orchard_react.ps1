$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$frontendRoot=Join-Path $projectRoot 'web/react'
if (!(Test-Path -LiteralPath (Join-Path $frontendRoot 'node_modules/react'))) {
  throw 'Install pinned frontend dependencies first: pnpm --dir web/react install --frozen-lockfile'
}
$cliPath=Join-Path $projectRoot '.build/tailwind/tailwindcss-v4.3.3-windows-x64.exe'
if (!(Test-Path -LiteralPath $cliPath)) { throw 'Run tools/build_orchard_tailwind.ps1 once to obtain the verified Tailwind CLI.' }
if ((Get-FileHash -LiteralPath $cliPath -Algorithm SHA256).Hash -ne 'E0E260CE048014E9268F6237FF18F8CCF02CEF521CBD0AE04E82C2CDF7AA3955') { throw 'Tailwind checksum mismatch' }
& node (Join-Path $projectRoot 'tools/build_orchard_react.mjs')
if ($LASTEXITCODE -ne 0) { throw 'React build failed' }
& $cliPath -i (Join-Path $frontendRoot 'src/style.css') -o (Join-Path $projectRoot 'research_data/five_province_history/orchard_app.css') --minify
if ($LASTEXITCODE -ne 0) { throw 'Tailwind build failed' }
