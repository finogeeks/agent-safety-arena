param([Parameter(Mandatory=$true)][string]$StopFile)
$ErrorActionPreference = 'Stop'
$case = Split-Path -Leaf (Split-Path -Parent $PSScriptRoot)
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
& (Join-Path $repo 'scripts\system-boundary-display.ps1') -StopFile $StopFile -RepoRoot $repo -CaseId $case -ObserverScript (Join-Path $repo 'scripts\system_ipc_observer.py')
