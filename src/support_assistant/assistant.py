"""Answer one customer message: retrieve → ask the model → check the answer with code.

The model proposes; code decides. An answer only reaches the customer if
  1. it cites at least one policy section that was actually shown to the model, and
  2. every number in it appears in the cited sections or the question, or follows from them by
     one step of arithmetic (e.g. a per-passenger fee times the passengers in the question).
Otherwise the message goes to a person. A made-up fee or deadline cannot get through.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

from . import prompts
from .config import MODELS, Settings
from .llm import LLM
from .policies import PolicyBook, load_policies
from .retrieval import get_retriever
from .text import derivable, numbers, question_numbers

ACTIONS = {"answer", "handoff", "redirect"}
_ARABIC = re.compile(r"[؀-ۿ]")


def language(text: str) -> str:
    return "ar" if _ARABIC.search(text) else "en"


def check_answer(book: PolicyBook, question: str, reply: str, cited: list[str], shown: list[str]) -> str:
    """Return why an answer must not be sent, or "" if it may."""
    if not reply:
        return "empty reply"
    cited_ok = [s for s in cited if s in shown and book.get(s)]
    if not cited_ok:
        return "cites no section that was shown"
    return stray_numbers(book, question, reply, cited_ok)


def stray_numbers(book: PolicyBook, question: str, reply: str, section_ids: list[str]) -> str:
    """Describe the numbers in `reply` that neither the sections nor the question account for."""
    source = " ".join(book.get(s).ar + " " + book.get(s).en for s in section_ids if book.get(s))
    allowed = derivable(numbers(source), question_numbers(question))
    stray = sorted(n for n in numbers(reply) if n not in allowed)
    return "numbers not in the policy: " + ", ".join(f"{n:g}" for n in stray) if stray else ""


@dataclass
class Result:
    question: str
    action: str                      # answer | handoff | redirect — what the customer gets
    reply: str
    sections: list[str]
    reason: str = ""
    summary_for_agent: str = ""
    model_action: str = ""           # what the model proposed, before the checks
    overruled: str = ""              # why code turned an answer into a handoff, if it did
    reply_replaced: str = ""         # why code replaced a hand-over/redirect reply's wording, if it did
    retrieved: list[str] = field(default_factory=list)
    calls: int = 0
    cost_usd: float = 0.0
    seconds: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class Assistant:
    def __init__(self, settings: Settings, model: str | None = None):
        self.settings = settings
        self.book: PolicyBook = load_policies(settings.policies_file)
        self.retriever = get_retriever(self.book, settings.embed_model)
        self.llm = LLM(MODELS[model or settings.model], settings)
        index = "\n".join(f"- {s.id}: {s.title_en} / {s.title_ar}" for s in self.book.sections)
        self.system = prompts.SYSTEM.format(company_en=self.book.company_en, company_ar=self.book.company_ar, index=index)

    # ------------------------------------------------------------------ public

    def ask(self, question: str) -> Result:
        lang = language(question)
        shown = [h.section_id for h in self.retriever.search(question, self.settings.top_k)]
        res = Result(question=question, action="handoff", reply="", sections=[], retrieved=list(shown))

        out = self._call(question, shown, lang, res)
        if out.get("action") == "need_section":
            extra = [s for s in out.get("sections", []) if self.book.get(s) and s not in shown]
            if extra:
                shown += extra
                res.retrieved = list(shown)
                out = self._call(question, shown, lang, res)

        res.model_action = str(out.get("action", ""))
        res.reply = str(out.get("reply", "")).strip()
        res.sections = [s for s in out.get("sections", []) if isinstance(s, str)]
        res.reason = str(out.get("reason", "") or "")
        res.summary_for_agent = str(out.get("summary_for_agent", "") or "")
        res.action = res.model_action if res.model_action in ACTIONS else "handoff"

        if res.action == "answer":
            problem = self.check(question, res.reply, res.sections, shown)
            if problem:
                res.action, res.overruled, res.reason = "handoff", problem, "unverified"
                res.summary_for_agent = f"Bot answer withheld by the check ({problem}). Customer asked: {question}"
                res.reply = prompts.HANDOFF_FALLBACK[lang]
        if res.action != "answer" and res.reply and not res.overruled:
            # Hand-over and redirect replies get the same number check: a phone number or a fee the
            # policy doesn't contain is replaced with the standard hand-over text.
            stray = stray_numbers(self.book, question, res.reply, shown)
            if stray:
                res.reply_replaced, res.reply = stray, prompts.HANDOFF_FALLBACK[lang]
        if res.action == "handoff" and not res.reply:
            res.reply = prompts.HANDOFF_FALLBACK[lang]
        return res

    def check(self, question: str, reply: str, cited: list[str], shown: list[str]) -> str:
        return check_answer(self.book, question, reply, cited, shown)

    # ------------------------------------------------------------------ internals

    def _call(self, question: str, shown: list[str], lang: str, res: Result) -> dict:
        blocks = []
        for sid in shown:
            s = self.book.get(sid)
            blocks.append(f"[{s.id}] {s.title(lang)}\n{s.text(lang)}")
        messages = [
            {"role": "system", "content": self.system},
            {"role": "user", "content": prompts.USER.format(
                sections="\n\n".join(blocks), question=question, reply_language=prompts.LANGUAGE_NAME[lang])},
        ]
        reply = self.llm.chat(messages)
        res.calls += 1
        res.cost_usd += reply.cost_usd
        res.seconds += reply.seconds
        try:
            out = json.loads(reply.text)
            return out if isinstance(out, dict) else {}
        except json.JSONDecodeError:
            return {}
