import json
import re
import time
from dataclasses import dataclass
from typing import Iterator

from groq import APIConnectionError, BadRequestError, Groq, RateLimitError

from app.config import get_settings


@dataclass
class LLMResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency: float = 0.0


def parse_json(text: str) -> dict:
    """Best-effort JSON extraction from an LLM reply (handles code fences and chatter)."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        data = json.loads(text[start : end + 1])
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


class LLMService:
    def __init__(self, api_key: str | None = None):
        s = get_settings()
        self._api_key = api_key or s.groq_api_key
        self.model = s.groq_model
        self.fast_model = s.groq_fast_model
        self.reasoning_effort = s.groq_reasoning_effort
        self._client: Groq | None = None

    @property
    def client(self) -> Groq:
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")
            self._client = Groq(api_key=self._api_key)
        return self._client

    @staticmethod
    def _budget(model: str, max_tokens: int) -> int:
        """Reasoning tokens count against max_tokens; add headroom so the final answer isn't cut off (empty)."""
        return max_tokens + 2000 if "gpt-oss" in model else max_tokens

    def _extra(self, model: str) -> dict:
        """gpt-oss models reason before answering; keep effort low for fast, cheap content generation."""
        return {"reasoning_effort": self.reasoning_effort} if "gpt-oss" in model else {}

    def _messages(self, system: str, user: str) -> list[dict]:
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def chat(
        self,
        system: str,
        user: str,
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResult:
        model = model or self.model
        kwargs = dict(
            model=model,
            messages=self._messages(system, user),
            temperature=temperature,
            max_tokens=self._budget(model, max_tokens),
            **self._extra(model),
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        last_err: Exception | None = None
        for attempt in range(3):
            t0 = time.perf_counter()
            try:
                resp = self.client.chat.completions.create(**kwargs)
                usage = resp.usage
                return LLMResult(
                    text=resp.choices[0].message.content or "",
                    input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                    output_tokens=getattr(usage, "completion_tokens", 0) or 0,
                    latency=time.perf_counter() - t0,
                )
            except (RateLimitError, APIConnectionError) as e:
                last_err = e
                time.sleep(2**attempt)
        raise RuntimeError(f"Groq request failed after retries: {last_err}")

    def chat_json(self, system: str, user: str, **kw) -> tuple[dict, LLMResult]:
        temperature = kw.pop("temperature", 0.3)
        try:
            res = self.chat(system, user, json_mode=True, temperature=temperature, **kw)
        except BadRequestError as e:
            if "json_validate_failed" not in str(e):
                raise
            # Strict JSON mode rejected the output: retry as plain text and extract the JSON ourselves.
            res = self.chat(system, user + "\n\nReturn only the JSON object, nothing else.",
                            json_mode=False, temperature=temperature, **kw)
        return parse_json(res.text), res

    def stream(
        self,
        system: str,
        user: str,
        usage: dict,
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 3000,
    ) -> Iterator[str]:
        """Yield text chunks; fills `usage` with input/output tokens and latency when done."""
        t0 = time.perf_counter()
        usage.update(input_tokens=0, output_tokens=0, latency=0.0)
        out_chars = 0
        model = model or self.model
        stream = self.client.chat.completions.create(
            model=model,
            messages=self._messages(system, user),
            temperature=temperature,
            max_tokens=self._budget(model, max_tokens),
            stream=True,
            **self._extra(model),
        )
        for chunk in stream:
            x = getattr(chunk, "x_groq", None)
            if x is not None and getattr(x, "usage", None):
                usage["input_tokens"] = x.usage.prompt_tokens or 0
                usage["output_tokens"] = x.usage.completion_tokens or 0
            if chunk.choices and chunk.choices[0].delta.content:
                piece = chunk.choices[0].delta.content
                out_chars += len(piece)
                yield piece
        if not usage["output_tokens"]:
            usage["output_tokens"] = out_chars // 4  # rough fallback when usage isn't reported
        usage["latency"] = time.perf_counter() - t0


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    s = get_settings()
    return round((input_tokens * s.cost_per_m_input + output_tokens * s.cost_per_m_output) / 1_000_000, 6)
