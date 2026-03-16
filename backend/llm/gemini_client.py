"""
llm/gemini_client.py
────────────────────
Thin async wrapper around google-genai for:
  - Text generation (chat completions)
  - Text embedding

Usage:
    client = GeminiClient()
    reply = await client.generate_text("Hello")
    vector = await client.embed_text("AHU power factor")
"""

import asyncio
from functools import partial
from typing import Optional

from google import genai
from google.genai import types

from config import get_gemini_api_key, get_gemini_model, get_gemini_embed_model


class GeminiClient:
    """Async wrapper for Gemini generation and embedding APIs."""

    def __init__(self):
        api_key = get_gemini_api_key()
        self._client = genai.Client(api_key=api_key)
        self._model_name = get_gemini_model()
        self._embed_model = get_gemini_embed_model()

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
        max_output_tokens: int = 512,
    ) -> str:
        """Single-turn text generation."""
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        if system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            partial(
                self._client.models.generate_content,
                model=self._model_name,
                contents=prompt,
                config=config,
            ),
        )
        return response.text

    async def generate_chat_response(
        self,
        messages: list[dict],
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 1024,
    ) -> str:
        """
        Multi-turn conversational generation.

        Args:
            messages: List of {"role": "user"|"model", "parts": [str]} dicts.
                      The last message must be role="user".
        """
        if not messages:
            raise ValueError("messages must not be empty")

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        if system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )

        # Convert our message format to google-genai Content objects
        history = []
        for msg in messages[:-1]:
            role = msg["role"]
            content_text = msg["parts"][0] if isinstance(msg["parts"], list) else msg["parts"]
            history.append(types.Content(role=role, parts=[types.Part(text=content_text)]))

        last_user_content = messages[-1]["parts"][0] if isinstance(messages[-1]["parts"], list) else messages[-1]["parts"]

        loop = asyncio.get_event_loop()

        def _run_chat():
            chat = self._client.chats.create(
                model=self._model_name,
                history=history,
                config=config,
            )
            return chat.send_message(last_user_content)

        response = await loop.run_in_executor(None, _run_chat)
        return response.text

    async def embed_text(self, text: str, task_type: str = "retrieval_document") -> list[float]:
        """Generate a text embedding vector."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                self._client.models.embed_content,
                model=self._embed_model,
                contents=text,
            ),
        )
        # google-genai returns EmbedContentResponse with .embeddings list
        return list(result.embeddings[0].values)
