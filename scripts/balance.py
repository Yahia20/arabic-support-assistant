"""Print the DeepSeek account balance (the key never leaves this process).

    python scripts/balance.py --env-file ../other-project/.env
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from support_assistant.config import get_settings  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--env-file", default=None)
key = get_settings(ap.parse_args().env_file).key_for("deepseek")
req = urllib.request.Request("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {key}"})
info = json.load(urllib.request.urlopen(req, timeout=30))
for b in info.get("balance_infos", []):
    print(f"{b['currency']} {b['total_balance']}")
