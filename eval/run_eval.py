"""Run the assistant over a question set and mark every reply.

    python eval/run_eval.py --set dev
    python eval/run_eval.py --set test --model deepseek-v4-pro
    python eval/run_eval.py --set dev --env-file ../other-project/.env   # borrow a key without copying it

Writes results/<model>/<set>.jsonl (one line per question) and results/<model>/<set>.summary.json.
Replies are cached, so a re-run only pays for questions it hasn't seen.
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_assistant.assistant import Assistant  # noqa: E402
from support_assistant.config import MODELS, get_settings  # noqa: E402
from support_assistant.grade import grade, summarise  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["dev", "test"], default="dev")
    ap.add_argument("--model", default=None, choices=sorted(MODELS))
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--only", nargs="*", help="run just these question ids")
    args = ap.parse_args()

    settings = get_settings(args.env_file)
    bot = Assistant(settings, args.model)
    items = yaml.safe_load((ROOT / "eval" / f"{args.set}.yaml").read_text(encoding="utf-8"))
    if args.only:
        items = [i for i in items if i["id"] in set(args.only)]

    def one(item):
        res = bot.ask(item["q"]).to_dict()
        return {"item": item, "result": res, "grade": grade(item, res)}

    with ThreadPoolExecutor(args.workers) as pool:
        rows = list(pool.map(one, items))

    out = settings.results_dir / bot.llm.spec.name
    out.mkdir(parents=True, exist_ok=True)
    if not args.only:
        with (out / f"{args.set}.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = summarise(rows) | {"model": bot.llm.spec.name, "set": args.set}
    if not args.only:
        (out / f"{args.set}.summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    for r in rows:
        if not r["grade"]["ok"]:
            res = r["result"]
            print(f"✗ {r['item']['id']} [{r['item']['lang']}] {r['item']['q']}\n"
                  f"    {r['grade']['why']} · model={res['model_action']} {res['overruled']}\n"
                  f"    reply: {res['reply'][:220]}")
    print(json.dumps({k: v for k, v in summary.items() if k != "by_language"}, ensure_ascii=False))
    print(f"total spend so far: ${bot.llm.spent():.4f} of ${settings.max_spend_usd:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
