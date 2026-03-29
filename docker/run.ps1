#Requires -Version 5.1
<#
.SYNOPSIS
    AnonLFI — Docker wrapper for Windows (PowerShell).

.DESCRIPTION
    Creates an .\anon\ folder in your current directory to keep everything
    together: input files, output, and the NER model cache.

      anon\
      ├── input\    ← optional: put files here if you prefer
      ├── output\   ← anonymized files appear here
      ├── db\       ← entity mapping database (needed for de-anonymization)
      └── models\   ← NER model cached here on first run (~1 GB, automatic)

.EXAMPLE
    $env:ANON_SECRET_KEY = [System.BitConverter]::ToString(
        [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
    ).Replace("-","").ToLower()

    .\run.ps1 .\YOUR_FILE.csv
    .\run.ps1 .\your\folder\
    .\run.ps1 --gpu .\YOUR_FILE.csv
    .\run.ps1 --help
    .\run.ps1 --list-entities

.NOTES
    Override the base folder:
      $env:ANON_DIR = ".\my-project"; .\run.ps1 .\my-project\input\file.csv
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Write-Info { param([string]$Msg) Write-Host "[anon] $Msg" -ForegroundColor Cyan  }
function Write-Ok   { param([string]$Msg) Write-Host "[anon] $Msg" -ForegroundColor Green }
function Write-Err  { param([string]$Msg) Write-Host "[anon] $Msg" -ForegroundColor Red   }

# Resolve an absolute path whether or not the target exists yet.
function Get-HostPath {
    param([string]$Path)
    if (Test-Path $Path -PathType Container) {
        return (Resolve-Path $Path).ProviderPath
    }
    $parent = Split-Path $Path -Parent
    if (-not $parent -or $parent -eq '') { $parent = (Get-Location).Path }
    $leaf = Split-Path $Path -Leaf
    return [System.IO.Path]::GetFullPath((Join-Path $parent $leaf))
}

# ---------------------------------------------------------------------------
# Base directory — everything lives here
# ---------------------------------------------------------------------------
$AnonDir       = if ($env:ANON_DIR) { $env:ANON_DIR } else { Join-Path (Get-Location).Path "anon" }
$ModelsDir     = Join-Path $AnonDir "models"
$DefaultOutput = Join-Path $AnonDir "output"
$DbDir         = Join-Path $AnonDir "db"

# ---------------------------------------------------------------------------
# Parse --gpu (consumed here, not forwarded)
# ---------------------------------------------------------------------------
$UseGpu     = $false
$ScriptArgs = [System.Collections.Generic.List[string]]::new()
foreach ($a in $args) {
    if ($a -eq "--gpu") { $UseGpu = $true }
    else                { $ScriptArgs.Add([string]$a) }
}

# ---------------------------------------------------------------------------
# Detect info-only commands and slug-length 0 (no key needed)
# ---------------------------------------------------------------------------
$IsInfoCmd = $false
$SlugZero  = $false
$prev      = ""
foreach ($a in $ScriptArgs) {
    if ($a -eq "--help" -or $a -like "--list-*") { $IsInfoCmd = $true }
    if ($prev -eq "--slug-length" -and $a -eq "0") { $SlugZero = $true }
    if ($a -eq "--slug-length=0")                  { $SlugZero = $true }
    $prev = $a
}

# ---------------------------------------------------------------------------
# Validate Docker
# ---------------------------------------------------------------------------
$dockerCheck = & docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Docker is not running."
    exit 1
}

# ---------------------------------------------------------------------------
# Validate secret key
# ---------------------------------------------------------------------------
if (-not $env:ANON_SECRET_KEY -and -not $IsInfoCmd -and -not $SlugZero) {
    Write-Err "ANON_SECRET_KEY is not set."
    Write-Err "Generate one (run in PowerShell):"
    Write-Err '  $env:ANON_SECRET_KEY = [System.BitConverter]::ToString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).Replace("-","").ToLower()'
    exit 1
}

# ---------------------------------------------------------------------------
# Create folder structure
# ---------------------------------------------------------------------------
$null = New-Item -ItemType Directory -Force -Path $ModelsDir
$null = New-Item -ItemType Directory -Force -Path $DefaultOutput
$null = New-Item -ItemType Directory -Force -Path (Join-Path $AnonDir "input")
$null = New-Item -ItemType Directory -Force -Path $DbDir

# ---------------------------------------------------------------------------
# Select image
# ---------------------------------------------------------------------------
if ($UseGpu) {
    $Image    = "anonshield/anon:gpu"
    $GpuFlags = [string[]]@("--gpus", "all")
    Write-Info "Using GPU image"
} else {
    $Image    = "anonshield/anon:latest"
    $GpuFlags = [string[]]@()
}

# ---------------------------------------------------------------------------
# Info commands — no path remapping needed
# ---------------------------------------------------------------------------
if ($IsInfoCmd) {
    $secretKey = if ($env:ANON_SECRET_KEY) { $env:ANON_SECRET_KEY } else { "" }
    & docker run --rm @GpuFlags `
        -e "ANON_SECRET_KEY=$secretKey" `
        -v "${ModelsDir}:/app/models" `
        $Image `
        @ScriptArgs
    exit $LASTEXITCODE
}

