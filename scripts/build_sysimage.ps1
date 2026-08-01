<#
.SYNOPSIS
Builds a PackageCompiler sysimage for REopt.jl to eliminate Julia JIT cold-start.

.DESCRIPTION
Invokes legacy/julia/scripts/build_sysimage.jl with the project environment,
stores the artifact at artifacts/sysimage/reopt_sysimage.{dll,so}.

.PARAMETER SkipPrecompile
If set, skips the precompile workload for faster build (less warm coverage).

.EXAMPLE
.\scripts\build_sysimage.ps1
.\scripts\build_sysimage.ps1 -SkipPrecompile
#>

param(
    [switch]$SkipPrecompile
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$JuliaProjectDir = Join-Path (Join-Path $RepoRoot "legacy") "julia"
$SysimageScript = Join-Path (Join-Path $JuliaProjectDir "scripts") "build_sysimage.jl"
$SysimageDir = Join-Path (Join-Path $RepoRoot "artifacts") "sysimage"

if (-not (Test-Path $SysimageDir)) {
    New-Item -ItemType Directory -Path $SysimageDir -Force | Out-Null
}

Write-Host "=== Building REopt sysimage ===" -ForegroundColor Cyan
Write-Host "Repo root:    $RepoRoot"
Write-Host "Sysimage dir: $SysimageDir"
if ($SkipPrecompile) {
    Write-Host "Precompile:   SKIPPED (--SkipPrecompile)"
}

$env:JULIA_PKG_PRECOMPILE_AUTO = "0"

$juliaArgs = @("--project=$JuliaProjectDir", $SysimageScript)
if ($SkipPrecompile) {
    $env:SKIP_PRECOMPILE = "true"
}

Write-Host "`nStarting sysimage build (5-15 min)..." -ForegroundColor Yellow
& julia $juliaArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "Sysimage build failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

# Verify artifact exists
$ext = if ($IsWindows -or (-not $IsWindows -and -not $IsLinux)) { ".dll" } else { ".so" }
$sysimagePath = Join-Path $SysimageDir "reopt_sysimage$ext"
if (Test-Path $sysimagePath) {
    $size = (Get-Item $sysimagePath).Length / 1MB
    Write-Host "`n=== Sysimage built successfully ===" -ForegroundColor Green
    Write-Host "Path: $sysimagePath ($([math]::Round($size, 1)) MB)"
    Write-Host "`nRun a scenario with:"
    Write-Host "  .\scripts\run_solve.ps1 --scenario <path> --output-dir <dir>"
} else {
    # Try .so on Linux
    $altPath = Join-Path $SysimageDir "reopt_sysimage.so"
    if (Test-Path $altPath) {
        $size = (Get-Item $altPath).Length / 1MB
        Write-Host "`n=== Sysimage built successfully ===" -ForegroundColor Green
        Write-Host "Path: $altPath ($([math]::Round($size, 1)) MB)"
    } else {
        Write-Warning "Sysimage build completed but artifact not found at expected paths."
        Write-Host "Check: $SysimageDir"
    }
}
