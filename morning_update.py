#!/usr/bin/env python3
"""
morning_update.py
Run each morning (Mon-Fri) to:
  1. Regenerate training dashboard HTML
  2. Sync stocks data to GitHub (so theilves is always fresh)
  3. Check if a new week plan is needed and report
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, date, timedelta
from glob import glob
import subprocess

TRAINING_DIR = os.path.dirname(__file__)

def is_new_week_needed():
    """Check if today's week_*.json is about to end (it's the last day = Sunday)"""
    files = sorted(glob(os.path.join(TRAINING_DIR, "week_*.json")))
    if not files:
        return False, "No week file found!"
    latest = files[-1]
    import json
    with open(latest) as f:
        week = json.load(f)
    week_start = datetime.strptime(week["week_start"], "%Y-%m-%d").date()
    week_end   = week_start + timedelta(days=6)
    today = date.today()
    days_left = (week_end - today).days
    return days_left == 0, f"Today is the last day of the week! Week of {week['week_start']} ends today. New week plan needed."

def main():
    print(f"[{datetime.now().isoformat()}] Morning training update")

    # 1. Regenerate training dashboard
    print("→ Regenerating training dashboard...")
    result = subprocess.run(
        ["python3", "generate_dashboard.py"],
        cwd=TRAINING_DIR,
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  ✅ {result.stdout.strip()}")
    else:
        print(f"  ❌ {result.stderr}")

    # 2. Sync stocks to GitHub
    print("→ Syncing stocks to GitHub...")
    result2 = subprocess.run(
        ["node", "sync-to-github.mjs"],
        cwd="/home/timilv/.openclaw/workspace/stocks-dashboard",
        capture_output=True, text=True
    )
    if result2.returncode == 0:
        print(f"  ✅ Stocks synced")
    else:
        print(f"  ⚠️  Stocks sync: {result2.stderr.strip()}")

    # 3. Check week rollover
    needs_new, msg = is_new_week_needed()
    if needs_new:
        print(f"⚠️  WEEK PLAN: {msg}")
        print("   → Creating next week's plan...")
    else:
        print(f"  ✅ Week plan: {msg}")

    print(f"[{datetime.now().isoformat()}] Morning update done")

if __name__ == "__main__":
    main()
