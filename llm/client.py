"""Provider-independent LLM interface; configure a provider to generate SQL."""

from typing import Protocol


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str:
        """Return the translator's JSON response as text."""
        ...


class UnconfiguredLLMClient:
    def generate(self, prompt: str) -> str:
        raise RuntimeError('LLM integration is not configured; no invoice query was executed.')
