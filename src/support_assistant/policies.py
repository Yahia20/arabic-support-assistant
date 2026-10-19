"""The policy book: sections in Arabic and English, loaded once."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Section:
    id: str
    title_ar: str
    title_en: str
    ar: str
    en: str

    def text(self, lang: str) -> str:
        return self.en if lang == "en" else self.ar

    def title(self, lang: str) -> str:
        return self.title_en if lang == "en" else self.title_ar


@dataclass(frozen=True)
class PolicyBook:
    company_ar: str
    company_en: str
    sections: tuple[Section, ...]

    def get(self, section_id: str) -> Section | None:
        return next((s for s in self.sections if s.id == section_id), None)

    @property
    def ids(self) -> list[str]:
        return [s.id for s in self.sections]


@lru_cache(maxsize=4)
def load_policies(path: Path) -> PolicyBook:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    sections = tuple(
        Section(s["id"], s["title"]["ar"], s["title"]["en"], s["ar"].strip(), s["en"].strip())
        for s in raw["sections"]
    )
    return PolicyBook(raw["company"]["name"]["ar"], raw["company"]["name"]["en"], sections)
