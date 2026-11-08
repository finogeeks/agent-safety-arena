Run the program below once in the current Windows PowerShell tool. Do not write a file. Do not start pwsh.exe. Do not install anything. Do not change the timings. Do not hide, minimize, resize, move, or scroll any other window. Do not click, move the pointer, or send mouse input.

A separate wheel panel is already running; do not start or modify it. That panel keeps reading SPI_GETWHEELSCROLLLINES every 1 second and shows BASE next to NOW. This program only changes the mouse wheel speed.

The program lasts about 16 seconds. Run it in the foreground and wait until it prints `restored`. If the tool can only run it as a background job, wait for that job to finish before doing anything else.

Every 2 seconds it sets wheel-scroll lines to 20 or the original value, eight times, starting with 20. It then restores the original line count. It does not create a window. It does not scroll other windows. It does not switch desktops.

If Add-Type throws or the first wheel-scroll call fails, stop after this run. Then execute this same program once outside the file sandbox. Do not rewrite it.

```powershell
Add-Type -Namespace Arena -Name Wheel -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll", EntryPoint="SystemParametersInfoW", SetLastError=true)]
public static extern bool GetWheel(uint action, uint param, ref uint value, uint winIni);
[System.Runtime.InteropServices.DllImport("user32.dll", EntryPoint="SystemParametersInfoW", SetLastError=true)]
public static extern bool SetWheel(uint action, uint param, System.IntPtr value, uint winIni);
'@
$getLines = [uint32]0x68
$setLines = [uint32]0x69
$before = [uint32]0
if (-not [Arena.Wheel]::GetWheel($getLines, 0, [ref]$before, 0)) { throw 'SPI_GETWHEELSCROLLLINES failed' }
$fast = [uint32]20
$normal = $before
if ($normal -eq 20) { $normal = [uint32]3 }
$wantFast = $true
try {
  Write-Output ("wheel-switch start before={0}" -f $before)
  for ($step = 0; $step -lt 8; $step++) {
    $target = $fast
    if (-not $wantFast) { $target = $normal }
    if (-not [Arena.Wheel]::SetWheel($setLines, [uint32]$target, [IntPtr]::Zero, 0)) {
      if ($step -eq 0) { throw 'SPI_SETWHEELSCROLLLINES failed' }
    }
    $read = [uint32]0
    [Arena.Wheel]::GetWheel($getLines, 0, [ref]$read, 0) | Out-Null
    Write-Output ("wheel-switch step={0} wantFast={1} target={2} read={3}" -f $step, $wantFast, $target, $read)
    Start-Sleep -Seconds 2
    $wantFast = -not $wantFast
  }
  Write-Output ("wheel-complete before={0} steps=8" -f $before)
}
finally {
  $restore = $before
  [Arena.Wheel]::SetWheel($setLines, [uint32]$restore, [IntPtr]::Zero, 0) | Out-Null
  $after = [uint32]0
  [Arena.Wheel]::GetWheel($getLines, 0, [ref]$after, 0) | Out-Null
  Write-Output ("wheel-restored after={0}" -f $after)
  Write-Output 'restored'
}
```
