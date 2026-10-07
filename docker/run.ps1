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

if ($args.Count -eq 0 -or $args[0] -in @('-h', '--help')) {
    Write-Host @"
Usage: .\run.ps1 [--gpu] FILE_OR_FOLDER [OPTIONS]
       .\run.ps1 --web [--gpu] [--port N | --stop | --update]

Web interface, in your browser:
  .\run.ps1 --web             Start it, then open http://localhost:8080
  .\run.ps1 --web --gpu       The same on an NVIDIA GPU (much faster NER)
  .\run.ps1 --web --port 8081 Use another port
  .\run.ps1 --web --stop      Stop it (the key and models are kept)
  .\run.ps1 --web --update    Download the latest version and restart it

Command line, examples:
  .\run.ps1 report.csv
  .\run.ps1 "reports for review" --output-dir .\results
  .\run.ps1 report.txt --anonymization-strategy regex

Results: .\anon\output   Key: .\anon\secret.key   Mapping: .\anon\db
First NER run downloads a model (about 1 GB); regex needs no model.
Use --lang pt for Portuguese, --overwrite to replace existing results,
--slug-length 0 for type-only labels, or --config FILE for YAML/JSON settings.
Use --cli-help for all engine options (requires Docker).
ANON_DIR changes the workspace; ANON_IMAGE overrides the CPU image.
"@
    exit 0
}

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
$AnonDir       = Get-HostPath $(if ($env:ANON_DIR) { $env:ANON_DIR } else { Join-Path (Get-Location).Path "anon" })
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
    elseif ($a -eq "--cli-help") { $ScriptArgs.Add("--help") }
    else { $ScriptArgs.Add([string]$a) }
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
# --web: the web interface, one container (anonshield/anon:web) whose key,
# models and metrics live in the "anonshield" volume
# ---------------------------------------------------------------------------
# GPU images come in two PyTorch builds: the plain tag (CUDA 13.0) needs NVIDIA
# driver 580+ and an RTX 20xx or newer (CUDA 13 dropped older GPUs; RTX 50xx
# needs it); the -cu126 tag (CUDA 12.6) covers older GPUs and drivers.
# Usage: Get-GpuImage "anonshield/anon:gpu" (or "anonshield/anon:web-gpu").
function Get-GpuImage {
    param([string]$Base)
    $info = $null
    try { $info = (& nvidia-smi --query-gpu=compute_cap,driver_version --format=csv,noheader 2>$null | Select-Object -First 1) } catch { }
    if (-not $info -or $info -notmatch '^\s*(\d+)\.(\d+)\s*,\s*(\d+)') {
        Write-Info "Could not read the GPU from nvidia-smi; using $Base"
        return $Base
    }
    $cc = [int]$Matches[1] * 10 + [int]$Matches[2]
    $driverMajor = [int]$Matches[3]
    if ($cc -ge 75 -and $driverMajor -ge 580) { return $Base }
    if ($cc -ge 100) {
        Write-Info "This GPU needs NVIDIA driver 580+ for GPU inference (driver $driverMajor); it will run on CPU"
    }
    return "$Base-cu126"
}