# ---------------------------------------------------------------------------
# Remap local paths to container paths
#
# Each local path gets its own volume mount:
#   input file/dir  → /anon_input[/filename]
#   --output-dir    → /anon_output
#   --anonymization-config → /anon_config/filename
#   --word-list     → /anon_wordlist/filename
# ---------------------------------------------------------------------------
$Volumes    = [System.Collections.Generic.List[string]]::new()
$Volumes.AddRange([string[]]@("-v", "${ModelsDir}:/app/models", "-v", "${DbDir}:/app/db"))

$NewArgs    = [System.Collections.Generic.List[string]]::new()
$InputSet   = $false
$OutputSet  = $false
$OutputHost = ""

$i = 0
while ($i -lt $ScriptArgs.Count) {
    $arg = $ScriptArgs[$i]

    if ($arg -eq "--output-dir") {
        $i++
        $val  = $ScriptArgs[$i]
        $hostPath = Get-HostPath $val
        $null = New-Item -ItemType Directory -Force -Path $hostPath
        $Volumes.AddRange([string[]]@("-v", "${hostPath}:/anon_output"))
        $NewArgs.AddRange([string[]]@("--output-dir", "/anon_output"))
        $OutputSet  = $true
        $OutputHost = $hostPath

    } elseif ($arg -like "--output-dir=*") {
        $val  = $arg.Substring("--output-dir=".Length)
        $hostPath = Get-HostPath $val
        $null = New-Item -ItemType Directory -Force -Path $hostPath
        $Volumes.AddRange([string[]]@("-v", "${hostPath}:/anon_output"))
        $NewArgs.AddRange([string[]]@("--output-dir", "/anon_output"))
        $OutputSet  = $true
        $OutputHost = $hostPath

    } elseif ($arg -eq "--anonymization-config") {
        $i++
        $val  = $ScriptArgs[$i]
        $hostPath = Get-HostPath $val
        $dir  = Split-Path $hostPath -Parent
        $leaf = Split-Path $hostPath -Leaf
        $Volumes.AddRange([string[]]@("-v", "${dir}:/anon_config:ro"))
        $NewArgs.AddRange([string[]]@("--anonymization-config", "/anon_config/$leaf"))

    } elseif ($arg -like "--anonymization-config=*") {
        $val  = $arg.Substring("--anonymization-config=".Length)
        $hostPath = Get-HostPath $val
        $dir  = Split-Path $hostPath -Parent
        $leaf = Split-Path $hostPath -Leaf
        $Volumes.AddRange([string[]]@("-v", "${dir}:/anon_config:ro"))
        $NewArgs.Add("--anonymization-config=/anon_config/$leaf")

    } elseif ($arg -eq "--word-list") {
        $i++
        $val  = $ScriptArgs[$i]
        $hostPath = Get-HostPath $val
        $dir  = Split-Path $hostPath -Parent
        $leaf = Split-Path $hostPath -Leaf
        $Volumes.AddRange([string[]]@("-v", "${dir}:/anon_wordlist:ro"))
        $NewArgs.AddRange([string[]]@("--word-list", "/anon_wordlist/$leaf"))

    } elseif ($arg -like "--word-list=*") {
        $val  = $arg.Substring("--word-list=".Length)
        $hostPath = Get-HostPath $val
        $dir  = Split-Path $hostPath -Parent
        $leaf = Split-Path $hostPath -Leaf
        $Volumes.AddRange([string[]]@("-v", "${dir}:/anon_wordlist:ro"))
        $NewArgs.Add("--word-list=/anon_wordlist/$leaf")

    } elseif ($arg -like "--*") {
        # Pass through flag unchanged; if the next token is a value (not a flag), carry it too
        $NewArgs.Add($arg)
        $next = $i + 1
        if ($next -lt $ScriptArgs.Count -and -not $ScriptArgs[$next].StartsWith("--")) {
            $i++
            $NewArgs.Add($ScriptArgs[$i])
        }

    } else {
        # First positional argument = input path
        if (-not $InputSet) {
            $InputSet = $true
            $hostPath = Get-HostPath $arg
            if (-not (Test-Path $hostPath)) {
                Write-Err "Input not found: $arg"
                exit 1
            }
            if (Test-Path $hostPath -PathType Container) {
                $Volumes.AddRange([string[]]@("-v", "${hostPath}:/anon_input:ro"))
                $NewArgs.Add("/anon_input")
            } else {
                $dir  = Split-Path $hostPath -Parent
                $leaf = Split-Path $hostPath -Leaf
                $Volumes.AddRange([string[]]@("-v", "${dir}:/anon_input:ro"))
                $NewArgs.Add("/anon_input/$leaf")
            }
        } else {
            $NewArgs.Add($arg)
        }
    }

    $i++
}

# Default output: .\anon\output\
if (-not $OutputSet) {
    $OutputHost = $DefaultOutput
    $Volumes.AddRange([string[]]@("-v", "${OutputHost}:/anon_output"))
    $NewArgs.AddRange([string[]]@("--output-dir", "/anon_output"))
}

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
$secretKey   = if ($env:ANON_SECRET_KEY) { $env:ANON_SECRET_KEY } else { "" }
$VolumesArr  = $Volumes.ToArray()
$NewArgsArr  = $NewArgs.ToArray()

& docker run --rm @GpuFlags `
    -e "ANON_SECRET_KEY=$secretKey" `
    @VolumesArr `
    $Image `
    @NewArgsArr

Write-Ok "Output is in $OutputHost"
