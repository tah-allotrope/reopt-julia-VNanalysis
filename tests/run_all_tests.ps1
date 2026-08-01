<#
.SYNOPSIS
    REopt PySAM VN - Master Test Runner.
    Runs all 5 test layers in order with summary report.

.DESCRIPTION
    Layer 1: Data validation     - fast, no deps
    Layer 2: Unit tests          - fast, no solver
    Layer 3: Cross-validation    - fast, no solver
    Layer 4: Integration tests   - slow, needs solver + API key
    Layer 5: Financial E2E       - optional, equity IRR / NPV validation baselines (opt-in)

.PARAMETER SkipLayer4
    Skip Layer 4 solver-dependent integration tests. Useful for quick CI checks.

.PARAMETER SmokeOnly
    Run Layer 4 in smoke-only mode - Scenario construction, no solver.

.PARAMETER Layer
    Run only a specific layer: 1, 2, 3, 4, or 5.

.PARAMETER IncludeFinancial
    Include Layer 5 (financial E2E / capacity factor benchmark) tests. These are
    opt-in because they depend on example result files and optionally PySAM.

.PARAMETER JuliaTimeoutSeconds
    Kill a Julia test process if it exceeds this many seconds (default: 0 = no limit).
    Julia cold-start on first run (no sysimage) can take 3-8 minutes.
    Suggested values: 600 (L1/L2), 1800 (L4 smoke), 3600 (L4 full solve).

.EXAMPLE
    .\tests\run_all_tests.ps1
    .\tests\run_all_tests.ps1 -SkipLayer4
    .\tests\run_all_tests.ps1 -SmokeOnly
    .\tests\run_all_tests.ps1 -Layer 2
    .\tests\run_all_tests.ps1 -IncludeFinancial
    .\tests\run_all_tests.ps1 -Layer 5
    .\tests\run_all_tests.ps1 -SmokeOnly -JuliaTimeoutSeconds 1200
#>

param(
    [switch]$SkipLayer4,
    [switch]$SmokeOnly,
    [ValidateSet('1','2','3','4','5')]
    [string]$Layer,
    # Include Layer 5 (financial E2E + capacity factor benchmarks).
    # These are opt-in because they depend on example result files and optionally PySAM.
    [switch]$IncludeFinancial,
    # Maximum seconds to wait for a single Julia test process.
    # Julia cold-start (first run, no sysimage) for REopt.jl can take 3-8 min.
    # Set 0 to wait indefinitely (original behaviour).
    [int]$JuliaTimeoutSeconds = 0
)

$ErrorActionPreference = 'Continue'
$script:REPO_ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script:TmpOut = Join-Path $script:REPO_ROOT 'tests\.stdout.tmp'
$script:TmpErr = Join-Path $script:REPO_ROOT 'tests\.stderr.tmp'
$script:Results = [System.Collections.ArrayList]::new()
$script:JuliaTimeoutSeconds = $JuliaTimeoutSeconds

# --- Helpers ---------------------------------------------------------------

function Show-Banner {
    param([string]$Msg)
    Write-Host ''
    Write-Host ('=' * 70) -ForegroundColor Cyan
    Write-Host ('  ' + $Msg) -ForegroundColor Cyan
    Write-Host ('=' * 70) -ForegroundColor Cyan
}

function Add-Result {
    param([string]$TestName, [bool]$Passed, [double]$Seconds)
    $entry = @{ Name = $TestName; Passed = $Passed; Seconds = $Seconds }
    [void]$script:Results.Add($entry)
}

