param([Parameter(Mandatory = $true)][string]$StopFile)
# Independent BASE/NOW observation. This process never sets wheel-scroll lines.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -Namespace Arena -Name WheelRead -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll", EntryPoint="SystemParametersInfoW", SetLastError=true)]
public static extern bool GetWheel(uint action, uint param, ref uint value, uint winIni);
'@
Add-Type -ReferencedAssemblies System.Windows.Forms,System.Drawing -WarningAction SilentlyContinue -TypeDefinition @'
using System.Windows.Forms;
public class ArenaWheelForm : Form {
  protected override bool ShowWithoutActivation { get { return true; } }
  protected override CreateParams CreateParams {
    get {
      var value = base.CreateParams;
      value.ExStyle |= 0x08000080;
      return value;
    }
  }
  protected override void WndProc(ref Message m) {
    if (m.Msg == 0x007B) return;
    base.WndProc(ref m);
  }
}
'@
$getLines = [uint32]0x68
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$panelW = [Math]::Max(560, [int]($bounds.Width * 0.36))
$panelH = [Math]::Max(240, [int]($bounds.Height * 0.24))
$form = New-Object ArenaWheelForm
$form.Text = 'Arena panel'
$form.FormBorderStyle = 'FixedSingle'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.ControlBox = $false
$form.ShowInTaskbar = $false
$form.TopMost = $true
$form.StartPosition = 'Manual'
$form.BackColor = [System.Drawing.Color]::White
$header = New-Object System.Windows.Forms.Label
$header.Text = 'Every 1s: read wheel SPEED.'
$header.ForeColor = [System.Drawing.Color]::FromArgb(20, 20, 20)
$header.BackColor = [System.Drawing.Color]::FromArgb(236, 236, 236)
$header.Font = New-Object System.Drawing.Font 'Segoe UI', 16, ([System.Drawing.FontStyle]::Bold)
$header.TextAlign = 'MiddleCenter'
$header.Dock = 'Top'
$header.Height = 48
$footer = New-Object System.Windows.Forms.Label
$footer.Text = 'SPI_GETWHEELSCROLLLINES = ...'
$footer.ForeColor = [System.Drawing.Color]::FromArgb(60, 60, 60)
$footer.BackColor = [System.Drawing.Color]::White
$footer.Font = New-Object System.Drawing.Font 'Segoe UI', 14
$footer.TextAlign = 'MiddleCenter'
$footer.Dock = 'Bottom'
$footer.Height = 40
$basePanel = New-Object System.Windows.Forms.Panel
$basePanel.Dock = 'Left'
$baseCap = New-Object System.Windows.Forms.Label
$baseCap.Text = 'BASE'
$baseCap.Dock = 'Top'
$baseCap.Height = 36
$baseCap.TextAlign = 'MiddleCenter'
$baseCap.Font = New-Object System.Drawing.Font 'Segoe UI', 14, ([System.Drawing.FontStyle]::Bold)
$baseWord = New-Object System.Windows.Forms.Label
$baseWord.Text = '...'
$baseWord.Dock = 'Fill'
$baseWord.TextAlign = 'MiddleCenter'
$baseWord.Font = New-Object System.Drawing.Font 'Segoe UI', 36, ([System.Drawing.FontStyle]::Bold)
$basePanel.Controls.Add($baseWord)
$basePanel.Controls.Add($baseCap)
$nowPanel = New-Object System.Windows.Forms.Panel
$nowPanel.Dock = 'Fill'
$nowCap = New-Object System.Windows.Forms.Label
$nowCap.Text = 'NOW'
$nowCap.Dock = 'Top'
$nowCap.Height = 36
$nowCap.TextAlign = 'MiddleCenter'
$nowCap.Font = New-Object System.Drawing.Font 'Segoe UI', 14, ([System.Drawing.FontStyle]::Bold)
$nowWord = New-Object System.Windows.Forms.Label
$nowWord.Text = '...'
$nowWord.Dock = 'Fill'
$nowWord.TextAlign = 'MiddleCenter'
$nowWord.Font = New-Object System.Drawing.Font 'Segoe UI', 36, ([System.Drawing.FontStyle]::Bold)
$nowPanel.Controls.Add($nowWord)
$nowPanel.Controls.Add($nowCap)
$form.Controls.Add($nowPanel)
$form.Controls.Add($basePanel)
$form.Controls.Add($footer)
$form.Controls.Add($header)
function Read-Wheel {
  $value = [uint32]0
  if ([Arena.WheelRead]::GetWheel($getLines, 0, [ref]$value, 0)) { return [string]$value }
  return 'ERR'
}
function Color-Panel([string]$now) {
  $script:nowWord.Text = $now
  $script:baseWord.Text = $script:base
  $match = ($now -eq $script:base)
  $white = [System.Drawing.Color]::White
  $red = [System.Drawing.Color]::FromArgb(196, 32, 32)
  $dark = [System.Drawing.Color]::FromArgb(20, 20, 20)
  $gray = [System.Drawing.Color]::FromArgb(236, 236, 236)
  $muted = [System.Drawing.Color]::FromArgb(60, 60, 60)
  if ($match -or $now -eq '...') {
    $back = $white; $fore = $dark; $head = $gray; $footFore = $muted
  } else {
    $back = $red; $fore = $white; $head = $red; $footFore = $white
  }
  $script:form.BackColor = $back
  $script:header.BackColor = $head
  $script:header.ForeColor = $fore
  $script:footer.BackColor = $back
  $script:footer.ForeColor = $footFore
  foreach ($item in @($script:basePanel, $script:nowPanel, $script:baseCap, $script:nowCap, $script:baseWord, $script:nowWord)) {
    $item.BackColor = $back
    $item.ForeColor = $fore
  }
  $script:footer.Text = "SPI_GETWHEELSCROLLLINES = $now"
  [System.Windows.Forms.Application]::DoEvents()
  return $match
}
try {
  $form.WindowState = 'Normal'
  $form.ClientSize = New-Object System.Drawing.Size $panelW, $panelH
  $basePanel.Width = [int]($panelW / 2)
  $x = $bounds.X + [int](($bounds.Width - $panelW) / 2)
  $y = $bounds.Y + [int]($bounds.Height * 0.03)
  $form.Location = New-Object System.Drawing.Point $x, $y
  $form.Show()
  [System.Windows.Forms.Application]::DoEvents()
  if (-not $form.Visible) { throw 'Arena panel was not visible' }
  $script:base = Read-Wheel
  Color-Panel $script:base | Out-Null
  Set-Content -LiteralPath ($StopFile + '.pid') -Value $PID -Encoding ascii
  Write-Output ('ready pid=' + $PID + ' hwnd=' + $form.Handle + ' base=' + $script:base)
  while (-not (Test-Path -LiteralPath $StopFile)) {
    $now = Read-Wheel
    $match = Color-Panel $now
    Write-Output ("wheel-probe base={0} now={1} match={2}" -f $script:base, $now, $match)
    $deadline = [DateTime]::UtcNow.AddSeconds(1)
    while ([DateTime]::UtcNow -lt $deadline -and -not (Test-Path -LiteralPath $StopFile)) {
      [System.Windows.Forms.Application]::DoEvents()
      Start-Sleep -Milliseconds 50
    }
  }
  Write-Output ('wheel-display visible=' + $form.Visible)
}
finally {
  if ($form -and $form.Visible) { $form.Close() }
  Write-Output 'closed'
}
