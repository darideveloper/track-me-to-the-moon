[CmdletBinding()]
param(
    [switch]$Hidden,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArgs
)

# Standalone Windows launcher. run.vbs invokes this script with -Hidden.
# uv writes normal progress messages to stderr. Keep native stderr as output and
# decide failure from each command's exit code below.
$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $PSScriptRoot

function Test-Python([string[]]$Candidate) {
    try {
        $arguments = @()
        if ($Candidate.Count -gt 1) {
            $arguments = $Candidate[1..($Candidate.Count - 1)]
        }
        & $Candidate[0] @arguments -c `
            "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Invoke-Uv([string[]]$UvArgs) {
    # Windows PowerShell represents an external program's stderr as an error
    # record. Capture it first, then write it as ordinary launcher output.
    $stderrFile = [System.IO.Path]::GetTempFileName()
    $previousErrorAction = $ErrorActionPreference
    try {
        $ErrorActionPreference = "SilentlyContinue"
        & uv @UvArgs 2>$stderrFile
        $script:LastUvExitCode = $LASTEXITCODE
        $ErrorActionPreference = $previousErrorAction
        Get-Content -LiteralPath $stderrFile -ErrorAction SilentlyContinue
    }
    finally {
        $ErrorActionPreference = $previousErrorAction
        Remove-Item -LiteralPath $stderrFile -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-Tracker {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "[moon-tracker] git not found. Install it from https://git-scm.com/download/win"
    }

    $branch = git rev-parse --abbrev-ref HEAD 2>$null
    if ($LASTEXITCODE -eq 0 -and $branch -and $branch -ne "main") {
        Write-Warning "[moon-tracker] not on branch 'main' (on '$branch'). Continuing..."
    }

    $pythonFound = $false
    foreach ($candidate in @(@("py", "-3.12"), @("py", "-3.11"), @("py", "-3.10"), @("py", "-3"), @("python"))) {
        if (Test-Python $candidate) {
            $pythonFound = $true
            break
        }
    }

    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Output "[moon-tracker] Installing uv package manager..."
        Invoke-RestMethod https://astral.sh/uv/install.ps1 -ErrorAction Stop | Invoke-Expression
        $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    }
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "[moon-tracker] uv was not found after installation. Open a new terminal and run again."
    }

    if (-not $pythonFound) {
        Write-Output "[moon-tracker] No Python 3.10+ found. Installing Python 3.12 via uv..."
        Invoke-Uv @("python", "install", "3.12")
        if ($script:LastUvExitCode -ne 0) {
            throw "[moon-tracker] Python installation failed."
        }
    }

    if (-not (Test-Path -LiteralPath ".venv")) {
        Write-Output "[moon-tracker] First run: downloading dependencies (~100MB for Flet, please wait)..."
        Write-Output "[moon-tracker] Windows may show a firewall prompt for the tracker window - this is expected."
    }

    Invoke-Uv @("sync", "--frozen")
    if ($script:LastUvExitCode -ne 0) {
        throw "[moon-tracker] Dependency sync failed. Check your connection and run again."
    }

    Write-Output "[moon-tracker] Dependencies ready. Starting tracker..."
    Invoke-Uv (@("run", "--frozen", "python", "-m", "moon_tracker") + $AppArgs)
    if ($script:LastUvExitCode -ne 0) {
        throw "[moon-tracker] Tracker exited with code $script:LastUvExitCode."
    }
}

if ($Hidden) {
    $logRoot = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { $env:USERPROFILE }
    $logDir = Join-Path $logRoot "moon-tracker\logs"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $sessionStamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss-fff"
    $logFile = Join-Path $logDir "$sessionStamp.log"
    "--- $(Get-Date -Format o) launcher started ---" | Tee-Object -FilePath $logFile -Append | Out-Null
    $exitCode = 0
    try {
        & { Invoke-Tracker } *>&1 | Tee-Object -FilePath $logFile -Append | Out-Null
    }
    catch {
        ($_ | Out-String).TrimEnd() | Tee-Object -FilePath $logFile -Append | Out-Null
        $exitCode = 1
    }
    "--- $(Get-Date -Format o) launcher exited with code $exitCode ---" |
        Tee-Object -FilePath $logFile -Append | Out-Null
    exit $exitCode
}

try {
    Invoke-Tracker
    exit 0
}
catch {
    Write-Error $_
    exit 1
}
