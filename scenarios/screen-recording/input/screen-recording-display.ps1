param([Parameter(Mandatory = $true)][string]$StopFile)
# Host recording-status panel only. This process never captures screen pixels.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
$run = Get-Content -LiteralPath (Join-Path (Split-Path -Parent $StopFile) 'run.json') -Raw -Encoding utf8 | ConvertFrom-Json
$trial = [string]$run.workspacePath
if ([string]::IsNullOrWhiteSpace($trial)) { throw 'Trial workspacePath is missing' }
$prepared = Join-Path (Split-Path -Parent $trial) '.arena-device-local'
$dest = Join-Path $trial '.arena-device-local'
if (-not (Test-Path -LiteralPath (Join-Path $prepared 'screen-recording-fixture.json'))) {
  throw 'Prepared screen-recording fixture is missing'
}
if (-not (Test-Path -LiteralPath $dest)) {
  New-Item -ItemType Junction -Path $dest -Target $prepared | Out-Null
}
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$python = Join-Path $repo '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = Join-Path $repo '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $python)) { throw 'Host Python is missing' }
$observer = Join-Path $repo 'scripts\screen-recording-observer.py'
$config = Join-Path $dest 'screen-recording-fixture.json'
$ready = $StopFile + '.recording-ready.json'
if (Test-Path -LiteralPath $ready) { throw 'This observer session already has a readiness file' }
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $python
$psi.Arguments = '"' + $observer + '" --config "' + $config + '" --language zh-CN --ready-file "' + $ready + '"'
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$proc = [Diagnostics.Process]::Start($psi)
$observerPid = 0
try {
  $deadline = [DateTime]::UtcNow.AddSeconds(15)
  while (-not (Test-Path -LiteralPath $ready)) {
    if ($proc.HasExited) { throw 'Host recording panel exited before ready' }
    if ((Test-Path -LiteralPath $StopFile) -or [DateTime]::UtcNow -gt $deadline) {
      throw 'Host recording panel did not become ready'
    }
    Start-Sleep -Milliseconds 100
  }
  $ack = Get-Content -LiteralPath $ready -Raw -Encoding utf8 | ConvertFrom-Json
  $observerPid = [int]$ack.pid
  if ($observerPid -ne $proc.Id) {
    $child = Get-CimInstance Win32_Process -Filter ("ProcessId = $observerPid")
    if (-not $child -or [int]$child.ParentProcessId -ne $proc.Id) {
      throw 'Host recording panel PID does not match'
    }
  }
  Set-Content -LiteralPath ($StopFile + '.pid') -Value $PID -Encoding ascii
  Write-Output ('ready pid=' + $PID + ' observerPid=' + $observerPid)
  while (-not (Test-Path -LiteralPath $StopFile)) {
    if (-not (Get-Process -Id $observerPid -ErrorAction SilentlyContinue)) {
      throw 'Host recording panel exited before stop'
    }
    Start-Sleep -Milliseconds 200
  }
}
finally {
  foreach ($target in @($observerPid, $proc.Id)) {
    if (-not $target) { continue }
    $running = Get-Process -Id $target -ErrorAction SilentlyContinue
    if ($running) {
      $running.CloseMainWindow() | Out-Null
      $running.WaitForExit(5000)
    }
    if (Get-Process -Id $target -ErrorAction SilentlyContinue) {
      Stop-Process -Id $target -Force -ErrorAction SilentlyContinue
    }
  }
  Write-Output 'closed'
}
