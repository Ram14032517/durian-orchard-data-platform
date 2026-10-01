param([string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot))

# Mechanical migration: preserve existing values without printing credentials.
$gatewayPath = Join-Path $ProjectRoot 'receiver_gateway\receiver_gateway.ino'
$privatePath = Join-Path $ProjectRoot 'receiver_gateway\farm_secret.h'
$examplePath = Join-Path $ProjectRoot 'receiver_gateway\farm_secret.example.h'
$names = @('SUPABASE_INGEST_URL', 'GOOGLE_SHEETS_URL', 'DEVICE_INGEST_KEY')
$source = [IO.File]::ReadAllText($gatewayPath)
if (-not $source.Contains('#include "farm_secret.h"')) {
    throw 'The gateway must already include farm_secret.h. No files changed.'
}
if (-not (Test-Path -LiteralPath $privatePath)) {
    throw 'Local farm_secret.h is missing. No files changed.'
}
$privateText = [IO.File]::ReadAllText($privatePath)
$exampleText = [IO.File]::ReadAllText($examplePath)
$moved = @()
foreach ($name in $names) {
    $pattern = '(?m)^const\s+char\s*\*\s*' + [regex]::Escape($name) + '\s*=\s*"(?:\\.|[^"\\])*"\s*;[^\r\n]*\r?\n?'
    $sourceMatches = [regex]::Matches($source, $pattern)
    $privateMatches = [regex]::Matches($privateText, $pattern)
    if ($sourceMatches.Count -gt 1 -or $privateMatches.Count -gt 1) {
        throw "Duplicate declaration for $name. No files changed."
    }
    if ($sourceMatches.Count -eq 1) {
        $declaration = $sourceMatches[0].Value.Trim()
        if ($privateMatches.Count -eq 1) {
            $valuePattern = '"(?:\\.|[^"\\])*"'
            $sourceValue = [regex]::Match($declaration, $valuePattern).Value
            $privateValue = [regex]::Match($privateMatches[0].Value, $valuePattern).Value
            if ($sourceValue -ne $privateValue) {
                throw "Conflicting local value for $name. No files changed."
            }
        } else {
            $privateText = $privateText.TrimEnd() + "`r`n" + $declaration + "`r`n"
        }
        $source = [regex]::Replace($source, $pattern, '')
        $moved += $name
    } elseif ($privateMatches.Count -ne 1) {
        throw "Missing declaration for $name. No files changed."
    }
    $exampleText = [regex]::Replace($exampleText, $pattern, '')
    $exampleText = $exampleText.TrimEnd() + "`r`nconst char* $name = `"CHANGE_ME`";`r`n"
}

# Reject a tracked or non-ignored private header before any writes.
Push-Location $ProjectRoot
try {
    $tracked = & git ls-files -- 'receiver_gateway/farm_secret.h'
    if ($tracked) { throw 'farm_secret.h is tracked. No files changed.' }
    & git check-ignore -q -- 'receiver_gateway/farm_secret.h'
    if ($LASTEXITCODE -ne 0) { throw 'farm_secret.h is not ignored. No files changed.' }
} finally { Pop-Location }

if ($moved.Count -eq 0) {
    Write-Host 'Ingest configuration is already in the ignored private header.'
    exit 0
}
$backupDir = Join-Path $ProjectRoot ('.build\private-config-backup\' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item -LiteralPath $gatewayPath -Destination (Join-Path $backupDir 'receiver_gateway.ino')
Copy-Item -LiteralPath $privatePath -Destination (Join-Path $backupDir 'farm_secret.h')
$encoding = New-Object Text.UTF8Encoding($false)
# Private configuration is written first so the source always has its definitions.
[IO.File]::WriteAllText($privatePath, $privateText, $encoding)
[IO.File]::WriteAllText($examplePath, $exampleText, $encoding)
[IO.File]::WriteAllText($gatewayPath, $source, $encoding)
Write-Host ('Moved configuration names only: ' + ($moved -join ', '))
Write-Host 'Values preserved locally. No key rotation, Git history rewrite, or upload performed.'
