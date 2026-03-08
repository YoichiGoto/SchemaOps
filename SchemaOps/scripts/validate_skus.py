#!/usr/bin/env python3
"""
Validate synthetic SKUs against Canonical schema and optional determination rules.
TRAM Production: determination-based listable/restrictions check when rules available.
"""
import csv
import json
import sys
from pathlib import Path

def load_rows(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def load_rules(rules_dir: Path) -> dict:
    """Load determination rules from rules/{mp}/{category}_v*.json."""
    rules = {}
    if not rules_dir.exists():
        return rules
    for mp_dir in rules_dir.iterdir():
        if mp_dir.is_dir():
            for rule_file in mp_dir.glob("*_v*.json"):
                try:
                    with open(rule_file, "r", encoding="utf-8") as f:
                        r = json.load(f)
                    key = (r.get("marketplace", ""), r.get("category", ""))
                    rules[key] = r
                except Exception:
                    pass
    return rules

def check_determination(sku: dict, rules: dict) -> list:
    """Check SKU against determination rules (listable, restrictions). Returns fail reasons."""
    fails = []
    mp = sku.get("marketplace") or sku.get("mp")
    cat = sku.get("category") or sku.get("product_category")
    if not mp or not cat:
        return fails
    rule = rules.get((mp, cat)) or rules.get((mp, "default"))
    if not rule:
        return fails
    if not rule.get("listable", True):
        fails.append((sku.get("SKU", ""), "determination", "category not listable on this marketplace"))
    for restr in rule.get("restrictions", []):
        if restr and isinstance(restr, str):
            fails.append((sku.get("SKU", ""), "restriction", restr))
    return fails

def allowed_values_map(canonical_rows):
    m = {}
    for r in canonical_rows:
        aid = r['attributeId']
        vals = (r.get('allowedValues') or '').strip()
        m[aid] = [v.strip() for v in vals.split(';') if v.strip()]
    return m

def main():
    root = Path(__file__).resolve().parents[1]
    rules_dir = None
    if "--rules" in sys.argv:
        idx = sys.argv.index("--rules")
        rules_dir = Path(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else root / "30_Archive" / "rules"

    canonical = load_rows(root/'02_Templates'/'Canonical_Schema.csv')
    allowed = allowed_values_map(canonical)
    rules = load_rules(rules_dir) if rules_dir else {}

    data = load_rows(root/'20_QA'/'synthetic_skus.csv')

    total = 0
    pass_count = 0
    fails = []

    for r in data:
        total += 1
        ok = True
        # required checks
        for req in ['title','brand','gtin','image_link']:
            if not r.get(req):
                ok = False
                fails.append((r['SKU'], req, 'required missing'))
        # length checks for title
        if len(r.get('title', '')) > 150:
            ok = False
            fails.append((r['SKU'], 'title', 'length >150'))
        # allowed values for size
        if allowed.get('size'):
            if r.get('size') not in allowed['size']:
                ok = False
                fails.append((r['SKU'], 'size', f"invalid value: {r.get('size')}"))
        # simple GTIN length check
        if len(r.get('gtin', '')) < 8:
            ok = False
            fails.append((r['SKU'], 'gtin', 'too short'))
        # determination-based check (when rules available)
        if rules:
            det_fails = check_determination(r, rules)
            for sku, attr, reason in det_fails:
                ok = False
                fails.append((sku, attr, reason))

        if ok:
            pass_count += 1

    pct = pass_count / total * 100 if total else 0
    print(f'Total: {total}, PASS: {pass_count}, PASS%: {pct:.1f}%')
    if rules:
        print(f'  (determination rules: {len(rules)} loaded)')
    if fails:
        print('\nSample fails (up to 10):')
        for sku, attr, reason in fails[:10]:
            print(f'- {sku} [{attr}]: {reason}')

if __name__ == '__main__':
    main()






