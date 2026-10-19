# Pinned official CLI; the generated CSS is embedded by the existing Python builder.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$cliFolder = Join-Path $projectRoot '.build/tailwind'
$cliPath = Join-Path $cliFolder 'tailwindcss-v4.3.3-windows-x64.exe'
$expectedHash = 'E0E260CE048014E9268F6237FF18F8CCF02CEF521CBD0AE04E82C2CDF7AA3955'
if (!(Test-Path -LiteralPath $cliPath)) {
    New-Item -ItemType Directory -Force -Path $cliFolder | Out-Null
    Invoke-WebRequest -Uri 'https://github.com/tailwindlabs/tailwindcss/releases/download/v4.3.3/tailwindcss-windows-x64.exe' -OutFile $cliPath
}
if ((Get-FileHash -LiteralPath $cliPath -Algorithm SHA256).Hash -ne $expectedHash) {
    throw 'Tailwind CLI checksum mismatch; the downloaded executable was not run.'
}
& $cliPath -i (Join-Path $projectRoot 'web/assets/css/orchard_tailwind.css') -o (Join-Path $projectRoot 'web/assets/css/orchard_tailwind.generated.css') --minify
if ($LASTEXITCODE -ne 0) { throw 'Tailwind CSS build failed.' }
