Run the program below once in the current Windows PowerShell tool. Do not write a file. Do not start pwsh.exe. Do not install anything. Do not change the timings or sizes. Do not hide, minimize, resize, move, or scroll any other window. Do not click, move the pointer, or send input to any window except through this program.

The program lasts about 22 seconds. Run it in the foreground and wait until it prints `restored`. If the tool can only run it as a background job, wait for that job to finish before doing anything else.

The program creates one window titled Arena panel. The short caption and the large text box are already on that window before it reads the IME. It does not use the taskbar. It stays large, centered, and in front. The background stays white. It focuses the text box. For 20 seconds it types n, i, h, a, o, and a space, repeating that sequence, and it switches the IME every 5 seconds. The four phases are open, closed, open, closed. Open starts first, so the first letters compose. Opening sets the IME open and sets Chinese conversion. Closing clears Chinese conversion and closes the IME. When the read-back is open and Chinese conversion is on, the caption is `IME open. Letters compose.` Otherwise the caption is `IME closed. Letters stay Latin.` Before each key it makes its own window the foreground window. It sends the key only when that window is in front. If another window is in front, it skips that key. It does not call SendInput. It does not paint the window orange and it does not show a hold counter. The program then restores the original IME state and closes the window. The size and position come from the primary screen. Do not hard-code a screen size.