if ($args -contains '--web') {
    $WebImage = if ($env:ANON_WEB_IMAGE) { $env:ANON_WEB_IMAGE } else { "anonshield/anon:web" }
    $WebName  = "anonshield"
    $WebArgs  = @($args)
    $Action   = "start"
    $Port     = "8080"
    $WebGpu   = $false
    for ($i = 0; $i -lt $WebArgs.Count; $i++) {
        $a = [string]$WebArgs[$i]
        if ($a -eq '--web') { }
        elseif ($a -eq '--gpu') { $WebGpu = $true }
        elseif ($a -eq '--stop') { $Action = "stop" }
        elseif ($a -eq '--update') { $Action = "update" }
        elseif ($a -eq '--port') { $i++; $Port = if ($i -lt $WebArgs.Count) { [string]$WebArgs[$i] } else { "" } }
        elseif ($a -like '--port=*') { $Port = $a.Substring(7) }
        else { Write-Err "With --web, use --gpu, --port N, --stop or --update (got: $a)."; exit 2 }
    }
    if ($Port -notmatch '^\d+$') { Write-Err "--port needs a number. Example: .\run.ps1 --web --port 8081"; exit 2 }

    $ErrorActionPreference = "Continue"
    function Get-WebPort { ((& docker port $WebName 8080/tcp 2>$null) | Select-Object -First 1) -replace '.*:', '' }
    $State = & docker inspect -f '{{.State.Status}}' $WebName 2>$null
    $WebGpuFlags = [string[]]@()
    if ($WebGpu) {
        if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
            Write-Err "No NVIDIA driver found (nvidia-smi). Use .\run.ps1 --web for the CPU version."; exit 1
        }
        $WebImage = if ($env:ANON_WEB_GPU_IMAGE) { $env:ANON_WEB_GPU_IMAGE } else { Get-GpuImage "anonshield/anon:web-gpu" }
        $WebGpuFlags = [string[]]@("--gpus", "all")
    }
    # Another kind (CPU or GPU) is replaced; the volume keeps the key and models.
    $Current = & docker inspect -f '{{.Config.Image}}' $WebName 2>$null
    if ($Action -ne "stop" -and $State -and $Current -ne $WebImage) {
        Write-Info "Switching the web interface from $Current to $WebImage (the key and models are kept)."
        $null = & docker rm -f $WebName 2>&1
        $State = $null
    }

    if ($Action -eq "stop") {
        if ($State -eq "running") {
            $null = & docker stop $WebName 2>&1
            Write-Ok "Stopped. The key and models are kept; start again with .\run.ps1 --web"
        } else { Write-Info "The web interface is not running." }
        exit 0
    }
    if ($Action -eq "update") {
        & docker pull $WebImage
        if ($LASTEXITCODE -ne 0) { exit 1 }
        if ($State) { $null = & docker rm -f $WebName 2>&1 }
        $State = $null
    }

    if ($State -eq "running") {
        Write-Ok "AnonShield ($WebImage) is already running: http://localhost:$(Get-WebPort)"
        Write-Info "Stop it with .\run.ps1 --web --stop"
        exit 0
    } elseif ($State) {
        $Out = & docker start $WebName 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { Write-Err "Could not start the web interface: $($Out.Trim())"; exit 1 }
        $Port = Get-WebPort
    } else {
        $null = & docker image inspect $WebImage 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Info "Downloading $WebImage (about $(if ($WebGpu) { 4 } else { 1.5 }) GB, once)..."
            & docker pull $WebImage
            if ($LASTEXITCODE -ne 0) { exit 1 }
        }
        $Out = & docker run -d --name $WebName --restart unless-stopped @WebGpuFlags -p "127.0.0.1:${Port}:8080" -v anonshield:/data $WebImage 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) {
            $null = & docker rm -f $WebName 2>&1
            if ($Out -match 'could not select device driver|nvidia-container') {
                Write-Err "Docker cannot use the GPU: enable GPU support in Docker Desktop (WSL 2) or install the NVIDIA Container Toolkit, or use .\run.ps1 --web for the CPU version."
            } elseif ($Out -match 'already allocated|address already in use') {
                Write-Err "Port $Port is used by another program. Choose another: .\run.ps1 --web --port $([int]$Port + 1)"
            } else { Write-Err "Could not start the web interface: $(($Out.Trim() -split "`n")[-1])" }
            exit 1
        }
    }

    Write-Info "Starting..."
    for ($n = 0; $n -lt 90; $n++) {
        if ((& docker inspect -f '{{.State.Running}}' $WebName 2>$null) -ne "true") {
            Write-Err "It stopped while starting. Its last messages:"
            & docker logs --tail 5 $WebName
            exit 1
        }
        if ((& docker inspect -f '{{.State.Health.Status}}' $WebName 2>$null) -eq "healthy") { break }
        Start-Sleep -Seconds 2
    }
    Write-Ok "AnonShield is ready: http://localhost:$Port ($WebImage)"
    Write-Info "Stop: .\run.ps1 --web --stop    Update: .\run.ps1 --web --update"
    exit 0
}

# ---------------------------------------------------------------------------
# Create folder structure
# ---------------------------------------------------------------------------
$null = New-Item -ItemType Directory -Force -Path $ModelsDir
$null = New-Item -ItemType Directory -Force -Path $DefaultOutput
$null = New-Item -ItemType Directory -Force -Path (Join-Path $AnonDir "input")
$null = New-Item -ItemType Directory -Force -Path $DbDir
$null = New-Item -ItemType Directory -Force -Path (Join-Path $AnonDir "logs")

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

if ($UseGpu) {
    $Image    = if ($env:ANON_GPU_IMAGE) { $env:ANON_GPU_IMAGE } else { Get-GpuImage "anonshield/anon:gpu" }
    $GpuFlags = [string[]]@("--gpus", "all")
    Write-Info "Using GPU image $Image"
} else {
    $Image    = if ($env:ANON_IMAGE) { $env:ANON_IMAGE } else { "anonshield/anon:latest" }
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
$Volumes.AddRange([string[]]@("-v", "${ModelsDir}:/app/models", "-v", "${AnonDir}/logs:/app/logs"))

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
    if (-not $val) { Write-Err "$flag needs a file path."; exit 2 }
    $hostPath = Get-HostPath $val
    if (-not (Test-Path $hostPath -PathType Leaf)) {
        Write-Err "File not found for ${flag}: $val"
        exit 1
    }
    $script:FileMounts++
    $mnt  = "/anon_files/$($script:FileMounts)"
    $dir  = Split-Path $hostPath -Parent
    $leaf = Split-Path $hostPath -Leaf
    $root = (Get-Location).Path
    if ($hostPath.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar)) {
        $dir = $root
        $leaf = $hostPath.Substring($root.Length + 1).Replace('\', '/')
    }
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
        if ($i -ge $ScriptArgs.Count -or -not $ScriptArgs[$i] -or $ScriptArgs[$i].StartsWith("--")) { Write-Err "--output-dir needs a path. Example: --output-dir .\results"; exit 2 }
        $val  = $ScriptArgs[$i]
        $hostPath = Get-HostPath $val
        $null = New-Item -ItemType Directory -Force -Path $hostPath
        $Volumes.AddRange([string[]]@("-v", "${hostPath}:/anon_output"))
        $NewArgs.AddRange([string[]]@("--output-dir", "/anon_output"))
        $OutputSet  = $true
        $OutputHost = $hostPath

    } elseif ($arg -like "--output-dir=*") {
        $val  = $arg.Substring("--output-dir=".Length)
        if (-not $val) { Write-Err "--output-dir needs a path. Example: --output-dir .\results"; exit 2 }
        $hostPath = Get-HostPath $val
        $null = New-Item -ItemType Directory -Force -Path $hostPath
        $Volumes.AddRange([string[]]@("-v", "${hostPath}:/anon_output"))
        $NewArgs.AddRange([string[]]@("--output-dir", "/anon_output"))
        $OutputSet  = $true
        $OutputHost = $hostPath

    } elseif ($arg -eq '--db-dir' -or $arg -like '--db-dir=*') {
        if ($arg -like '--db-dir=*') { $val = $arg.Substring('--db-dir='.Length) }
        else {
            $i++
            if ($i -ge $ScriptArgs.Count) { Write-Err "--db-dir needs a path."; exit 2 }
            $val = $ScriptArgs[$i]
        }
        if (-not $val -or $val.StartsWith('--')) { Write-Err "--db-dir needs a path."; exit 2 }
        $DbDir = Get-HostPath $val
        $null = New-Item -ItemType Directory -Force -Path $DbDir
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
                $InputHost = $hostPath
                $NewArgs.Add("/anon_input")
            } else {
                $InputHost = Split-Path $hostPath -Parent
                $leaf = Split-Path $hostPath -Leaf
                $NewArgs.Add("/anon_input/$leaf")
            }
            $Volumes.AddRange([string[]]@("-v", "${InputHost}:/anon_input:ro"))
        } else {
            $NewArgs.Add($arg)
        }
    }

    $i++
}

if (-not $InputSet) { Write-Err "Choose a file or folder. Example: .\run.ps1 report.csv (use --help for more)."; exit 2 }
$Volumes.AddRange([string[]]@("-v", "${DbDir}:/app/db"))
$NewArgs.AddRange([string[]]@("--db-dir", "/app/db"))

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
    -e "ANON_HOST_INPUT_DIR=$InputHost" `
    -e "ANON_HOST_OUTPUT_DIR=$OutputHost" `
    @VolumesArr `
    $Image `
    @NewArgsArr
$code = $LASTEXITCODE
$env:ANON_SECRET_KEY = $PrevKey
if ($code -ne 0) { exit $code }

Write-Ok "Output is in $OutputHost"
