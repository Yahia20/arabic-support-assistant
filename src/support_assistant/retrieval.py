"""Find the policy sections a question is about.

Every policy line is embedded on its own, in both languages, with a multilingual
sentence-transformers model. A section scores as well as its best-matching
line, so a short question like "تقبلون مدى؟" lands on the one line that mentions mada instead of
being averaged away by the rest of the section. A small word-overlap score breaks ties between
sections that share vocabulary.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from .policies import PolicyBook
from .text import normalize

_WORD = re.compile(r"[\w]+")
_AR_PREFIXES = ("وال", "بال", "كال", "فال", "لل", "ال", "و", "ب", "ل", "ف")
_STOP = {"في", "من", "على", "عن", "الى", "او", "ما", "هل", "كم", "the", "a", "an", "of", "to", "is",
         "for", "and", "or", "my", "i", "can", "do", "how", "what", "in", "on", "it", "be", "you"}


def _stems(text: str) -> set[str]:
    out = set()
    for w in _WORD.findall(normalize(text)):
        for p in _AR_PREFIXES:
            if w.startswith(p) and len(w) - len(p) >= 3:
                w = w[len(p):]
                break
        if len(w) >= 2 and w not in _STOP:
            out.add(w)
    return out


@dataclass
class Hit:
    section_id: str
    score: float


class Retriever:
    def __init__(self, book: PolicyBook, model_name: str):
        from sentence_transformers import SentenceTransformer

        self.book = book
        self.model = SentenceTransformer(model_name)
        lines, owners = [], []
        for s in book.sections:
            for lang in ("ar", "en"):
                lines.append(s.title(lang))
                owners.append(s.id)
                for line in s.text(lang).splitlines():
                    line = line.strip("- ").strip()
                    if line:
                        lines.append(f"{s.title(lang)}: {line}")
                        owners.append(s.id)
        self.owners = np.array(owners)
        self.vectors = self.model.encode(lines, normalize_embeddings=True, batch_size=64)
        self.words = {s.id: _stems(f"{s.title_ar} {s.title_en} {s.ar} {s.en}") for s in book.sections}

    def search(self, question: str, k: int) -> list[Hit]:
        q = self.model.encode([question], normalize_embeddings=True)[0]
        sims = self.vectors @ q
        q_words = _stems(question)
        hits = []
        for sid in self.book.ids:
            dense = float(sims[self.owners == sid].max())
            lexical = len(q_words & self.words[sid]) / (len(q_words) or 1)
            hits.append(Hit(sid, dense + 0.25 * lexical))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]


@lru_cache(maxsize=2)
def get_retriever(book: PolicyBook, model_name: str) -> Retriever:
    return Retriever(book, model_name)