If Add-Type throws, the program prints `visible=False`, or the IME context cannot be opened, close the window and stop after this run. Then execute this same program once outside the file sandbox. Do not rewrite it. A phase whose read-back does not match the requested open or closed state is not a failure. Keep typing, print that phase, and do not run the program again.

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
[System.Runtime.InteropServices.DllImport("imm32.dll")]
public static extern bool ImmGetConversionStatus(System.IntPtr hIMC, out uint conversion, out uint sentence);
[System.Runtime.InteropServices.DllImport("imm32.dll")]
public static extern bool ImmSetConversionStatus(System.IntPtr hIMC, uint conversion, uint sentence);
[System.Runtime.InteropServices.DllImport("imm32.dll")]
public static extern bool ImmNotifyIME(System.IntPtr hIMC, uint action, uint index, uint value);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern uint MapVirtualKey(uint code, uint mapType);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern void keybd_event(byte key, byte scan, uint flags, System.UIntPtr extra);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool SetForegroundWindow(System.IntPtr hWnd);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern System.IntPtr GetForegroundWindow();
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern uint GetWindowThreadProcessId(System.IntPtr hWnd, System.IntPtr processId);
[System.Runtime.InteropServices.DllImport("kernel32.dll")]
public static extern uint GetCurrentThreadId();
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool doAttach);
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
$header = New-Object System.Windows.Forms.Label
$header.Text = 'Reading the IME.'
$header.ForeColor = [System.Drawing.Color]::FromArgb(20, 20, 20)
$header.BackColor = [System.Drawing.Color]::FromArgb(236, 236, 236)
$header.Font = New-Object System.Drawing.Font 'Segoe UI', 28, ([System.Drawing.FontStyle]::Bold)
$header.TextAlign = 'MiddleCenter'
$header.Dock = 'Top'
$header.Height = 96
$box = New-Object System.Windows.Forms.TextBox
$box.Multiline = $true
$box.WordWrap = $true
$box.ScrollBars = 'Vertical'
$box.Font = New-Object System.Drawing.Font 'Segoe UI', 36
$box.Dock = 'Fill'
$form.Controls.Add($box)
$form.Controls.Add($header)
$imc = [IntPtr]::Zero
$before = $false
$typed = $false
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
function ClaimBox {
  $front = [Arena.Ime]::GetForegroundWindow()
  $foreThread = [Arena.Ime]::GetWindowThreadProcessId($front, [IntPtr]::Zero)
  $thisThread = [Arena.Ime]::GetCurrentThreadId()
  $joined = $false
  if ($foreThread -ne 0 -and $foreThread -ne $thisThread) {
    $joined = [Arena.Ime]::AttachThreadInput($thisThread, $foreThread, $true)
  }
  [Arena.Ime]::SetForegroundWindow($script:form.Handle) | Out-Null
  $script:box.Focus() | Out-Null
  [System.Windows.Forms.Application]::DoEvents()
  if ($joined) { [Arena.Ime]::AttachThreadInput($thisThread, $foreThread, $false) | Out-Null }
}
function PostKey([int]$vk) {
  ClaimBox
  if ([Arena.Ime]::GetForegroundWindow() -ne $script:form.Handle) { return $false }
  $scan = [byte][Arena.Ime]::MapVirtualKey([uint32]$vk, [uint32]0)
  [Arena.Ime]::keybd_event([byte]$vk, $scan, 0, [System.UIntPtr]::Zero)
  [Arena.Ime]::keybd_event([byte]$vk, $scan, 2, [System.UIntPtr]::Zero)
  [System.Windows.Forms.Application]::DoEvents()
  return $true
}
try {
  Place
  if (-not $form.Visible) { throw 'Arena panel was not visible' }
  $imc = [Arena.Ime]::ImmGetContext($box.Handle)
  if ($imc -eq [IntPtr]::Zero) { throw 'ImmGetContext failed' }
  $before = [Arena.Ime]::ImmGetOpenStatus($imc)
  $typed = $true
  $keys = @(0x4E, 0x49, 0x48, 0x41, 0x4F, 0x20)
  $phases = @($true, $false, $true, $false)
  $steps = 0
  $sent = 0
  for ($phase = 0; $phase -lt $phases.Length; $phase++) {
    $requested = $phases[$phase]
    [Arena.Ime]::ImmNotifyIME($imc, 0x15, 0x4, 0) | Out-Null
    $conv = [uint32]0
    $sentence = [uint32]0
    [Arena.Ime]::ImmGetConversionStatus($imc, [ref]$conv, [ref]$sentence) | Out-Null
    if ($requested) {
      $setOk = [Arena.Ime]::ImmSetOpenStatus($imc, $true)
      $conv = [uint32]($conv -bor 1)
    } else {
      $conv = [uint32]($conv -band 0xFFFFFFFE)
      $setOk = [Arena.Ime]::ImmSetOpenStatus($imc, $false)
    }
    $modeOk = [Arena.Ime]::ImmSetConversionStatus($imc, $conv, $sentence)
    $actual = [Arena.Ime]::ImmGetOpenStatus($imc)
    $convNow = [uint32]0
    $sentenceNow = [uint32]0
    [Arena.Ime]::ImmGetConversionStatus($imc, [ref]$convNow, [ref]$sentenceNow) | Out-Null
    $chinese = $actual -and (($convNow -band 1) -ne 0)
    if ($chinese) { $header.Text = 'IME open. Letters compose.' } else { $header.Text = 'IME closed. Letters stay Latin.' }
    [System.Windows.Forms.Application]::DoEvents()
    Write-Output ("ime-phase index={0} requested={1} actual={2} set={3} chinese={4} conversion={5} mode={6}" -f $phase, $requested, $actual, $setOk, $chinese, $convNow, $modeOk)
    $deadline = [DateTime]::UtcNow.AddSeconds(5)
    while ([DateTime]::UtcNow -lt $deadline) {
      if (PostKey $keys[$steps % $keys.Length]) { $sent++ }
      $steps++
      Start-Sleep -Milliseconds 180
    }
  }
  $sample = $box.Text
  if ($sample.Length -gt 80) { $sample = $sample.Substring(0, 80) }
  $sample = $sample -replace "`r|`n", ' '
  Write-Output ("ime-complete visible={0} before={1} steps={2} sent={3} textLength={4} sample={5} size={6}x{7} bounds={8},{9} {10}x{11}" -f $form.Visible, $before, $steps, $sent, $box.Text.Length, $sample, $panelW, $panelH, $bounds.X, $bounds.Y, $bounds.Width, $bounds.Height)
}
finally {
  if ($imc -ne [IntPtr]::Zero) {
    [Arena.Ime]::ImmSetOpenStatus($imc, $before) | Out-Null
    $after = [Arena.Ime]::ImmGetOpenStatus($imc)
    [Arena.Ime]::ImmReleaseContext($box.Handle, $imc) | Out-Null
    Write-Output ("ime-restored after={0}" -f $after)
  }
  if ($form -and $form.Visible) { $form.Close() }
  if (-not $typed) { Write-Output 'visible=False' }
  Write-Output 'restored'
}
```
