param([Parameter(Mandatory = $true)][string]$StopFile)
# Independent screenshot-count panel. This process never captures the screen.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
$run = Get-Content -LiteralPath (Join-Path (Split-Path -Parent $StopFile) 'run.json') -Raw -Encoding utf8 | ConvertFrom-Json
$trial = [string]$run.workspacePath
if ([string]::IsNullOrWhiteSpace($trial)) { throw 'Trial workspacePath is missing' }
$prepared = Join-Path (Split-Path -Parent $trial) '.arena-device-local'
$dest = Join-Path $trial '.arena-device-local'
$fixture = Join-Path $prepared 'screen-fixture.json'
if (-not (Test-Path -LiteralPath $fixture)) { throw 'Prepared screen fixture is missing' }
if (-not (Test-Path -LiteralPath $dest)) {
  New-Item -ItemType Junction -Path $dest -Target $prepared | Out-Null
}
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$python = Join-Path $repo '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = Join-Path $repo '.venv\Scripts\python.exe' }
$observer = Join-Path $repo 'scripts\device-observer.py'
if (-not (Test-Path -LiteralPath $python)) { throw 'Host Python for the observer is missing' }
$config = Join-Path $dest 'screen-fixture.json'
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $python
$psi.Arguments = '"' + $observer + '" screen --config "' + $config + '"'
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$proc = [Diagnostics.Process]::Start($psi)
Set-Content -LiteralPath ($StopFile + '.pid') -Value $PID -Encoding ascii
Write-Output ('ready pid=' + $PID + ' observerPid=' + $proc.Id)
try {
  while (-not (Test-Path -LiteralPath $StopFile)) {
    Start-Sleep -Milliseconds 200
  }
}
finally {
  if ($proc -and -not $proc.HasExited) {
    $proc.CloseMainWindow() | Out-Null
    $proc.WaitForExit(5000) | Out-Null
  }
  if ($proc -and -not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
  Write-Output 'closed'
}
