"""Runtime configuration, read from env / .env so keys and paths are never hardcoded."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# repo root = three levels up from this file (src/support_assistant/config.py)
ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    # One key per provider. LLM_API_KEY is accepted as the DeepSeek key too.
    deepseek_api_key: str = ""
    llm_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""

    model: str = "deepseek-flash"
    max_spend_usd: float = 1.00          # cumulative across runs, tracked in .cache/spend.json

    embed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    top_k: int = 4                        # policy sections shown to the model per question

    policies_file: Path = ROOT / "policies" / "policies.yaml"
    cache_dir: Path = ROOT / ".cache"
    results_dir: Path = ROOT / "results"

    def key_for(self, provider: str) -> str:
        if provider == "deepseek":
            return self.deepseek_api_key or self.llm_api_key
        return {"gemini": self.gemini_api_key, "groq": self.groq_api_key}[provider]


@dataclass(frozen=True)
class ModelSpec:
    """An OpenAI-compatible chat model and what it costs (USD per 1M tokens)."""
    name: str            # our label
    provider: str
    api_model: str       # the id the provider expects
    base_url: str
    price_in: float      # uncached input
    price_out: float
    price_cached: float = 0.0
    offpeak_half: bool = False   # DeepSeek charges half outside its peak hours


DEEPSEEK = "https://api.deepseek.com"
MODELS: dict[str, ModelSpec] = {
    m.name: m for m in [
        ModelSpec("deepseek-flash", "deepseek", "deepseek-flash", DEEPSEEK, 0.30, 1.20, 0.006, offpeak_half=True),
        ModelSpec("deepseek-v4-pro", "deepseek", "deepseek-v4-pro", DEEPSEEK, 1.32, 3.96, 0.044, offpeak_half=True),
    ]
}


def get_settings(env_file: str | Path | None = None) -> Settings:
    """`env_file` lets a run borrow keys from another file without copying them anywhere."""
    if env_file:
        return Settings(_env_file=(ROOT / ".env", Path(env_file)))
    return Settings()
