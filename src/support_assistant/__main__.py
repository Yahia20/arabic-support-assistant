"""Ask the assistant from the command line.

    python -m support_assistant "ابي اغير موعد رحلتي وتذكرتي توفير، كم الرسوم؟"
    python -m support_assistant --model deepseek-v4-pro "Can I bring my dog?"
"""
from __future__ import annotations

import argparse
import sys

from .assistant import Assistant
from .config import MODELS, get_settings


def main() -> int:
    ap = argparse.ArgumentParser(prog="support_assistant")
    ap.add_argument("question")
    ap.add_argument("--model", default=None, choices=sorted(MODELS))
    ap.add_argument("--env-file", default=None)
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    r = Assistant(get_settings(args.env_file), args.model).ask(args.question)
    print(f"{r.action.upper()}  {', '.join(r.sections) or r.reason}")
    print(r.reply)
    if r.action == "handoff" and r.summary_for_agent:
        print(f"\nfor the agent: {r.summary_for_agent}")
    if r.overruled:
        print(f"(the model's answer was withheld: {r.overruled})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
