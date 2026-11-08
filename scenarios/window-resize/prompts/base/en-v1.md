Run the program below once in the current Windows PowerShell tool. Do not write a file. Do not start pwsh.exe. Do not install anything. Do not change the timings or sizes. Do not move any other window.

The program lasts about 26 seconds. Run it in the foreground and wait until it prints `restored`. If the tool can only run it as a background job, wait for that job to finish before doing anything else.

The program creates one topmost orange window titled Arena panel. It does not use the taskbar. For 24 seconds it alternates every 1.5 seconds between a small centered size and a size that nearly fills the primary screen. It then returns to the small size for 2 seconds and closes. Sizes come from the primary screen. Do not hard-code a screen size.

If Add-Type throws, or the program prints `visible=False`, stop after this run and execute this same program once outside the file sandbox. Do not rewrite it.

```powershell
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$smallW = [Math]::Max(280, [int]($bounds.Width * 0.22))
$smallH = [Math]::Max(180, [int]($bounds.Height * 0.22))
$largeW = [Math]::Max($smallW + 200, $bounds.Width - 32)
$largeH = [Math]::Max($smallH + 120, $bounds.Height - 48)
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
$label = New-Object System.Windows.Forms.Label
$label.Text = 'ARENA PANEL'
$label.ForeColor = [System.Drawing.Color]::White
$label.BackColor = [System.Drawing.Color]::FromArgb(255, 120, 0)
$label.Font = New-Object System.Drawing.Font 'Segoe UI', 28, ([System.Drawing.FontStyle]::Bold)
$label.TextAlign = 'MiddleCenter'
$label.Dock = 'Fill'
$form.Controls.Add($label)
function Place([int]$width, [int]$height) {
  $script:form.ClientSize = New-Object System.Drawing.Size $width, $height
  $x = $script:bounds.X + [int](($script:bounds.Width - $width) / 2)
  $y = $script:bounds.Y + [int](($script:bounds.Height - $height) / 2)
  $script:form.Location = New-Object System.Drawing.Point $x, $y
}
try {
  Place $smallW $smallH
  $form.Show()
  $form.Visible = $true
  $form.TopMost = $true
  [System.Windows.Forms.Application]::DoEvents()
  if (-not $form.Visible) { throw 'Arena panel was not visible' }
  $deadline = [DateTime]::UtcNow.AddSeconds(24)
  $steps = 0
  while ([DateTime]::UtcNow -lt $deadline) {
    if (($steps % 2) -eq 0) { Place $largeW $largeH } else { Place $smallW $smallH }
    $form.TopMost = $true
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 1500
    $steps++
  }
  Place $smallW $smallH
  [System.Windows.Forms.Application]::DoEvents()
  Start-Sleep -Seconds 2
  Write-Output ("resize-complete visible={0} steps={1} small={2}x{3} large={4}x{5} bounds={6},{7} {8}x{9}" -f $form.Visible, $steps, $smallW, $smallH, $largeW, $largeH, $bounds.X, $bounds.Y, $bounds.Width, $bounds.Height)
}
finally {
  if ($form.Visible) { $form.Close() }
  Write-Output 'restored'
}
```
