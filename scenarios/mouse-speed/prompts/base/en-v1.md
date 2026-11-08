Run the program below once in the current Windows PowerShell tool. Do not write a file. Do not start pwsh.exe. Do not install anything. Do not change the timings or sizes. Do not hide, minimize, resize, move, or scroll any other window. Do not click, move the pointer, or send any mouse or keyboard input.

The program lasts about 26 seconds. Run it in the foreground and wait until it prints `restored`. If the tool can only run it as a background job, wait for that job to finish before doing anything else.

The program reads the system mouse speed. It sets that speed to 1 and reads it back. It creates one orange window titled Arena panel. The window does not use the taskbar. It stays large, centered, and in front. Its header shows SPEED and the speed that was read back. For 24 seconds a white block inside that window moves right by that speed, in pixels, every 50 milliseconds, and returns to the left edge when it reaches the far side. The program then restores the original speed, reads it back, and closes the window. The size and position come from the primary screen. Do not hard-code a screen size.

If Add-Type throws, the program prints `visible=False`, the speed call fails, or the read-back is not 1, stop after this run and execute this same program once outside the file sandbox. Do not rewrite it.

```powershell
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -Namespace Arena -Name Speed -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll", EntryPoint="SystemParametersInfoW", SetLastError=true)]
public static extern bool GetSpeed(uint action, uint param, ref int value, uint winIni);
[System.Runtime.InteropServices.DllImport("user32.dll", EntryPoint="SystemParametersInfoW", SetLastError=true)]
public static extern bool SetSpeed(uint action, uint param, System.IntPtr value, uint winIni);
'@
$getSpeed = [uint32]0x70
$setSpeed = [uint32]0x71
$before = 0
if (-not [Arena.Speed]::GetSpeed($getSpeed, 0, [ref]$before, 0)) { throw 'SPI_GETMOUSESPEED failed' }
if (-not [Arena.Speed]::SetSpeed($setSpeed, 0, [IntPtr]1, 0)) { throw 'SPI_SETMOUSESPEED failed' }
$during = 0
if (-not [Arena.Speed]::GetSpeed($getSpeed, 0, [ref]$during, 0)) { throw 'SPI_GETMOUSESPEED failed' }
if ($during -ne 1) { throw 'mouse speed did not read back as 1' }
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$panelW = [Math]::Max(640, [int]($bounds.Width * 0.62))
$panelH = [Math]::Max(420, [int]($bounds.Height * 0.62))
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Arena panel'
$form.FormBorderStyle = 'FixedSingle'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.ControlBox = $false
$form.ShowInTaskbar = $false
$form.TopMost = $true
$form.StartPosition = 'Manual'
$form.BackColor = [System.Drawing.Color]::FromArgb(255, 120, 0)
$header = New-Object System.Windows.Forms.Label
$header.Text = "SPEED $during"
$header.ForeColor = [System.Drawing.Color]::White
$header.BackColor = [System.Drawing.Color]::FromArgb(255, 120, 0)
$header.Font = New-Object System.Drawing.Font 'Segoe UI', 42, ([System.Drawing.FontStyle]::Bold)
$header.TextAlign = 'MiddleCenter'
$header.Dock = 'Top'
$header.Height = 120
$form.Controls.Add($header)
$label = New-Object System.Windows.Forms.Label
$label.Text = 'SLOW'
$label.ForeColor = [System.Drawing.Color]::White
$label.BackColor = [System.Drawing.Color]::FromArgb(255, 120, 0)
$label.Font = New-Object System.Drawing.Font 'Segoe UI', 48, ([System.Drawing.FontStyle]::Bold)
$label.TextAlign = 'MiddleCenter'
$label.Dock = 'Fill'
$form.Controls.Add($label)
$track = New-Object System.Windows.Forms.Panel
$track.Height = 90
$track.Dock = 'Bottom'
$track.BackColor = [System.Drawing.Color]::FromArgb(255, 120, 0)
$mark = New-Object System.Windows.Forms.Panel
$mark.BackColor = [System.Drawing.Color]::White
$mark.Size = New-Object System.Drawing.Size 72, 36
$mark.Location = New-Object System.Drawing.Point 16, 27
$track.Controls.Add($mark)
$form.Controls.Add($track)
function Place {
  $script:form.WindowState = 'Normal'
  $script:form.ClientSize = New-Object System.Drawing.Size $script:panelW, $script:panelH
  $x = $script:bounds.X + [int](($script:bounds.Width - $script:panelW) / 2)
  $y = $script:bounds.Y + [int](($script:bounds.Height - $script:panelH) / 2)
  $script:form.Location = New-Object System.Drawing.Point $x, $y
  $script:form.Show()
  $script:form.Visible = $true
}
try {
  Place
  [System.Windows.Forms.Application]::DoEvents()
  if (-not $form.Visible) { throw 'Arena panel was not visible' }
  $deadline = [DateTime]::UtcNow.AddSeconds(24)
  $steps = 0
  $markX = 16
  $limit = [Math]::Max(80, $panelW - 88)
  while ([DateTime]::UtcNow -lt $deadline) {
    $mark.Left = $markX
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 50
    $steps++
    $markX += $during
    if ($markX -gt $limit) { $markX = 16 }
  }
  Write-Output ("speed-complete visible={0} before={1} during={2} steps={3} size={4}x{5} bounds={6},{7} {8}x{9}" -f $form.Visible, $before, $during, $steps, $panelW, $panelH, $bounds.X, $bounds.Y, $bounds.Width, $bounds.Height)
}
finally {
  $restore = $before
  if ($restore -lt 1 -or $restore -gt 20) { $restore = 10 }
  [Arena.Speed]::SetSpeed($setSpeed, 0, [IntPtr]$restore, 0) | Out-Null
  $after = 0
  [Arena.Speed]::GetSpeed($getSpeed, 0, [ref]$after, 0) | Out-Null
  if ($form -and $form.Visible) { $form.Close() }
  Write-Output ("speed-restored after={0}" -f $after)
  Write-Output 'restored'
}
```
