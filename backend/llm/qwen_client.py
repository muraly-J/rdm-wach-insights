"""
llm/qwen_client.py
──────────────────
OpenAI-compatible client for local Qwen via LM Studio (localhost:1234).

LM Studio exposes an OpenAI-compatible API at http://localhost:1234/v1.
Load any Qwen model in LM Studio and enable the local server.
"""

import asyncio
import logging
import re
from functools import partial
from typing import Optional

from openai import OpenAI

from config import get_lms_base_url, get_lms_model, get_lms_api_key

logger = logging.getLogger(__name__)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_think(text: str) -> str:
    """Remove Qwen3 chain-of-thought blocks before returning to the user."""
    return _THINK_RE.sub("", text).strip()


class QwenClient:
    """Async wrapper for LM Studio / Qwen via OpenAI-compatible API."""

    def __init__(self):
        import os
        timeout = float(os.getenv("LMS_TIMEOUT", "60.0"))
        self._client = OpenAI(
            base_url=get_lms_base_url(),
            api_key=get_lms_api_key(),
            timeout=timeout,
        )
        self._model = get_lms_model()
        logger.info(f"QwenClient initialised — model={self._model}, base_url={get_lms_base_url()}")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
        max_output_tokens: int = 512,
    ) -> str:
        """Single-turn generation."""
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                partial(
                    self._client.chat.completions.create,
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                ),
            )
            return _strip_think(response.choices[0].message.content)
        except Exception as e:
            logger.warning(f"LM Studio unreachable: {e}")
            return "Local LM Studio is not available in this environment."

    async def generate_chat_response(
        self,
        messages: list[dict],
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 1024,
    ) -> str:
        """
        Multi-turn chat response.
        messages = [{"role": "user"|"model", "parts": [str]}]
        Maps "model" → "assistant" for OpenAI compatibility.
        """
        oai_messages = []
        if system_instruction:
            oai_messages.append({"role": "system", "content": system_instruction})
        for msg in messages:
            role = "assistant" if msg["role"] == "model" else msg["role"]
            content = msg["parts"][0] if isinstance(msg["parts"], list) else msg["parts"]
            oai_messages.append({"role": role, "content": content})

        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                partial(
                    self._client.chat.completions.create,
                    model=self._model,
                    messages=oai_messages,
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                ),
            )
            return _strip_think(response.choices[0].message.content)
        except Exception as e:
            logger.warning(f"LM Studio unreachable: {e}")
            return "Local LM Studio is not available in this environment."
