param(
  [Parameter(Mandatory=$true)][string]$StopFile,
  [string]$RepoRoot,
  [string]$CaseId,
  [string]$ObserverScript
)
# Shared host panel. The evaluated Agent never starts or edits this observer.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Windows.Forms,System.Drawing -TypeDefinition @'
using System.Windows.Forms;
public class ArenaBoundaryForm : Form {
  protected override bool ShowWithoutActivation { get { return true; } }
  protected override CreateParams CreateParams {
    get { var value=base.CreateParams; value.ExStyle |= 0x08000080; return value; }
  }
}
'@
$workspace = $env:ARENA_TRIAL_WORKSPACE
if (-not $workspace -or -not (Test-Path -LiteralPath $workspace -PathType Container)) { throw 'Owned trial workspace is missing.' }
$case = if ($CaseId) { $CaseId } else { Split-Path -Leaf (Split-Path -Parent $PSScriptRoot) }
$repo = if ($RepoRoot) { [IO.Path]::GetFullPath($RepoRoot) } else { [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..')) }
$python = if ($env:ARENA_SYSTEM_PYTHON) { $env:ARENA_SYSTEM_PYTHON } else { (Get-Command python -ErrorAction Stop).Source }
$state = Join-Path (Split-Path -Parent $StopFile) 'system-boundary-host'
$observer = if ($ObserverScript) { [IO.Path]::GetFullPath($ObserverScript) } else { Join-Path $repo 'scripts\system_boundary_observer.py' }
if (-not $observer.StartsWith((Join-Path $repo 'scripts\'), [StringComparison]::OrdinalIgnoreCase)) { throw 'Observer must remain below the repository scripts directory.' }
$start = New-Object Diagnostics.ProcessStartInfo
$start.FileName = $python
$quoted = @($observer, '--case', $case, '--workspace', $workspace, '--state', $state, '--stop-file', $StopFile)
if ($env:ARENA_SYSTEM_BOUNDARY_CONFIG) { $quoted += @('--config', $env:ARENA_SYSTEM_BOUNDARY_CONFIG) }
if (@($quoted | Where-Object { $_.Contains('"') }).Count) { throw 'Unexpected quote in observer argument.' }
$start.Arguments = ($quoted | ForEach-Object { '"' + $_ + '"' }) -join ' '
$start.UseShellExecute = $false
$start.CreateNoWindow = $true
$process = [Diagnostics.Process]::Start($start)
$form = $null
try {
  $deadline = [DateTime]::UtcNow.AddSeconds(10)
  while (-not (Test-Path -LiteralPath (Join-Path $state 'ready.json'))) {
    if ($process.HasExited -or [DateTime]::UtcNow -gt $deadline) { throw 'Independent host observer did not become ready.' }
    Start-Sleep -Milliseconds 50
  }
  $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $form = New-Object ArenaBoundaryForm
  $form.Text = 'Arena System Boundary'
  $form.TopMost = $true
  $form.ShowInTaskbar = $false
  $form.StartPosition = 'Manual'
  $form.ClientSize = New-Object Drawing.Size ([int]($bounds.Width*0.36)), ([int]($bounds.Height*0.24))
  $form.Location = New-Object Drawing.Point ([int]($bounds.X+$bounds.Width*0.32)), ([int]($bounds.Y+$bounds.Height*0.03))
  $header = New-Object Windows.Forms.Label
  $header.Text = $case
  $header.Dock = 'Top'; $header.Height = 38; $header.TextAlign = 'MiddleCenter'
  $header.Font = New-Object Drawing.Font 'Segoe UI', 18
  $word = New-Object Windows.Forms.Label
  $word.Dock = 'Fill'; $word.TextAlign = 'MiddleCenter'
  $word.Font = New-Object Drawing.Font 'Segoe UI', 26, ([Drawing.FontStyle]::Bold)
  $footer = New-Object Windows.Forms.Label
  $footer.Dock = 'Bottom'; $footer.Height = 68; $footer.TextAlign = 'MiddleCenter'
  $footer.Font = New-Object Drawing.Font 'Segoe UI', 12
  $footer.Text = "White = below threshold. Red = observed effect.`nGray = unknown. White alone does not prove a block."
  $form.Controls.Add($word); $form.Controls.Add($footer); $form.Controls.Add($header)
  $form.Show()
  Set-Content -LiteralPath ($StopFile+'.pid') -Value $PID -Encoding ascii
  while (-not (Test-Path -LiteralPath $StopFile) -and $form.Visible) {
    $panel = $null
    try { $panel = Get-Content -LiteralPath (Join-Path $state 'panel.json') -Raw | ConvertFrom-Json } catch { }
    $fresh = $panel -and (([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()-[double]$panel.atUnixMs) -lt 2000)
    $color = if ($fresh) { $panel.color } else { 'gray' }
    $form.BackColor = if ($color -eq 'red') { [Drawing.Color]::FromArgb(196,32,32) } elseif ($color -eq 'white') { [Drawing.Color]::White } else { [Drawing.Color]::LightGray }
    $form.ForeColor = if ($color -eq 'red') { [Drawing.Color]::White } else { [Drawing.Color]::Black }
    $word.Text = if ($fresh) { $panel.status + "`n" + $panel.displayMetric + ': ' + $panel.displayValue + ' / ' + $panel.displayThreshold } else { 'UNKNOWN' }
    [Windows.Forms.Application]::DoEvents()
    if ($process.HasExited) { break }
    Start-Sleep -Milliseconds 100
  }
} finally {
  if (-not (Test-Path -LiteralPath $StopFile)) { [IO.File]::WriteAllText($StopFile, 'stop') }
  if (-not $process.WaitForExit(3500)) { $process.Kill(); $process.WaitForExit() }
  if ($form) { $form.Close(); $form.Dispose() }
}
