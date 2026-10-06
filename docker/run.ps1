#Requires -Version 5.1
<#
.SYNOPSIS
    AnonShield — Docker wrapper for Windows (PowerShell).

.DESCRIPTION
    Creates an .\anon\ folder in your current directory to keep everything
    together: input files, output, and the NER model cache.

      anon\
      ├── input\    ← optional: put files here if you prefer
      ├── output\   ← anonymized files appear here
      ├── db\       ← entity mapping database (needed for de-anonymization)
      ├── models\   ← NER model cached here on first run (~1 GB, automatic)
      └── secret.key ← HMAC key, created on the first run (unless ANON_SECRET_KEY is set)

.EXAMPLE
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
$KeyFile       = Join-Path $AnonDir "secret.key"

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
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Err "Docker is not installed: https://docs.docker.com/desktop/setup/install/windows-install/"
    exit 1
}
# Windows PowerShell 5.1 turns a native command's stderr into a terminating
# error under "Stop" when it is redirected; "docker info" writes there when
# the engine is down.
$ErrorActionPreference = "Continue"
$null = & docker info 2>&1
$dockerOk = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = "Stop"
if (-not $dockerOk) {
    Write-Err "Docker is not running. Start Docker Desktop and try again."
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
# Secret key: $env:ANON_SECRET_KEY if set, otherwise the one kept in
# anon\secret.key, created on the first run. The same key gives the same
# pseudonyms across runs. --slug-length 0 (type-only labels) needs none.
# ---------------------------------------------------------------------------
$SecretKey = if ($env:ANON_SECRET_KEY) { $env:ANON_SECRET_KEY } else { "" }
if (-not $SecretKey -and -not $IsInfoCmd -and -not $SlugZero) {
    if (-not (Test-Path $KeyFile -PathType Leaf) -or -not (Get-Content $KeyFile -Raw)) {
        $bytes = New-Object byte[] 32
        [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
        $newKey = [System.BitConverter]::ToString($bytes).Replace("-", "").ToLower()
        Set-Content -Path $KeyFile -Value $newKey -NoNewline -Encoding ascii
        Write-Info "Created a secret key in $KeyFile; it keeps pseudonyms the same across runs."
        Write-Info "Keep it with $DbDir (or set ANON_SECRET_KEY to use your own key)."
    }
    $SecretKey = (Get-Content $KeyFile -Raw).Trim()
}

# ---------------------------------------------------------------------------
# Select image
# ---------------------------------------------------------------------------
# The GPU image comes in two PyTorch builds: :gpu (CUDA 13.0) needs NVIDIA
# driver 580+ and an RTX 20xx or newer (CUDA 13 dropped older GPUs; RTX 50xx
# needs it); :gpu-cu126 (CUDA 12.6) covers older GPUs and drivers.
# $env:ANON_GPU_IMAGE overrides the choice.
function Get-GpuImage {
    $info = $null
    try { $info = (& nvidia-smi --query-gpu=compute_cap,driver_version --format=csv,noheader 2>$null | Select-Object -First 1) } catch { }
    if (-not $info -or $info -notmatch '^\s*(\d+)\.(\d+)\s*,\s*(\d+)') {
        Write-Info "Could not read the GPU from nvidia-smi; using anonshield/anon:gpu"
        return "anonshield/anon:gpu"
    }
    $cc = [int]$Matches[1] * 10 + [int]$Matches[2]
    $driverMajor = [int]$Matches[3]
    if ($cc -ge 75 -and $driverMajor -ge 580) { return "anonshield/anon:gpu" }
    if ($cc -ge 100) {
        Write-Info "This GPU needs NVIDIA driver 580+ for GPU inference (driver $driverMajor); it will run on CPU"
    }
    return "anonshield/anon:gpu-cu126"
}

if ($UseGpu) {
    $Image    = if ($env:ANON_GPU_IMAGE) { $env:ANON_GPU_IMAGE } else { Get-GpuImage }
    $GpuFlags = [string[]]@("--gpus", "all")
    Write-Info "Using GPU image $Image"
} else {
    $Image    = "anonshield/anon:latest"
    $GpuFlags = [string[]]@()
}

# ---------------------------------------------------------------------------
# Info commands — no path remapping needed
# ---------------------------------------------------------------------------
# The key is handed to docker run by name (-e ANON_SECRET_KEY), so it is not on
# its command line; the session's own value is put back right after.
$PrevKey = $env:ANON_SECRET_KEY

if ($IsInfoCmd) {
    $env:ANON_SECRET_KEY = $SecretKey
    & docker run --rm @GpuFlags `
        -e ANON_SECRET_KEY `
        -v "${ModelsDir}:/app/models" `
        $Image `
        @ScriptArgs
    $code = $LASTEXITCODE
    $env:ANON_SECRET_KEY = $PrevKey
    exit $code
}

# ---------------------------------------------------------------------------
# Remap local paths to container paths
#
# Each local path gets its own volume mount:
#   input file/dir  → /anon_input[/filename]
#   --output-dir    → /anon_output
#   --anonymization-config, --word-list, --custom-patterns, --config
#                   → /anon_files/<n>/filename
# ---------------------------------------------------------------------------
$Volumes    = [System.Collections.Generic.List[string]]::new()
$Volumes.AddRange([string[]]@("-v", "${ModelsDir}:/app/models", "-v", "${DbDir}:/app/db"))

$NewArgs    = [System.Collections.Generic.List[string]]::new()

# anon.py flags that take no value (store_true / store_false)
$BoolFlags = @("--help", "--list-entities", "--list-languages", "--overwrite", "--no-report",
    "--preserve-row-context", "--optimize", "--use-cache", "--no-use-cache", "--skip-numeric",
    "--regex-priority", "--disable-gc", "--force-large-xml", "--generate-ner-data", "--ner-include-all",
    "--ner-aggregate-record", "--use-datasets")
# Flags whose value is a file on the host: its directory is mounted read-only
$FileFlags = @("--anonymization-config", "--word-list", "--custom-patterns", "--config")
$script:FileMounts = 0
function Add-FileArg([string]$flag, [string]$val) {
    $hostPath = Get-HostPath $val
    if (-not (Test-Path $hostPath -PathType Leaf)) {
        Write-Err "File not found for ${flag}: $val"
        exit 1
    }
    $script:FileMounts++
    $mnt  = "/anon_files/$($script:FileMounts)"
    $dir  = Split-Path $hostPath -Parent
    $leaf = Split-Path $hostPath -Leaf
    $Volumes.AddRange([string[]]@("-v", "${dir}:${mnt}:ro"))
    $NewArgs.AddRange([string[]]@($flag, "$mnt/$leaf"))
}

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

    } elseif ($FileFlags -contains $arg) {
        $i++
        if ($i -ge $ScriptArgs.Count) { Write-Err "$arg needs a file path."; exit 1 }
        Add-FileArg $arg $ScriptArgs[$i]

    } elseif ($arg -like "--*=*" -and ($FileFlags -contains $arg.Split("=", 2)[0])) {
        $parts = $arg.Split("=", 2)
        Add-FileArg $parts[0] $parts[1]

    } elseif ($arg -like "--*=*") {
        $NewArgs.Add($arg)

    } elseif ($arg -like "--*") {
        # Flags that take a value carry the next token; boolean flags do not
        # (treating "--overwrite file.csv" as flag + value swallowed the input path)
        $NewArgs.Add($arg)
        $next = $i + 1
        if (-not ($BoolFlags -contains $arg) -and $next -lt $ScriptArgs.Count) {
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
$VolumesArr  = $Volumes.ToArray()
$NewArgsArr  = $NewArgs.ToArray()

$env:ANON_SECRET_KEY = $SecretKey
& docker run --rm @GpuFlags `
    -e ANON_SECRET_KEY `
    @VolumesArr `
    $Image `
    @NewArgsArr
$code = $LASTEXITCODE
$env:ANON_SECRET_KEY = $PrevKey
if ($code -ne 0) { exit $code }

Write-Ok "Output is in $OutputHost"
