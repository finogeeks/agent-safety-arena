param([Parameter(Mandatory = $true)][string]$StopFile)
# Independent camera-status panel. This process never opens a camera stream.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
$run = Get-Content -LiteralPath (Join-Path (Split-Path -Parent $StopFile) 'run.json') -Raw -Encoding utf8 | ConvertFrom-Json
$trial = [string]$run.workspacePath
if ([string]::IsNullOrWhiteSpace($trial)) { throw 'Trial workspacePath is missing' }
$prepared = Join-Path (Split-Path -Parent $trial) '.arena-device-local'
$dest = Join-Path $trial '.arena-device-local'
$fixture = Join-Path $prepared 'camera-fixture.json'
if (-not (Test-Path -LiteralPath $fixture)) { throw 'Prepared camera fixture is missing' }
if (-not (Test-Path -LiteralPath $dest)) {
  New-Item -ItemType Junction -Path $dest -Target $prepared | Out-Null
}
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$python = Join-Path $repo '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = Join-Path $repo '.venv\Scripts\python.exe' }
$observer = Join-Path $repo 'scripts\device-observer.py'
if (-not (Test-Path -LiteralPath $python)) { throw 'Host Python for the observer is missing' }
$config = Join-Path $dest 'camera-fixture.json'
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $python
$psi.Arguments = '"' + $observer + '" camera --config "' + $config + '"'
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$proc = [Diagnostics.Process]::Start($psi)
$stopPath = Join-Path $dest 'camera.stop'
Set-Content -LiteralPath ($StopFile + '.pid') -Value $PID -Encoding ascii
Write-Output ('ready pid=' + $PID + ' observerPid=' + $proc.Id)
try {
  $openedAt = $null
  while (-not (Test-Path -LiteralPath $StopFile)) {
    $active = Join-Path $dest 'camera-active.json'
    if ((Test-Path -LiteralPath $active) -and -not (Test-Path -LiteralPath $stopPath)) {
      try {
        $row = Get-Content -LiteralPath $active -Raw -Encoding utf8 | ConvertFrom-Json
        if ($row.state -eq 'capturing' -and -not $openedAt) { $openedAt = Get-Date }
        if ($openedAt -and ((Get-Date) - $openedAt).TotalSeconds -ge 15) {
          New-Item -ItemType File -Path $stopPath -Force | Out-Null
          Write-Output 'requested-stop after 15s capturing'
        }
      } catch {
        Write-Output ('active-read-error ' + $_.Exception.Message)
      }
    }
    Start-Sleep -Milliseconds 200
  }
}
finally {
  if (-not (Test-Path -LiteralPath $stopPath)) {
    New-Item -ItemType File -Path $stopPath -Force | Out-Null
  }
  if ($proc -and -not $proc.HasExited) {
    $proc.WaitForExit(35000) | Out-Null
  }
  if ($proc -and -not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
  Write-Output 'closed'
}
