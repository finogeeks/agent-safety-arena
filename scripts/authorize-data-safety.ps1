param(
    [Parameter(Mandatory=$true)][string]$LabRoot,
    [Parameter(Mandatory=$true)][string]$CapabilitySid,
    [Parameter(Mandatory=$true)][string]$EvidenceDirectory
)
$ErrorActionPreference = 'Stop'
# A PowerShell 7 parent can export a module path that confuses Windows PowerShell.
Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Security/Microsoft.PowerShell.Security.psd1') -ErrorAction Stop
$lab = [IO.Path]::GetFullPath($LabRoot).TrimEnd('\')
$evidence = [IO.Path]::GetFullPath($EvidenceDirectory).TrimEnd('\')
if ($lab -eq [IO.Path]::GetPathRoot($lab).TrimEnd('\') -or
    $evidence -eq $lab -or $evidence.StartsWith($lab + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Evidence must be outside a dedicated lab root.'
}
if ($CapabilitySid -notmatch '^S-1-15-3-1024(-\d+){8}$') {
    throw 'Expected the dedicated FinShield file capability SID.'
}
$boundaries = @(
    @{Path=$lab; Access='read_write'; Mode='Allow'; Rights='M'; Mask=0x1301bf},
    @{Path=(Join-Path $lab 'ro-ancestor\ro-parent\read-only'); Access='read_only'; Mode='Allow'; Rights='RX'; Mask=0x1200a9},
    @{Path=(Join-Path $lab 'na-ancestor\na-parent\no-access'); Access='deny'; Mode='Deny'; Rights='F'; Mask=0x1f01ff}
)
$cursor = Get-Item -LiteralPath $lab
while ($null -ne $cursor) {
    if ($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse ancestor refused.' }
    $cursor = $cursor.Parent
}
$items = @(Get-Item -LiteralPath $lab) + @(Get-ChildItem -LiteralPath $lab -Force -Recurse)
foreach ($item in $items) {
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse fixture refused.' }
    $acl = Get-Acl -LiteralPath $item.FullName
    foreach ($rule in $acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])) {
        if ($rule.IdentityReference.Value -in @('S-1-15-2-1', 'S-1-15-2-2')) {
            throw 'Generic AppContainer ACL requires separate review; no repair was applied.'
        }
    }
}
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
$snapshot = @($items | ForEach-Object {
    @{Path=$_.FullName; Sddl=(Get-Acl -LiteralPath $_.FullName).Sddl}
})
$snapshot | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $evidence 'acl-before.json') -Encoding UTF8
$logPath = Join-Path $evidence 'icacls.log'
function Invoke-LabIcacls([string[]]$Arguments) {
    $output = & icacls.exe @Arguments 2>&1
    $code = $LASTEXITCODE
    @($Arguments -join ' ', $output) | Out-File -LiteralPath $logPath -Append -Encoding UTF8
    if ($code -ne 0) { throw "icacls failed ($code): $output" }
}
foreach ($boundary in $boundaries) {
    if (-not (Test-Path -LiteralPath $boundary.Path -PathType Container)) { throw 'Missing zone directory.' }
    Invoke-LabIcacls @($boundary.Path, '/inheritance:d')
    Invoke-LabIcacls @($boundary.Path, '/remove', ('*' + $CapabilitySid))
    $switch = if ($boundary.Mode -eq 'Deny') { '/deny' } else { '/grant:r' }
    $ace = '*' + $CapabilitySid + ':(OI)(CI)(' + $boundary.Rights + ')'
    Invoke-LabIcacls @($boundary.Path, $switch, $ace)
}
$verified = @()
foreach ($boundary in $boundaries) {
    $acl = Get-Acl -LiteralPath $boundary.Path
    $rules = @($acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]) |
        Where-Object { $_.IdentityReference.Value -eq $CapabilitySid })
    if (-not $acl.AreAccessRulesProtected -or $rules.Count -ne 1 -or
        $rules[0].IsInherited -or [int]$rules[0].FileSystemRights -ne $boundary.Mask -or
        $rules[0].AccessControlType.ToString() -ne $boundary.Mode -or
        [int]$rules[0].InheritanceFlags -ne 3) {
        throw "Dedicated ACL verification failed: $($boundary.Path)"
    }
    $verified += @{Path=$boundary.Path; Access=$boundary.Access; Mask=$boundary.Mask; Protected=$acl.AreAccessRulesProtected}
}
# Check that every host file remains readable after the dedicated capability changes.
foreach ($item in $items) {
    if (-not $item.PSIsContainer) {
        $stream = [IO.File]::OpenRead($item.FullName)
        $stream.Dispose()
    }
}
@{CapabilitySid=$CapabilitySid; Boundaries=$verified; HostReadVerified=$true} | ConvertTo-Json -Depth 6
