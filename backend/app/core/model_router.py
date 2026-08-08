"""
OBSIDIAN — NVIDIA Build Model Router.

Routes LLM calls to the appropriate NVIDIA Build model based on
capability tier. Supports fallbacks, retries, and model switching
without changing any business logic.

Model Tiers:
  - reasoning:   Complex multi-step analysis (49B Nemotron Super)
  - code:        Code generation & patching (70B Nemotron Instruct)
  - lightweight: Classification & routing (8B Nemotron Nano)
  - embedding:   Vector embeddings (nv-embedqa-e5-v5)
  - rerank:      Search reranking (llama-nemotron-rerank)
  - vision:      Image/diagram analysis (Nemotron Nano VL)
  - safety:      Content filtering (Llama Guard 3)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import structlog
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = structlog.get_logger()

# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════


@dataclass
class ModelResponse:
    """Structured response from a model call."""
    content: str
    model: str
    tier: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    raw_response: Any = None


@dataclass
class ModelConfig:
    """Configuration for a model tier."""
    primary: str
    fallbacks: list[str] = field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 0.1


# ═══════════════════════════════════════════════════════════════════
# Model Router
# ═══════════════════════════════════════════════════════════════════


class ModelRouter:
    """
    Unified interface for all NVIDIA Build model calls.

    Usage:
        router = ModelRouter()
        response = await router.complete(
            tier="reasoning",
            messages=[{"role": "user", "content": "Analyze this code..."}],
        )
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=self.settings.nvidia_api_key,
            base_url=self.settings.nvidia_base_url,
        )

        # Define tier configurations with fallback chains
        self._tiers: dict[str, ModelConfig] = {
            "reasoning": ModelConfig(
                primary=self.settings.nvidia_reasoning_model,
                fallbacks=[
                    self.settings.nvidia_code_model,
                    self.settings.nvidia_lightweight_model,
                ],
                max_tokens=8192,
                temperature=0.1,
            ),
            "code": ModelConfig(
                primary=self.settings.nvidia_code_model,
                fallbacks=[
                    self.settings.nvidia_reasoning_model,
                    self.settings.nvidia_lightweight_model,
                ],
                max_tokens=8192,
                temperature=0.0,
            ),
            "lightweight": ModelConfig(
                primary=self.settings.nvidia_lightweight_model,
                fallbacks=[self.settings.nvidia_code_model],
                max_tokens=2048,
                temperature=0.0,
            ),
            "safety": ModelConfig(
                primary=self.settings.nvidia_safety_model,
                fallbacks=[self.settings.nvidia_lightweight_model],
                max_tokens=512,
                temperature=0.0,
            ),
            "vision": ModelConfig(
                primary=self.settings.nvidia_vision_model,
                fallbacks=[self.settings.nvidia_reasoning_model],
                max_tokens=4096,
                temperature=0.1,
            ),
        }

        # Metrics tracking
        self._call_count: dict[str, int] = {}
        self._total_tokens: dict[str, int] = {}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def complete(
        self,
        tier: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> ModelResponse:
        """
        Send a completion request to the appropriate model.

        Args:
            tier: Capability tier (reasoning, code, lightweight, safety, vision)
            messages: Chat messages in OpenAI format
            temperature: Override default temperature
            max_tokens: Override default max tokens
            response_format: Optional structured output format (JSON mode)

        Returns:
            ModelResponse with content and metadata
        """
        config = self._tiers.get(tier)
        if config is None:
            raise ValueError(f"Unknown tier: {tier!r}")

        models_to_try = [config.primary, *config.fallbacks]
        last_error: Exception | None = None

        for model in models_to_try:
            try:
                start = time.perf_counter()

                kwargs: dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature if temperature is not None else config.temperature,
                    "max_tokens": max_tokens or config.max_tokens,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                response = await self.client.chat.completions.create(**kwargs)

                latency = (time.perf_counter() - start) * 1000
                content = response.choices[0].message.content or ""
                tokens = response.usage.total_tokens if response.usage else 0

                # Track metrics
                self._call_count[model] = self._call_count.get(model, 0) + 1
                self._total_tokens[model] = self._total_tokens.get(model, 0) + tokens

                logger.info(
                    "Model call successful",
                    tier=tier,
                    model=model,
                    tokens=tokens,
                    latency_ms=f"{latency:.0f}",
                )

                return ModelResponse(
                    content=content,
                    model=model,
                    tier=tier,
                    tokens_used=tokens,
                    latency_ms=latency,
                    raw_response=response,
                )

            except Exception as e:
                last_error = e
                logger.warning(
                    "Model call failed, trying fallback",
                    tier=tier,
                    model=model,
                    error=str(e),
                )

        raise RuntimeError(
            f"All models failed for tier {tier!r}: {last_error}"
        ) from last_error

    async def complete_json(
        self,
        tier: str,
        messages: list[dict[str, str]],
        **kwargs,
    ) -> dict:
        """Complete and parse as JSON. Falls back to extracting JSON from markdown."""
        response = await self.complete(
            tier=tier,
            messages=messages,
            response_format={"type": "json_object"},
            **kwargs,
        )
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown code blocks
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content.strip())

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using the configured embedding model."""
        response = await self.client.embeddings.create(
            model=self.settings.nvidia_embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    async def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        embeddings = await self.embed([text])
        return embeddings[0]

    async def check_safety(self, text: str) -> dict[str, Any]:
        """
        Run content safety check using Llama Guard.

        Returns:
            {"safe": True/False, "categories": [...], "raw": "..."}
        """
        response = await self.complete(
            tier="safety",
            messages=[{"role": "user", "content": text}],
        )
        content = response.content.strip().lower()
        is_safe = content.startswith("safe")

        return {
            "safe": is_safe,
            "categories": [] if is_safe else content.split("\n")[1:],
            "raw": response.content,
        }

    def get_metrics(self) -> dict[str, Any]:
        """Return usage metrics for all models."""
        return {
            "call_counts": dict(self._call_count),
            "total_tokens": dict(self._total_tokens),
            "tiers": {
                name: {
                    "primary": cfg.primary,
                    "fallbacks": cfg.fallbacks,
                }
                for name, cfg in self._tiers.items()
            },
        }


# ── Singleton ──────────────────────────────────────────────────────

_router: ModelRouter | None = None


def get_model_router() -> ModelRouter:
    """Get or create the singleton ModelRouter."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
