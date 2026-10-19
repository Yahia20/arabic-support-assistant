"""Mark one result against its test item. Pure code — no model grades another model here."""
from __future__ import annotations

from .text import has_number, normalize


def _fact_present(reply: str, alternatives: list[str]) -> bool:
    text = normalize(reply)
    for alt in alternatives:
        a = str(alt).replace(",", "")
        if a.replace(".", "", 1).isdigit():
            if has_number(reply, float(a)):
                return True
        elif normalize(a) in text:
            return True
    return False


def grade(item: dict, result: dict) -> dict:
    """Returns {"ok": bool, "why": str}. An answer is right only if the action is right, it cites an
    expected section, and every expected fact is in the reply."""
    expect, action = item["expect"], result["action"]
    if action != expect:
        return {"ok": False, "why": f"expected {expect}, got {action}"}
    if expect != "answer":
        return {"ok": True, "why": ""}
    if not set(result["sections"]) & set(item["sections"]):
        return {"ok": False, "why": f"cited {result['sections']}, expected one of {item['sections']}"}
    missing = [g for g in item.get("facts", []) if not _fact_present(result["reply"], g)]
    if missing:
        return {"ok": False, "why": "missing " + " / ".join("|".join(g) for g in missing)}
    return {"ok": True, "why": ""}


def summarise(rows: list[dict]) -> dict:
    """The headline numbers. Each one is defined so a customer-facing reader can check it."""
    def share(n, d):
        return round(n / d, 4) if d else None

    answers_given = [r for r in rows if r["result"]["action"] == "answer"]
    right_answers = [r for r in answers_given if r["grade"]["ok"]]
    should_handoff = [r for r in rows if r["item"]["expect"] == "handoff"]
    answerable = [r for r in rows if r["item"]["expect"] == "answer"]
    redirects = [r for r in rows if r["item"]["expect"] == "redirect"]
    by_lang = {}
    for lang in sorted({r["item"]["lang"] for r in rows}):
        mine = [r for r in rows if r["item"]["lang"] == lang]
        by_lang[lang] = {"n": len(mine), "right": sum(r["grade"]["ok"] for r in mine)}

    return {
        "questions": len(rows),
        "right_action_and_content": sum(r["grade"]["ok"] for r in rows),
        # Of the answers it actually sent to customers, how many were right.
        "answer_precision": share(len(right_answers), len(answers_given)),
        "answers_sent": len(answers_given),
        "wrong_answers_sent": len(answers_given) - len(right_answers),
        # Of the messages a person had to handle, how many it handed over.
        "handoff_recall": share(sum(r["result"]["action"] == "handoff" for r in should_handoff), len(should_handoff)),
        "handoff_cases": len(should_handoff),
        # Of the questions the policy answers, how many it answered correctly by itself.
        "automation": share(sum(r["grade"]["ok"] for r in answerable), len(answerable)),
        "answerable": len(answerable),
        "redirect_accuracy": share(sum(r["grade"]["ok"] for r in redirects), len(redirects)),
        "overruled_by_check": sum(bool(r["result"]["overruled"]) for r in rows),
        "by_language": by_lang,
        "cost_usd": round(sum(r["result"]["cost_usd"] for r in rows), 5),
        "cost_per_1000_usd": round(1000 * sum(r["result"]["cost_usd"] for r in rows) / len(rows), 3) if rows else None,
        "median_seconds": sorted(r["result"]["seconds"] for r in rows)[len(rows) // 2] if rows else None,
    }
