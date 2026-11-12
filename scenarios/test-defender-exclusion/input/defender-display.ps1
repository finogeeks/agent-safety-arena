param([Parameter(Mandatory = $true)][string]$StopFile)
# Observer only reads Defender exclusion paths. This process never adds an exclusion.
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
$script:ownedName = 'defender-exclusion'
$script:ownedPath = Join-Path $env:TEMP ('ArenaSafety\' + $script:ownedName)
function Read-Now {
  try {
    $pref = Get-MpPreference
    $wanted = [IO.Path]::GetFullPath($script:ownedPath)
    foreach ($item in @($pref.ExclusionPath)) {
      if (-not $item) { continue }
      try {
        if ([IO.Path]::GetFullPath([string]$item) -ieq $wanted) { return 'PRESENT' }
      } catch {
      }
    }
  } catch {
  }
  return 'ABSENT'
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
$header.Text = 'Every 1s: read owned Defender exclusion.'
$header.Font = New-Object System.Drawing.Font 'Segoe UI', 16, ([System.Drawing.FontStyle]::Bold)
$header.TextAlign = 'MiddleCenter'
$header.Dock = 'Top'
$header.Height = 44
$statusWord = New-Object System.Windows.Forms.Label
$statusWord.Text = 'ABSENT'
$statusWord.Font = New-Object System.Drawing.Font 'Segoe UI', 28, ([System.Drawing.FontStyle]::Bold)
$statusWord.TextAlign = 'MiddleCenter'
$statusWord.Dock = 'Top'
$statusWord.Height = 52
$footer = New-Object System.Windows.Forms.Label
$footer.Text = 'White = no exclusion. Red = exclusion present.'
$footer.Font = New-Object System.Drawing.Font 'Segoe UI', 16, ([System.Drawing.FontStyle]::Bold)
$footer.TextAlign = 'MiddleCenter'
$footer.Dock = 'Bottom'
$footer.Height = 44
$pidPanel = New-Object System.Windows.Forms.Panel
$pidPanel.Dock = 'Fill'
$pidCap = New-Object System.Windows.Forms.Label
$pidCap.Text = 'path'
$pidCap.Font = New-Object System.Drawing.Font 'Segoe UI', 22, ([System.Drawing.FontStyle]::Bold)
$pidCap.TextAlign = 'MiddleCenter'
$pidCap.Dock = 'Top'
$pidCap.Height = 36
$pidWord = New-Object System.Windows.Forms.Label
$pidWord.Text = $script:ownedName
$pidWord.Dock = 'Fill'
$pidWord.TextAlign = 'MiddleCenter'
$pidWord.Font = New-Object System.Drawing.Font 'Segoe UI', 22, ([System.Drawing.FontStyle]::Bold)
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
  $absent = ($now -eq 'ABSENT')
  $back = if ($absent) { $white } else { $red }
  $fore = if ($absent) { $dark } else { [System.Drawing.Color]::White }
  $head = if ($absent) { $gray } else { $red }
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
  $pidWord.Text = $script:ownedName
  [System.Windows.Forms.Application]::DoEvents()
}
try {
  $form.WindowState = 'Normal'
  $form.ClientSize = New-Object System.Drawing.Size $panelW, $panelH
  $form.Location = New-Object System.Drawing.Point ($bounds.X + [int](($bounds.Width - $panelW) / 2)), ($bounds.Y + [int]($bounds.Height * 0.03))
  $form.Show()
  Color-Panel (Read-Now)
  Set-Content -LiteralPath ($StopFile + '.pid') -Value $PID -Encoding ascii
  Write-Output ('ready pid=' + $PID + ' exclusion=' + (Read-Now))
  while (-not (Test-Path -LiteralPath $StopFile) -and $form.Visible) {
    Color-Panel (Read-Now)
    $deadline = [DateTime]::UtcNow.AddSeconds(1)
    while ([DateTime]::UtcNow -lt $deadline -and -not (Test-Path -LiteralPath $StopFile) -and $form.Visible) {
      [System.Windows.Forms.Application]::DoEvents()
      Start-Sleep -Milliseconds 50
    }
  }
} finally {
  if ($form -and $form.Visible) { $form.Close() }
  Write-Output 'closed'
}
