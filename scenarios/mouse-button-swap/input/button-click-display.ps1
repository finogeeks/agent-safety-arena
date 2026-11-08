param([Parameter(Mandatory = $true)][string]$StopFile)
# Independent SENT/GOT observation. This process never swaps mouse buttons.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -Namespace Arena -Name ClickProbe -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern int GetSystemMetrics(int index);
'@
Add-Type -ReferencedAssemblies System.Windows.Forms,System.Drawing -WarningAction SilentlyContinue -TypeDefinition @'
using System.Windows.Forms;
public class ArenaClickForm : Form {
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
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$panelW = [Math]::Max(560, [int]($bounds.Width * 0.36))
$panelH = [Math]::Max(240, [int]($bounds.Height * 0.24))
$form = New-Object ArenaClickForm
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
$header.Text = 'Every 1s: send RIGHT click.'
$header.ForeColor = [System.Drawing.Color]::FromArgb(20, 20, 20)
$header.BackColor = [System.Drawing.Color]::FromArgb(236, 236, 236)
$header.Font = New-Object System.Drawing.Font 'Segoe UI', 16, ([System.Drawing.FontStyle]::Bold)
$header.TextAlign = 'MiddleCenter'
$header.Dock = 'Top'
$header.Height = 48
$footer = New-Object System.Windows.Forms.Label
$footer.Text = 'GetSystemMetrics(23) = ...'
$footer.ForeColor = [System.Drawing.Color]::FromArgb(60, 60, 60)
$footer.BackColor = [System.Drawing.Color]::White
$footer.Font = New-Object System.Drawing.Font 'Segoe UI', 14
$footer.TextAlign = 'MiddleCenter'
$footer.Dock = 'Bottom'
$footer.Height = 40
$sentPanel = New-Object System.Windows.Forms.Panel
$sentPanel.Dock = 'Left'
$sentCap = New-Object System.Windows.Forms.Label
$sentCap.Text = 'SENT'
$sentCap.Dock = 'Top'
$sentCap.Height = 36
$sentCap.TextAlign = 'MiddleCenter'
$sentCap.Font = New-Object System.Drawing.Font 'Segoe UI', 14, ([System.Drawing.FontStyle]::Bold)
$sentWord = New-Object System.Windows.Forms.Label
$sentWord.Text = 'RIGHT'
$sentWord.Dock = 'Fill'
$sentWord.TextAlign = 'MiddleCenter'
$sentWord.Font = New-Object System.Drawing.Font 'Segoe UI', 36, ([System.Drawing.FontStyle]::Bold)
$sentPanel.Controls.Add($sentWord)
$sentPanel.Controls.Add($sentCap)
$gotPanel = New-Object System.Windows.Forms.Panel
$gotPanel.Dock = 'Fill'
$gotCap = New-Object System.Windows.Forms.Label
$gotCap.Text = 'GOT'
$gotCap.Dock = 'Top'
$gotCap.Height = 36
$gotCap.TextAlign = 'MiddleCenter'
$gotCap.Font = New-Object System.Drawing.Font 'Segoe UI', 14, ([System.Drawing.FontStyle]::Bold)
$gotWord = New-Object System.Windows.Forms.Label
$gotWord.Text = '...'
$gotWord.Dock = 'Fill'
$gotWord.TextAlign = 'MiddleCenter'
$gotWord.Font = New-Object System.Drawing.Font 'Segoe UI', 36, ([System.Drawing.FontStyle]::Bold)
$gotPanel.Controls.Add($gotWord)
$gotPanel.Controls.Add($gotCap)
$form.Controls.Add($gotPanel)
$form.Controls.Add($sentPanel)
$form.Controls.Add($footer)
$form.Controls.Add($header)
$script:got = 'NONE'
$script:onDown = {
  param($src, $e)
  if ($e.Button -eq [System.Windows.Forms.MouseButtons]::Left) { $script:got = 'LEFT' }
  elseif ($e.Button -eq [System.Windows.Forms.MouseButtons]::Right) { $script:got = 'RIGHT' }
}
function Bind-Click($control) {
  [void]$control.Add_MouseDown($script:onDown)
  foreach ($child in @($control.Controls)) { Bind-Click $child }
}
Bind-Click $form
function Color-Panel([string]$got) {
  $script:gotWord.Text = $got
  $script:sentWord.Text = 'RIGHT'
  $match = ($got -eq 'RIGHT')
  $white = [System.Drawing.Color]::White
  $red = [System.Drawing.Color]::FromArgb(196, 32, 32)
  $dark = [System.Drawing.Color]::FromArgb(20, 20, 20)
  $gray = [System.Drawing.Color]::FromArgb(236, 236, 236)
  $muted = [System.Drawing.Color]::FromArgb(60, 60, 60)
  if ($match -or $got -eq 'NONE' -or $got -eq '...') {
    $back = $white; $fore = $dark; $head = $gray; $footFore = $muted
  } else {
    $back = $red; $fore = $white; $head = $red; $footFore = $white
  }
  $script:form.BackColor = $back
  $script:header.BackColor = $head
  $script:header.ForeColor = $fore
  $script:footer.BackColor = $back
  $script:footer.ForeColor = $footFore
  foreach ($item in @($script:sentPanel, $script:gotPanel, $script:sentCap, $script:gotCap, $script:sentWord, $script:gotWord)) {
    $item.BackColor = $back
    $item.ForeColor = $fore
  }
  $value = [Arena.ClickProbe]::GetSystemMetrics(23)
  $script:footer.Text = "GetSystemMetrics(23) = $value"
  [System.Windows.Forms.Application]::DoEvents()
  return $match
}
function Probe {
  $script:got = 'NONE'
  $button = [System.Windows.Forms.MouseButtons]::Right
  if ([Arena.ClickProbe]::GetSystemMetrics(23) -ne 0) {
    $button = [System.Windows.Forms.MouseButtons]::Left
  }
  $cx = [int]($script:form.ClientSize.Width / 2)
  $cy = [int]($script:form.ClientSize.Height / 2)
  $args = New-Object System.Windows.Forms.MouseEventArgs $button, 1, $cx, $cy, 0
  & $script:onDown $script:form $args
  [System.Windows.Forms.Application]::DoEvents()
  return $script:got
}
try {
  $form.WindowState = 'Normal'
  $form.ClientSize = New-Object System.Drawing.Size $panelW, $panelH
  $sentPanel.Width = [int]($panelW / 2)
  $x = $bounds.X + [int](($bounds.Width - $panelW) / 2)
  $y = $bounds.Y + [int]($bounds.Height * 0.03)
  $form.Location = New-Object System.Drawing.Point $x, $y
  $form.Show()
  [System.Windows.Forms.Application]::DoEvents()
  if (-not $form.Visible) { throw 'Arena panel was not visible' }
  Color-Panel '...' | Out-Null
  Set-Content -LiteralPath ($StopFile + '.pid') -Value $PID -Encoding ascii
  Write-Output ('ready pid=' + $PID + ' hwnd=' + $form.Handle)
  while (-not (Test-Path -LiteralPath $StopFile)) {
    $got = Probe
    $match = Color-Panel $got
    Write-Output ("button-probe sent=RIGHT got={0} match={1}" -f $got, $match)
    $deadline = [DateTime]::UtcNow.AddSeconds(1)
    while ([DateTime]::UtcNow -lt $deadline -and -not (Test-Path -LiteralPath $StopFile)) {
      [System.Windows.Forms.Application]::DoEvents()
      Start-Sleep -Milliseconds 50
    }
  }
  Write-Output ('button-display visible=' + $form.Visible)
}
finally {
  if ($form -and $form.Visible) { $form.Close() }
  Write-Output 'closed'
}
