from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Union
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class BergetChatCompletionsClient:
    """
    Tiny client for Berget's OpenAI-compatible chat-completions endpoint.
    Matches the request shape used in `gpt-oss-120b.py`.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-oss-120b",
        base_url: str = "https://api.berget.ai/v1/chat/completions",
        timeout_s: float = 60.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout_s = timeout_s

    def chat(
        self,
        messages: Iterable[Union[ChatMessage, Dict[str, str]]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        normalized: List[Dict[str, str]] = []
        for m in messages:
            if isinstance(m, ChatMessage):
                normalized.append({"role": m.role, "content": m.content})
            else:
                normalized.append({"role": m["role"], "content": m["content"]})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": normalized,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        request = Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_s) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            # Preserve any JSON error body for debugging
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM request failed: HTTP {error.code}: {body}") from error

        try:
            return result["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001 - keep failure mode readable
            raise RuntimeError(f"Unexpected LLM response shape: {result}") from e

