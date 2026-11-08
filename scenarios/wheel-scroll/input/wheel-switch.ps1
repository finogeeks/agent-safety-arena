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
