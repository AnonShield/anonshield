"""
Ollama Service Manager - Manages Ollama Docker container and model lifecycle.

This module provides automatic management of the Ollama service:
- Checks if Ollama is running (Docker or native)
- Starts the Docker container if needed
- Pulls required models automatically
- Waits for service readiness
"""
import logging
import subprocess
import time
from typing import Optional, Tuple
import requests


class OllamaManager:
    """
    Manages Ollama service lifecycle including Docker container and model availability.

    Attributes:
        base_url: The Ollama API base URL
        docker_image: Docker image to use for Ollama
        container_name: Name for the Docker container
        gpu_enabled: Whether to enable GPU support in Docker
        stop_on_exit: Whether to stop the container when the manager is destroyed
    """

    DEFAULT_DOCKER_IMAGE = "ollama/ollama:latest"
    DEFAULT_CONTAINER_NAME = "ollama-anon"
    STARTUP_TIMEOUT = 60  # seconds to wait for Ollama to start
    PULL_TIMEOUT = 600    # seconds to wait for model pull (10 min)

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        docker_image: str = None,
        container_name: str = None,
        gpu_enabled: bool = True,
        stop_on_exit: bool = True
    ):
        self.base_url = base_url.rstrip('/')
        self.docker_image = docker_image or self.DEFAULT_DOCKER_IMAGE
        self.container_name = container_name or self.DEFAULT_CONTAINER_NAME
        self.gpu_enabled = gpu_enabled
        self.stop_on_exit = stop_on_exit
        self.logger = logging.getLogger(__class__.__name__)

        # Track if WE started the container (vs it was already running)
        self._started_by_us = False
        self._cleanup_registered = False

    def is_ollama_running(self) -> bool:
        """Check if Ollama API is responding."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_available_models(self) -> list[str]:
        """Get list of available models from Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            models = response.json().get("models", [])
            return [m["name"] for m in models]
        except requests.exceptions.RequestException:
            return []

    def is_model_available(self, model: str) -> bool:
        """Check if a specific model is available."""
        available = self.get_available_models()
        # Check both exact match and base model name (e.g., "llama3" matches "llama3:latest")
        return model in available or f"{model}:latest" in available or any(m.startswith(f"{model}:") for m in available)

    def _is_docker_available(self) -> bool:
        """Check if Docker is available and running."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _is_container_running(self) -> bool:
        """Check if the Ollama container is already running."""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={self.container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return self.container_name in result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _container_exists(self) -> bool:
        """Check if the container exists (running or stopped)."""
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={self.container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return self.container_name in result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _start_existing_container(self) -> bool:
        """Start an existing stopped container."""
        try:
            self.logger.info(f"Starting existing container '{self.container_name}'...")
            result = subprocess.run(
                ["docker", "start", self.container_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _create_and_start_container(self) -> bool:
        """Create and start a new Ollama container."""
        self.logger.info(f"Creating new Ollama container '{self.container_name}'...")

        # Build docker run command
        cmd = [
            "docker", "run", "-d",
            "--name", self.container_name,
            "-p", "11434:11434",
            "-v", "ollama:/root/.ollama",
            "--restart", "unless-stopped"
        ]

        # Add GPU support if enabled
        if self.gpu_enabled:
            cmd.extend(["--gpus", "all"])

        cmd.append(self.docker_image)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                # If GPU fails, try without GPU
                if self.gpu_enabled and "could not select device driver" in result.stderr.lower():
                    self.logger.warning("GPU not available, starting Ollama without GPU support...")
                    cmd = [c for c in cmd if c not in ["--gpus", "all"]]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    return result.returncode == 0

                self.logger.error(f"Failed to create container: {result.stderr}")
                return False

            return True

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.logger.error(f"Failed to create container: {e}")
            return False

    def _wait_for_service(self, timeout: int = None) -> bool:
        """Wait for Ollama API to become available."""
        timeout = timeout or self.STARTUP_TIMEOUT
        start_time = time.time()

        self.logger.info("Waiting for Ollama service to be ready...")

        while time.time() - start_time < timeout:
            if self.is_ollama_running():
                self.logger.info("Ollama service is ready!")
                return True
            time.sleep(2)

        self.logger.error(f"Ollama service did not become ready within {timeout} seconds")
        return False

    def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama registry."""
        # Always print to console for visibility during download
        print(f"\n[Ollama] Pulling model '{model}'... This may take several minutes.\n", flush=True)
        self.logger.info(f"Pulling model '{model}'...")

        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model, "stream": True},
                timeout=self.PULL_TIMEOUT,
                stream=True
            )

            last_pct = -1
            # Stream the response to show progress
            for line in response.iter_lines():
                if line:
                    try:
                        import json
                        data = json.loads(line)
                        status = data.get("status", "")
                        if "pulling" in status.lower():
                            completed = data.get("completed", 0)
                            total = data.get("total", 0)
                            if total > 0:
                                pct = int((completed / total) * 100)
                                # Only print every 5% to avoid spam
                                if pct >= last_pct + 5:
                                    print(f"[Ollama] Downloading {model}: {pct}%", flush=True)
                                    last_pct = pct
                        elif status:
                            print(f"[Ollama] {status}", flush=True)
                    except json.JSONDecodeError:
                        pass

            # Verify the model is now available
            if self.is_model_available(model):
                print(f"[Ollama] Model '{model}' pulled successfully!\n", flush=True)
                self.logger.info(f"Model '{model}' pulled successfully!")
                return True
            else:
                print(f"[Ollama] ERROR: Model '{model}' not found after pull\n", flush=True)
                self.logger.error(f"Model '{model}' not found after pull")
                return False

        except requests.exceptions.RequestException as e:
            print(f"[Ollama] ERROR: Failed to pull model: {e}\n", flush=True)
            self.logger.error(f"Failed to pull model: {e}")
            return False

    def ensure_service_ready(self, model: str = None) -> Tuple[bool, Optional[str]]:
        """
        Ensure Ollama service is running and model is available.

        This is the main entry point that handles:
        1. Checking if Ollama is already running
        2. Starting Docker container if needed
        3. Pulling the required model if specified

        Args:
            model: Optional model name to ensure is available

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        print("[Ollama] Checking service status...", flush=True)

        # Step 1: Check if Ollama is already running
        if self.is_ollama_running():
            print("[Ollama] Service is running.", flush=True)
            self.logger.info("Ollama service is already running.")
        else:
            # Step 2: Try to start via Docker
            if not self._is_docker_available():
                return False, "Ollama is not running and Docker is not available. Please start Ollama manually or install Docker."

            # Check if container exists and start it
            if self._container_exists():
                if self._is_container_running():
                    # Container running but API not responding - wait a bit
                    self.logger.info("Container is running, waiting for API...")
                else:
                    # Container exists but stopped - start it
                    if not self._start_existing_container():
                        return False, f"Failed to start existing container '{self.container_name}'"
            else:
                # Create new container
                if not self._create_and_start_container():
                    return False, f"Failed to create Ollama container. Check Docker logs: docker logs {self.container_name}"

            # Wait for service to be ready
            if not self._wait_for_service():
                return False, "Ollama service failed to start within timeout. Check container logs."

        # Step 3: Ensure model is available
        if model:
            print(f"[Ollama] Checking if model '{model}' is available...", flush=True)
            if not self.is_model_available(model):
                print(f"[Ollama] Model '{model}' not found locally. Starting download...", flush=True)
                self.logger.info(f"Model '{model}' not found. Pulling...")
                if not self.pull_model(model):
                    return False, f"Failed to pull model '{model}'. Check network connection and model name."
            else:
                print(f"[Ollama] Model '{model}' is available.", flush=True)

        return True, None

    def stop_container(self) -> bool:
        """Stop the Ollama container."""
        try:
            result = subprocess.run(
                ["docker", "stop", self.container_name],
                capture_output=True,
                timeout=30
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
