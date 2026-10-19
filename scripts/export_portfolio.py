"""Export the test results in the shape the portfolio site's examples table reads.

    python scripts/export_portfolio.py ../portfolio-site/data/demos/support-assistant

Writes examples.json (a sample of test messages, the right outcome, and each model's outcome)
and labels.yaml. An outcome is the action, and for answers whether the reply passed the marking.
The sample always includes every message where the models disagree; the full set is in results/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = [("deepseek-flash", "DeepSeek Flash"), ("deepseek-v4-pro", "DeepSeek V4 Pro")]
# A spread across topics, languages and outcomes, picked for reading, not for the score.
SAMPLE = ["t001", "t012", "t023", "t029", "t047", "t056", "t081", "t103", "t123", "t146", "t165",
          "t166", "t184", "t198", "t210", "t214", "t222", "t230", "t234"]
LABELS = """\
answer_ok: { en: "Correct answer", ar: "إجابة صحيحة" }
answer_wrong: { en: "Wrong answer", ar: "إجابة خاطئة" }
handoff: { en: "Hands to a person", ar: "يحوّل لموظف" }
redirect: { en: "Polite redirect", ar: "يعتذر ويوجّه" }
"""


def outcome(row: dict) -> str:
    action = row["result"]["action"]
    if action != "answer":
        return action
    return "answer_ok" if row["grade"]["ok"] else "answer_wrong"


def _expected(row: dict) -> str:
    return "answer_ok" if row["item"]["expect"] == "answer" else row["item"]["expect"]


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    runs = {}
    for mid, _ in MODELS:
        rows = [json.loads(l) for l in (ROOT / "results" / mid / "test.jsonl").read_text(encoding="utf-8").splitlines()]
        runs[mid] = {r["item"]["id"]: r for r in rows}
    first = runs[MODELS[0][0]]
    messages = []
    disagree = {q for q in first if len({outcome(runs[m][q]) == _expected(first[q]) for m, _ in MODELS}) > 1}
    for qid, r in first.items():
        if qid not in disagree and qid not in SAMPLE:
            continue
        expect = r["item"]["expect"]
        messages.append({
            "id": qid,
            "text": r["item"]["q"],
            "expected": "answer_ok" if expect == "answer" else expect,
            "predictions": {mid: outcome(runs[mid][qid]) for mid, _ in MODELS},
        })
    data = {"models": [{"id": mid, "name": {"en": name, "ar": name}} for mid, name in MODELS], "messages": messages}
    (out / "examples.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "labels.yaml").write_text(LABELS, encoding="utf-8")
    print(f"wrote {len(messages)} messages to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
