<#
.SYNOPSIS
Solve a REopt scenario — locally via Julia (with optional sysimage) or via NREL API.

.DESCRIPTION
Validates input, then invokes the Julia solve script with or without a sysimage.
If no sysimage exists and --fallback is set, uses solve_via_api.py instead.

.PARAMETER Scenario
Path to the scenario JSON file (required).

.PARAMETER OutputDir
Directory for results (default: artifacts/results/<auto>).

.PARAMETER NoSolve
Validate scenario JSON without solving.

.PARAMETER Fallback
Use NREL API fallback if local Julia solve is unavailable or sysimage missing.

.PARAMETER Sysimage
Path to a PackageCompiler sysimage. Auto-detected from artifacts/sysimage/ if omitted.

.EXAMPLE
.\scripts\run_solve.ps1 --scenario scenarios/generated/tou_comparison/.../input.json
.\scripts\run_solve.ps1 --scenario <path> --fallback
.\scripts\run_solve.ps1 --scenario <path> --sysimage artifacts/sysimage/reopt_sysimage.dll
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$Scenario,
    [string]$OutputDir,
    [switch]$NoSolve,
    [switch]$Fallback,
    [string]$Sysimage
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$JuliaProjectDir = Join-Path $RepoRoot "legacy" "julia"

# Validate scenario exists
if (-not (Test-Path $Scenario)) {
    Write-Error "Scenario not found: $Scenario"
    exit 1
}
$Scenario = (Resolve-Path $Scenario).Path

# Determine output directory
if (-not $OutputDir) {
    $ScenarioName = [System.IO.Path]::GetFileNameWithoutExtension($Scenario)
    $OutputDir = Join-Path $RepoRoot "artifacts" "results" $ScenarioName
}
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# Auto-detect sysimage if not specified
if (-not $Sysimage -and -not $Fallback) {
    $sysimgDir = Join-Path $RepoRoot "artifacts" "sysimage"
    $candidates = @(Get-ChildItem -Path $sysimgDir -Filter "reopt_sysimage.*" -ErrorAction SilentlyContinue)
    if ($candidates.Count -gt 0) {
        $Sysimage = $candidates[0].FullName
        Write-Host "Auto-detected sysimage: $Sysimage"
    }
}

$useSysimage = $Sysimage -and (Test-Path $Sysimage)

if ($NoSolve) {
    Write-Host "=== Validating scenario (--no-solve) ===" -ForegroundColor Cyan
    $noSolveFlag = if ($useSysimage) { "--sysimage", $Sysimage, "--no-solve" } else { "--no-solve" }
    & julia --project=$JuliaProjectDir @noSolveFlag $Scenario
    exit $LASTEXITCODE
}

if ($useSysimage) {
    Write-Host "=== Solving via Julia + sysimage ===" -ForegroundColor Cyan
    Write-Host "Sysimage: $Sysimage"

    $env:JULIA_PKG_PRECOMPILE_AUTO = "0"
    & julia --sysimage=$Sysimage --project=$JuliaProjectDir `
        (Join-Path $RepoRoot "legacy" "julia" "scripts" "run_vietnam_scenario.jl") `
        --scenario $Scenario --output-dir $OutputDir

    if ($LASTEXITCODE -eq 0) {
        $resultsFile = Join-Path $OutputDir "reopt-results.json"
        if (Test-Path $resultsFile) {
            Write-Host "Results saved to: $resultsFile" -ForegroundColor Green
        }
    } else {
        Write-Error "Julia solve failed with exit code $LASTEXITCODE"
    }
    exit $LASTEXITCODE
}

if ($Fallback) {
    Write-Host "=== Solving via NREL API fallback ===" -ForegroundColor Cyan
    $venvPython = Join-Path $RepoRoot ".venv" "Scripts" "python.exe"
    $fallbackScript = Join-Path $RepoRoot "scripts" "python" "reopt" "solve_via_api.py"

    if (Test-Path $venvPython) {
        & $venvPython $fallbackScript --scenario $Scenario --output-dir $OutputDir
    } else {
        & python $fallbackScript --scenario $Scenario --output-dir $OutputDir
    }

    if ($LASTEXITCODE -eq 0) {
        Write-Host "API solve completed." -ForegroundColor Green
    } else {
        Write-Error "API solve failed with exit code $LASTEXITCODE"
    }
    exit $LASTEXITCODE
}

# Default: cold-start Julia (no sysimage, no fallback)
Write-Host "=== Solving via Julia (cold-start) ===" -ForegroundColor Cyan
Write-Host "Tip: use --sysimage or --fallback for faster solves" -ForegroundColor Yellow

$env:JULIA_PKG_PRECOMPILE_AUTO = "0"
& julia --project=$JuliaProjectDir --compile=min `
    (Join-Path $RepoRoot "legacy" "julia" "scripts" "run_vietnam_scenario.jl") `
    --scenario $Scenario --output-dir $OutputDir

exit $LASTEXITCODE
