#!/usr/bin/env python3
"""
generate_data_json.py
Creates training/data.json snapshot for the public GitHub Pages site.
Run daily before sync-to-github.mjs
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

import sqlite3
from datetime import datetime, date, timedelta
from glob import glob

DB_PATH      = os.path.join(os.path.dirname(__file__), "training.db")
TRAINING_DIR = os.path.dirname(__file__)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_week_stats():
    conn = get_db()
    cur = conn.cursor()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    today    = date.today().isoformat()
    cur.execute("""
        SELECT COUNT(*) as n, SUM(distance_m)/1000 as km, SUM(moving_time_s)/3600 as hrs
        FROM activities WHERE date >= ? AND date <= ?
    """, (week_ago, today))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else {"n": 0, "km": 0, "hrs": 0}

def get_this_week_plan():
    files = sorted(glob(os.path.join(TRAINING_DIR, "week_*.json")))
    if not files:
        return None
    with open(files[-1]) as f:
        return json.load(f)

def get_status():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM training_blocks WHERE status = 'active' LIMIT 1")
    row = cur.fetchone()
    block = dict(row) if row else None
    cur.execute("SELECT * FROM goals WHERE status = 'upcoming' ORDER BY date LIMIT 5")
    goals = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT * FROM athlete WHERE id = 22865516")
    row = cur.fetchone()
    ath = dict(row) if row else {}
    conn.close()
    return block, goals, ath

def days_until(date_str):
    return (datetime.strptime(date_str, "%Y-%m-%d").date() - date.today()).days

def main():
    block, goals, ath = get_status()
    week   = get_this_week_plan()
    stats  = get_week_stats()
    today  = date.today()

    # Build goals with computed fields
    goals_out = []
    for g in goals:
        d = days_until(g['date'])
        if d < 0: label = "DONE"; cls = "done"
        elif d == 0: label = "TODAY!"; cls = "small"
        elif d <= 30: label = f"{d}d"; cls = "medium"
        else: label = f"{d}d"; cls = "big"
        goals_out.append({**g, "days_label": label, "days_class": cls, "days_until": d})

    # Block with progress
    block_out = None
    if block:
        start   = datetime.strptime(block['start_date'], "%Y-%m-%d").date()
        end     = datetime.strptime(block['end_date'], "%Y-%m-%d").date()
        total   = (end - start).days
        elapsed = (today - start).days
        pct     = min(100, max(0, int(elapsed / total * 100)))
        block_out = {**block, "progress_pct": pct, "days_remaining": max(0, (end - today).days)}

    # Sessions with completion status from DB
    sessions_out = []
    if week:
        conn = get_db()
        cur  = conn.cursor()
        today_iso = today.isoformat()
        for s in week.get('sessions', []):
            day_str = s.get('date')
            cur.execute("SELECT sport_type FROM activities WHERE date = ?", (day_str,))
            done_types = {r['sport_type'].lower() for r in cur.fetchall()}
            type_map = {
                'ride':'ride','vo2max':'ride','long z2 ride':'ride',
                'strength':'weighttraining','weighttraining':'weighttraining',
                'hill sprints':'run','recovery':''
            }
            stype_key = type_map.get(s.get('type','').lower(), s.get('type','').lower())
            done = stype_key in done_types
            sessions_out.append({**s, "completed": done})
        conn.close()

        # Also attach commute completion
        for s in sessions_out:
            if s.get('commute'):
                s['commute_completed'] = False  # unknown without Strava per-day check

    payload = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "today": today.isoformat(),
        "week": {
            "week_start": week.get('week_start') if week else None,
            "week_number": week.get('week_number') if week else None,
            "theme": week.get('theme') if week else None,
            "sessions": sessions_out,
        } if week else None,
        "goals": goals_out,
        "block": block_out,
        "athlete": ath,
        "week_stats": {
            "sessions": stats.get('n') or 0,
            "km": round(stats.get('km') or 0, 1),
            "hours": round(stats.get('hrs') or 0, 1),
        },
    }

    out_path = os.path.join(TRAINING_DIR, "data.json")
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"✅ data.json written ({len(sessions_out)} sessions, {len(goals_out)} goals)")
    return out_path

if __name__ == "__main__":
    main()
