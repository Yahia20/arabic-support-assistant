"""The one place that talks to a model.

- Any OpenAI-compatible endpoint (DeepSeek, Gemini, Groq...), chosen by name from config.MODELS.
- Every response is cached on disk by (model, messages), so re-running an evaluation is free.
- Spend is written to a ledger and checked *before* each call; past the cap, calls stop.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import ModelSpec, Settings


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Reply:
    text: str
    cost_usd: float
    seconds: float
    cached: bool
    tokens_in: int = 0
    tokens_out: int = 0


class LLM:
    _ledger_lock = threading.Lock()

    def __init__(self, spec: ModelSpec, settings: Settings):
        from openai import OpenAI

        key = settings.key_for(spec.provider)
        if not key:
            raise RuntimeError(f"No API key for {spec.provider}. Put it in .env (see .env.example).")
        self.spec = spec
        self.client = OpenAI(api_key=key, base_url=spec.base_url, timeout=120, max_retries=3)
        self.cache_dir = Path(settings.cache_dir) / "llm" / spec.name
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = Path(settings.cache_dir) / "spend.json"
        self.max_spend = settings.max_spend_usd

    def spent(self) -> float:
        try:
            return json.loads(self.ledger.read_text())["usd"]
        except (FileNotFoundError, ValueError, KeyError):
            return 0.0

    def _record(self, usd: float) -> None:
        with self._ledger_lock:
            self.ledger.write_text(json.dumps({"usd": round(self.spent() + usd, 6)}))

    def chat(self, messages: list[dict]) -> Reply:
        key = hashlib.sha256(json.dumps([self.spec.api_model, messages], ensure_ascii=False).encode()).hexdigest()
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            hit = json.loads(path.read_text(encoding="utf-8"))
            # Cached replies keep the cost and time of the original call, so reports stay true.
            return Reply(hit["text"], hit["cost_usd"], hit["seconds"], True, hit.get("in", 0), hit.get("out", 0))
        if self.spent() >= self.max_spend:
            raise BudgetExceeded(f"spend cap reached (${self.max_spend:.2f}); raise MAX_SPEND_USD to continue")

        t0 = time.time()
        resp = self.client.chat.completions.create(
            model=self.spec.api_model, messages=messages, temperature=0,
            response_format={"type": "json_object"},
        )
        seconds = time.time() - t0
        text = resp.choices[0].message.content or ""
        cost, tin, tout = self._cost(resp.usage)
        self._record(cost)
        path.write_text(json.dumps({"text": text, "cost_usd": cost, "seconds": round(seconds, 3),
                                    "in": tin, "out": tout}, ensure_ascii=False), encoding="utf-8")
        return Reply(text, cost, seconds, False, tin, tout)

    def _cost(self, usage) -> tuple[float, int, int]:
        p = self.spec
        hit = getattr(usage, "prompt_cache_hit_tokens", 0) or 0
        miss = getattr(usage, "prompt_cache_miss_tokens", None)
        if miss is None:
            miss = usage.prompt_tokens - hit
        usd = (hit * p.price_cached + miss * p.price_in + usage.completion_tokens * p.price_out) / 1e6
        if p.offpeak_half and not _deepseek_peak():
            usd /= 2
        return usd, usage.prompt_tokens, usage.completion_tokens


def _deepseek_peak(now: datetime | None = None) -> bool:
    """DeepSeek peak hours: Mon-Fri 01:00-04:00 and 06:00-10:00 UTC. Everything else is half price."""
    now = now or datetime.now(timezone.utc)
    return now.weekday() < 5 and (1 <= now.hour < 4 or 6 <= now.hour < 10)
