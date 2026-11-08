Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -Namespace Arena -Name Foreground -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool SetForegroundWindow(System.IntPtr hWnd);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool SetWindowPos(System.IntPtr hWnd, System.IntPtr insertAfter, int x, int y, int cx, int cy, uint flags);
'@
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$panelW = [Math]::Max(560, [int]($bounds.Width * 0.42))
$panelH = [Math]::Max(360, [int]($bounds.Height * 0.42))
$shiftX = [int]($panelW * 0.28)
$shiftY = [int]($panelH * 0.28)
$workX = $bounds.X + [int](($bounds.Width - $panelW - $shiftX) / 2)
$workY = $bounds.Y + [int](($bounds.Height - $panelH - $shiftY) / 2)
function New-OwnedWindow($title, $back, $fore, $x, $y) {
  $form = New-Object System.Windows.Forms.Form
  $form.Text = $title
  $form.FormBorderStyle = 'FixedSingle'
  $form.MaximizeBox = $false
  $form.MinimizeBox = $false
  $form.ControlBox = $false
  $form.ShowInTaskbar = $false
  $form.TopMost = $false
  $form.StartPosition = 'Manual'
  $form.BackColor = $back
  $form.ClientSize = New-Object System.Drawing.Size $script:panelW, $script:panelH
  $form.Location = New-Object System.Drawing.Point $x, $y
  $form.WindowState = 'Normal'
  $label = New-Object System.Windows.Forms.Label
  $label.Text = 'BEHIND'
  $label.ForeColor = $fore
  $label.BackColor = $back
  $label.Font = New-Object System.Drawing.Font 'Segoe UI', 36, ([System.Drawing.FontStyle]::Bold)
  $label.TextAlign = 'MiddleCenter'
  $label.Dock = 'Fill'
  $form.Controls.Add($label)
  $form | Add-Member NoteProperty ArenaLabel $label
  $form.Show()
  $form.Visible = $true
  return $form
}
function Stack-Pair($front, $back) {
  $front.ArenaLabel.Text = 'IN FRONT'
  $back.ArenaLabel.Text = 'BEHIND'
  [Arena.Foreground]::SetWindowPos($front.Handle, [IntPtr]::Zero, 0, 0, 0, 0, 3) | Out-Null
  $ok = [Arena.Foreground]::SetForegroundWindow($front.Handle)
  [Arena.Foreground]::SetWindowPos($back.Handle, $front.Handle, 0, 0, 0, 0, 19) | Out-Null
  return $ok
}
$work = $null
$panel = $null
try {
  $work = New-OwnedWindow 'Work' ([System.Drawing.Color]::FromArgb(245, 247, 251)) ([System.Drawing.Color]::FromArgb(23, 43, 66)) $workX $workY
  $panel = New-OwnedWindow 'Arena panel' ([System.Drawing.Color]::FromArgb(255, 120, 0)) ([System.Drawing.Color]::White) ($workX + $shiftX) ($workY + $shiftY)
  [System.Windows.Forms.Application]::DoEvents()
  if (-not $work.Visible -or -not $panel.Visible) { throw 'visible=False' }
  $first = Stack-Pair $panel $work
  [System.Windows.Forms.Application]::DoEvents()
  if (-not $first) { throw 'SetForegroundWindow returned false' }
  $deadline = [DateTime]::UtcNow.AddSeconds(24)
  $steps = 0
  $front = 0
  $back = 0
  $panelFront = $true
  while ([DateTime]::UtcNow -lt $deadline) {
    if ($panelFront) {
      if (Stack-Pair $panel $work) { $front++ }
    } else {
      if (Stack-Pair $work $panel) { $back++ }
    }
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 1500
    $steps++
    $panelFront = -not $panelFront
  }
  Stack-Pair $panel $work | Out-Null
  [System.Windows.Forms.Application]::DoEvents()
  Start-Sleep -Seconds 2
  Write-Output ("foreground-complete visibleWork={0} visiblePanel={1} first={2} steps={3} front={4} back={5} size={6}x{7} bounds={8},{9} {10}x{11}" -f $work.Visible, $panel.Visible, $first, $steps, $front, $back, $panelW, $panelH, $bounds.X, $bounds.Y, $bounds.Width, $bounds.Height)
}
finally {
  if ($panel -and $panel.Visible) { $panel.Close() }
  if ($work -and $work.Visible) { $work.Close() }
  Write-Output 'restored'
}
