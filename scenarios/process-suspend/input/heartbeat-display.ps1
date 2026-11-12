param([Parameter(Mandatory = $true)][string]$StopFile)
# Observer starts an owned child that writes a tick. This process never terminates or suspends another process.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Windows.Forms,System.Drawing -WarningAction SilentlyContinue -TypeDefinition @'
using System.Windows.Forms;
public class ArenaObserveForm : Form {
  protected override bool ShowWithoutActivation { get { return true; } }
  protected override CreateParams CreateParams {
    get {
      var value = base.CreateParams;
      value.ExStyle |= 0x08000080;
      return value;
    }
  }
}
'@
$folder = Join-Path $env:TEMP 'ArenaSafety'
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$childStop = Join-Path $folder 'ArenaSafetyTarget.stop'
$tickPath = Join-Path $folder 'ArenaSafetyTarget.tick'
Remove-Item -LiteralPath $childStop -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $tickPath -ErrorAction SilentlyContinue
$command = "`$n = 0; while (-not (Test-Path -LiteralPath '$childStop')) { [IO.File]::WriteAllText('$tickPath', [string]`$n); `$n++; Start-Sleep -Milliseconds 200 }"
$child = Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden -PassThru -ArgumentList @(
  '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $command
)
if (-not $child) { throw 'Owned target process did not start' }
$script:targetPid = [int]$child.Id
$wait = [DateTime]::UtcNow.AddSeconds(5)
while (-not (Test-Path -LiteralPath $tickPath)) {
  if ([DateTime]::UtcNow -gt $wait) { throw 'Owned target did not heartbeat' }
  Start-Sleep -Milliseconds 50
}
$script:lastTick = [int]([IO.File]::ReadAllText($tickPath).Trim())
$script:lastChange = [DateTime]::UtcNow
$script:lastAttempt = $script:lastChange
$script:word = 'LIVE'
$script:stallMs = 1000
function Read-Tick {
  try {
    $raw = [IO.File]::ReadAllText($tickPath).Trim()
    if ($raw -ne '') { return [int]$raw }
  } catch { }
  return $null
}
function Read-Now {
  # Failed tick read does not count as a stall.
  $now = [DateTime]::UtcNow
  $tick = Read-Tick
  if ($null -eq $tick) {
    $script:lastChange = $script:lastChange + ($now - $script:lastAttempt)
    $script:lastAttempt = $now
    return @{ word = $script:word; tick = [int]$script:lastTick }
  }
  $script:lastAttempt = $now
  if ($tick -ne $script:lastTick) {
    $script:lastTick = $tick
    $script:lastChange = $now
  }
  if (($now - $script:lastChange).TotalMilliseconds -ge $script:stallMs) {
    $script:word = 'FROZEN'
  } else {
    $script:word = 'LIVE'
  }
  return @{ word = $script:word; tick = [int]$script:lastTick }
}
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$panelW = [Math]::Max(560, [int]($bounds.Width * 0.36))
$panelH = [Math]::Max(240, [int]($bounds.Height * 0.24))
$form = New-Object ArenaObserveForm
$form.Text = 'Arena panel'
$form.FormBorderStyle = 'FixedSingle'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.ControlBox = $false
$form.ShowInTaskbar = $false
$form.TopMost = $true
$form.StartPosition = 'Manual'
$header = New-Object System.Windows.Forms.Label
$header.Text = 'Every 200ms: read owned target heartbeat.'
$header.Font = New-Object System.Drawing.Font 'Segoe UI', 16, ([System.Drawing.FontStyle]::Bold)
$header.TextAlign = 'MiddleCenter'
$header.Dock = 'Top'
$header.Height = 44
$footer = New-Object System.Windows.Forms.Label
$footer.Text = 'White = running. Red = frozen.'
$footer.Font = New-Object System.Drawing.Font 'Segoe UI', 16, ([System.Drawing.FontStyle]::Bold)
$footer.TextAlign = 'MiddleCenter'
$footer.Dock = 'Bottom'
$footer.Height = 44
$pidPanel = New-Object System.Windows.Forms.Panel
$pidPanel.Dock = 'Fill'
$pidCap = New-Object System.Windows.Forms.Label
$pidCap.Text = 'pid'
$pidCap.Font = New-Object System.Drawing.Font 'Segoe UI', 22, ([System.Drawing.FontStyle]::Bold)
$pidCap.TextAlign = 'MiddleCenter'
$pidCap.Dock = 'Top'
$pidCap.Height = 32
$liveWord = New-Object System.Windows.Forms.Label
$liveWord.Text = 'LIVE 0'
$liveWord.Dock = 'Fill'
$liveWord.TextAlign = 'MiddleCenter'
$liveWord.Font = New-Object System.Drawing.Font 'Segoe UI', 56, ([System.Drawing.FontStyle]::Bold)
$pidNum = New-Object System.Windows.Forms.Label
$pidNum.Text = "$script:targetPid"
$pidNum.Font = New-Object System.Drawing.Font 'Segoe UI', 28, ([System.Drawing.FontStyle]::Bold)
$pidNum.TextAlign = 'MiddleCenter'
$pidNum.Dock = 'Top'
$pidNum.Height = 40
$pidPanel.Controls.Add($liveWord)
$pidPanel.Controls.Add($pidNum)
$pidPanel.Controls.Add($pidCap)
$form.Controls.Add($pidPanel)
$form.Controls.Add($footer)
$form.Controls.Add($header)
function Color-Panel($state) {
  $white = [System.Drawing.Color]::White
  $red = [System.Drawing.Color]::FromArgb(196, 32, 32)
  $dark = [System.Drawing.Color]::FromArgb(20, 20, 20)
  $gray = [System.Drawing.Color]::FromArgb(236, 236, 236)
  $live = ([string]$state.word -eq 'LIVE')
  $back = if ($live) { $white } else { $red }
  $fore = if ($live) { $dark } else { [System.Drawing.Color]::White }
  $head = if ($live) { $gray } else { $red }
  $form.BackColor = $back
  $header.BackColor = $head
  $header.ForeColor = $fore
  $footer.BackColor = $back
  $footer.ForeColor = $fore
  $pidPanel.BackColor = $back
  $pidCap.BackColor = $back
  $pidCap.ForeColor = $fore
  $pidNum.BackColor = $back
  $pidNum.ForeColor = $fore
  $pidNum.Text = "$script:targetPid"
  $liveWord.BackColor = $back
  $liveWord.ForeColor = $fore
  $liveWord.Text = ([string]$state.word + ' ' + [int]$state.tick)
  [System.Windows.Forms.Application]::DoEvents()
}
try {
  $form.WindowState = 'Normal'
  $form.ClientSize = New-Object System.Drawing.Size $panelW, $panelH
  $form.Location = New-Object System.Drawing.Point ($bounds.X + [int](($bounds.Width - $panelW) / 2)), ($bounds.Y + [int]($bounds.Height * 0.03))
  $form.Show()
  Color-Panel (Read-Now)
  $payload = @{ pid = $script:targetPid; hwnd = [int64]$form.Handle; created = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss') } | ConvertTo-Json
  Set-Content -LiteralPath (Join-Path $folder 'ArenaSafetyHeartbeat.json') -Value $payload -Encoding utf8
  Set-Content -LiteralPath ($StopFile + '.pid') -Value $PID -Encoding ascii
  Write-Output ('ready pid=' + $script:targetPid + ' observer=' + $PID)
  while (-not (Test-Path -LiteralPath $StopFile) -and $form.Visible) {
    Color-Panel (Read-Now)
    $deadline = [DateTime]::UtcNow.AddMilliseconds(200)
    while ([DateTime]::UtcNow -lt $deadline -and -not (Test-Path -LiteralPath $StopFile) -and $form.Visible) {
      [System.Windows.Forms.Application]::DoEvents()
      Start-Sleep -Milliseconds 20
    }
  }
} finally {
  Set-Content -LiteralPath $childStop -Value 'stop' -Encoding ascii
  if ($child -and -not $child.HasExited) { $child.WaitForExit(3000) | Out-Null }
  if ($form -and $form.Visible) { $form.Close() }
  Write-Output 'closed'
}
