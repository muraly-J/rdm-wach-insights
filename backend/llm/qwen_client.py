from __future__ import annotations

"""
llm/qwen_client.py
──────────────────
OpenAI-compatible client for local Qwen via LM Studio (localhost:1234).

LM Studio exposes an OpenAI-compatible API at http://localhost:1234/v1.
Load any Qwen model in LM Studio and enable the local server.
"""

import asyncio
import re
from functools import partial

from config import get_lms_api_key, get_lms_base_url, get_lms_model, settings
from core.logger import get_logger
from llm.circuit_breaker import CircuitBreaker, LLMUnavailableError
from openai import OpenAI

logger = get_logger(__name__)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_think(text: str) -> str:
    """Remove Qwen3 chain-of-thought blocks before returning to the user."""
    return _THINK_RE.sub("", text).strip()


class QwenClient:
    """Async wrapper for LM Studio / Qwen via OpenAI-compatible API."""

    def __init__(self):
        timeout = settings.lms_timeout
        self._client = OpenAI(
            base_url=get_lms_base_url(),
            api_key=get_lms_api_key(),
            timeout=timeout,
        )
        self._model = get_lms_model()
        self._breaker = CircuitBreaker()
        logger.info(f"QwenClient initialised — model={self._model}, base_url={get_lms_base_url()}")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        max_output_tokens: int = 512,
    ) -> str:
        """Single-turn generation."""
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        self._breaker.check_state()
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
            self._breaker.record_success()
            return _strip_think(response.choices[0].message.content)
        except LLMUnavailableError:
            raise
        except Exception as e:
            self._breaker.record_failure()
            logger.warning(f"LM Studio unreachable: {e}")
            raise LLMUnavailableError(f"LM Studio unreachable: {e}")

    async def generate_chat_response(
        self,
        messages: list[dict],
        system_instruction: str | None = None,
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

        self._breaker.check_state()
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
            self._breaker.record_success()
            return _strip_think(response.choices[0].message.content)
        except LLMUnavailableError:
            raise
        except Exception as e:
            self._breaker.record_failure()
            logger.warning(f"LM Studio unreachable: {e}")
            raise LLMUnavailableError(f"LM Studio unreachable: {e}")

    async def generate_with_tools(
        self,
        system_prompt: str,
        messages: list,
        tools: list,
        tool_dispatcher,
        max_tool_rounds: int = 5,
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
    ) -> str:
        """
        Agentic tool-calling loop.

        Sends messages + tool definitions to the model. If the model issues
        tool_calls, executes them via tool_dispatcher and feeds results back.
        Repeats until the model produces a final text response or max_tool_rounds
        is reached.

        Args:
            system_prompt: Lean system prompt (no pre-loaded data).
            messages: Conversation history in OpenAI format
                      [{"role": "user"|"assistant", "content": str}, ...].
            tools: List of tool definitions in OpenAI function-calling schema.
            tool_dispatcher: Async callable(name: str, args: dict) -> dict.
            max_tool_rounds: Safety cap on tool-call iterations.
            temperature: Sampling temperature.
            max_output_tokens: Max tokens for final response.

        Returns:
            Final assistant response string with <think> blocks stripped.
        """
        import json
        self._breaker.check_state()
        full_messages = [{"role": "system", "content": system_prompt}] + list(messages)

        for round_num in range(max_tool_rounds + 1):
            is_final_round = (round_num == max_tool_rounds)

            # On the final round, send without tools so the model must answer
            call_tools = tools if not is_final_round else []

            loop = asyncio.get_event_loop()
            try:
                kwargs = dict(
                    model=self._model,
                    messages=full_messages,
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                )
                if call_tools:
                    kwargs["tools"] = call_tools
                    kwargs["tool_choice"] = "auto"

                response = await loop.run_in_executor(
                    None,
                    partial(self._client.chat.completions.create, **kwargs),
                )
            except LLMUnavailableError:
                raise
            except Exception as e:
                self._breaker.record_failure()
                logger.warning(f"LM Studio unreachable: {e}")
                raise LLMUnavailableError(f"LM Studio unreachable: {e}")

            choice = response.choices[0]
            tool_calls = getattr(choice.message, "tool_calls", None)

            # No tool calls → final answer
            if not tool_calls:
                self._breaker.record_success()
                content = choice.message.content or ""
                return _strip_think(content)

            # Append assistant message (with tool_calls) to history
            full_messages.append({
                "role": "assistant",
                "content": choice.message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            })

            # Execute each tool call and append results
            for tc in tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                result = await tool_dispatcher(tc.function.name, args)
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str),
                })

        # Should not reach here (final round sends without tools)
        return "I was unable to complete the analysis."
