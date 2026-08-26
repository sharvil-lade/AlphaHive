# PowerShell entry point: `./build`, `./build setup`, `./build test`, ...
#
# All the logic lives in ./build (bash). This only locates Git Bash and forwards.
# It does NOT use whatever `bash` is on PATH, because on Windows that is usually
# WSL's bash, which can't see the Windows virtualenv this project builds.

$ErrorActionPreference = 'Stop'

$gitBash = @(
    "$env:ProgramFiles\Git\bin\bash.exe",
    "${env:ProgramFiles(x86)}\Git\bin\bash.exe",
    "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $gitBash) {
    Write-Error "Git Bash not found. Install Git for Windows: https://git-scm.com/download/win"
    exit 1
}

# Windows PowerShell 5.1 has no VT processing, so ANSI codes print as literal "[1m".
if ($PSVersionTable.PSVersion.Major -lt 6) { $env:NO_COLOR = '1' }

& $gitBash "$PSScriptRoot\build" @args
exit $LASTEXITCODE
