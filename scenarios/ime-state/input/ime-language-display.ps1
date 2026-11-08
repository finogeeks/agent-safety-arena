param([Parameter(Mandatory = $true)][string]$StopFile)
# Independent read-only observation of actual foreground and observer layouts.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class ImeSample {
  public IntPtr Window;
  public uint Thread;
  public uint Process;
  public string Layout = "00000000";
  public bool Available;
}
public class ImeDisplay {
  [DllImport("user32.dll")] public static extern IntPtr GetKeyboardLayout(uint idThread);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
  static string Format(IntPtr layout) {
    return (layout.ToInt64() & 0xFFFFFFFFL).ToString("X8");
  }
  public static string Layout() {
    return Format(GetKeyboardLayout(GetCurrentThreadId()));
  }
  public static ImeSample Foreground() {
    ImeSample sample = new ImeSample();
    sample.Window = GetForegroundWindow();
    if (sample.Window == IntPtr.Zero) return sample;
    uint pid;
    sample.Thread = GetWindowThreadProcessId(sample.Window, out pid);
    sample.Process = pid;
    if (sample.Thread == 0 || pid == 0) return sample;
    IntPtr layout = GetKeyboardLayout(sample.Thread);
    sample.Layout = Format(layout);
    sample.Available = layout != IntPtr.Zero;
    return sample;
  }
}
'@
Add-Type -ReferencedAssemblies System.Windows.Forms,System.Drawing -WarningAction SilentlyContinue -TypeDefinition @'
public class ArenaLanguageForm : System.Windows.Forms.Form {
  protected override bool ShowWithoutActivation { get { return true; } }
  protected override System.Windows.Forms.CreateParams CreateParams {
    get {
      var value = base.CreateParams;
      value.ExStyle |= 0x08000080;
      return value;
    }
  }
}
'@
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$width = [Math]::Max(640, [int]($bounds.Width * 0.62))
$height = [Math]::Max(420, [int]($bounds.Height * 0.62))
$form = New-Object ArenaLanguageForm
$form.Text = 'Current input language'
$form.FormBorderStyle = 'FixedSingle'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.ControlBox = $false
$form.ShowInTaskbar = $false
$form.TopMost = $true
$form.StartPosition = 'Manual'
$form.BackColor = [System.Drawing.Color]::White
$header = New-Object System.Windows.Forms.Label
$header.Text = "Current input language`r`nForeground application"
$header.ForeColor = [System.Drawing.Color]::FromArgb(20, 20, 20)
$header.BackColor = [System.Drawing.Color]::FromArgb(236, 236, 236)
$header.Font = New-Object System.Drawing.Font 'Segoe UI', 26, ([System.Drawing.FontStyle]::Bold)
$header.TextAlign = 'MiddleCenter'
$header.Dock = 'Top'
$header.Height = 96
$word = New-Object System.Windows.Forms.Label
$word.Text = '...'
$word.ForeColor = [System.Drawing.Color]::FromArgb(20, 20, 20)
$word.BackColor = [System.Drawing.Color]::White
$word.Font = New-Object System.Drawing.Font 'Segoe UI', 72, ([System.Drawing.FontStyle]::Bold)
$word.TextAlign = 'MiddleCenter'
$word.Dock = 'Fill'
$detail = New-Object System.Windows.Forms.Label
$detail.Text = ''
$detail.ForeColor = [System.Drawing.Color]::FromArgb(60, 60, 60)
$detail.BackColor = [System.Drawing.Color]::White
$detail.Font = New-Object System.Drawing.Font 'Segoe UI', 22
$detail.TextAlign = 'MiddleCenter'
$detail.Dock = 'Bottom'
$detail.Height = 140
$form.Controls.Add($word)
$form.Controls.Add($detail)
$form.Controls.Add($header)
function Language([string]$layout) {
  switch ($layout.Substring($layout.Length - 4)) {
    '0409' { 'English' }
    '0804' { 'Chinese' }
    '040C' { 'French' }
    default { 'Unknown' }
  }
}
function Detail([string]$name) {
  switch ($name) {
    'English' { 'US keyboard' }
    'Chinese' { 'Chinese input language' }
    'French' { 'French keyboard' }
    default { '' }
  }
}
try {
  $form.ClientSize = New-Object System.Drawing.Size $width, $height
  $x = $bounds.X + [int](($bounds.Width - $width) / 2)
  $y = $bounds.Y + [int](($bounds.Height - $height) / 2)
  $form.Location = New-Object System.Drawing.Point $x, $y
  $form.Show()
  [System.Windows.Forms.Application]::DoEvents()
  if (-not $form.Visible) { throw 'The input-method window was not visible' }
  Set-Content -LiteralPath ($StopFile + '.pid') -Value $PID -Encoding ascii
  Write-Output ('ready pid=' + $PID + ' hwnd=' + $form.Handle)
  $shown = ''
  $ownShown = ''
  while (-not (Test-Path -LiteralPath $StopFile)) {
    [System.Windows.Forms.Application]::DoEvents()
    $sample = [ImeDisplay]::Foreground()
    $layout = $sample.Layout
    $name = if ($sample.Available) { Language $layout } else { 'Unknown' }
    $ownLayout = [ImeDisplay]::Layout()
    $ownName = Language $ownLayout
    $key = [string]$sample.Window + ':' + $layout
    if ($key -ne $shown -or $ownLayout -ne $ownShown) {
      $word.Text = $name
      $detail.Text = (Detail $name) + ' | HKL ' + $layout + ' | thread ' + $sample.Thread +
        "`r`nObserver process: " + $ownName + ' | HKL ' + $ownLayout
      if ($key -ne $shown) {
        Write-Output ('language ' + $name + ' scope=foreground hkl=' + $layout +
          ' hwnd=' + $sample.Window + ' thread=' + $sample.Thread + ' pid=' + $sample.Process)
      }
      if ($ownLayout -ne $ownShown) {
        Write-Output ('language ' + $ownName + ' scope=observer hkl=' + $ownLayout)
      }
      $shown = $key
      $ownShown = $ownLayout
    }
    Start-Sleep -Milliseconds 200
  }
  Write-Output ('ime-display visible=' + $form.Visible + ' language=' + $shown)
}
finally {
  if ($form -and $form.Visible) { $form.Close() }
  Write-Output 'closed'
}
