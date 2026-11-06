param(
    [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvRoot = Join-Path $repoRoot '.venv'
$venvPython = Join-Path $venvRoot 'Scripts\python.exe'

& $Python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 2)'
if ($LASTEXITCODE -ne 0) {
    throw 'Python 3.12 or later is required. Use -Python with the installed executable path.'
}
if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    & $Python -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
& $venvPython -m pip install --disable-pip-version-check --editable $repoRoot
if ($LASTEXITCODE -ne 0) { throw 'Arena installation failed.' }

$localProfile = Join-Path $repoRoot 'profiles\recording\windows-dsh-desktop.local.json'
if (-not (Test-Path -LiteralPath $localProfile)) {
    Copy-Item -LiteralPath (Join-Path $repoRoot 'profiles\recording\windows-dsh-desktop.example.json') -Destination $localProfile
    Write-Output "Created local profile: $localProfile"
} else {
    Write-Output "Preserved local profile: $localProfile"
}
& $venvPython -m arena doctor --root $repoRoot
if ($LASTEXITCODE -ne 0) { throw 'Arena repository checks failed.' }
Write-Output 'Arena is installed. Read docs/reproduction.md before a live trial.'
