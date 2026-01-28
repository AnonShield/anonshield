"""
SLM Client Module - Abstract interface for interacting with local LLMs via Ollama

This module provides a protocol-based abstraction for SLM operations, ensuring
dependency inversion and easy testability.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Protocol, List, Dict, Any, Optional
import logging
import requests
import json
from dataclasses import dataclass

from .ollama_manager import OllamaManager


@dataclass
class SLMResponse:
    """Structured response from an SLM query."""
    content: str
    model: str
    tokens_used: int = 0
    success: bool = True
    error: Optional[str] = None


class SLMClient(Protocol):
    """Protocol defining the interface for SLM clients."""

    def query(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> SLMResponse:
        """Send a query to the SLM and return structured response."""
        ...

    def query_json(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Query SLM and parse JSON response."""
        ...


class OllamaClient:
    """
    Concrete implementation of SLM client using Ollama REST API.

    This client follows the Dependency Inversion Principle by depending on
    configuration rather than hard-coded values.

    When auto_manage=True (default), the client will automatically:
    - Start the Ollama Docker container if not running
    - Pull the required model if not available

    Example:
        client = OllamaClient(model="llama3", base_url="http://localhost:11434")
        response = client.query("Extract entities from: John works at Google")
    """

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
        timeout: int = 120,
        temperature: float = None,  # Will use LLM_CONFIG default if None
        max_retries: int = 3,
        auto_manage: bool = True,  # Auto-manage Ollama service
        docker_image: str = None,
        container_name: str = None,
        gpu_enabled: bool = True
    ):
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        # Import here to avoid circular dependency
        from ..config import LLM_CONFIG
        self.temperature = temperature if temperature is not None else LLM_CONFIG['ollama']['temperature']
        self.max_retries = max_retries
        self.auto_manage = auto_manage
        self.logger = logging.getLogger(__class__.__name__)

        # Initialize Ollama manager for service lifecycle
        self.manager = OllamaManager(
            base_url=base_url,
            docker_image=docker_image,
            container_name=container_name,
            gpu_enabled=gpu_enabled
        )

        # Validate connectivity on init (with auto-management if enabled)
        self._validate_connection()
    
    def _validate_connection(self) -> None:
        """
        Validates that Ollama is running and the model is available.

        If auto_manage is enabled, will attempt to:
        1. Start the Ollama Docker container if not running
        2. Pull the required model if not available
        """
        if self.auto_manage:
            # Use the manager to ensure service and model are ready
            success, error = self.manager.ensure_service_ready(model=self.model)
            if not success:
                self.logger.error(f"Failed to initialize Ollama: {error}")
                raise ConnectionError(error)
            return

        # Manual validation (original behavior when auto_manage=False)
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()

            available_models = [m["name"] for m in response.json().get("models", [])]

            if self.model not in available_models:
                self.logger.warning(
                    f"Model '{self.model}' not found in Ollama. "
                    f"Available models: {', '.join(available_models)}. "
                    "The model will be pulled on first use."
                )
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to connect to Ollama at {self.base_url}: {e}")
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running with: ollama serve"
            ) from e
    
    def query(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> SLMResponse:
        """
        Send a query to the SLM with automatic retry logic.
        
        Args:
            prompt: The user prompt to send
            system_prompt: Optional system context
            **kwargs: Additional parameters to pass to Ollama
        
        Returns:
            SLMResponse with content and metadata
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", 2048),
            }
        }
        
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Querying Ollama (attempt {attempt + 1}/{self.max_retries})")
                
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                content = data.get("message", {}).get("content", "")
                
                return SLMResponse(
                    content=content,
                    model=self.model,
                    tokens_used=data.get("eval_count", 0),
                    success=True
                )
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"Request timed out (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    return SLMResponse(
                        content="",
                        model=self.model,
                        success=False,
                        error="Request timed out after maximum retries"
                    )
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed: {e}")
                if attempt == self.max_retries - 1:
                    return SLMResponse(
                        content="",
                        model=self.model,
                        success=False,
                        error=str(e)
                    )
        
        # Should never reach here, but for type safety
        return SLMResponse(content="", model=self.model, success=False, error="Unknown error")
    
    def query_json(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        json_retries: int = 2,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Query the SLM and parse JSON response with robust error handling and retries.
        
        This method enforces JSON output and includes a retry mechanism to ask the
        SLM to fix its own malformed JSON.
        
        Returns:
            Parsed JSON dictionary, or {"error": "..."} on failure.
        """
        json_instruction = "\n\nRespond ONLY with valid JSON. No explanations or markdown."
        current_prompt = prompt + json_instruction
        current_system_prompt = system_prompt

        for attempt in range(json_retries + 1):
            response = self.query(current_prompt, current_system_prompt, **kwargs)
            
            if not response.success:
                return {"error": response.error}
            
            content = response.content.strip()
            
            # Improved cleanup: remove markdown fences and surrounding text
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            try:
                # Attempt to parse the cleaned content
                return json.loads(content)
            except json.JSONDecodeError as e:
                self.logger.warning(f"JSON parse failed on attempt {attempt + 1}: {e}")
                self.logger.debug(f"Invalid raw content: {content[:500]}")
                
                if attempt < json_retries:
                    # If it's not the last attempt, create a "fixer" prompt
                    self.logger.info("Attempting to fix JSON with another SLM call...")
                    current_system_prompt = None  # The fixer prompt is self-contained
                    current_prompt = (
                        "The following text is not valid JSON. Please fix it and return ONLY the corrected JSON object. "
                        "Ensure that any backslashes within regex patterns are double-escaped (e.g., `\\d` instead of `\d`, `\\\\s` instead of `\\s`). "
                        "Do not add any explanations, apologies, or markdown formatting.\n\n"
                        f"Invalid JSON:\n---\n{content}\n---\nCorrected JSON:"
                    )
                else:
                    # On the last attempt, return the error
                    self.logger.error(f"Final attempt to parse JSON failed. Raw content: {content[:500]}")
                    return {"error": f"Invalid JSON response after retries: {e}", "raw_content": content}

        # This part should not be reached
        return {"error": "JSON generation failed after multiple retries."}


class MockSLMClient:
    """Mock client for testing without requiring Ollama."""
    
    def __init__(self, mock_responses: Optional[List[str]] = None):
        self.mock_responses = mock_responses or []
        self.call_count = 0
        self.logger = logging.getLogger(__class__.__name__)
    
    def query(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> SLMResponse:
        response_content = self.mock_responses[self.call_count % len(self.mock_responses)] if self.mock_responses else ""
        self.call_count += 1
        
        return SLMResponse(
            content=response_content,
            model="mock",
            tokens_used=len(response_content.split()),
            success=True
        )
    
    def query_json(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        response = self.query(prompt, system_prompt, **kwargs)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"error": "Mock response is not valid JSON"}