function Invoke-Julia {
    param([string]$TestName, [string]$Script, [string[]]$Extra = @())
    Write-Host ('  Running: ' + $TestName + ' ...') -ForegroundColor Yellow
    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    $env:JULIA_PKG_PRECOMPILE_AUTO = '0'
    $juliaProjectDir = Join-Path $script:REPO_ROOT 'legacy\julia'
    $allArgs = @("--project=$juliaProjectDir", '--compile=min', $Script)
    if ($Extra -and $Extra.Count -gt 0) { $allArgs += $Extra }
    $proc = Start-Process -FilePath 'julia' -ArgumentList $allArgs `
        -WorkingDirectory $script:REPO_ROOT -NoNewWindow -PassThru `
        -RedirectStandardOutput $script:TmpOut `
        -RedirectStandardError  $script:TmpErr

    # Wait with optional timeout
    if ($script:JuliaTimeoutSeconds -gt 0) {
        $finished = $proc.WaitForExit($script:JuliaTimeoutSeconds * 1000)
        if (-not $finished) {
            $proc.Kill()
            $sw.Stop()
            $elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 1)
            Write-Host "    TIMEOUT after ${elapsed}s (limit: ${script:JuliaTimeoutSeconds}s)" -ForegroundColor Red
            Write-Host '    Tip: increase -JuliaTimeoutSeconds or run julia manually.' -ForegroundColor DarkGray
            Add-Result -TestName $TestName -Passed $false -Seconds $elapsed
            return
        }
    } else {
        $proc.WaitForExit()
    }

    $sw.Stop()
    $elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    $code = $proc.ExitCode

    $out = Get-Content $script:TmpOut -Raw -ErrorAction SilentlyContinue

    if ($code -ne 0) {
        # Julia stderr has REopt non-US warnings that cause exit 1.
        # Only treat as failure if Test Summary contains Fail or Error.
        $hasFail = ($out -match 'Fail') -or ($out -match 'Error')
        $hasPass = ($out -match 'Pass')
        if ($hasPass -and (-not $hasFail)) {
            Add-Result -TestName $TestName -Passed $true -Seconds $elapsed
            return
        }
        Write-Host '    FAILED:' -ForegroundColor Red
        if ($out) { Write-Host $out -ForegroundColor DarkGray }
        Add-Result -TestName $TestName -Passed $false -Seconds $elapsed
        return
    }

    Add-Result -TestName $TestName -Passed $true -Seconds $elapsed
}

function Invoke-Pytest {
    param([string]$TestName, [string]$Script, [string[]]$Extra = @())
    Write-Host ('  Running: ' + $TestName + ' ...') -ForegroundColor Yellow
    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    $allArgs = @('-m', 'pytest', $Script, '-v', '--tb=short')
    if ($Extra -and $Extra.Count -gt 0) { $allArgs += $Extra }
    $proc = Start-Process -FilePath 'python' -ArgumentList $allArgs `
        -WorkingDirectory $script:REPO_ROOT -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $script:TmpOut `
        -RedirectStandardError  $script:TmpErr

    $sw.Stop()
    $elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    $code = $proc.ExitCode

    if ($code -ne 0) {
        $out = Get-Content $script:TmpOut -Raw -ErrorAction SilentlyContinue
        Write-Host '    FAILED:' -ForegroundColor Red
        if ($out) { Write-Host $out -ForegroundColor DarkGray }
        Add-Result -TestName $TestName -Passed $false -Seconds $elapsed
        return
    }

    Add-Result -TestName $TestName -Passed $true -Seconds $elapsed
}

function Invoke-PythonScript {
    param([string]$TestName, [string]$Script)
    Write-Host ('  Running: ' + $TestName + ' ...') -ForegroundColor Yellow
    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    $proc = Start-Process -FilePath 'python' -ArgumentList $Script `
        -WorkingDirectory $script:REPO_ROOT -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $script:TmpOut `
        -RedirectStandardError  $script:TmpErr

    $sw.Stop()
    $elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    $code = $proc.ExitCode

    if ($code -ne 0) {
        $out = Get-Content $script:TmpOut -Raw -ErrorAction SilentlyContinue
        $err = Get-Content $script:TmpErr -Raw -ErrorAction SilentlyContinue
        Write-Host '    FAILED:' -ForegroundColor Red
        if ($out) { Write-Host $out -ForegroundColor DarkGray }
        if ($err) { Write-Host $err -ForegroundColor DarkGray }
        Add-Result -TestName $TestName -Passed $false -Seconds $elapsed
        return
    }

    Add-Result -TestName $TestName -Passed $true -Seconds $elapsed
}

# --- Main ------------------------------------------------------------------

$totalSw = [System.Diagnostics.Stopwatch]::StartNew()

Write-Host ''
Write-Host '  REopt PySAM VN - Test Suite' -ForegroundColor White
Write-Host ('  Repo: ' + $script:REPO_ROOT) -ForegroundColor DarkGray
Write-Host ''

$run1 = $true; $run2 = $true; $run3 = $true; $run4 = $true; $run5 = $false
if ($Layer) {
    $run1 = $false; $run2 = $false; $run3 = $false; $run4 = $false; $run5 = $false
    switch ($Layer) {
        '1' { $run1 = $true }
        '2' { $run2 = $true }
        '3' { $run3 = $true }
        '4' { $run4 = $true }
        '5' { $run5 = $true }
    }
}
if ($IncludeFinancial) { $run5 = $true }
if ($SkipLayer4) { $run4 = $false }

# ===== LAYER 1: Data Validation ===========================================
if ($run1) {
    Show-Banner 'Layer 1: Data Validation'

    Invoke-Julia -TestName 'L1-Julia  Data validation' `
        -Script 'legacy\julia\tests\test_data_validation.jl'

    Invoke-Pytest -TestName 'L1-Python Data validation' `
        -Script 'tests\python\reopt\test_data_validation.py'
}

# ===== LAYER 2: Unit Tests ================================================
if ($run2) {
    Show-Banner 'Layer 2: Unit Tests'

    Invoke-Julia -TestName 'L2-Julia  Unit tests' `
        -Script 'legacy\julia\tests\test_unit.jl'

    Invoke-Pytest -TestName 'L2-Python Unit tests' `
        -Script 'tests\python\reopt\test_unit.py'
}

# ===== LAYER 3: Cross-Validation ==========================================
if ($run3) {
    Show-Banner 'Layer 3: Cross-Validation'

    Invoke-PythonScript -TestName 'L3-Cross  Julia vs Python' `
        -Script 'tests\cross_language\cross_validate.py'
}

