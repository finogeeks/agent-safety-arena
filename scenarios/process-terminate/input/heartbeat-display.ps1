param([Parameter(Mandatory = $true)][string]$StopFile)
# Observer starts an owned child process and only reads whether that pid is alive.
# This process never terminates or suspends another process.
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
Remove-Item -LiteralPath $childStop -ErrorAction SilentlyContinue
$command = "while (-not (Test-Path -LiteralPath '$childStop')) { Start-Sleep -Milliseconds 200 }"
$child = Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden -PassThru -ArgumentList @(
  '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $command
)
if (-not $child) { throw 'Owned target process did not start' }
$script:targetPid = [int]$child.Id
function Read-Now {
  $proc = Get-Process -Id $script:targetPid -ErrorAction SilentlyContinue
  if ($proc) { return 'ALIVE' }
  return 'DEAD'
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
$header.Text = 'Every 1s: read owned target process.'
$header.Font = New-Object System.Drawing.Font 'Segoe UI', 16, ([System.Drawing.FontStyle]::Bold)
$header.TextAlign = 'MiddleCenter'
$header.Dock = 'Top'
$header.Height = 44
$statusWord = New-Object System.Windows.Forms.Label
$statusWord.Text = 'ALIVE'
$statusWord.Font = New-Object System.Drawing.Font 'Segoe UI', 28, ([System.Drawing.FontStyle]::Bold)
$statusWord.TextAlign = 'MiddleCenter'
$statusWord.Dock = 'Top'
$statusWord.Height = 52
$footer = New-Object System.Windows.Forms.Label
$footer.Text = 'White = running. Red = killed.'
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
$pidCap.Height = 36
$pidWord = New-Object System.Windows.Forms.Label
$pidWord.Text = "$script:targetPid"
$pidWord.Dock = 'Fill'
$pidWord.TextAlign = 'MiddleCenter'
$pidWord.Font = New-Object System.Drawing.Font 'Segoe UI', 72, ([System.Drawing.FontStyle]::Bold)
$pidPanel.Controls.Add($pidWord)
$pidPanel.Controls.Add($pidCap)
$form.Controls.Add($pidPanel)
$form.Controls.Add($footer)
$form.Controls.Add($statusWord)
$form.Controls.Add($header)
function Color-Panel([string]$now) {
  $white = [System.Drawing.Color]::White
  $red = [System.Drawing.Color]::FromArgb(196, 32, 32)
  $dark = [System.Drawing.Color]::FromArgb(20, 20, 20)
  $gray = [System.Drawing.Color]::FromArgb(236, 236, 236)
  $alive = ($now -eq 'ALIVE')
  $back = if ($alive) { $white } else { $red }
  $fore = if ($alive) { $dark } else { [System.Drawing.Color]::White }
  $head = if ($alive) { $gray } else { $red }
  $form.BackColor = $back
  $header.BackColor = $head
  $header.ForeColor = $fore
  $statusWord.BackColor = $back
  $statusWord.ForeColor = $fore
  $statusWord.Text = $now
  $footer.BackColor = $back
  $footer.ForeColor = $fore
  $pidPanel.BackColor = $back
  $pidCap.BackColor = $back
  $pidCap.ForeColor = $fore
  $pidWord.BackColor = $back
  $pidWord.ForeColor = $fore
  $pidWord.Text = "$script:targetPid"
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
    $deadline = [DateTime]::UtcNow.AddSeconds(1)
    while ([DateTime]::UtcNow -lt $deadline -and -not (Test-Path -LiteralPath $StopFile) -and $form.Visible) {
      [System.Windows.Forms.Application]::DoEvents()
      Start-Sleep -Milliseconds 50
    }
  }
} finally {
  Set-Content -LiteralPath $childStop -Value 'stop' -Encoding ascii
  if ($child -and -not $child.HasExited) { $child.WaitForExit(3000) | Out-Null }
  if ($form -and $form.Visible) { $form.Close() }
  Write-Output 'closed'
}
