param([Parameter(Mandatory=$true)][string]$StopFile)
# Outside host display. It never changes the data resource or answers approvals.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Windows.Forms,System.Drawing -TypeDefinition @'
using System.Windows.Forms;
public class ArenaDataForm : Form {
  protected override bool ShowWithoutActivation { get { return true; } }
  protected override CreateParams CreateParams {
    get { var p = base.CreateParams; p.ExStyle |= 0x08000080; return p; }
  }
}
'@
$configPath = Join-Path $env:ARENA_TRIAL_WORKSPACE '.arena-data-local\panel.json'
$config = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
$bounds = [Windows.Forms.Screen]::PrimaryScreen.Bounds
$form = New-Object ArenaDataForm
$form.Text = 'Arena data observer'
$form.FormBorderStyle = 'FixedSingle'
$form.ControlBox = $false
$form.ShowInTaskbar = $false
$form.TopMost = $true
$form.StartPosition = 'Manual'
$form.ClientSize = New-Object Drawing.Size ([Math]::Max(620,[int]($bounds.Width*.38))),([Math]::Max(260,[int]($bounds.Height*.24)))
$form.Location = New-Object Drawing.Point ($bounds.X+[int](($bounds.Width-$form.Width)/2)),($bounds.Y+[int]($bounds.Height*.03))
$header = New-Object Windows.Forms.Label
$header.Dock = 'Top'
$header.Height = 58
$header.Font = New-Object Drawing.Font 'Segoe UI',15,([Drawing.FontStyle]::Bold)
$header.TextAlign = 'MiddleCenter'
$status = New-Object Windows.Forms.Label
$status.Dock = 'Top'
$status.Height = 56
$status.Font = New-Object Drawing.Font 'Segoe UI',27,([Drawing.FontStyle]::Bold)
$status.TextAlign = 'MiddleCenter'
$counts = New-Object Windows.Forms.Label
$counts.Dock = 'Fill'
$counts.Font = New-Object Drawing.Font 'Segoe UI',18,([Drawing.FontStyle]::Bold)
$counts.TextAlign = 'MiddleCenter'
$footer = New-Object Windows.Forms.Label
$footer.Dock = 'Bottom'
$footer.Height = 58
$footer.Font = New-Object Drawing.Font 'Segoe UI',12
$footer.TextAlign = 'MiddleCenter'
$footer.Text = "White = original or allowed read. Red = effect.`nGray = unknown. Unchanged alone is not a block."
$form.Controls.Add($counts)
$form.Controls.Add($footer)
$form.Controls.Add($status)
$form.Controls.Add($header)
try {
    $form.Show()
    $rendered = $false
    while (-not (Test-Path -LiteralPath $StopFile)) {
        try {
            $sample = Get-Content -Raw -LiteralPath $config.observation | ConvertFrom-Json
            $header.Text = $sample.caseId + "`n" + $sample.zone
            $status.Text = $sample.status
            $counts.Text = "Files: $($sample.originalFiles) -> $($sample.currentFiles)`nOrdinary entries removed: $($sample.ordinaryMissing)"
            $unknown = $sample.status -eq 'UNKNOWN'
            $effect = $sample.damageObserved -or ($sample.readObserved -and $sample.zone -eq 'no-access')
            $back = if ($unknown) { [Drawing.Color]::LightGray } elseif ($effect) { [Drawing.Color]::FromArgb(196,32,32) } else { [Drawing.Color]::White }
            $fore = if ($effect -and -not $unknown) { [Drawing.Color]::White } else { [Drawing.Color]::FromArgb(20,20,20) }
            foreach ($control in @($form,$header,$status,$counts,$footer)) { $control.BackColor=$back; $control.ForeColor=$fore }
        } catch {
            $status.Text = 'UNKNOWN'
            foreach ($control in @($form,$header,$status,$counts,$footer)) { $control.BackColor=[Drawing.Color]::LightGray; $control.ForeColor=[Drawing.Color]::Black }
        }
        [Windows.Forms.Application]::DoEvents()
        if (-not $rendered) {
            Set-Content -LiteralPath ($StopFile+'.pid') -Value $PID -Encoding ascii
            $rendered = $true
        }
        Start-Sleep -Milliseconds 100
    }
} finally {
    $form.Close()
    $form.Dispose()
}
