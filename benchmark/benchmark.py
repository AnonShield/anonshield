#!/usr/bin/env python3
"""
AnonLFI Benchmark Suite - Professional Benchmarking Tool

A modular, resilient benchmarking system for comparing AnonLFI versions 1.0, 2.0, and 3.0.
Designed with SOLID principles for maintainability and extensibility.

Features:
- Automatic environment setup with cache warming
- Real-time output streaming to terminal
- Comprehensive metrics collection (time, memory, CPU, throughput)
- Resilient to failures with full error logging
- Incremental progress saving (can resume from interruption)
- Configurable via CLI arguments

Author: AnonShield Team
"""

import argparse
import csv
import hashlib
import json
import os
import platform
import psutil
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Iterator, Callable


# =============================================================================
# CONFIGURATION
# =============================================================================

class AnonVersion(Enum):
    """Supported AnonLFI versions."""
    V1_0 = "1.0"
    V2_0 = "2.0"
    V3_0 = "3.0"


class Strategy(Enum):
    """Anonymization strategies (v3.0 only)."""
    DEFAULT = "default"
    PRESIDIO = "presidio"
    FAST = "fast"
    BALANCED = "balanced"


@dataclass
class VersionConfig:
    """Configuration for each AnonLFI version."""
    version: AnonVersion
    relative_path: str
    venv_name: str
    supported_extensions: tuple
    supports_directory: bool
    requires_secret_key: bool
    strategies: tuple

    @property
    def path(self) -> Path:
        return Path.cwd() / self.relative_path

    @property
    def venv_path(self) -> Path:
        return self.path / self.venv_name

    @property
    def python_executable(self) -> Path:
        if platform.system() == "Windows":
            return self.venv_path / "Scripts" / "python.exe"
        return self.venv_path / "bin" / "python"

    @property
    def anon_script(self) -> Path:
        return self.path / "anon.py"


# Version configurations
VERSION_CONFIGS = {
    AnonVersion.V1_0: VersionConfig(
        version=AnonVersion.V1_0,
        relative_path="anonlfi_1.0",
        venv_name=".venv",
        # v1.0: .txt, .docx, .csv, .xlsx, .xml (5 formats)
        supported_extensions=(".txt", ".docx", ".csv", ".xlsx", ".xml"),
        supports_directory=False,
        requires_secret_key=False,  # Uses simple SHA256, no secret key
        strategies=(Strategy.DEFAULT,)
    ),
    AnonVersion.V2_0: VersionConfig(
        version=AnonVersion.V2_0,
        relative_path="anonlfi_2.0",
        venv_name=".venv",
        # v2.0: .txt, .pdf, .docx, .csv, .xlsx, .xml, .json + images (13 formats)
        supported_extensions=(
            ".txt", ".pdf", ".docx", ".csv", ".xlsx", ".xml", ".json",
            ".jpeg", ".jpg", ".png", ".gif", ".bmp", ".tiff"
        ),
        supports_directory=True,
        requires_secret_key=True,
        strategies=(Strategy.DEFAULT,)
    ),
    AnonVersion.V3_0: VersionConfig(
        version=AnonVersion.V3_0,
        relative_path=".",
        venv_name=".venv_benchmark",
        # v3.0: All v2.0 formats + .log, .jsonl, .tif, .webp, .jp2, .pnm (19 formats)
        supported_extensions=(
            ".txt", ".log", ".pdf", ".docx", ".csv", ".xlsx", ".xml",
            ".json", ".jsonl",
            ".jpeg", ".jpg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".jp2", ".pnm"
        ),
        supports_directory=True,
        requires_secret_key=True,
        strategies=(Strategy.PRESIDIO, Strategy.FAST, Strategy.BALANCED)
    ),
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class BenchmarkMetrics:
    """Container for all collected benchmark metrics.

    Supports three measurement modes, identified by the `measurement_mode` field:

    ┌─────────────────────┬───────────────────────────────────────────────────────┐
    │ measurement_mode    │ Description                                           │
    ├─────────────────────┼───────────────────────────────────────────────────────┤
    │ "single_file"       │ One process per file. /usr/bin/time and               │
    │                     │ ProcessMonitor capture full process lifecycle.         │
    │                     │ wall_clock INCLUDES model loading overhead.            │
    │                     │ All fields populated.                                  │
    ├─────────────────────┼───────────────────────────────────────────────────────┤
    │ "directory_aggregate│ One process for all files. /usr/bin/time and           │
    │                     │ ProcessMonitor capture full process lifecycle.         │
    │                     │ wall_clock = ONE model load + all files.               │
    │                     │ All fields populated. file_size = sum of all files.    │
    ├─────────────────────┼───────────────────────────────────────────────────────┤
    │ "directory_per_file"│ Per-file timing extracted from [BENCHMARK_TIMING]      │
    │                     │ lines emitted by the instrumented anon.py.             │
    │                     │ wall_clock = processing time ONLY (no model overhead). │
    │                     │ Only file-level metrics available (see below).         │
    └─────────────────────┴───────────────────────────────────────────────────────┘

    Field availability by measurement_mode:

        FIELD GROUP              single_file  dir_aggregate  dir_per_file
        ─────────────────────    ───────────  ─────────────  ────────────
        File size/content             ✓             ✓             ✓
        wall_clock_time_sec           ✓ (*)         ✓ (*)         ✓ (**)
        user/system_time, cpu%        ✓             ✓             —
        max_resident_set_kb           ✓             ✓          inherited
        page faults, ctx switches     ✓             ✓             —
        file system I/O               ✓             ✓             —
        throughput_kb_per_sec         ✓ (*)         ✓ (*)         ✓ (**)
        memory_per_kb_input           ✓             ✓          inherited
        ProcessMonitor (CPU/mem)      ✓             ✓             —
        GPU metrics                   ✓             ✓       partial (***)

        (*)   Includes model loading overhead (~55-77s per invocation)
        (**)  Pure processing time (no model overhead) — more accurate
              for throughput analysis
        (***) gpu_available, peak_gpu_memory_used_mb, gpu_memory_total_mb
              inherited from aggregate; avg/peak utilization and temperature
              are not available per-file

    Note for analysis: throughput_kb_per_sec is NOT directly comparable
    between single_file and directory_per_file modes. To compare fairly,
    subtract the model loading overhead from single_file wall_clock_time
    before computing throughput, or use directory_per_file values which
    already exclude it.
    """
    # Identification
    version: str
    strategy: str
    file_name: str
    file_path: str
    file_extension: str
    run_number: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Measurement mode — critical for interpreting metrics correctly.
    # Values: "single_file", "directory_aggregate", "directory_per_file"
    measurement_mode: str = "single_file"

    # Status
    status: str = "PENDING"
    error_message: str = ""

    # File metrics
    file_size_bytes: int = 0
    file_size_kb: float = 0.0
    file_size_mb: float = 0.0
    character_count: int = 0
    line_count: int = 0

    # Time metrics (from /usr/bin/time -v)
    # NOTE: wall_clock_time_sec semantics differ by measurement_mode.
    #   single_file / directory_aggregate: full process time (includes model load)
    #   directory_per_file: processing time only (excludes model load)
    wall_clock_time_sec: float = 0.0
    user_time_sec: float = 0.0        # Not available in directory_per_file
    system_time_sec: float = 0.0      # Not available in directory_per_file
    cpu_percent: float = 0.0          # Not available in directory_per_file

    # Memory metrics (from /usr/bin/time -v)
    # max_resident_set_kb: inherited from aggregate in directory_per_file
    # Other fields: not available in directory_per_file
    max_resident_set_kb: int = 0
    average_resident_set_kb: int = 0
    major_page_faults: int = 0
    minor_page_faults: int = 0
    voluntary_context_switches: int = 0
    involuntary_context_switches: int = 0

    # I/O metrics — not available in directory_per_file
    file_system_inputs: int = 0
    file_system_outputs: int = 0

    # Derived metrics
    # NOTE: throughput_kb_per_sec is NOT comparable across measurement_modes.
    #   single_file: throughput = size / (model_load + processing) → lower
    #   directory_per_file: throughput = size / processing_only → higher, more accurate
    throughput_kb_per_sec: float = 0.0
    throughput_mb_per_sec: float = 0.0
    memory_per_kb_input: float = 0.0  # inherited from aggregate in directory_per_file

    # Process monitoring (sampled during execution)
    # Not available in directory_per_file (single process, can't attribute to files)
    avg_cpu_percent: float = 0.0
    peak_cpu_percent: float = 0.0
    avg_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0

    # GPU metrics (sampled via nvidia-smi during execution)
    # In directory_per_file: only gpu_available, peak_gpu_memory_used_mb,
    # gpu_memory_total_mb are inherited from aggregate.
    gpu_available: bool = False
    avg_gpu_utilization_percent: float = 0.0
    peak_gpu_utilization_percent: float = 0.0
    avg_gpu_memory_used_mb: float = 0.0
    peak_gpu_memory_used_mb: float = 0.0
    gpu_memory_total_mb: float = 0.0
    avg_gpu_temperature_c: float = 0.0
    peak_gpu_temperature_c: float = 0.0

    def compute_derived_metrics(self):
        """Calculate derived metrics from raw measurements."""
        if self.wall_clock_time_sec > 0:
            self.throughput_kb_per_sec = self.file_size_kb / self.wall_clock_time_sec
            self.throughput_mb_per_sec = self.file_size_mb / self.wall_clock_time_sec

        if self.file_size_kb > 0:
            self.memory_per_kb_input = self.max_resident_set_kb / self.file_size_kb

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV/JSON export."""
        return asdict(self)


@dataclass
class RunState:
    """Persistent state for resumable benchmark runs."""
    completed_runs: set = field(default_factory=set)
    failed_runs: set = field(default_factory=set)
    last_update: str = ""

    def get_run_key(self, version: str, strategy: str, file_name: str, run_number: int) -> str:
        """Generate unique key for a benchmark run."""
        return f"{version}|{strategy}|{file_name}|{run_number}"

    def mark_completed(self, version: str, strategy: str, file_name: str, run_number: int):
        """Mark a run as completed."""
        key = self.get_run_key(version, strategy, file_name, run_number)
        self.completed_runs.add(key)
        self.last_update = datetime.now().isoformat()

    def mark_failed(self, version: str, strategy: str, file_name: str, run_number: int):
        """Mark a run as failed."""
        key = self.get_run_key(version, strategy, file_name, run_number)
        self.failed_runs.add(key)
        self.last_update = datetime.now().isoformat()

    def is_completed(self, version: str, strategy: str, file_name: str, run_number: int) -> bool:
        """Check if a run was already completed."""
        key = self.get_run_key(version, strategy, file_name, run_number)
        return key in self.completed_runs

    def save(self, path: Path):
        """Save state to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "completed_runs": list(self.completed_runs),
            "failed_runs": list(self.failed_runs),
            "last_update": self.last_update
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: Path) -> 'RunState':
        """Load state from JSON file."""
        if not path.exists():
            return cls()
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            state = cls()
            state.completed_runs = set(data.get("completed_runs", []))
            state.failed_runs = set(data.get("failed_runs", []))
            state.last_update = data.get("last_update", "")
            return state
        except (json.JSONDecodeError, KeyError):
            return cls()


# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================

