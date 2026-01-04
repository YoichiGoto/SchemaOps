#!/usr/bin/env python3
import csv
import sys
from pathlib import Path

def load_rows(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def allowed_values_map(canonical_rows):
    m = {}
    for r in canonical_rows:
        aid = r['attributeId']
        vals = (r.get('allowedValues') or '').strip()
        m[aid] = [v.strip() for v in vals.split(';') if v.strip()]
    return m

def main():
    root = Path(__file__).resolve().parents[1]
    canonical = load_rows(root/'02_Templates'/'Canonical_Schema.csv')
    allowed = allowed_values_map(canonical)

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
        if len(r['title']) > 150:
            ok = False
            fails.append((r['SKU'], 'title', 'length >150'))
        # allowed values for size
        if allowed.get('size'):
            if r['size'] not in allowed['size']:
                ok = False
                fails.append((r['SKU'], 'size', f"invalid value: {r['size']}"))
        # simple GTIN length check
        if len(r['gtin']) < 8:
            ok = False
            fails.append((r['SKU'], 'gtin', 'too short'))

        if ok:
            pass_count += 1

    print(f'Total: {total}, PASS: {pass_count}, PASS%: {pass_count/total*100:.1f}%')
    if fails:
        print('\nSample fails (up to 10):')
        for sku, attr, reason in fails[:10]:
            print(f'- {sku} [{attr}]: {reason}')

if __name__ == '__main__':
    main()






