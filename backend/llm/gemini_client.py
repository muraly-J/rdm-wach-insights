"""
llm/gemini_client.py
────────────────────
Thin async wrapper around google-generativeai for:
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

import google.generativeai as genai

from config import get_gemini_api_key, get_gemini_model, get_gemini_embed_model


class GeminiClient:
    """Async wrapper for Gemini generation and embedding APIs."""

    def __init__(self):
        api_key = get_gemini_api_key()
        genai.configure(api_key=api_key)
        self._model_name = get_gemini_model()
        self._embed_model = get_gemini_embed_model()

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
        max_output_tokens: int = 512,
    ) -> str:
        """
        Single-turn text generation.

        Args:
            prompt: User message.
            system_instruction: Optional system prompt injected at model level.
            temperature: Sampling temperature (0 = deterministic).
            max_output_tokens: Cap on output length.

        Returns:
            Generated text as a string.
        """
        model = genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system_instruction,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, partial(model.generate_content, prompt)
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
            system_instruction: System prompt.
            temperature: Sampling temperature.
            max_output_tokens: Cap on output length.

        Returns:
            Assistant reply as a string.
        """
        if not messages:
            raise ValueError("messages must not be empty")

        # Separate history from the final user turn
        history = messages[:-1]
        last_user_content = messages[-1]["parts"][0]

        model = genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system_instruction,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        chat = model.start_chat(history=history)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, partial(chat.send_message, last_user_content)
        )
        return response.text

    async def embed_text(self, text: str, task_type: str = "retrieval_document") -> list[float]:
        """
        Generate a text embedding vector.

        Args:
            text: Input text to embed.
            task_type: One of "retrieval_document", "retrieval_query",
                       "semantic_similarity", "classification".

        Returns:
            Embedding as a list of floats.
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                genai.embed_content,
                model=self._embed_model,
                content=text,
                task_type=task_type,
            ),
        )
        return result["embedding"]