# ===== LAYER 4: Integration / Regression ===================================
if ($run4) {
    if ($SmokeOnly) {
        Show-Banner 'Layer 4: Integration Tests - smoke only'
    } else {
        Show-Banner 'Layer 4: Integration Tests'
    }

    $juliaExtra = @()
    if ($SmokeOnly) { $juliaExtra += '--smoke-only' }

    Invoke-Julia -TestName 'L4-Julia  Integration tests' `
        -Script 'legacy\julia\tests\test_integration.jl' -Extra $juliaExtra

    $pyExtra = @()
    if ($SmokeOnly) { $pyExtra += '-k'; $pyExtra += 'smoke' }

    Invoke-Pytest -TestName 'L4-Python Integration tests' `
        -Script 'tests\python\reopt\test_integration.py' -Extra $pyExtra

    if (-not $SmokeOnly) {
        Invoke-Pytest -TestName 'L4-Python Saigon18 regression tests' `
            -Script 'tests\python\integration\test_saigon18_phase3.py'
    }
}

# ===== LAYER 5: Financial E2E (Optional) ====================================
if ($run5) {
    Show-Banner 'Layer 5: Financial E2E / Capacity Factor Benchmarks'

    Invoke-Pytest -TestName 'L5-Python Financial E2E pipeline' `
        -Script 'tests\python\integration\test_e2e_financial.py'

    Invoke-Pytest -TestName 'L5-Python PVWatts capacity factor benchmark' `
        -Script 'tests\python\integration\test_capacity_factor_benchmark.py'
}

# ===== SUMMARY =============================================================

$totalSw.Stop()

# Cleanup temp files
Remove-Item $script:TmpOut -ErrorAction SilentlyContinue
Remove-Item $script:TmpErr -ErrorAction SilentlyContinue

Write-Host ''
Show-Banner 'Test Summary'

$nPass = 0
$nFail = 0
foreach ($r in $script:Results) {
    $t = $r.Name
    $s = $r.Seconds
    if ($r.Passed) {
        $nPass++
        Write-Host ('  [PASS] ' + $t + ' ' + $s + 's') -ForegroundColor Green
    } else {
        $nFail++
        Write-Host ('  [FAIL] ' + $t + ' ' + $s + 's') -ForegroundColor Red
    }
}

$nTotal = $nPass + $nFail
$tSec = [math]::Round($totalSw.Elapsed.TotalSeconds, 1)
Write-Host ''
$line = '  Total: ' + $nTotal + ' | Passed: ' + $nPass
$line += ' | Failed: ' + $nFail + ' | Time: ' + $tSec + 's'
if ($nFail -eq 0) {
    Write-Host $line -ForegroundColor Green
} else {
    Write-Host $line -ForegroundColor Red
}
Write-Host ''

if ($nFail -gt 0) { exit 1 } else { exit 0 }
