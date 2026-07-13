param(
    [string]$RemoteName = 'origin',
    [string]$Branch = '',
    [string]$HostAlias = 'waffentactics-vps',
    [string]$RemotePath = '/home/ubuntu/waffen-tactics-game',
    [switch]$RunTests,
    [switch]$AutoCommit,
    [string]$CommitMessage = 'deploy: sync local changes to VPS'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host ""
    Write-Host "==> $Name"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$repoRoot = Split-Path -Parent $PSCommandPath
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($Branch)) {
    $Branch = (git branch --show-current).Trim()
}

if ([string]::IsNullOrWhiteSpace($Branch)) {
    throw "Could not determine the current git branch."
}

Write-Host "Deploy target: ${HostAlias}:$RemotePath"
Write-Host "Git branch:    $Branch"

if ($RunTests) {
    Invoke-Step "Core tests" { python -m pytest -q 'waffen-tactics\tests' }
    Invoke-Step "Backend tests" { python -m pytest -q 'waffen-tactics-web\backend\tests' }
    Invoke-Step "Frontend tests" { Push-Location 'waffen-tactics-web'; try { npx vitest run } finally { Pop-Location } }
}

function Get-TrackedChanges {
    $tracked = @()
    $tracked += git diff --name-only
    $tracked += git diff --cached --name-only
    return $tracked | Where-Object { $_ } | Sort-Object -Unique
}

function Get-UntrackedPaths {
    $lines = git status --porcelain --untracked-files=normal
    $lines | Where-Object { $_ -match '^\?\? ' } | ForEach-Object { $_.Substring(3) }
}

$trackedChanges = Get-TrackedChanges
$untrackedPaths = Get-UntrackedPaths

if ($untrackedPaths) {
    Write-Host ""
    Write-Host "Warning: untracked paths present; they will not be committed:"
    $untrackedPaths | ForEach-Object { Write-Host "  - $_" }
}

if ($trackedChanges.Count -gt 0) {
    if (-not $AutoCommit) {
        Write-Host ""
        Write-Host "Working tree is dirty. Commit your changes first, or rerun with -AutoCommit."
        throw "Refusing to deploy from an uncommitted tree."
    }

    Invoke-Step "Commit local changes" {
        git add -A
        git commit -m $CommitMessage
    }
}

Invoke-Step "Push branch to origin" {
    git push $RemoteName "HEAD:refs/heads/$Branch"
}

$remoteScript = @"
set -euo pipefail
cd '$RemotePath'
git fetch '$RemoteName' '$Branch'
git reset --hard '$RemoteName/$Branch'
./stop-all.sh
./start-all.sh
./status.sh
"@

Invoke-Step "Sync and restart on VPS" {
    $remoteScript | ssh $HostAlias 'bash -s'
}

Write-Host ""
Write-Host "Deploy complete."