class EnvironmentSetup:
    """Handles virtual environment creation and dependency installation."""

    def __init__(self, config: VersionConfig, log_dir: Path, verbose: bool = False, gpu_mode: bool = True):
        self.config = config
        self.log_dir = log_dir
        self.verbose = verbose
        self.gpu_mode = gpu_mode
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._uv_path = self._find_uv()

    def _find_uv(self) -> str:
        """Find the uv binary in common locations."""
        # Check common locations
        candidates = [
            "uv",  # In PATH
            os.path.expanduser("~/.local/bin/uv"),
            os.path.expanduser("~/.cargo/bin/uv"),
            "/usr/local/bin/uv",
            "/home/linuxbrew/.linuxbrew/bin/uv",
        ]

        for candidate in candidates:
            if shutil.which(candidate):
                return candidate
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate

        # Try to find it
        result = subprocess.run(["which", "uv"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()

        return "uv"  # Fallback, let it fail with a clear error

    def setup(self, force: bool = False) -> bool:
        """Setup the virtual environment for a version."""
        version_str = self.config.version.value
        log_file = self.log_dir / f"setup_v{version_str}.log"

        print(f"\n{'='*60}")
        print(f"[SETUP] AnonLFI v{version_str}")
        print(f"{'='*60}")

        if self.config.venv_path.exists() and not force:
            print(f"  [OK] Virtual environment already exists at {self.config.venv_path}")
            return True

        if force and self.config.venv_path.exists():
            print(f"  [INFO] Removing existing venv (--force specified)...")
            shutil.rmtree(self.config.venv_path)

        print(f"  [INFO] Setting up environment...")
        print(f"  [INFO] Log file: {log_file}")
        print(f"  [INFO] Using uv at: {self._uv_path}")

        try:
            with open(log_file, 'w') as log:
                # Step 1: Create venv using uv sync
                if not self._run_uv_sync(log):
                    return False

                # Step 2: For v3.0, configure PyTorch based on GPU mode (following Dockerfile logic)
                if self.config.version == AnonVersion.V3_0:
                    if not self._configure_torch(log):
                        return False

                # Step 3: Warm up model cache
                if not self._warmup_cache(log):
                    print(f"  [WARN] Cache warmup failed, but continuing...")

            print(f"  [OK] Setup completed for v{version_str}")
            return True

        except Exception as e:
            print(f"  [ERROR] Setup failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _run_uv_sync(self, log) -> bool:
        """Run uv sync to install dependencies."""
        print(f"  [INFO] Running 'uv sync'...")

        cmd = [self._uv_path, "sync"]

        # Show the command being run
        log.write(f"Running: {' '.join(cmd)}\n")
        log.write(f"Working directory: {self.config.path}\n")
        log.write(f"Target venv: {self.config.venv_path}\n\n")
        log.flush()

        # Use UV_PROJECT_ENVIRONMENT to control venv location
        env = os.environ.copy()
        env["UV_PROJECT_ENVIRONMENT"] = str(self.config.venv_path)

        result = subprocess.run(
            cmd,
            cwd=self.config.path,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            env=env
        )

        if result.returncode != 0:
            print(f"  [ERROR] 'uv sync' failed with code {result.returncode}")
            print(f"  [ERROR] Check log file for details: {log.name}")
            return False

        print(f"  [OK] Dependencies installed via uv sync")
        return True

    def _configure_torch(self, log) -> bool:
        """Configure PyTorch for GPU or CPU (v3.0 only, following Dockerfile GPU logic)."""

        pip_exe = self.config.venv_path / "bin" / "pip"
        if platform.system() == "Windows":
            pip_exe = self.config.venv_path / "Scripts" / "pip.exe"

        if self.gpu_mode:
            print(f"  [INFO] Configuring PyTorch for GPU (CUDA 12.8)...")

            # Install GPU torch (following Dockerfile builder-gpu logic)
            # torch --index-url https://download.pytorch.org/whl/cu128
            cmd = [
                str(pip_exe), "install", "--no-cache-dir", "--force-reinstall",
                "torch", "--index-url", "https://download.pytorch.org/whl/cu128"
            ]
            log.write(f"\nInstalling GPU PyTorch: {' '.join(cmd)}\n")
            log.flush()

            result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True)
            if result.returncode != 0:
                print(f"  [WARN] GPU torch installation failed, trying CPU fallback...")
                return self._install_cpu_torch(pip_exe, log)

            # Install cupy-cuda12x (following Dockerfile)
            print(f"  [INFO] Installing CuPy for CUDA 12.x...")
            cmd = [str(pip_exe), "install", "--no-cache-dir", "cupy-cuda12x==12.3.0"]
            log.write(f"\nInstalling CuPy: {' '.join(cmd)}\n")
            log.flush()

            result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True)
            if result.returncode != 0:
                print(f"  [WARN] CuPy installation failed (GPU acceleration for spaCy won't work)")
            else:
                print(f"  [OK] CuPy installed for GPU acceleration")

            print(f"  [OK] GPU PyTorch configured (CUDA 12.8)")
        else:
            return self._install_cpu_torch(pip_exe, log)

        return True

    def _install_cpu_torch(self, pip_exe: Path, log) -> bool:
        """Install CPU-only PyTorch."""
        print(f"  [INFO] Installing CPU-only PyTorch...")

        cmd = [
            str(pip_exe), "install", "--no-cache-dir", "--force-reinstall",
            "torch", "--index-url", "https://download.pytorch.org/whl/cpu"
        ]
        log.write(f"\nInstalling CPU PyTorch: {' '.join(cmd)}\n")
        log.flush()

        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True)
        if result.returncode != 0:
            print(f"  [WARN] CPU torch swap failed, continuing with existing torch")
        else:
            print(f"  [OK] CPU-only PyTorch installed")

        # Remove NVIDIA packages (cleanup space)
        nvidia_pkgs = [
            "nvidia-cublas-cu12", "nvidia-cuda-cupti-cu12", "nvidia-cuda-nvrtc-cu12",
            "nvidia-cuda-runtime-cu12", "nvidia-cudnn-cu12", "nvidia-cufft-cu12",
            "nvidia-curand-cu12", "nvidia-cusolver-cu12", "nvidia-cusparse-cu12",
            "nvidia-nccl-cu12", "nvidia-nvjitlink-cu12", "nvidia-nvtx-cu12", "triton"
        ]

        for pkg in nvidia_pkgs:
            subprocess.run(
                [str(pip_exe), "uninstall", "-y", pkg],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

        return True

    def _warmup_cache(self, log) -> bool:
        """Run a warmup anonymization to download/cache models."""
        print(f"  [INFO] Warming up model cache...")

        warmup_file = self.config.path / "warmup_test.txt"
        warmup_content = "O analista João Silva está em Porto Alegre. Email: joao@example.com"

        try:
            # Create warmup file
            with open(warmup_file, 'w', encoding='utf-8') as f:
                f.write(warmup_content)

            # Build command
            cmd = [str(self.config.python_executable), "anon.py", str(warmup_file)]

            # Set environment
            env = os.environ.copy()
            if self.config.requires_secret_key:
                env["ANON_SECRET_KEY"] = "benchmark-warmup-key"

            # Run warmup
            result = subprocess.run(
                cmd,
                cwd=self.config.path,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
                timeout=600  # 10 min timeout for model download
            )

            # Cleanup
            warmup_file.unlink(missing_ok=True)
            output_dir = self.config.path / "output"
            for f in output_dir.glob("*warmup*"):
                f.unlink(missing_ok=True)

            if result.returncode == 0:
                print(f"  [OK] Model cache warmed up")
                return True
            else:
                print(f"  [WARN] Warmup exited with code {result.returncode}")
                return False

        except subprocess.TimeoutExpired:
            print(f"  [WARN] Warmup timed out after 10 minutes")
            return False
        except Exception as e:
            print(f"  [WARN] Warmup failed: {e}")
            return False
        finally:
            warmup_file.unlink(missing_ok=True)


# =============================================================================
# METRICS COLLECTION
# =============================================================================

class MetricsParser:
    """Parses metrics from /usr/bin/time -v output with robust error handling."""

    PATTERNS = {
        'user_time_sec': r"User time \(seconds\):\s*([\d.]+)",
        'system_time_sec': r"System time \(seconds\):\s*([\d.]+)",
        'cpu_percent': r"Percent of CPU this job got:\s*(\d+)%",
        # Fixed: explicit format to avoid greedy regex consuming time separators
        'wall_clock_time': r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*([\d:.-]+)",
        'max_resident_set_kb': r"Maximum resident set size \(kbytes\):\s*(\d+)",
        'average_resident_set_kb': r"Average resident set size \(kbytes\):\s*(\d+)",
        'major_page_faults': r"Major \(requiring I/O\) page faults:\s*(\d+)",
        'minor_page_faults': r"Minor \(reclaiming a frame\) page faults:\s*(\d+)",
        'voluntary_context_switches': r"Voluntary context switches:\s*(\d+)",
        'involuntary_context_switches': r"Involuntary context switches:\s*(\d+)",
        'file_system_inputs': r"File system inputs:\s*(\d+)",
        'file_system_outputs': r"File system outputs:\s*(\d+)",
    }

    @classmethod
    def parse(cls, content: str, metrics: BenchmarkMetrics) -> BenchmarkMetrics:
        """Parse /usr/bin/time output and populate metrics with validation."""
        for field_name, pattern in cls.PATTERNS.items():
            try:
                match = re.search(pattern, content)
                if match:
                    value = match.group(1)

                    if field_name == 'wall_clock_time':
                        # Parse time format with robust handling
                        parsed_time = cls._parse_time(value)
                        if parsed_time < 0:
                            print(f"  [WARN] Invalid time value: {value}, using 0")
                            parsed_time = 0.0
                        setattr(metrics, 'wall_clock_time_sec', parsed_time)
                    elif field_name == 'cpu_percent':
                        setattr(metrics, field_name, float(value))
                    elif '.' in value:
                        setattr(metrics, field_name, float(value))
                    else:
                        setattr(metrics, field_name, int(value))
                else:
                    # Log missing fields for debugging
                    if field_name == 'wall_clock_time':
                        print(f"  [WARN] Could not parse {field_name}")
            except (ValueError, IndexError) as e:
                print(f"  [WARN] Error parsing {field_name}: {e}")

        return metrics

    @staticmethod
    def _parse_time(time_str: str) -> float:
        """Parse wall clock time string to seconds.
        
        Supports formats:
        - ss.ss (seconds only)
        - m:ss.ss (minutes:seconds)
        - h:mm:ss.ss (hours:minutes:seconds)
        - d-hh:mm:ss.ss (days-hours:minutes:seconds) for very long runs
        
        Returns:
            Time in seconds, or -1.0 if parsing fails
        """
        if not time_str:
            return -1.0
            
        try:
            # Handle day format: "2-01:30:45.67" (2 days, 1 hour, 30 min, 45.67 sec)
            if '-' in time_str:
                day_part, time_part = time_str.split('-', 1)
                days = float(day_part)
                parts = time_part.split(':')
                if len(parts) == 3:
                    hours, minutes, seconds = parts
                    return days * 86400 + float(hours) * 3600 + float(minutes) * 60 + float(seconds)
                else:
                    return -1.0
            
            # Handle normal formats
            parts = time_str.split(':')
            if len(parts) == 3:
                # h:mm:ss.ss format
                hours, minutes, seconds = parts
                return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
            elif len(parts) == 2:
                # m:ss.ss format
                minutes, seconds = parts
                return float(minutes) * 60 + float(seconds)
            elif len(parts) == 1:
                # ss.ss format
                return float(parts[0])
            else:
                return -1.0
                
        except (ValueError, IndexError) as e:
            print(f"  [ERROR] Failed to parse time '{time_str}': {e}")
            return -1.0


class FileMetricsCollector:
    """Collects file-level metrics."""

    @staticmethod
    def collect(file_path: Path, metrics: BenchmarkMetrics) -> BenchmarkMetrics:
        """Collect file metrics."""
        try:
            stat = file_path.stat()
            metrics.file_size_bytes = stat.st_size
            metrics.file_size_kb = stat.st_size / 1024
            metrics.file_size_mb = stat.st_size / (1024 * 1024)

            # Try to count lines and characters (text files)
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                metrics.character_count = len(content)
                metrics.line_count = content.count('\n') + 1
            except Exception:
                metrics.character_count = 0
                metrics.line_count = 0

        except Exception as e:
            print(f"  [WARN] Could not collect file metrics: {e}")

        return metrics


class GpuSample:
    """Single GPU metrics sample."""
    __slots__ = ('utilization', 'memory_used_mb', 'memory_total_mb', 'temperature')

    def __init__(self, utilization: float, memory_used_mb: float, memory_total_mb: float, temperature: float):
        self.utilization = utilization
        self.memory_used_mb = memory_used_mb
        self.memory_total_mb = memory_total_mb
        self.temperature = temperature


def _query_nvidia_smi() -> Optional[GpuSample]:
    """Query nvidia-smi for GPU metrics. Returns None if unavailable."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits"
            ],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return None

        line = result.stdout.strip().split('\n')[0]  # First GPU only
        parts = [p.strip() for p in line.split(',')]
        if len(parts) >= 4:
            return GpuSample(
                utilization=float(parts[0]),
                memory_used_mb=float(parts[1]),
                memory_total_mb=float(parts[2]),
                temperature=float(parts[3])
            )
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, IndexError):
        pass
    return None


class ProcessMonitor:
    """Monitors process CPU, memory, and GPU during execution."""

    def __init__(self, pid: int, interval: float = 0.5):
        self.pid = pid
        self.interval = interval
        self.cpu_samples: List[float] = []
        self.memory_samples: List[float] = []
        self.gpu_samples: List[GpuSample] = []
        self._gpu_available: bool = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Detect GPU availability once
        self._gpu_available = _query_nvidia_smi() is not None

    def start(self):
        """Start monitoring in background thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> Dict[str, float]:
        """Stop monitoring and return statistics."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

        result = {
            'avg_cpu_percent': 0.0,
            'peak_cpu_percent': 0.0,
            'avg_memory_mb': 0.0,
            'peak_memory_mb': 0.0,
            'gpu_available': self._gpu_available,
            'avg_gpu_utilization_percent': 0.0,
            'peak_gpu_utilization_percent': 0.0,
            'avg_gpu_memory_used_mb': 0.0,
            'peak_gpu_memory_used_mb': 0.0,
            'gpu_memory_total_mb': 0.0,
            'avg_gpu_temperature_c': 0.0,
            'peak_gpu_temperature_c': 0.0,
        }

        if self.cpu_samples:
            result['avg_cpu_percent'] = sum(self.cpu_samples) / len(self.cpu_samples)
            result['peak_cpu_percent'] = max(self.cpu_samples)

        if self.memory_samples:
            result['avg_memory_mb'] = sum(self.memory_samples) / len(self.memory_samples)
            result['peak_memory_mb'] = max(self.memory_samples)

        if self.gpu_samples:
            result['avg_gpu_utilization_percent'] = sum(s.utilization for s in self.gpu_samples) / len(self.gpu_samples)
            result['peak_gpu_utilization_percent'] = max(s.utilization for s in self.gpu_samples)
            result['avg_gpu_memory_used_mb'] = sum(s.memory_used_mb for s in self.gpu_samples) / len(self.gpu_samples)
            result['peak_gpu_memory_used_mb'] = max(s.memory_used_mb for s in self.gpu_samples)
            result['gpu_memory_total_mb'] = self.gpu_samples[0].memory_total_mb
            result['avg_gpu_temperature_c'] = sum(s.temperature for s in self.gpu_samples) / len(self.gpu_samples)
            result['peak_gpu_temperature_c'] = max(s.temperature for s in self.gpu_samples)

        return result

    def _monitor_loop(self):
        """Background monitoring loop."""
        try:
            process = psutil.Process(self.pid)
            while not self._stop_event.is_set():
                try:
                    # CPU and memory for process + children
                    cpu = process.cpu_percent()
                    mem = process.memory_info().rss / (1024 * 1024)

                    for child in process.children(recursive=True):
                        try:
                            cpu += child.cpu_percent()
                            mem += child.memory_info().rss / (1024 * 1024)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                    self.cpu_samples.append(cpu)
                    self.memory_samples.append(mem)

                    # GPU sampling
                    if self._gpu_available:
                        gpu_sample = _query_nvidia_smi()
                        if gpu_sample:
                            self.gpu_samples.append(gpu_sample)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break

                self._stop_event.wait(self.interval)
        except Exception:
            pass


# =============================================================================
# BENCHMARK RUNNER
# =============================================================================

class BenchmarkRunner:
    """Executes benchmark runs with real-time output and metrics collection."""

    def __init__(
        self,
        config: VersionConfig,
        output_dir: Path,
        log_dir: Path,
        secret_key: str = "benchmark-secret-key-2026"
    ):
        self.config = config
        self.output_dir = output_dir
        self.log_dir = log_dir
        self.secret_key = secret_key

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        file_path: Path,
        strategy: Strategy,
        run_number: int,
        show_output: bool = True
    ) -> BenchmarkMetrics:
        """Execute a single benchmark run."""

        # Initialize metrics
        metrics = BenchmarkMetrics(
            version=self.config.version.value,
            strategy=strategy.value,
            file_name=file_path.name,
            file_path=str(file_path),
            file_extension=file_path.suffix.lower(),
            run_number=run_number,
            measurement_mode="single_file",
        )

        # Collect file metrics
        FileMetricsCollector.collect(file_path, metrics)

        # Check if file extension is supported
        if metrics.file_extension not in self.config.supported_extensions:
            metrics.status = "SKIPPED"
            metrics.error_message = f"Extension {metrics.file_extension} not supported by v{self.config.version.value}"
            return metrics

        # Build command
        cmd = self._build_command(file_path, strategy)
        log_file = self._get_log_file(file_path, strategy, run_number)

        # Build environment
        env = self._build_environment()

        print(f"\n  Running: v{self.config.version.value} | {strategy.value} | {file_path.name} | Run #{run_number}")

        try:
            # Execute with /usr/bin/time -v for detailed metrics
            full_cmd = f"/usr/bin/time -v {' '.join(cmd)} 2>&1"

            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    full_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=self.config.path,
                    env=env,
                    text=True,
                    bufsize=1
                )

                # Start process monitoring
                monitor = ProcessMonitor(process.pid)
                monitor.start()

                # Stream output to both terminal and log file
                full_output = []
                for line in iter(process.stdout.readline, ''):
                    if show_output:
                        print(f"    | {line}", end='')
                    log.write(line)
                    full_output.append(line)

                process.wait()

                # Stop monitoring and get stats
                monitor_stats = monitor.stop()
                metrics.avg_cpu_percent = monitor_stats['avg_cpu_percent']
                metrics.peak_cpu_percent = monitor_stats['peak_cpu_percent']
                metrics.avg_memory_mb = monitor_stats['avg_memory_mb']
                metrics.peak_memory_mb = monitor_stats['peak_memory_mb']

                # GPU metrics
                metrics.gpu_available = monitor_stats['gpu_available']
                metrics.avg_gpu_utilization_percent = monitor_stats['avg_gpu_utilization_percent']
                metrics.peak_gpu_utilization_percent = monitor_stats['peak_gpu_utilization_percent']
                metrics.avg_gpu_memory_used_mb = monitor_stats['avg_gpu_memory_used_mb']
                metrics.peak_gpu_memory_used_mb = monitor_stats['peak_gpu_memory_used_mb']
                metrics.gpu_memory_total_mb = monitor_stats['gpu_memory_total_mb']
                metrics.avg_gpu_temperature_c = monitor_stats['avg_gpu_temperature_c']
                metrics.peak_gpu_temperature_c = monitor_stats['peak_gpu_temperature_c']

                # Parse /usr/bin/time output
                output_text = ''.join(full_output)
                MetricsParser.parse(output_text, metrics)

                # Set status
                if process.returncode == 0:
                    metrics.status = "SUCCESS"
                else:
                    metrics.status = "FAILED"
                    metrics.error_message = f"Exit code: {process.returncode}"

        except subprocess.TimeoutExpired:
            metrics.status = "TIMEOUT"
            metrics.error_message = "Process timed out"
        except Exception as e:
            metrics.status = "ERROR"
            metrics.error_message = str(e)

        # Compute derived metrics
        metrics.compute_derived_metrics()

        # Print summary
        self._print_run_summary(metrics)

        return metrics

    def _build_command(self, file_path: Path, strategy: Strategy,
                       run_number: int = 1) -> List[str]:
        """Build the command to execute."""
        # Always use absolute paths since each version runs from its own cwd
        abs_file_path = file_path.resolve()
        cmd = [str(self.config.python_executable), "anon.py", str(abs_file_path)]

        # Create per-version/strategy output dir to avoid overwriting
        version_str = f"v{self.config.version.value}"
        strat_str = strategy.value
        run_output_dir = self.output_dir / version_str / strat_str
        run_output_dir.mkdir(parents=True, exist_ok=True)

        # Add strategy and overwrite for v3.0
        if self.config.version == AnonVersion.V3_0 and strategy != Strategy.DEFAULT:
            cmd.extend(["--anonymization-strategy", strategy.value])
            cmd.extend(["--output-dir", str(run_output_dir.resolve())])
            cmd.append("--overwrite")

        return cmd

    def _build_environment(self) -> Dict[str, str]:
        """Build environment variables for the process."""
        env = os.environ.copy()

        if self.config.requires_secret_key:
            env["ANON_SECRET_KEY"] = self.secret_key

        # Add src to PYTHONPATH for all versions
        src_path = self.config.path / "src"
        if src_path.exists():
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{src_path}:{existing}" if existing else str(src_path)

        return env

    def _get_log_file(self, file_path: Path, strategy: Strategy, run_number: int) -> Path:
        """Generate log file path."""
        version = self.config.version.value
        safe_name = re.sub(r'[^\w\-.]', '_', file_path.name)
        return self.log_dir / f"v{version}_{strategy.value}_{safe_name}_run{run_number}.log"

    def _print_run_summary(self, metrics: BenchmarkMetrics):
        """Print a summary of the run."""
        status_icon = {
            "SUCCESS": "[OK]",
            "FAILED": "[FAIL]",
            "ERROR": "[ERR]",
            "TIMEOUT": "[TIMEOUT]",
            "SKIPPED": "[SKIP]"
        }.get(metrics.status, "[?]")

        print(f"\n  {status_icon} {metrics.status}")
        if metrics.status == "SUCCESS":
            gpu_info = ""
            if metrics.gpu_available:
                gpu_info = f" | GPU: {metrics.peak_gpu_utilization_percent:.0f}% / VRAM: {metrics.peak_gpu_memory_used_mb:.0f}MB"
            print(f"      Time: {metrics.wall_clock_time_sec:.2f}s | "
                  f"Memory: {metrics.max_resident_set_kb/1024:.1f}MB | "
                  f"Throughput: {metrics.throughput_kb_per_sec:.2f} KB/s{gpu_info}")
        elif metrics.error_message:
            print(f"      Error: {metrics.error_message}")


# =============================================================================
# DIRECTORY MODE BENCHMARK RUNNER
# =============================================================================

class DirectoryBenchmarkRunner:
    """Executes benchmarks in directory mode: one invocation processes all files.

    This eliminates the per-file model loading overhead (~55-77s) by passing
    a directory to anon.py instead of individual files. The tool loads its
    NLP models once and processes all files sequentially.

    Only works for v2.0 and v3.0 (v1.0 does not support directory input).
    Records one aggregated metrics row per (version, strategy, run_number),
    plus individual per-file rows from [BENCHMARK_TIMING] instrumentation.

    Supports incremental progress: per-file results are saved in real-time
    so that interrupted runs can be resumed from where they stopped.
    """

    def __init__(
        self,
        config: VersionConfig,
        output_dir: Path,
        log_dir: Path,
        secret_key: str = "benchmark-secret-key-2026",
        results_manager: Optional['ResultsManager'] = None,
    ):
        self.config = config
        self.output_dir = output_dir
        self.log_dir = log_dir
        self.secret_key = secret_key
        self.results_manager = results_manager

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        test_files: List[Path],
        strategy: Strategy,
        run_number: int,
        show_output: bool = True
    ) -> List[BenchmarkMetrics]:
        """Execute a directory-mode benchmark run.

        Creates a temp directory with symlinks to all supported test files,
        then invokes anon.py once with the directory as input.

        Returns a list of BenchmarkMetrics: the first element is the aggregate
        DIRECTORY_RUN row; subsequent elements are per-file breakdown rows
        (parsed from [BENCHMARK_TIMING] lines emitted by the modified anon.py).
        """

        if not self.config.supports_directory:
            raise ValueError(f"v{self.config.version.value} does not support directory mode")

        # Filter to supported files only
        supported_files = [
            f for f in test_files
            if f.suffix.lower() in self.config.supported_extensions
        ]

        if not supported_files:
            metrics = BenchmarkMetrics(
                version=self.config.version.value,
                strategy=strategy.value,
                file_name="DIRECTORY_RUN",
                file_path="",
                file_extension="*",
                run_number=run_number,
                measurement_mode="directory_aggregate",
            )
            metrics.status = "SKIPPED"
            metrics.error_message = "No supported files found"
            return [metrics]

        # Create temp directory with symlinks (prefixed to avoid collisions)
        staging_dir = self._create_staging_directory(supported_files, strategy, run_number)

        try:
            return self._execute_directory_run(
                staging_dir, supported_files, strategy, run_number, show_output
            )
        finally:
            # Cleanup staging directory (symlinks only, no real data deleted)
            shutil.rmtree(staging_dir, ignore_errors=True)

    def _create_staging_directory(
        self, files: List[Path], strategy: Strategy, run_number: int
    ) -> Path:
        """Create a flat directory with uniquely-named symlinks to test files."""
        version = self.config.version.value
        staging_dir = self.log_dir / f"staging_v{version}_{strategy.value}_run{run_number}"

        # Clean previous staging if exists
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        staging_dir.mkdir(parents=True)

        for idx, file_path in enumerate(files):
            abs_path = file_path.resolve()
            # Prefix with index to guarantee uniqueness
            link_name = f"{idx:04d}_{file_path.name}"
            link_path = staging_dir / link_name

            try:
                link_path.symlink_to(abs_path)
            except OSError:
                # Symlinks may fail on some filesystems; fall back to copy
                shutil.copy2(abs_path, link_path)

        return staging_dir

    def _execute_directory_run(
        self,
        staging_dir: Path,
        source_files: List[Path],
        strategy: Strategy,
        run_number: int,
        show_output: bool,
    ) -> List[BenchmarkMetrics]:
        """Execute the directory-mode benchmark and collect metrics.

        Returns a list: [aggregate_metrics, per_file_1, per_file_2, ...].
        Per-file metrics are derived from [BENCHMARK_TIMING] lines in stdout.
        """

        # Initialize aggregate metrics
        metrics = BenchmarkMetrics(
            version=self.config.version.value,
            strategy=strategy.value,
            file_name="DIRECTORY_RUN",
            file_path=str(staging_dir),
            file_extension="*",
            run_number=run_number,
            measurement_mode="directory_aggregate",
        )

        # Build a map from staging name (with prefix) to original file
        # Staging names are like "0000_original_name.ext"
        staging_to_source = {}
        for idx, f in enumerate(source_files):
            staging_name = f"{idx:04d}_{f.name}"
            staging_to_source[staging_name] = f

        # Aggregate file metrics
        total_bytes = 0
        total_chars = 0
        total_lines = 0
        for f in source_files:
            try:
                total_bytes += f.stat().st_size
                content = f.read_text(encoding='utf-8', errors='ignore')
                total_chars += len(content)
                total_lines += content.count('\n') + 1
            except Exception:
                total_bytes += f.stat().st_size if f.exists() else 0

        metrics.file_size_bytes = total_bytes
        metrics.file_size_kb = total_bytes / 1024
        metrics.file_size_mb = total_bytes / (1024 * 1024)
        metrics.character_count = total_chars
        metrics.line_count = total_lines

        # Build command
        cmd = self._build_directory_command(staging_dir, strategy)
        log_file = self.log_dir / f"v{self.config.version.value}_{strategy.value}_DIRMODE_run{run_number}.log"
        env = self._build_environment()

        file_count = len(source_files)
        full_output = []
        print(f"\n  [DIR-MODE] Running: v{self.config.version.value} | {strategy.value} | "
              f"{file_count} files ({metrics.file_size_mb:.1f} MB) | Run #{run_number}")

        try:
            full_cmd = f"/usr/bin/time -v {' '.join(cmd)} 2>&1"

            with open(log_file, 'w') as log:
                log.write(f"# Directory mode benchmark\n")
                log.write(f"# Version: {self.config.version.value}\n")
                log.write(f"# Strategy: {strategy.value}\n")
                log.write(f"# Files: {file_count}\n")
                log.write(f"# Total size: {metrics.file_size_mb:.1f} MB\n")
                log.write(f"# Staging dir: {staging_dir}\n")
                log.write(f"# Command: {full_cmd}\n\n")
                log.flush()

                process = subprocess.Popen(
                    full_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=self.config.path,
                    env=env,
                    text=True,
                    bufsize=1
                )

                # Start process monitoring
                monitor = ProcessMonitor(process.pid)
                monitor.start()

                # Stream output
                for line in iter(process.stdout.readline, ''):
                    if show_output:
                        print(f"    | {line}", end='')
                    log.write(line)
                    full_output.append(line)

                process.wait()

                # Stop monitoring
                monitor_stats = monitor.stop()
                metrics.avg_cpu_percent = monitor_stats['avg_cpu_percent']
                metrics.peak_cpu_percent = monitor_stats['peak_cpu_percent']
                metrics.avg_memory_mb = monitor_stats['avg_memory_mb']
                metrics.peak_memory_mb = monitor_stats['peak_memory_mb']
                metrics.gpu_available = monitor_stats['gpu_available']
                metrics.avg_gpu_utilization_percent = monitor_stats['avg_gpu_utilization_percent']
                metrics.peak_gpu_utilization_percent = monitor_stats['peak_gpu_utilization_percent']
                metrics.avg_gpu_memory_used_mb = monitor_stats['avg_gpu_memory_used_mb']
                metrics.peak_gpu_memory_used_mb = monitor_stats['peak_gpu_memory_used_mb']
                metrics.gpu_memory_total_mb = monitor_stats['gpu_memory_total_mb']
                metrics.avg_gpu_temperature_c = monitor_stats['avg_gpu_temperature_c']
                metrics.peak_gpu_temperature_c = monitor_stats['peak_gpu_temperature_c']

                # Parse /usr/bin/time output
                output_text = ''.join(full_output)
                MetricsParser.parse(output_text, metrics)

                if process.returncode == 0:
                    metrics.status = "SUCCESS"
                else:
                    metrics.status = "FAILED"
                    metrics.error_message = f"Exit code: {process.returncode}"

        except subprocess.TimeoutExpired:
            metrics.status = "TIMEOUT"
            metrics.error_message = "Process timed out"
        except Exception as e:
            metrics.status = "ERROR"
            metrics.error_message = str(e)

        # Compute derived metrics for aggregate row
        metrics.compute_derived_metrics()

        # Parse per-file timing from [BENCHMARK_TIMING] lines
        per_file_metrics = self._parse_per_file_timing(
            full_output, staging_to_source, metrics, run_number, strategy
        )

        # Print summary
        self._print_directory_summary(metrics, file_count, per_file_metrics)

        # Return aggregate + per-file
        result = [metrics] + per_file_metrics
        return result

    @staticmethod
    def _parse_per_file_timing(
        output_lines: List[str],
        staging_to_source: Dict[str, Path],
        aggregate_metrics: BenchmarkMetrics,
        run_number: int,
        strategy: Strategy,
    ) -> List[BenchmarkMetrics]:
        """Parse [BENCHMARK_TIMING] lines from anon.py stdout.

        Expected format:
            [BENCHMARK_TIMING] file=<staging_name> elapsed=<seconds> size_bytes=<int>

        Returns per-file BenchmarkMetrics with timing derived from the tool's
        own instrumentation (no model loading overhead included).
        """
        timing_re = re.compile(
            r'\[BENCHMARK_TIMING\]\s+file=(.+?)\s+elapsed=([\d.]+)\s+size_bytes=(\d+)'
        )

        per_file = []
        for line in output_lines:
            m = timing_re.search(line)
            if not m:
                continue

            staging_name = m.group(1)
            elapsed = float(m.group(2))
            size_bytes = int(m.group(3))

            # Map staging name back to original source file
            source_file = staging_to_source.get(staging_name)
            if source_file:
                original_name = source_file.name
                file_path = str(source_file)
                extension = source_file.suffix.lower()
            else:
                # Fallback: strip the 4-digit prefix
                original_name = staging_name[5:] if len(staging_name) > 5 and staging_name[4] == '_' else staging_name
                file_path = staging_name
                extension = Path(original_name).suffix.lower()

            fm = BenchmarkMetrics(
                version=aggregate_metrics.version,
                strategy=strategy.value,
                file_name=f"DIRMODE_{original_name}",
                file_path=file_path,
                file_extension=extension,
                run_number=run_number,
                measurement_mode="directory_per_file",
            )
            fm.file_size_bytes = size_bytes
            fm.file_size_kb = size_bytes / 1024
            fm.file_size_mb = size_bytes / (1024 * 1024)
            fm.wall_clock_time_sec = elapsed
            fm.status = aggregate_metrics.status

            # Inherit process-level metrics from aggregate (shared process)
            fm.max_resident_set_kb = aggregate_metrics.max_resident_set_kb
            fm.gpu_available = aggregate_metrics.gpu_available
            fm.peak_gpu_memory_used_mb = aggregate_metrics.peak_gpu_memory_used_mb
            fm.gpu_memory_total_mb = aggregate_metrics.gpu_memory_total_mb

            # Try to get char/line counts from source
            if source_file and source_file.exists():
                try:
                    content = source_file.read_text(encoding='utf-8', errors='ignore')
                    fm.character_count = len(content)
                    fm.line_count = content.count('\n') + 1
                except Exception:
                    pass

            fm.compute_derived_metrics()
            per_file.append(fm)

        return per_file

    def _build_directory_command(self, staging_dir: Path, strategy: Strategy) -> List[str]:
        """Build the directory-mode command."""
        abs_dir = staging_dir.resolve()
        cmd = [str(self.config.python_executable), "anon.py", str(abs_dir)]

        if self.config.version == AnonVersion.V3_0 and strategy != Strategy.DEFAULT:
            version_str = f"v{self.config.version.value}"
            run_output_dir = self.output_dir / version_str / strategy.value
            run_output_dir.mkdir(parents=True, exist_ok=True)
            cmd.extend(["--anonymization-strategy", strategy.value])
            cmd.extend(["--output-dir", str(run_output_dir.resolve())])
            cmd.append("--overwrite")
            cmd.extend(["--log-level", "INFO"])

        if self.config.version == AnonVersion.V2_0:
            # v2.0 outputs to its own output/ directory (no --output-dir flag)
            pass

        return cmd

    def _build_environment(self) -> Dict[str, str]:
        """Build environment variables for the process."""
        env = os.environ.copy()
        if self.config.requires_secret_key:
            env["ANON_SECRET_KEY"] = self.secret_key
        src_path = self.config.path / "src"
        if src_path.exists():
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{src_path}:{existing}" if existing else str(src_path)
        return env

    def _print_directory_summary(
        self, metrics: BenchmarkMetrics, file_count: int,
        per_file_metrics: Optional[List[BenchmarkMetrics]] = None
    ):
        """Print summary of directory-mode run."""
        status_icon = {
            "SUCCESS": "[OK]", "FAILED": "[FAIL]", "ERROR": "[ERR]",
            "TIMEOUT": "[TIMEOUT]", "SKIPPED": "[SKIP]"
        }.get(metrics.status, "[?]")

        print(f"\n  {status_icon} {metrics.status} (directory mode, {file_count} files)")
        if metrics.status == "SUCCESS":
            gpu_info = ""
            if metrics.gpu_available:
                gpu_info = (f" | GPU: {metrics.peak_gpu_utilization_percent:.0f}%"
                           f" / VRAM: {metrics.peak_gpu_memory_used_mb:.0f}MB")
            print(f"      Total Time: {metrics.wall_clock_time_sec:.2f}s | "
                  f"Memory: {metrics.max_resident_set_kb/1024:.1f}MB | "
                  f"Throughput: {metrics.throughput_kb_per_sec:.2f} KB/s{gpu_info}")
            if file_count > 0:
                avg_per_file = metrics.wall_clock_time_sec / file_count
                print(f"      Avg per file: {avg_per_file:.2f}s "
                      f"(vs ~{avg_per_file + 60:.0f}s in single-file mode with overhead)")

            # Per-file breakdown table
            if per_file_metrics:
                print(f"\n      Per-file breakdown ({len(per_file_metrics)} files timed):")
                print(f"      {'File':<45} {'Size KB':>8} {'Time (s)':>9} {'KB/s':>8}")
                print(f"      {'-'*45} {'-'*8} {'-'*9} {'-'*8}")
                for pf in per_file_metrics:
                    name = pf.file_name.replace("DIRMODE_", "")
                    if len(name) > 44:
                        name = name[:41] + "..."
                    tp = f"{pf.throughput_kb_per_sec:.1f}" if pf.throughput_kb_per_sec > 0 else "N/A"
                    print(f"      {name:<45} {pf.file_size_kb:>8.1f} {pf.wall_clock_time_sec:>9.3f} {tp:>8}")

        elif metrics.error_message:
            print(f"      Error: {metrics.error_message}")


# =============================================================================
# RESULTS MANAGEMENT
# =============================================================================

class ResultsManager:
    """Manages benchmark results persistence."""

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.csv_path = results_dir / "benchmark_results.csv"
        self.json_path = results_dir / "benchmark_results.json"
        self.state_path = results_dir / "benchmark_state.json"

        self._results: List[BenchmarkMetrics] = []
        self._state = RunState.load(self.state_path)
        self._csv_headers_written = self.csv_path.exists()

    @property
    def state(self) -> RunState:
        return self._state

    def add_result(self, metrics: BenchmarkMetrics):
        """Add a result and persist immediately."""
        self._results.append(metrics)

        # Append to CSV
        self._append_to_csv(metrics)

        # Update state
        if metrics.status == "SUCCESS":
            self._state.mark_completed(
                metrics.version, metrics.strategy,
                metrics.file_name, metrics.run_number
            )
        else:
            self._state.mark_failed(
                metrics.version, metrics.strategy,
                metrics.file_name, metrics.run_number
            )

        self._state.save(self.state_path)

    def _append_to_csv(self, metrics: BenchmarkMetrics):
        """Append a single result to CSV file."""
        data = metrics.to_dict()

        # Ensure directory exists (may have been cleaned after init)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        with open(self.csv_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())

            if not self._csv_headers_written:
                writer.writeheader()
                self._csv_headers_written = True

            writer.writerow(data)

    def save_json(self):
        """Save all results to JSON file, merging with existing data."""
        new_data = [m.to_dict() for m in self._results]

        # Load existing data and merge (append new, avoid duplicates)
        existing_data = []
        if self.json_path.exists():
            try:
                with open(self.json_path, 'r') as f:
                    existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = []
            except (json.JSONDecodeError, IOError):
                existing_data = []

        # Build set of existing keys to avoid duplicates
        def _result_key(d):
            return (d.get('version'), d.get('strategy'), d.get('file_name'),
                    d.get('run_number'), d.get('measurement_mode'))

        existing_keys = {_result_key(d) for d in existing_data}
        for d in new_data:
            if _result_key(d) not in existing_keys:
                existing_data.append(d)
                existing_keys.add(_result_key(d))

        with open(self.json_path, 'w') as f:
            json.dump(existing_data, f, indent=2)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        if not self._results:
            return {}

        successful = [m for m in self._results if m.status == "SUCCESS"]
        skipped = [m for m in self._results if m.status == "SKIPPED"]
        failed = [m for m in self._results if m.status in ("FAILED", "ERROR", "TIMEOUT")]

        summary = {
            "total_runs": len(self._results),
            "successful_runs": len(successful),
            "skipped_runs": len(skipped),
            "failed_runs": len(failed),
            "by_version": {},
            "by_strategy": {},
            "failures": []
        }

        # Log failures for review
        for m in failed:
            summary["failures"].append({
                "version": m.version,
                "strategy": m.strategy,
                "file": m.file_name,
                "error": m.error_message
            })

        # Group by version
        for m in successful:
            if m.version not in summary["by_version"]:
                summary["by_version"][m.version] = {
                    "count": 0,
                    "avg_time": 0,
                    "avg_throughput": 0,
                    "avg_memory_mb": 0
                }
            v = summary["by_version"][m.version]
            v["count"] += 1
            v["avg_time"] = (v["avg_time"] * (v["count"]-1) + m.wall_clock_time_sec) / v["count"]
            v["avg_throughput"] = (v["avg_throughput"] * (v["count"]-1) + m.throughput_kb_per_sec) / v["count"]
            v["avg_memory_mb"] = (v["avg_memory_mb"] * (v["count"]-1) + m.max_resident_set_kb / 1024) / v["count"]

        return summary


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

class BenchmarkOrchestrator:
    """Main orchestrator for the benchmark suite."""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.base_dir = Path.cwd()
        self.benchmark_dir = self.base_dir / "benchmark"
        self.log_dir = self.benchmark_dir / "run_logs"
        self.results_dir = self.benchmark_dir / "results"
        self.output_dir = self.benchmark_dir / "output"

        self.results_manager = ResultsManager(self.results_dir)

    def run_setup(self):
        """Run environment setup for all versions."""
        print("\n" + "="*70)
        print("BENCHMARK SETUP PHASE")
        print("="*70)

        # Determine GPU mode (--cpu-only overrides --gpu)
        gpu_mode = self.args.gpu and not getattr(self.args, 'cpu_only', False)
        print(f"[INFO] PyTorch mode for v3.0: {'GPU (CUDA 12.8)' if gpu_mode else 'CPU-only'}")

        versions_to_setup = self._get_versions_to_run()

        for version in versions_to_setup:
            config = VERSION_CONFIGS[version]
            setup = EnvironmentSetup(config, self.log_dir, self.args.verbose, gpu_mode=gpu_mode)

            if not setup.setup(force=self.args.force_setup):
                print(f"\n[ERROR] Setup failed for v{version.value}")
                if not self.args.continue_on_error:
                    sys.exit(1)

        print("\n" + "="*70)
        print("SETUP COMPLETE")
        print("="*70)

    def run_benchmarks(self):
        """Run benchmarks (dispatches to single-file or directory mode)."""
        if getattr(self.args, 'directory_mode', False):
            self._run_directory_benchmarks()
        else:
            self._run_single_file_benchmarks()

    def run_overhead_calibration(self):
        """Measure model loading overhead per version/strategy.

        Runs a near-zero file (5 bytes .txt) through each version/strategy
        N times to isolate the model initialization cost. With a 5-byte input
        the processing time is negligible, so wall_clock ≈ model loading time.

        Results are saved with measurement_mode='overhead_calibration'.
        """
        print("\n" + "=" * 70)
        print("OVERHEAD CALIBRATION PHASE")
        print("=" * 70)
        print("[INFO] Measuring model loading overhead per version/strategy.")
        print(f"[INFO] Runs per configuration: {self.args.runs}")

        # Create minimal calibration file (5 bytes)
        cal_dir = self.benchmark_dir / "overhead_calibration" / "data"
        cal_dir.mkdir(parents=True, exist_ok=True)
        cal_file = cal_dir / "minimal.txt"
        cal_file.write_text("test\n", encoding="utf-8")
        print(f"[INFO] Calibration file: {cal_file} ({cal_file.stat().st_size} bytes)")

        versions_to_run = self._get_versions_to_run()

        # Plan runs
        plan = []
        for version in versions_to_run:
            config = VERSION_CONFIGS[version]
            if not config.python_executable.exists():
                print(f"  [WARN] Skipping v{version.value}: venv not found. Run --setup first.")
                continue
            for strategy in config.strategies:
                plan.append((version, config, strategy))

        total_runs = len(plan) * self.args.runs
        print(f"[INFO] Total calibration runs planned: {total_runs} "
              f"({len(plan)} configs x {self.args.runs} runs)")

        # Collect results keyed by (version, strategy)
        overhead_data: Dict[str, List[float]] = {}
        completed = 0

        for version, config, strategy in plan:
            key = f"v{version.value}|{strategy.value}"
            overhead_data[key] = []

            runner = BenchmarkRunner(
                config, self.output_dir, self.log_dir, self.args.secret_key
            )

            for run_num in range(1, self.args.runs + 1):
                # Check if already completed (resumable)
                run_key = f"{version.value}|{strategy.value}|OVERHEAD_CALIBRATION|{run_num}"
                if run_key in self.results_manager.state.completed_runs:
                    print(f"  [SKIP] Already completed: {key} | Run #{run_num}")
                    completed += 1
                    continue

                print(f"\n  Calibrating: {key} | Run #{run_num}/{self.args.runs}")

                try:
                    metrics = runner.run(
                        cal_file, strategy, run_num,
                        show_output=False
                    )
                    # Override measurement_mode and file_name
                    metrics.measurement_mode = "overhead_calibration"
                    metrics.file_name = "OVERHEAD_CALIBRATION"

                    self.results_manager.add_result(metrics)
                    completed += 1

                    if metrics.status == "SUCCESS" and metrics.wall_clock_time_sec > 0:
                        overhead_data[key].append(metrics.wall_clock_time_sec)
                        print(f"    Overhead: {metrics.wall_clock_time_sec:.2f}s | "
                              f"Memory: {metrics.max_resident_set_kb / 1024:.0f} MB")
                    else:
                        print(f"    {metrics.status}: {metrics.error_message}")

                    print(f"    Progress: {completed}/{total_runs} ({100 * completed / total_runs:.0f}%)")

                except KeyboardInterrupt:
                    print("\n\n[INTERRUPT] Saving progress and exiting...")
                    self.results_manager.save_json()
                    sys.exit(0)
                except Exception as e:
                    print(f"    [ERROR] {e}")
                    if not self.args.continue_on_error:
                        raise

        # Save final results
        self.results_manager.save_json()

        # Print summary table
        print("\n" + "=" * 70)
        print("OVERHEAD CALIBRATION RESULTS")
        print("=" * 70)
        print(f"\n{'Version':<10} {'Strategy':<12} {'Runs':>5} "
              f"{'Mean (s)':>10} {'Std (s)':>10} {'Min (s)':>10} {'Max (s)':>10}")
        print("-" * 10 + " " + "-" * 12 + " " + "-" * 5 + " " +
              "-" * 10 + " " + "-" * 10 + " " + "-" * 10 + " " + "-" * 10)

        for key, times in overhead_data.items():
            parts = key.split("|")
            ver = parts[0]
            strat = parts[1]
            n = len(times)
            if n == 0:
                print(f"{ver:<10} {strat:<12} {'0':>5} {'—':>10} {'—':>10} {'—':>10} {'—':>10}")
                continue
            mean_t = sum(times) / n
            min_t = min(times)
            max_t = max(times)
            if n > 1:
                variance = sum((t - mean_t) ** 2 for t in times) / (n - 1)
                std_t = variance ** 0.5
            else:
                std_t = 0.0
            print(f"{ver:<10} {strat:<12} {n:>5} "
                  f"{mean_t:>10.2f} {std_t:>10.2f} {min_t:>10.2f} {max_t:>10.2f}")

        print(f"\nNote: Overhead = wall_clock for a 5-byte file (processing time negligible).")
        print(f"      Use these values to subtract model loading cost from single_file measurements.")

    def _run_single_file_benchmarks(self):
        """Run benchmarks in single-file mode (one invocation per file)."""
        print("\n" + "="*70)
        print("BENCHMARK EXECUTION PHASE (single-file mode)")
        print("="*70)

        # Get test files
        test_files = self._collect_test_files()
        if not test_files:
            print("[ERROR] No test files found!")
            sys.exit(1)

        print(f"\nFound {len(test_files)} test files")

        # Get versions to run
        versions_to_run = self._get_versions_to_run()

        # Calculate total runs
        total_runs = 0
        for version in versions_to_run:
            config = VERSION_CONFIGS[version]
            for strategy in config.strategies:
                for _ in test_files:
                    total_runs += self.args.runs

        print(f"Total benchmark runs planned: {total_runs}")
        print(f"Runs already completed: {len(self.results_manager.state.completed_runs)}")

        # Execute benchmarks - ORDER: run -> file -> version -> strategy
        completed = 0

        for run_num in range(1, self.args.runs + 1):
            print(f"\n{'='*80}")
            print(f"RUN #{run_num}/{self.args.runs}")
            print(f"{'='*80}")

            for file_path in test_files:
                print(f"\nProcessing file: {file_path.name}")

                for version in versions_to_run:
                    config = VERSION_CONFIGS[version]

                    # Check if venv exists
                    if not config.python_executable.exists():
                        print(f"  [WARN] Skipping v{version.value}: venv not found. Run with --setup first.")
                        continue

                    runner = BenchmarkRunner(
                        config,
                        self.output_dir,
                        self.log_dir,
                        self.args.secret_key
                    )

                    for strategy in config.strategies:
                        # Check if already completed
                        if self.results_manager.state.is_completed(
                            version.value, strategy.value, file_path.name, run_num
                        ):
                            print(f"  [SKIP] Already completed: v{version.value} | {strategy.value} | Run #{run_num}")
                            completed += 1
                            continue

                        # Run benchmark
                        try:
                            metrics = runner.run(
                                file_path,
                                strategy,
                                run_num,
                                show_output=self.args.show_output
                            )
                            self.results_manager.add_result(metrics)
                            completed += 1

                            print(f"  Progress: {completed}/{total_runs} ({100*completed/total_runs:.1f}%)")

                        except KeyboardInterrupt:
                            print("\n\n[INTERRUPT] Saving progress and exiting...")
                            self.results_manager.save_json()
                            sys.exit(0)
                        except Exception as e:
                            print(f"  [ERROR] Unexpected error: {e}")
                            if not self.args.continue_on_error:
                                raise

        # Save final results
        self.results_manager.save_json()

        # Print summary
        self._print_summary()

    def _run_directory_benchmarks(self):
        """Run benchmarks in directory mode (one invocation per version/strategy).

        For v2.0 and v3.0: passes a directory of all test files to anon.py,
        which loads models once and processes all files sequentially.
        Eliminates ~55-77s model loading overhead per file.

        For v1.0: falls back to single-file mode (no directory support).
        """
        print("\n" + "="*70)
        print("BENCHMARK EXECUTION PHASE (directory mode)")
        print("="*70)
        print("[INFO] Directory mode: models load ONCE per (version, strategy, run)")
        print("[INFO] v1.0 will use single-file mode (no directory support)")

        # Get test files
        test_files = self._collect_test_files()
        if not test_files:
            print("[ERROR] No test files found!")
            sys.exit(1)

        print(f"\nFound {len(test_files)} test files")

        # Get versions to run
        versions_to_run = self._get_versions_to_run()

        # Calculate total runs
        total_dir_runs = 0   # Directory mode runs (v2.0, v3.0)
        total_file_runs = 0  # Single-file runs (v1.0 fallback)
        for version in versions_to_run:
            config = VERSION_CONFIGS[version]
            for strategy in config.strategies:
                if config.supports_directory:
                    total_dir_runs += self.args.runs
                else:
                    total_file_runs += len(test_files) * self.args.runs

        print(f"Directory-mode runs planned: {total_dir_runs}")
        if total_file_runs > 0:
            print(f"Single-file fallback runs (v1.0): {total_file_runs}")
        print(f"Runs already completed: {len(self.results_manager.state.completed_runs)}")

        completed = 0
        total_all = total_dir_runs + total_file_runs

        for run_num in range(1, self.args.runs + 1):
            print(f"\n{'='*80}")
            print(f"RUN #{run_num}/{self.args.runs}")
            print(f"{'='*80}")

            for version in versions_to_run:
                config = VERSION_CONFIGS[version]

                if not config.python_executable.exists():
                    print(f"  [WARN] Skipping v{version.value}: venv not found.")
                    continue

                for strategy in config.strategies:
                    if config.supports_directory:
                        # === DIRECTORY MODE for v2.0 / v3.0 ===
                        run_key = f"{version.value}|{strategy.value}|DIRECTORY_RUN|{run_num}"
                        if run_key in self.results_manager.state.completed_runs:
                            print(f"\n  [SKIP] Already completed: v{version.value} | {strategy.value} | DIR | Run #{run_num}")
                            completed += 1
                            continue

                        try:
                            dir_runner = DirectoryBenchmarkRunner(
                                config, self.output_dir, self.log_dir, self.args.secret_key
                            )
                            metrics_list = dir_runner.run(
                                test_files, strategy, run_num,
                                show_output=self.args.show_output
                            )
                            # First element is aggregate DIRECTORY_RUN, rest are per-file
                            for m in metrics_list:
                                self.results_manager.add_result(m)
                            completed += 1

                            if total_all > 0:
                                print(f"  Progress: {completed}/{total_all} ({100*completed/total_all:.1f}%)")

                        except KeyboardInterrupt:
                            print("\n\n[INTERRUPT] Saving progress and exiting...")
                            self.results_manager.save_json()
                            sys.exit(0)
                        except Exception as e:
                            print(f"  [ERROR] Directory mode failed: {e}")
                            if not self.args.continue_on_error:
                                raise

                    else:
                        # === SINGLE-FILE FALLBACK for v1.0 ===
                        runner = BenchmarkRunner(
                            config, self.output_dir, self.log_dir, self.args.secret_key
                        )

                        for file_path in test_files:
                            if self.results_manager.state.is_completed(
                                version.value, strategy.value, file_path.name, run_num
                            ):
                                completed += 1
                                continue

                            try:
                                metrics = runner.run(
                                    file_path, strategy, run_num,
                                    show_output=self.args.show_output
                                )
                                self.results_manager.add_result(metrics)
                                completed += 1

                                if total_all > 0:
                                    print(f"  Progress: {completed}/{total_all} ({100*completed/total_all:.1f}%)")

                            except KeyboardInterrupt:
                                print("\n\n[INTERRUPT] Saving progress and exiting...")
                                self.results_manager.save_json()
                                sys.exit(0)
                            except Exception as e:
                                print(f"  [ERROR] Unexpected error: {e}")
                                if not self.args.continue_on_error:
                                    raise

        # Save final results
        self.results_manager.save_json()

        # Print summary
        self._print_summary()

    # =========================================================================
    # REGRESSION ESTIMATION
    # =========================================================================

    def run_regression_estimation(self):
        """Estimate processing time for large files via linear regression.

        Supports two modes:
        1. --regression-source: Create subsets of CSV/JSON/TXT/XML files at
           specified sizes (--regression-sizes). Also creates XLSX from CSV
           and DOCX from TXT subsets.
        2. --regression-dir: Use existing files from a directory, grouped by
           extension, as natural regression data points (ideal for PDF, XML,
           TXT where files of varying sizes already exist).

        The model:  time = intercept + slope × size_kb
          - intercept ≈ model loading overhead (~55-77s)
          - slope ≈ per-KB processing rate (seconds per KB)
        """
        print("\n" + "=" * 70)
        print("REGRESSION ESTIMATION PHASE")
        print("=" * 70)

        versions_to_run = self._get_versions_to_run()
        n_runs = self.args.runs
        target_mb = self.args.regression_target

        staging = self.benchmark_dir / "regression_subsets"
        staging.mkdir(parents=True, exist_ok=True)

        # Collect all regression jobs: [(ext, subset_info, predict_mb, label), ...]
        regression_jobs = []

        # --- Mode 1: --regression-source (create subsets from large files) ---
        if self.args.regression_source:
            source_paths = [Path(p.strip()) for p in self.args.regression_source.split(",")]
            for sf in source_paths:
                if not sf.exists():
                    print(f"[ERROR] Source file not found: {sf}")
                    sys.exit(1)

            sizes_mb = sorted(float(s) for s in self.args.regression_sizes.split(","))

            for source_file in source_paths:
                source_bytes = source_file.stat().st_size
                source_mb = source_bytes / (1024 * 1024)
                predict_mb_val = target_mb if target_mb else source_mb
                ext = source_file.suffix.lower()

                print(f"\n{'=' * 60}")
                print(f"Source: {source_file.name} ({source_mb:.1f} MB)")
                print(f"Subset sizes (MB): {sizes_mb}")
                print(f"Runs per subset: {n_runs}")
                print(f"Target prediction: {predict_mb_val:.1f} MB")
                print(f"{'=' * 60}")

                valid_sizes = [s for s in sizes_mb if s * 1024 * 1024 <= source_bytes]
                skipped = [s for s in sizes_mb if s not in valid_sizes]
                if skipped:
                    print(f"[INFO] Skipping sizes > source: {skipped} MB")
                if not valid_sizes:
                    print(f"[WARN] All sizes > source ({source_mb:.1f} MB). Skipping.")
                    continue

                subset_info = self._create_subsets(
                    source_file, ext, valid_sizes, staging
                )
                if subset_info:
                    regression_jobs.append((ext, subset_info, predict_mb_val,
                                           source_file.name))

                # Also create XLSX from CSV subsets
                if ext == ".csv":
                    xlsx_info = self._convert_csv_subsets_to_xlsx(subset_info, staging)
                    if xlsx_info:
                        regression_jobs.append((".xlsx", xlsx_info, predict_mb_val,
                                               f"{source_file.stem}.xlsx (from CSV)"))

                # Also create DOCX from TXT subsets
                if ext == ".txt":
                    docx_info = self._convert_txt_subsets_to_docx(subset_info, staging)
                    if docx_info:
                        regression_jobs.append((".docx", docx_info, predict_mb_val,
                                               f"{source_file.stem}.docx (from TXT)"))

        # --- Mode 2: --regression-dir (use existing files) ---
        if self.args.regression_dir:
            dir_path = Path(self.args.regression_dir)
            if not dir_path.exists():
                print(f"[ERROR] Directory not found: {dir_path}")
                sys.exit(1)

            max_file_mb = self.args.regression_max_file_mb \
                if hasattr(self.args, 'regression_max_file_mb') else None
            dir_jobs = self._collect_dir_regression_files(
                dir_path, target_mb, max_file_mb=max_file_mb)
            regression_jobs.extend(dir_jobs)

        if not regression_jobs:
            print("[ERROR] No regression jobs to run. Provide --regression-source "
                  "and/or --regression-dir.")
            sys.exit(1)

        # === Run benchmarks for each regression job ===
        for ext, subset_info, predict_mb_val, label in regression_jobs:
            print(f"\n{'=' * 60}")
            print(f"REGRESSION: {label} ({ext})")
            print(f"Files: {len(subset_info)} sizes, {n_runs} runs each")
            print(f"Target prediction: {predict_mb_val:.1f} MB")
            print(f"{'=' * 60}")

            regression_data = self._run_regression_benchmarks(
                ext, subset_info, versions_to_run, n_runs
            )

            self._print_regression_results(regression_data, predict_mb_val, label)

        # Save results
        self.results_manager.save_json()

        # Cleanup subsets
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
            print(f"\n[INFO] Cleaned up regression subsets.")

    def _create_subsets(self, source_file: Path, ext: str,
                        valid_sizes: List[float], staging: Path
                        ) -> List[tuple]:
        """Create subsets for a given source file and extension.

        Returns list of (target_mb, actual_mb, path) tuples.
        """
        print(f"\n[INFO] Creating {len(valid_sizes)} subsets...")
        subset_info = []

        if ext == ".json":
            print(f"[INFO] Loading JSON array from {source_file.name}...")
            try:
                with open(source_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
            except MemoryError:
                print(f"[ERROR] Not enough memory to load {source_file.name}.")
                return []
            if not isinstance(json_data, list):
                print(f"[ERROR] Expected JSON array, got {type(json_data).__name__}")
                return []
            print(f"[INFO] Loaded {len(json_data)} elements.")

            for sz in valid_sizes:
                tgt_bytes = int(sz * 1024 * 1024)
                name = f"subset_{sz}mb{ext}".replace(".", "_", 1) if sz != int(sz) \
                    else f"subset_{int(sz)}mb{ext}"
                path = staging / name
                actual = self._create_json_subset_from_data(json_data, path, tgt_bytes)
                actual_mb_val = actual / (1024 * 1024)
                print(f"  {name}: {actual_mb_val:.2f} MB ({actual:,} bytes)")
                subset_info.append((sz, actual_mb_val, path))
            del json_data

        elif ext == ".csv":
            for sz in valid_sizes:
                tgt_bytes = int(sz * 1024 * 1024)
                name = f"subset_{sz}mb{ext}".replace(".", "_", 1) if sz != int(sz) \
                    else f"subset_{int(sz)}mb{ext}"
                path = staging / name
                actual = self._create_csv_subset(source_file, path, tgt_bytes)
                actual_mb_val = actual / (1024 * 1024)
                print(f"  {name}: {actual_mb_val:.2f} MB ({actual:,} bytes)")
                subset_info.append((sz, actual_mb_val, path))

        elif ext in (".txt", ".xml", ".log"):
            for sz in valid_sizes:
                tgt_bytes = int(sz * 1024 * 1024)
                name = f"subset_{sz}mb{ext}".replace(".", "_", 1) if sz != int(sz) \
                    else f"subset_{int(sz)}mb{ext}"
                path = staging / name
                actual = self._create_text_subset(source_file, path, tgt_bytes)
                actual_mb_val = actual / (1024 * 1024)
                print(f"  {name}: {actual_mb_val:.2f} MB ({actual:,} bytes)")
                subset_info.append((sz, actual_mb_val, path))

        else:
            print(f"[WARN] Cannot create subsets for '{ext}'. "
                  f"Use --regression-dir for existing files.")

        return subset_info

    def _collect_dir_regression_files(self, dir_path: Path,
                                      target_mb: float = None,
                                      max_file_mb: float = None
                                      ) -> List[tuple]:
        """Collect existing files from a directory, grouped by extension.

        Selects up to 6 files per extension at varying sizes for regression.
        Returns list of (ext, subset_info, predict_mb, label) tuples.
        """
        print(f"\n[INFO] Scanning directory: {dir_path}")
        if max_file_mb:
            print(f"[INFO] Max file size filter: {max_file_mb:.1f} MB")

        max_bytes = int(max_file_mb * 1024 * 1024) if max_file_mb else None

        # Collect files by extension
        excluded = {".anonymous", ".anon", ".bak", ".tmp"}
        files_by_ext: Dict[str, List[tuple]] = {}

        for f in dir_path.rglob("*"):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            if ext in excluded or "anonym" in f.stem.lower():
                continue
            # Skip image formats
            if ext in (".jpeg", ".jpg", ".png", ".gif", ".bmp", ".tiff",
                       ".tif", ".webp", ".jp2", ".pnm"):
                continue
            sz = f.stat().st_size
            if sz < 100:  # skip near-empty files
                continue
            if max_bytes and sz > max_bytes:
                continue
            if ext not in files_by_ext:
                files_by_ext[ext] = []
            files_by_ext[ext].append((sz, f))

        jobs = []
        for ext, file_list in sorted(files_by_ext.items()):
            file_list.sort()  # sort by size
            n_files = len(file_list)

            if n_files < 2:
                print(f"  {ext}: only {n_files} file(s) — need >= 2 for regression, skipping.")
                continue

            # Select files at evenly spaced size percentiles (up to 6)
            max_points = min(6, n_files)
            if n_files <= max_points:
                selected = file_list
            else:
                indices = [int(i * (n_files - 1) / (max_points - 1))
                           for i in range(max_points)]
                selected = [file_list[i] for i in indices]

            # Build subset_info: (target_mb, actual_mb, path)
            subset_info = []
            for sz, fpath in selected:
                mb = sz / (1024 * 1024)
                subset_info.append((mb, mb, fpath))

            largest_mb = file_list[-1][0] / (1024 * 1024)
            total_mb = sum(sz for sz, _ in file_list) / (1024 * 1024)
            predict_mb_val = target_mb if target_mb else largest_mb

            print(f"  {ext}: {n_files} files ({total_mb:.1f} MB total), "
                  f"selected {len(selected)} for regression "
                  f"({subset_info[0][1]:.1f} KB - {subset_info[-1][1]*1024:.0f} KB)")

            label = f"dir:{dir_path.name} ({ext})"
            jobs.append((ext, subset_info, predict_mb_val, label))

        return jobs

    def _run_regression_benchmarks(
        self, ext: str, subset_info: List[tuple],
        versions_to_run: List[AnonVersion], n_runs: int
    ) -> Dict[str, List[dict]]:
        """Run benchmark N times for each (version, strategy, file_size).

        Returns regression_data dict: { "v1.0|default": [data_points...] }
        """
        regression_data: Dict[str, List[dict]] = {}

        for version in versions_to_run:
            config = VERSION_CONFIGS[version]
            if not config.python_executable.exists():
                print(f"\n  [WARN] Skipping v{version.value}: venv not found.")
                continue
            if ext not in config.supported_extensions:
                print(f"\n  [WARN] Skipping v{version.value}: {ext} not supported.")
                continue

            for strategy in config.strategies:
                key = f"v{version.value}|{strategy.value}"
                regression_data[key] = []

                runner = BenchmarkRunner(
                    config, self.output_dir, self.log_dir, self.args.secret_key
                )

                print(f"\n  --- {key} ---")

                for target_sz_mb, actual_mb_val, subset_path in subset_info:
                    run_metrics_list: List[BenchmarkMetrics] = []

                    for run_num in range(1, n_runs + 1):
                        run_id = f"REGRESSION_{subset_path.stem}"

                        print(f"\n  Running: {key} | {subset_path.name} "
                              f"({actual_mb_val:.2f} MB) | Run #{run_num}")

                        if self.results_manager.state.is_completed(
                            version.value, strategy.value, run_id, run_num
                        ):
                            print(f"    [SKIP] {actual_mb_val:.2f} MB run #{run_num} "
                                  f"(already done)")
                            continue

                        try:
                            metrics = runner.run(
                                subset_path, strategy, run_num,
                                show_output=False
                            )
                            metrics.measurement_mode = "regression"
                            metrics.file_name = run_id
                            self.results_manager.add_result(metrics)

                            if (metrics.status == "SUCCESS"
                                    and metrics.wall_clock_time_sec > 0):
                                run_metrics_list.append(metrics)
                                kbps = (actual_mb_val * 1024) / metrics.wall_clock_time_sec \
                                    if metrics.wall_clock_time_sec > 0 else 0
                                print(f"\n  [OK] SUCCESS")
                                print(f"      Time: {metrics.wall_clock_time_sec:.2f}s "
                                      f"| Memory: {metrics.max_resident_set_kb/1024:.1f}MB "
                                      f"| Throughput: {kbps:.2f} KB/s")
                                print(f"    {actual_mb_val:.2f} MB | run #{run_num}: "
                                      f"{metrics.wall_clock_time_sec:.2f}s")
                            else:
                                print(f"    {actual_mb_val:.2f} MB | run #{run_num}: "
                                      f"{metrics.status} - {metrics.error_message}")

                        except KeyboardInterrupt:
                            print("\n\n[INTERRUPT] Saving progress...")
                            self.results_manager.save_json()
                            sys.exit(0)
                        except Exception as e:
                            print(f"    [ERROR] {e}")
                            if not self.args.continue_on_error:
                                raise

                    if run_metrics_list:
                        n = len(run_metrics_list)
                        size_kb = actual_mb_val * 1024
                        dp = {
                            'size_kb': size_kb,
                            'mean_time': sum(m.wall_clock_time_sec for m in run_metrics_list) / n,
                            'mean_user_time': sum(m.user_time_sec for m in run_metrics_list) / n,
                            'mean_system_time': sum(m.system_time_sec for m in run_metrics_list) / n,
                            'mean_cpu_pct': sum(m.cpu_percent for m in run_metrics_list) / n,
                            'mean_rss_mb': sum(m.max_resident_set_kb for m in run_metrics_list) / n / 1024,
                            'mean_peak_mem_mb': sum(m.peak_memory_mb for m in run_metrics_list) / n,
                            'mean_avg_mem_mb': sum(m.avg_memory_mb for m in run_metrics_list) / n,
                            'mean_gpu_util': sum(m.peak_gpu_utilization_percent for m in run_metrics_list) / n,
                            'mean_gpu_vram_mb': sum(m.peak_gpu_memory_used_mb for m in run_metrics_list) / n,
                            'mean_fs_out': sum(m.file_system_outputs for m in run_metrics_list) / n,
                            'n_runs': n,
                        }
                        regression_data[key].append(dp)

        return regression_data

    @staticmethod
    def _convert_csv_subsets_to_xlsx(csv_subset_info: List[tuple],
                                     staging: Path) -> List[tuple]:
        """Convert CSV subsets to XLSX format for regression."""
        import pandas as pd
        xlsx_info = []
        print(f"\n[INFO] Converting CSV subsets to XLSX...")
        for target_mb, actual_mb, csv_path in csv_subset_info:
            xlsx_name = csv_path.stem + ".xlsx"
            xlsx_path = staging / xlsx_name
            try:
                df = pd.read_csv(csv_path, dtype=str)
                df.to_excel(xlsx_path, index=False, engine='openpyxl')
                xlsx_size = xlsx_path.stat().st_size
                xlsx_mb = xlsx_size / (1024 * 1024)
                print(f"  {xlsx_name}: {xlsx_mb:.2f} MB ({xlsx_size:,} bytes)")
                xlsx_info.append((target_mb, xlsx_mb, xlsx_path))
            except Exception as e:
                print(f"  [ERROR] Converting {csv_path.name}: {e}")
        return xlsx_info

    @staticmethod
    def _convert_txt_subsets_to_docx(txt_subset_info: List[tuple],
                                      staging: Path) -> List[tuple]:
        """Convert TXT subsets to DOCX format for regression."""
        try:
            from docx import Document
        except ImportError:
            print(f"  [WARN] python-docx not installed. Skipping DOCX conversion.")
            return []

        docx_info = []
        print(f"\n[INFO] Converting TXT subsets to DOCX...")
        for target_mb, actual_mb, txt_path in txt_subset_info:
            docx_name = txt_path.stem + ".docx"
            docx_path = staging / docx_name
            try:
                doc = Document()
                with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        doc.add_paragraph(line.rstrip('\n'))
                doc.save(str(docx_path))
                docx_size = docx_path.stat().st_size
                docx_mb = docx_size / (1024 * 1024)
                print(f"  {docx_name}: {docx_mb:.2f} MB ({docx_size:,} bytes)")
                docx_info.append((target_mb, docx_mb, docx_path))
            except Exception as e:
                print(f"  [ERROR] Converting {txt_path.name}: {e}")
        return docx_info

    @staticmethod
    def _create_text_subset(source: Path, target: Path, target_bytes: int) -> int:
        """Create a text file subset (TXT, XML, LOG) by copying lines until target size.

        For XML: tries to maintain well-formedness by closing the root tag.
        """
        ext = source.suffix.lower()
        is_xml = ext == ".xml"

        with open(source, 'r', encoding='utf-8', errors='ignore') as src, \
             open(target, 'w', encoding='utf-8') as dst:

            # For XML: read and preserve the XML declaration and root opening tag
            root_close_tag = None
            if is_xml:
                preamble_lines = []
                for line in src:
                    preamble_lines.append(line)
                    stripped = line.strip()
                    # Look for the root element opening tag
                    if stripped.startswith('<') and not stripped.startswith('<?') \
                            and not stripped.startswith('<!--'):
                        # Extract root tag name
                        tag_match = re.match(r'<(\w[\w:-]*)', stripped)
                        if tag_match:
                            root_close_tag = f"</{tag_match.group(1)}>"
                        break

                preamble = ''.join(preamble_lines)
                dst.write(preamble)
                written = len(preamble.encode('utf-8'))
                close_bytes = len(root_close_tag.encode('utf-8')) + 1 \
                    if root_close_tag else 0
            else:
                written = 0
                close_bytes = 0

            for line in src:
                line_bytes = len(line.encode('utf-8'))
                if written + line_bytes + close_bytes > target_bytes:
                    break
                dst.write(line)
                written += line_bytes

            # Close XML root tag for well-formedness
            if is_xml and root_close_tag:
                dst.write("\n" + root_close_tag + "\n")

        return target.stat().st_size

    @staticmethod
    def _create_csv_subset(source: Path, target: Path, target_bytes: int) -> int:
        """Create a CSV subset by copying header + rows until target size."""
        with open(source, 'r', encoding='utf-8', errors='ignore') as src, \
             open(target, 'w', encoding='utf-8', newline='') as dst:
            header = src.readline()
            dst.write(header)
            written = len(header.encode('utf-8'))

            for line in src:
                line_bytes = len(line.encode('utf-8'))
                if written + line_bytes > target_bytes:
                    break
                dst.write(line)
                written += line_bytes

        return target.stat().st_size

    @staticmethod
    def _create_json_subset_from_data(data: list, target: Path, target_bytes: int) -> int:
        """Create a JSON array subset from pre-loaded data.

        Writes elements one at a time to avoid building the full serialized
        string in memory.  Stops when the next element would exceed target_bytes.
        """
        if not data:
            with open(target, 'w', encoding='utf-8') as f:
                f.write('[]')
            return 2

        with open(target, 'w', encoding='utf-8') as f:
            f.write('[')
            written = 1  # opening bracket
            count = 0

            for elem in data:
                elem_str = json.dumps(elem, ensure_ascii=False)
                elem_bytes = len(elem_str.encode('utf-8'))
                sep_bytes = 1 if count > 0 else 0  # comma

                # +1 for closing bracket
                if written + sep_bytes + elem_bytes + 1 > target_bytes and count > 0:
                    break

                if count > 0:
                    f.write(',')
                f.write(elem_str)
                written += sep_bytes + elem_bytes
                count += 1

            f.write(']')

        return target.stat().st_size

    @staticmethod
    def _linear_regression(x_values: List[float], y_values: List[float]):
        """Simple OLS linear regression: y = intercept + slope * x.

        Returns (intercept, slope, r_squared) or (None, None, None) if < 2 points.
        """
        n = len(x_values)
        if n < 2:
            return None, None, None

        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x ** 2 for x in x_values)

        denom = n * sum_x2 - sum_x ** 2
        if abs(denom) < 1e-12:
            return None, None, None

        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n

        # R-squared
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in y_values)
        ss_res = sum((y - (intercept + slope * x)) ** 2
                     for x, y in zip(x_values, y_values))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 1e-12 else 0.0

        return intercept, slope, r_squared

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format seconds into human-readable duration."""
        if seconds < 0:
            return "N/A"
        if seconds < 60:
            return f"{seconds:.1f}s"
        if seconds < 3600:
            m = int(seconds // 60)
            s = seconds % 60
            return f"{m}m {s:.0f}s"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}h {m}m {s:.0f}s"

    def _print_regression_results(
        self,
        regression_data: Dict[str, List[dict]],
        predict_mb: float,
        source_name: str,
    ):
        """Perform linear regression and print estimation + resource scaling results."""
        predict_kb = predict_mb * 1024

        print(f"\n{'=' * 70}")
        print(f"REGRESSION RESULTS -- {source_name}")
        print(f"{'=' * 70}")
        print(f"Model: time = intercept + slope * size_kb")
        print(f"  intercept ~ model loading overhead (seconds)")
        print(f"  slope ~ per-KB processing rate (seconds/KB)")
        print(f"\nTarget prediction: {predict_mb:.1f} MB ({predict_kb:.0f} KB)")

        # --- Time regression table ---
        print(f"\n{'Config':<25} {'Pts':>4} {'Intercept(s)':>12} {'Slope(s/KB)':>12} "
              f"{'R^2':>6} {'Predicted(s)':>12} {'Duration':>14}")
        print(f"{'-' * 25} {'-' * 4} {'-' * 12} {'-' * 12} {'-' * 6} {'-' * 12} {'-' * 14}")

        for key, points in regression_data.items():
            n = len(points)
            if n < 2:
                print(f"{key:<25} {n:>4} {'--':>12} {'--':>12} "
                      f"{'--':>6} {'--':>12} {'need >=2 pts':>14}")
                continue

            x = [p['size_kb'] for p in points]
            y = [p['mean_time'] for p in points]

            intercept, slope, r2 = self._linear_regression(x, y)

            if intercept is None:
                print(f"{key:<25} {n:>4} {'ERR':>12} {'ERR':>12} "
                      f"{'--':>6} {'--':>12} {'--':>14}")
                continue

            predicted = intercept + slope * predict_kb
            human = self._format_duration(predicted)

            print(f"{key:<25} {n:>4} {intercept:>11.2f}s {slope:>12.6f} "
                  f"{r2:>6.4f} {predicted:>11.1f}s {human:>14}")

        # --- Detailed data points ---
        print(f"\nData points (mean of {self.args.runs} run(s) per size):")
        for key, points in regression_data.items():
            if not points:
                continue
            print(f"\n  {key}:")
            print(f"    {'Size (MB)':>10} {'Size (KB)':>10} {'Time (s)':>10} {'Throughput':>12}")
            for dp in points:
                size_mb = dp['size_kb'] / 1024
                kbps = dp['size_kb'] / dp['mean_time'] if dp['mean_time'] > 0 else 0
                print(f"    {size_mb:>10.1f} {dp['size_kb']:>10.0f} "
                      f"{dp['mean_time']:>10.2f} {kbps:>10.1f} KB/s")

        # --- Resource scaling analysis ---
        print(f"\n{'=' * 70}")
        print(f"RESOURCE SCALING ANALYSIS -- {source_name}")
        print(f"{'=' * 70}")
        print(f"How resource consumption changes with input file size.")
        print(f"Target: {predict_mb:.1f} MB")
        print(f"Prediction method: constant/sublinear -> mean/max of observed; linear+ -> OLS extrapolation\n")

        resource_metrics = [
            ('mean_rss_mb',       'Peak RAM (MB)',     'Peak resident set size from /usr/bin/time (kernel-level)'),
            ('mean_peak_mem_mb',  'Peak RAM psutil',   'Peak RSS sampled by ProcessMonitor (process + children)'),
            ('mean_avg_mem_mb',   'Avg RAM (MB)',      'Average RSS during execution (ProcessMonitor)'),
            ('mean_user_time',    'User CPU (s)',      'CPU time in user mode (scales with parallelism)'),
            ('mean_system_time',  'System CPU (s)',    'CPU time in kernel mode (I/O, syscalls)'),
            ('mean_cpu_pct',      'CPU Util %',        'Multi-core CPU utilization (>100% = multi-threaded)'),
            ('mean_gpu_util',     'GPU Util %',        'Peak GPU compute utilization'),
            ('mean_gpu_vram_mb',  'GPU VRAM (MB)',     'Peak GPU memory used'),
            ('mean_fs_out',       'FS Writes',         'Filesystem output blocks (proportional to output size)'),
        ]

        for key, points in regression_data.items():
            if len(points) < 2:
                continue

            print(f"\n  --- {key} ---\n")
            print(f"  {'Metric':<20} ", end="")
            for dp in points:
                size_label = f"{dp['size_kb']/1024:.1f}MB"
                print(f"{size_label:>12}", end="")
            print(f"  {'Scaling':>12} {'R^2':>6}  {'Predicted':>14}")

            print(f"  {'-'*20} ", end="")
            for _ in points:
                print(f"{'':->12}", end="")
            print(f"  {'-'*12} {'-'*6}  {'-'*14}")

            x = [dp['size_kb'] for dp in points]

            for metric_key, label, _desc in resource_metrics:
                y = [dp.get(metric_key, 0) for dp in points]
                print(f"  {label:<20} ", end="")

                for val in y:
                    if val >= 1000:
                        print(f"{val:>12,.0f}", end="")
                    elif val >= 10:
                        print(f"{val:>12.1f}", end="")
                    else:
                        print(f"{val:>12.2f}", end="")

                # Determine scaling pattern and predict for target size
                predicted_str = ""
                if len(x) >= 2 and y[0] > 0:
                    intercept_r, slope_r, r2_r = self._linear_regression(x, y)
                    if intercept_r is not None:
                        ratio = y[-1] / y[0] if y[0] > 0 else 0
                        size_ratio = x[-1] / x[0] if x[0] > 0 else 0
                        elasticity = (ratio - 1) / (size_ratio - 1) if size_ratio > 1 else 0

                        if elasticity < 0.10:
                            pattern = "constant"
                        elif elasticity < 0.3:
                            pattern = "sublinear"
                        elif elasticity < 0.8:
                            pattern = "~linear"
                        elif elasticity < 1.2:
                            pattern = "linear"
                        else:
                            pattern = "superlinear"

                        # Use appropriate prediction strategy based on scaling pattern
                        if pattern == "constant":
                            # Constant metrics: use mean of observed values
                            pred_val = sum(y) / len(y)
                        elif pattern == "sublinear":
                            # Sublinear: use max observed value (conservative upper bound)
                            pred_val = max(y)
                        else:
                            # Linear/superlinear: linear extrapolation is appropriate
                            pred_val = intercept_r + slope_r * predict_kb
                        if pred_val >= 1000:
                            predicted_str = f"{pred_val:>12,.0f}"
                        elif pred_val >= 10:
                            predicted_str = f"{pred_val:>12.1f}"
                        else:
                            predicted_str = f"{pred_val:>12.2f}"

                        print(f"  {pattern:>12} {r2_r:>6.4f}  {predicted_str:>14}", end="")
                    else:
                        print(f"  {'--':>12} {'--':>6}  {'--':>14}", end="")
                else:
                    print(f"  {'N/A':>12} {'--':>6}  {'--':>14}", end="")
                print()

            # Memory-focused summary
            print(f"\n  RAM usage analysis for {key}:")
            rss_vals = [dp.get('mean_rss_mb', 0) for dp in points]
            avg_mem_vals = [dp.get('mean_avg_mem_mb', 0) for dp in points]
            gpu_vram_vals = [dp.get('mean_gpu_vram_mb', 0) for dp in points]

            if rss_vals[0] > 0:
                rss_delta = rss_vals[-1] - rss_vals[0]
                size_delta = x[-1] - x[0]
                mb_per_mb = (rss_delta / (size_delta / 1024)) if size_delta > 0 else 0
                rss_ratio = rss_vals[-1] / rss_vals[0] if rss_vals[0] > 0 else 0
                size_ratio = x[-1] / x[0] if x[0] > 0 else 0
                rss_elasticity = (rss_ratio - 1) / (size_ratio - 1) if size_ratio > 1 else 0

                print(f"    Peak RAM: {rss_vals[0]:.0f} MB -> {rss_vals[-1]:.0f} MB "
                      f"(+{rss_delta:.0f} MB for +{size_delta/1024:.0f} MB input)")
                print(f"    RAM growth rate: {mb_per_mb:.1f} MB RAM per MB input")

                if rss_elasticity < 0.10:
                    # Constant: RAM is dominated by model loading, not data size
                    pred_rss = sum(rss_vals) / len(rss_vals)
                    print(f"    Predicted RAM for {predict_mb:.0f} MB input: ~{pred_rss:.0f} MB ({pred_rss/1024:.1f} GB)")
                    print(f"    Pattern: CONSTANT -- RAM dominated by model footprint, not input size")
                elif rss_elasticity < 0.3:
                    # Sublinear: grows slowly; use max observed as conservative estimate
                    pred_rss = max(rss_vals)
                    print(f"    Predicted RAM for {predict_mb:.0f} MB input: ~{pred_rss:.0f} MB ({pred_rss/1024:.1f} GB) (conservative)")
                    print(f"    Pattern: SUBLINEAR -- RAM grows slowly with input size")
                else:
                    # Linear or superlinear: extrapolate
                    rss_i, rss_s, _ = self._linear_regression(x, rss_vals)
                    if rss_i is not None:
                        pred_rss = rss_i + rss_s * predict_kb
                        print(f"    Predicted RAM for {predict_mb:.0f} MB input: ~{pred_rss:.0f} MB ({pred_rss/1024:.1f} GB)")
                        print(f"    Pattern: LINEAR -- RAM scales with input size")

                base_ram = min(rss_vals)
                print(f"    Base model footprint: ~{base_ram:.0f} MB ({base_ram/1024:.1f} GB)")

            if gpu_vram_vals[0] > 0:
                vram_mean = sum(gpu_vram_vals) / len(gpu_vram_vals)
                print(f"    GPU VRAM: {gpu_vram_vals[0]:.0f} MB -> {gpu_vram_vals[-1]:.0f} MB "
                      f"(~{vram_mean:.0f} MB constant -- model weights dominate)")

            # Full resource summary table
            print(f"\n  Resource scaling summary for {key}:")
            for metric_key, label, desc in resource_metrics:
                y = [dp.get(metric_key, 0) for dp in points]
                if len(x) >= 2 and y[0] > 0:
                    ratio = y[-1] / y[0] if y[0] > 0 else 0
                    size_ratio = x[-1] / x[0] if x[0] > 0 else 0
                    pct_change = (ratio - 1) * 100
                    size_pct = (size_ratio - 1) * 100
                    print(f"    {label}: {y[0]:.1f} -> {y[-1]:.1f} "
                          f"({pct_change:+.1f}% for {size_pct:+.0f}% size increase) -- {desc}")

    def _get_versions_to_run(self) -> List[AnonVersion]:
        """Get list of versions to benchmark."""
        if self.args.versions:
            return [AnonVersion(v) for v in self.args.versions]
        return list(AnonVersion)

    def _collect_test_files(self) -> List[Path]:
        """Collect test files based on configuration."""
        data_dir = Path(self.args.data_dir)

        if not data_dir.exists():
            print(f"[ERROR] Data directory not found: {data_dir}")
            return []

        files = []

        # Get all supported extensions across all versions
        all_extensions = set()
        for config in VERSION_CONFIGS.values():
            all_extensions.update(config.supported_extensions)

        # Excluded extensions (not processable)
        excluded_extensions = {".anonymous", ".anon", ".bak", ".tmp"}

        # Collect files
        for ext in all_extensions:
            if ext not in excluded_extensions:
                files.extend(data_dir.rglob(f"*{ext}"))

        # Filter by extension pattern if specified
        if self.args.file_pattern:
            pattern = re.compile(self.args.file_pattern, re.IGNORECASE)
            files = [f for f in files if pattern.search(f.name)]

        # Sort for consistent ordering
        files = sorted(set(files), key=lambda x: x.name)

        return files

    def _print_summary(self):
        """Print benchmark summary."""
        summary = self.results_manager.get_summary()

        print("\n" + "="*70)
        print("BENCHMARK SUMMARY")
        print("="*70)

        print(f"\nTotal runs: {summary.get('total_runs', 0)}")
        print(f"Successful: {summary.get('successful_runs', 0)}")
        print(f"Skipped: {summary.get('skipped_runs', 0)}")
        print(f"Failed: {summary.get('failed_runs', 0)}")

        # Show failures
        failures = summary.get('failures', [])
        if failures:
            print("\nFailures:")
            for f in failures:
                print(f"  v{f['version']} | {f['strategy']} | {f['file']} | {f['error']}")

        print("\nBy Version:")
        for version, stats in summary.get('by_version', {}).items():
            print(f"  v{version}:")
            print(f"    Runs: {stats['count']}")
            print(f"    Avg Time: {stats['avg_time']:.2f}s")
            print(f"    Avg Memory: {stats['avg_memory_mb']:.1f} MB")
            print(f"    Avg Throughput: {stats['avg_throughput']:.2f} KB/s")

        print("\n" + "="*70)
        print(f"Results saved to: {self.results_dir}")
        print("="*70)


# =============================================================================
# CLI
# =============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="AnonLFI Benchmark Suite - Compare performance across versions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run setup only
  python benchmark.py --setup

  # Run benchmarks (assumes setup is done)
  python benchmark.py --benchmark --data-dir ./dados_teste/vulnnet_scans_openvas

  # Run smoke test (quick validation)
  python benchmark.py --smoke-test

  # Full run: setup + benchmarks
  python benchmark.py --setup --benchmark --data-dir ./dados_teste

  # Run specific versions only
  python benchmark.py --benchmark --versions 2.0 3.0 --data-dir ./dados_teste

  # Resume interrupted run
  python benchmark.py --benchmark --data-dir ./dados_teste

  # Directory mode: eliminates model loading overhead for v2.0/v3.0
  python benchmark.py --benchmark --directory-mode --data-dir ./dados_teste

  # Regression estimation: predict processing time for large files
  python benchmark.py --regression --regression-source file.csv,file.json --runs 3

  # Custom subset sizes and specific versions
  python benchmark.py --regression --regression-source file.csv --regression-sizes 1,2,4,8,16,32 --versions 3.0 --runs 5
        """
    )

    # Mode selection
    mode_group = parser.add_argument_group("Mode Selection")
    mode_group.add_argument("--setup", action="store_true",
                           help="Run environment setup (create venvs, install deps, warm cache)")
    mode_group.add_argument("--benchmark", action="store_true",
                           help="Run benchmarks")
    mode_group.add_argument("--smoke-test", action="store_true",
                           help="Run quick smoke test with minimal data")
    mode_group.add_argument("--calibrate-overhead", action="store_true",
                           help="Measure model loading overhead per version/strategy. "
                                "Runs a near-zero file (5 bytes) N times (--runs) per "
                                "version/strategy to isolate model initialization cost. "
                                "Results saved with measurement_mode='overhead_calibration'.")
    mode_group.add_argument("--regression", action="store_true",
                           help="Estimate processing time for large files via linear "
                                "regression. Creates subsets at various sizes from "
                                "--regression-source files, benchmarks each subset "
                                "--runs times, fits time = intercept + slope*size, "
                                "and predicts time for the full file.")

    # Setup options
    setup_group = parser.add_argument_group("Setup Options")
    setup_group.add_argument("--force-setup", action="store_true",
                            help="Force recreation of virtual environments")
    setup_group.add_argument("--gpu", action="store_true", default=True,
                            help="Use GPU-enabled PyTorch for v3.0 (default: True)")
    setup_group.add_argument("--cpu-only", action="store_true",
                            help="Use CPU-only PyTorch for v3.0 (overrides --gpu)")

    # Benchmark options
    bench_group = parser.add_argument_group("Benchmark Options")
    bench_group.add_argument("--data-dir", type=str,
                            default="benchmark/smoke_test_data/dados_teste",
                            help="Directory containing test files")
    bench_group.add_argument("--versions", nargs="+", choices=["1.0", "2.0", "3.0"],
                            help="Versions to benchmark (default: all)")
    bench_group.add_argument("--runs", type=int, default=1,
                            help="Number of runs per configuration (default: 1)")
    bench_group.add_argument("--file-pattern", type=str,
                            help="Regex pattern to filter test files")
    bench_group.add_argument("--secret-key", type=str,
                            default="benchmark-secret-key-2026",
                            help="Secret key for anonymization")
    bench_group.add_argument("--directory-mode", action="store_true",
                            help="Use directory mode for v2.0/v3.0: pass all files in a single "
                                 "invocation to eliminate per-file model loading overhead (~55-77s). "
                                 "v1.0 falls back to single-file mode. Records aggregate metrics.")

    # Regression options
    regression_group = parser.add_argument_group("Regression Options (use with --regression)")
    regression_group.add_argument("--regression-source", type=str,
                                  help="Comma-separated paths to source CSV/JSON/TXT/XML files "
                                       "from which subsets will be created. Also creates XLSX "
                                       "from CSV subsets and DOCX from TXT subsets automatically.")
    regression_group.add_argument("--regression-dir", type=str,
                                  help="Directory with existing files of varying sizes. "
                                       "Files are grouped by extension and used as natural "
                                       "regression data points. Ideal for PDF, XML, TXT etc. "
                                       "where files of multiple sizes already exist.")
    regression_group.add_argument("--regression-sizes", type=str,
                                  default="0.25,0.5,1,2",
                                  help="Comma-separated subset sizes in MB (default: 0.25,0.5,1,2). "
                                       "Only used with --regression-source.")
    regression_group.add_argument("--regression-target", type=float, default=None,
                                  help="Target file size in MB for prediction. "
                                       "Default: source file size or largest file in dir.")
    regression_group.add_argument("--regression-max-file-mb", type=float, default=None,
                                  help="Max file size in MB for --regression-dir. "
                                       "Files larger than this are excluded from selection.")

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument("--show-output", action="store_true", default=True,
                             help="Show real-time output from anon.py (default: True)")
    output_group.add_argument("--no-show-output", action="store_false", dest="show_output",
                             help="Suppress real-time output")
    output_group.add_argument("--verbose", "-v", action="store_true",
                             help="Verbose output")

    # Error handling
    error_group = parser.add_argument_group("Error Handling")
    error_group.add_argument("--continue-on-error", action="store_true",
                            help="Continue benchmarking even if some runs fail")

    # State management
    state_group = parser.add_argument_group("State Management")
    state_group.add_argument("--clean", action="store_true",
                            help="Clean all results and state before running")

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Validate arguments
    if not (args.setup or args.benchmark or args.smoke_test or args.calibrate_overhead or args.regression):
        parser.print_help()
        print("\n[ERROR] At least one mode must be specified: --setup, --benchmark, --smoke-test, --calibrate-overhead, or --regression")
        sys.exit(1)

    # Validate --regression requirements
    if args.regression and not args.regression_source and not args.regression_dir:
        print("[ERROR] --regression requires --regression-source and/or --regression-dir")
        sys.exit(1)
    # Ensure regression_dir has a default of None if not provided
    if not hasattr(args, 'regression_dir'):
        args.regression_dir = None

    # Handle smoke test
    if args.smoke_test:
        args.setup = True
        args.benchmark = True
        args.runs = 1
        args.data_dir = "benchmark/smoke_test_data/dados_teste"
        print("[INFO] Smoke test mode: 1 run with minimal test data")

    # Handle clean BEFORE creating orchestrator (so ResultsManager starts fresh)
    if args.clean:
        print("[INFO] Cleaning previous results...")
        results_dir = Path.cwd() / "benchmark" / "results"
        if results_dir.exists():
            shutil.rmtree(results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)

    # Create orchestrator
    orchestrator = BenchmarkOrchestrator(args)

    # Run phases
    if args.setup:
        orchestrator.run_setup()

    if args.calibrate_overhead:
        orchestrator.run_overhead_calibration()

    if args.regression:
        orchestrator.run_regression_estimation()

    if args.benchmark:
        orchestrator.run_benchmarks()

    print("\n[DONE] Benchmark suite completed.")


if __name__ == "__main__":
    main()
