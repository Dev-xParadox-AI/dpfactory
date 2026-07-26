"""
Digital Product Factory - AI Content Generator
Generates product content using AI models.
Supports: NVIDIA NIM (via API key), Cloudflare Workers AI (free), Ollama (local free)
"""
import os
import json
import time
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from src.config_loader import config


@dataclass
class GenerationResult:
    content: str
    model_used: str
    tokens_used: int
    latency_ms: int
    success: bool
    error: Optional[str] = None


class AIContentGenerator:
    """Generates product content using AI models."""
    
    def __init__(self):
        self.provider = config.ai.provider
        self.models = config.ai.models
        self.temperature = config.ai.temperature
        self.max_tokens = config.ai.max_tokens
        
        # NVIDIA NIM credentials (from env)
        self.nvidia_api_key = os.environ.get("NVIDIA_NIM_API_KEY", "")
        self.nvidia_base_url = os.environ.get("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        
        # Cloudflare Workers AI credentials (set via secrets)
        self.cf_account_id = os.environ.get("CF_ACCOUNT_ID", "")
        self.cf_api_token = os.environ.get("CF_API_TOKEN", "")
        
        # Ollama local (fallback)
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    
    def generate(self, prompt: str, model_type: str = "text") -> GenerationResult:
        """Generate content using the configured AI provider."""
        model_name = self.models.get(model_type, self.models["text"])
        
        if self.provider == "nvidia_nim":
            return self._generate_nvidia_nim(prompt, model_name)
        elif self.provider == "cloudflare_ai":
            return self._generate_cloudflare(prompt, model_name)
        elif self.provider == "ollama_local":
            return self._generate_ollama(prompt, model_name)
        else:
            return GenerationResult(
                content="",
                model_used="none",
                tokens_used=0,
                latency_ms=0,
                success=False,
                error=f"Unknown provider: {self.provider}"
            )
    
    def _generate_nvidia_nim(self, prompt: str, model: str) -> GenerationResult:
        """Generate using NVIDIA NIM API."""
        if not self.nvidia_api_key:
            return GenerationResult(
                content="",
                model_used=model,
                tokens_used=0,
                latency_ms=0,
                success=False,
                error="NVIDIA_NIM_API_KEY not configured"
            )
        
        # Map internal model names to NVIDIA NIM model IDs
        nim_model_map = {
            "@cf/meta/llama-3-8b-instruct": "meta/llama-3.1-8b-instruct",
            "@cf/mistral/mistral-7b-instruct": "mistralai/mistral-7b-instruct-v0.3",
            "@cf/meta/codellama-7b-instruct": "codellama/codellama-7b-instruct",
            "llama-3.1-8b": "meta/llama-3.1-8b-instruct",
            "llama-3.1-70b": "meta/llama-3.1-70b-instruct",
            "mistral-7b": "mistralai/mistral-7b-instruct-v0.3",
            "nemotron-3-ultra": "nvidia/nemotron-3-ultra",
        }
        nim_model = nim_model_map.get(model, model)
        
        url = f"{self.nvidia_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.nvidia_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "model": nim_model,
            "messages": [
                {"role": "system", "content": "Jesteś ekspertem ds. produktów cyfrowych dla polskich twórców. Piszesz w języku polskim, profesjonalnie, praktycznie i bez lania wody."},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False
        }
        
        start = time.time()
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            latency_ms = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)
                return GenerationResult(
                    content=content,
                    model_used=nim_model,
                    tokens_used=tokens,
                    latency_ms=latency_ms,
                    success=True
                )
            else:
                return GenerationResult(
                    content="",
                    model_used=nim_model,
                    tokens_used=0,
                    latency_ms=latency_ms,
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text[:500]}"
                )
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            return GenerationResult(
                content="",
                model_used=nim_model,
                tokens_used=0,
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )
    
    def _generate_cloudflare(self, prompt: str, model: str) -> GenerationResult:
        """Generate using Cloudflare Workers AI (free tier: 100k req/day)."""
        if not self.cf_account_id or not self.cf_api_token:
            return GenerationResult(
                content="",
                model_used=model,
                tokens_used=0,
                latency_ms=0,
                success=False,
                error="Cloudflare credentials not configured (CF_ACCOUNT_ID, CF_API_TOKEN)"
            )
        
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.cf_account_id}/ai/run/{model}"
        headers = {
            "Authorization": f"Bearer {self.cf_api_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messages": [
                {"role": "system", "content": "Jesteś ekspertem ds. produktów cyfrowych dla polskich twórców. Piszesz w języku polskim, profesjonalnie, praktycznie i bez lania wody."},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False
        }
        
        start = time.time()
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            latency_ms = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    result = data["result"]
                    content = result.get("response", "")
                    # Cloudflare doesn't always return token usage
                    tokens = result.get("usage", {}).get("total_tokens", 0)
                    return GenerationResult(
                        content=content,
                        model_used=model,
                        tokens_used=tokens,
                        latency_ms=latency_ms,
                        success=True
                    )
                else:
                    return GenerationResult(
                        content="",
                        model_used=model,
                        tokens_used=0,
                        latency_ms=latency_ms,
                        success=False,
                        error=f"Cloudflare API error: {data.get('errors', 'Unknown')}"
                    )
            else:
                return GenerationResult(
                    content="",
                    model_used=model,
                    tokens_used=0,
                    latency_ms=latency_ms,
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text[:500]}"
                )
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            return GenerationResult(
                content="",
                model_used=model,
                tokens_used=0,
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )
    
    def _generate_ollama(self, prompt: str, model: str) -> GenerationResult:
        """Generate using local Ollama (fallback)."""
        # Map model names to Ollama models
        ollama_model_map = {
            "@cf/meta/llama-3-8b-instruct": "llama3:8b",
            "@cf/mistral/mistral-7b-instruct": "mistral:7b",
            "@cf/meta/codellama-7b-instruct": "codellama:7b",
            "llama-3.1-8b": "llama3.1:8b",
            "mistral-7b": "mistral:7b",
        }
        ollama_model = ollama_model_map.get(model, "llama3:8b")
        
        url = f"{self.ollama_host}/api/chat"
        payload = {
            "model": ollama_model,
            "messages": [
                {"role": "system", "content": "Jesteś ekspertem ds. produktów cyfrowych dla polskich twórców. Piszesz w języku polskim, profesjonalnie, praktycznie i bez lania wody."},
                {"role": "user", "content": prompt}
            ],
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            },
            "stream": False
        }
        
        start = time.time()
        try:
            response = requests.post(url, json=payload, timeout=180)
            latency_ms = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", "")
                tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
                return GenerationResult(
                    content=content,
                    model_used=ollama_model,
                    tokens_used=tokens,
                    latency_ms=latency_ms,
                    success=True
                )
            else:
                return GenerationResult(
                    content="",
                    model_used=ollama_model,
                    tokens_used=0,
                    latency_ms=latency_ms,
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text[:500]}"
                )
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            return GenerationResult(
                content="",
                model_used=ollama_model,
                tokens_used=0,
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )
    
    def generate_with_retry(self, prompt: str, model_type: str = "text", max_retries: int = 3) -> GenerationResult:
        """Generate with automatic retry on failure."""
        last_error = None
        for attempt in range(max_retries):
            result = self.generate(prompt, model_type)
            if result.success:
                return result
            last_error = result.error
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        return GenerationResult(
            content="",
            model_used="none",
            tokens_used=0,
            latency_ms=0,
            success=False,
            error=f"Failed after {max_retries} attempts. Last error: {last_error}"
        )


# Test
if __name__ == "__main__":
    gen = AIContentGenerator()
    test_prompt = "Napisz krótki wstęp do ebooka 'Jak zacząć z Notion' (200 słów, PL)."
    result = gen.generate_with_retry(test_prompt)
    print(f"Success: {result.success}")
    print(f"Model: {result.model_used}")
    print(f"Tokens: {result.tokens_used}")
    print(f"Latency: {result.latency_ms}ms")
    if result.success:
        print(f"Content preview: {result.content[:200]}...")
    else:
        print(f"Error: {result.error}")