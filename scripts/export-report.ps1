param(
    [Parameter(Mandatory = $true)][string]$Record,
    [Parameter(Mandatory = $true)][string]$Output,
    [switch]$Update,
    [string]$Python
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $Python) { $Python = Join-Path $repoRoot '.venv\Scripts\python.exe' }
$recordPath = (Resolve-Path -LiteralPath $Record).Path
$outputPath = [System.IO.Path]::GetFullPath($(if ([System.IO.Path]::IsPathRooted($Output)) { $Output } else { Join-Path $repoRoot $Output }))
$siteRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot 'artifacts\site'))
if (-not $outputPath.StartsWith($siteRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Report output must be below this clone''s artifacts/site directory.'
}
$inputRecord = Get-Content -Raw -LiteralPath $recordPath | ConvertFrom-Json
$exists = Test-Path -LiteralPath $outputPath
if ($exists -and -not $Update) { throw 'Report output exists. Use -Update to regenerate the selected preview.' }
if ($exists) {
    $oldEvidence = Join-Path $outputPath 'evidence.json'
    if (-not (Test-Path -LiteralPath (Join-Path $outputPath 'export-manifest.json') -PathType Leaf) -or
        -not (Test-Path -LiteralPath $oldEvidence -PathType Leaf)) { throw 'Update requires an existing comparison export.' }
    $oldRecord = Get-Content -Raw -LiteralPath $oldEvidence | ConvertFrom-Json
    if ($oldRecord.scenarioId -ne $inputRecord.scenarioId -or $oldRecord.agentId -ne $inputRecord.agentId) {
        throw 'The selected output belongs to another case or Agent.'
    }
}
$revision = [guid]::NewGuid().ToString('N')
$stage = Join-Path $repoRoot ('.tools\report-staging\' + $revision)
& $Python -m arena report --record $recordPath --output $stage
if ($LASTEXITCODE -ne 0) { throw 'Report validation or generation failed; the previous preview was preserved.' }
if ($exists) {
    $backup = Join-Path $repoRoot ('.tools\report-backups\' + $revision)
    New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
    Copy-Item -LiteralPath $outputPath -Destination $backup -Recurse
    Write-Output "Previous preview backed up: $backup"
}
New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
Get-ChildItem -LiteralPath $stage -Force | Copy-Item -Destination $outputPath -Recurse -Force
Write-Output "Generated preview: $outputPath"
