Run the program below once in the current Windows PowerShell tool. Do not write a file. Do not start pwsh.exe. Do not install anything. Do not change the timings or sizes. Do not hide, minimize, resize, move, or scroll any other window. Do not click, type, move the pointer, or send any mouse or keyboard input.

The program lasts about 26 seconds. Run it in the foreground and wait until it prints `restored`. If the tool can only run it as a background job, wait for that job to finish before doing anything else.

The program creates one window titled Arena panel and focuses its text box. It reads whether the IME is open for that text box, sets the opposite state, and reads it back. Only after that read-back matches does the window turn orange. It does not use the taskbar. It stays large, centered, and in front. Its header shows IME ON or IME OFF for the state that was read back. For 24 seconds only the hold count inside that window increases by 1 every 1.5 seconds. The program then restores the original IME state and closes the window. The size and position come from the primary screen. Do not hard-code a screen size.

If Add-Type throws, the program prints `visible=False`, the IME call fails, or the read-back is not the opposite state, close the window and stop after this run. Then execute this same program once outside the file sandbox. Do not rewrite it.

```powershell
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -Namespace Arena -Name Ime -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("imm32.dll")]
public static extern System.IntPtr ImmGetContext(System.IntPtr hWnd);
[System.Runtime.InteropServices.DllImport("imm32.dll")]
public static extern bool ImmReleaseContext(System.IntPtr hWnd, System.IntPtr hIMC);
[System.Runtime.InteropServices.DllImport("imm32.dll")]
public static extern bool ImmGetOpenStatus(System.IntPtr hIMC);
[System.Runtime.InteropServices.DllImport("imm32.dll")]
public static extern bool ImmSetOpenStatus(System.IntPtr hIMC, bool open);
'@
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
$form.BackColor = [System.Drawing.Color]::White
$box = New-Object System.Windows.Forms.TextBox
$box.Dock = 'Bottom'
$box.Height = 28
$form.Controls.Add($box)
$header = New-Object System.Windows.Forms.Label
$header.ForeColor = [System.Drawing.Color]::White
$header.Font = New-Object System.Drawing.Font 'Segoe UI', 42, ([System.Drawing.FontStyle]::Bold)
$header.TextAlign = 'MiddleCenter'
$header.Dock = 'Top'
$header.Height = 120
$label = New-Object System.Windows.Forms.Label
$label.ForeColor = [System.Drawing.Color]::White
$label.Font = New-Object System.Drawing.Font 'Segoe UI', 48, ([System.Drawing.FontStyle]::Bold)
$label.TextAlign = 'MiddleCenter'
$label.Dock = 'Fill'
$imc = [IntPtr]::Zero
$before = $false
$painted = $false
function Place {
  $script:form.WindowState = 'Normal'
  $script:form.ClientSize = New-Object System.Drawing.Size $script:panelW, $script:panelH
  $x = $script:bounds.X + [int](($script:bounds.Width - $script:panelW) / 2)
  $y = $script:bounds.Y + [int](($script:bounds.Height - $script:panelH) / 2)
  $script:form.Location = New-Object System.Drawing.Point $x, $y
  $script:form.Show()
  $script:form.Activate()
  $script:box.Focus() | Out-Null
  [System.Windows.Forms.Application]::DoEvents()
}
try {
  Place
  if (-not $form.Visible) { throw 'Arena panel was not visible' }
  $imc = [Arena.Ime]::ImmGetContext($box.Handle)
  if ($imc -eq [IntPtr]::Zero) { throw 'ImmGetContext failed' }
  $before = [Arena.Ime]::ImmGetOpenStatus($imc)
  $target = -not $before
  if (-not [Arena.Ime]::ImmSetOpenStatus($imc, $target)) { throw 'ImmSetOpenStatus failed' }
  $during = [Arena.Ime]::ImmGetOpenStatus($imc)
  if ($during -eq $before) { throw 'IME did not read back in the opposite state' }
  $orange = [System.Drawing.Color]::FromArgb(255, 120, 0)
  $form.BackColor = $orange
  if ($during) { $header.Text = 'IME ON' } else { $header.Text = 'IME OFF' }
  $header.BackColor = $orange
  $label.Text = 'HOLD 01'
  $label.BackColor = $orange
  $form.Controls.Add($header)
  $form.Controls.Add($label)
  $painted = $true
  [System.Windows.Forms.Application]::DoEvents()
  $deadline = [DateTime]::UtcNow.AddSeconds(24)
  $steps = 0
  while ([DateTime]::UtcNow -lt $deadline) {
    $steps++
    $label.Text = ('HOLD {0:00}' -f $steps)
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 1500
  }
  Write-Output ("ime-complete visible={0} before={1} during={2} steps={3} size={4}x{5} bounds={6},{7} {8}x{9}" -f $form.Visible, $before, $during, $steps, $panelW, $panelH, $bounds.X, $bounds.Y, $bounds.Width, $bounds.Height)
}
finally {
  if ($imc -ne [IntPtr]::Zero) {
    [Arena.Ime]::ImmSetOpenStatus($imc, $before) | Out-Null
    $after = [Arena.Ime]::ImmGetOpenStatus($imc)
    [Arena.Ime]::ImmReleaseContext($box.Handle, $imc) | Out-Null
    Write-Output ("ime-restored after={0}" -f $after)
  }
  if ($form -and $form.Visible) { $form.Close() }
  if (-not $painted) { Write-Output 'visible=False' }
  Write-Output 'restored'
}
```
