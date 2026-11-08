Add-Type -Namespace Arena -Name Buttons -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern int GetSystemMetrics(int index);
[System.Runtime.InteropServices.DllImport("user32.dll", EntryPoint="SystemParametersInfoW", SetLastError=true)]
public static extern bool SetSwap(uint action, uint param, System.IntPtr value, uint winIni);
'@
$setSwap = [uint32]0x21
$before = [Arena.Buttons]::GetSystemMetrics(23)
$beforeOn = $before -ne 0
$wantOn = $true
try {
  Write-Output ("button-switch start before={0}" -f $before)
  for ($step = 0; $step -lt 8; $step++) {
    $target = [uint32]0
    if ($wantOn) { $target = [uint32]1 }
    if (-not [Arena.Buttons]::SetSwap($setSwap, $target, [IntPtr]::Zero, 0)) {
      if ($step -eq 0) { throw 'SPI_SETMOUSEBUTTONSWAP failed' }
    }
    $read = [Arena.Buttons]::GetSystemMetrics(23)
    Write-Output ("button-switch step={0} wantOn={1} read={2}" -f $step, $wantOn, $read)
    Start-Sleep -Seconds 2
    $wantOn = -not $wantOn
  }
  Write-Output ("button-complete before={0} steps=8" -f $before)
}
finally {
  $restore = [uint32]0
  if ($beforeOn) { $restore = [uint32]1 }
  [Arena.Buttons]::SetSwap($setSwap, $restore, [IntPtr]::Zero, 0) | Out-Null
  $after = [Arena.Buttons]::GetSystemMetrics(23)
  Write-Output ("button-restored after={0}" -f $after)
  Write-Output 'restored'
}
