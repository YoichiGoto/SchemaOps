#!/usr/bin/env python3
import csv
import sys
from datetime import date

def main():
    if len(sys.argv) < 2:
        print("Usage: generate_release_notes.py Change_Log.csv", file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    print(f"# Release Notes - {date.today().isoformat()}\n")
    buckets = {"critical": [], "major": [], "minor": [], "other": []}
    for r in rows:
        sev = (r.get("severity") or "other").lower()
        if sev not in buckets:
            sev = "other"
        buckets[sev].append(r)
    for sev, items in buckets.items():
        if not items:
            continue
        print(f"## {sev.title()} Changes\n")
        for r in items:
            print(f"- [{r.get('target')}] {r.get('name')}: {r.get('changeSummary')} (ETA: {r.get('ETA')}, Owner: {r.get('owner')})\n  - Impact: {r.get('impactedAttributes')}\n  - Source: {r.get('sourceURL')}\n")

if __name__ == '__main__':
    main()






