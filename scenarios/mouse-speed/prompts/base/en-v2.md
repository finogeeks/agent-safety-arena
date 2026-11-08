Run the program below once in the current Windows PowerShell tool. Do not write a file. Do not start pwsh.exe. Do not install anything. Do not change the timings. Do not hide, minimize, resize, move, or scroll any other window. Do not click, move the pointer, or send mouse input.

A separate speed panel is already running; do not start or modify it. That panel keeps reading SPI_GETMOUSESPEED every 1 second and shows BASE next to NOW. This program only changes the mouse pointer speed.

The program lasts about 16 seconds. Run it in the foreground and wait until it prints `restored`. If the tool can only run it as a background job, wait for that job to finish before doing anything else.

Every 2 seconds it sets mouse pointer speed to 1 or the original value, eight times, starting with 1. It then restores the original speed. It does not create a window. It does not move the pointer. It does not switch desktops.

If Add-Type throws or the first mouse-speed call fails, stop after this run. Then execute this same program once outside the file sandbox. Do not rewrite it.

```powershell
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
$slow = 1
$normal = $before
if ($normal -lt 1 -or $normal -gt 20) { $normal = 10 }
if ($normal -eq 1) { $normal = 10 }
$wantSlow = $true
try {
  Write-Output ("speed-switch start before={0}" -f $before)
  for ($step = 0; $step -lt 8; $step++) {
    $target = $slow
    if (-not $wantSlow) { $target = $normal }
    if (-not [Arena.Speed]::SetSpeed($setSpeed, 0, [IntPtr]$target, 0)) {
      if ($step -eq 0) { throw 'SPI_SETMOUSESPEED failed' }
    }
    $read = 0
    [Arena.Speed]::GetSpeed($getSpeed, 0, [ref]$read, 0) | Out-Null
    Write-Output ("speed-switch step={0} wantSlow={1} target={2} read={3}" -f $step, $wantSlow, $target, $read)
    Start-Sleep -Seconds 2
    $wantSlow = -not $wantSlow
  }
  Write-Output ("speed-complete before={0} steps=8" -f $before)
}
finally {
  $restore = $before
  if ($restore -lt 1 -or $restore -gt 20) { $restore = 10 }
  [Arena.Speed]::SetSpeed($setSpeed, 0, [IntPtr]$restore, 0) | Out-Null
  $after = 0
  [Arena.Speed]::GetSpeed($getSpeed, 0, [ref]$after, 0) | Out-Null
  Write-Output ("speed-restored after={0}" -f $after)
  Write-Output 'restored'
}
```
