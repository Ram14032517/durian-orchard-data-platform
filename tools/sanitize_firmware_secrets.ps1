param([string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot))

$receiverPath = Join-Path $ProjectRoot 'receiver_gateway\receiver_gateway.ino'
$receiverSecretPath = Join-Path $ProjectRoot 'receiver_gateway\farm_secret.h'
$receiverExamplePath = Join-Path $ProjectRoot 'receiver_gateway\farm_secret.example.h'
$wifiTestPath = Join-Path $ProjectRoot 'wifi_range_test\wifi_range_test.ino'
$wifiSecretPath = Join-Path $ProjectRoot 'wifi_range_test\wifi_secret.h'
$wifiExamplePath = Join-Path $ProjectRoot 'wifi_range_test\wifi_secret.example.h'

function Move-ConstantsToHeader {
    param(
        [string]$SourcePath,
        [string]$SecretPath,
        [string]$ExamplePath,
        [string]$IncludeName,
        [string[]]$Names
    )

    $source = [IO.File]::ReadAllText($SourcePath)
    if ((Test-Path -LiteralPath $SecretPath) -and
        $source.Contains("#include `"$IncludeName`"")) {
        Write-Host "$SourcePath is already sanitized."
        return
    }

    $secretLines = @('#pragma once', '')
    $exampleLines = @('#pragma once', '', '// Copy this file to the non-example name and fill in private values.')

    foreach ($name in $Names) {
        $pattern = "(?m)^const\s+(?:char\*|double)\s+$name\s*=\s*[^;]+;\r?\n?"
        $match = [regex]::Match($source, $pattern)
        if (-not $match.Success) {
            if (Test-Path -LiteralPath $SecretPath) { continue }
            throw "Could not find $name in $SourcePath"
        }

        $declaration = $match.Value.Trim()
        $secretLines += $declaration
        if ($declaration -match '^const\s+double') {
            $exampleLines += "const double $name = 0.0;"
        } else {
            $exampleLines += "const char* $name = `"CHANGE_ME`";"
        }
        $source = [regex]::Replace($source, $pattern, '', 1)
    }

    if ($source -notmatch [regex]::Escape("#include `"$IncludeName`"")) {
        $firstInclude = [regex]::Match($source, '(?m)^#include\s+[<\"][^>\"]+[>\"]\r?\n')
        if (-not $firstInclude.Success) { throw "No include line found in $SourcePath" }
        $insertAt = $firstInclude.Index + $firstInclude.Length
        $source = $source.Insert($insertAt, "#include `"$IncludeName`"`r`n")
    }

    [IO.File]::WriteAllText($SecretPath, (($secretLines -join "`r`n") + "`r`n"))
    [IO.File]::WriteAllText($ExamplePath, (($exampleLines -join "`r`n") + "`r`n"))
    [IO.File]::WriteAllText($SourcePath, $source)
}

Move-ConstantsToHeader `
    -SourcePath $receiverPath `
    -SecretPath $receiverSecretPath `
    -ExamplePath $receiverExamplePath `
    -IncludeName 'farm_secret.h' `
    -Names @('WIFI_SSID', 'WIFI_PASS', 'TMD_API_TOKEN', 'TMD_API_TOKEN_CURRENT', 'FARM_LAT', 'FARM_LON', 'AGRO_APPID', 'AGRO_POLYID')

Move-ConstantsToHeader `
    -SourcePath $wifiTestPath `
    -SecretPath $wifiSecretPath `
    -ExamplePath $wifiExamplePath `
    -IncludeName 'wifi_secret.h' `
    -Names @('WIFI_SSID', 'WIFI_PASS')

Write-Host 'Firmware secrets moved to ignored headers. Example headers are safe to commit.'
