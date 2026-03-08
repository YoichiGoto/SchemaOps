#!/usr/bin/env python3
"""
Export Canonical, Mapping, and approved determinations to normalized JSON.
TRAM Production: determinations exported as versioned rules with effectiveDate.
"""
import csv
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

def load_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def export_canonical(canonical_rows):
    attrs = []
    for r in canonical_rows:
        attrs.append({
            "canonicalAttributeId": r.get("attributeId"),
            "labels": {"ja": r.get("attributeName_ja"), "en": r.get("attributeName_en")},
            "definition": r.get("definition"),
            "dataType": r.get("dataType"),
            "unit": r.get("unitStandard") or None,
            "allowedValues": (r.get("allowedValues") or None),
            "required": (r.get("requiredFlag","false").lower() == "true"),
            "conditionalRule": r.get("conditionalRule") or None,
            "examples": r.get("examples") or None,
            "categoryPath": r.get("categoryPath") or None,
            "notes": r.get("notes") or None,
            "version": r.get("version") or None,
        })
    return {"attributes": attrs, "exportedAt": datetime.now(timezone.utc).isoformat()+"Z"}

def export_mapping(mapping_rows):
    out = {}
    for r in mapping_rows:
        mp = r.get("mpName") or "UNKNOWN"
        out.setdefault(mp, [])
        out[mp].append({
            "category": r.get("categoryIdOrPath"),
            "mpAttributeName": r.get("mpAttributeName"),
            "canonicalAttributeId": r.get("canonicalAttributeId"),
            "transformRule": r.get("transformRule") or None,
            "regexRule": r.get("regexRule") or None,
            "unitConversion": r.get("unitConversion") or None,
            "required": r.get("required") or None,
            "constraints": {
                "min": r.get("min") or None,
                "max": r.get("max") or None,
                "length": r.get("length") or None,
                "valueList": r.get("valueList") or None,
            },
            "example": {"in": r.get("exampleIn"), "out": r.get("exampleOut")},
            "approvalNotes": r.get("approvalNotes") or None,
            "lastVerifiedAt": r.get("lastVerifiedAt") or None,
            "sourceURL": r.get("sourceURL") or None,
        })
    return {"mappings": out, "exportedAt": datetime.now(timezone.utc).isoformat()+"Z"}


def export_determination_rules(determinations: list, out_dir: Path, date_str: str = None):
    """
    Export approved determinations to rules/{mp}/{category}/v{date}.json.
    Each rule includes effectiveDate for scheduling.
    """
    date_str = date_str or datetime.now(timezone.utc).strftime("%Y%m%d")
    rules_dir = out_dir / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    for d in determinations:
        mp = d.get("marketplace", "unknown")
        cat = d.get("category", "default")
        mp_dir = rules_dir / mp.replace(" ", "_")
        mp_dir.mkdir(parents=True, exist_ok=True)
        rule_path = mp_dir / f"{cat.replace('/', '_')}_v{date_str}.json"
        rule = {
            "marketplace": mp,
            "category": cat,
            "listable": d.get("listable", True),
            "restrictions": d.get("restrictions", []),
            "displayRequirements": d.get("displayRequirements", []),
            "effectiveDate": d.get("effectiveDate", date_str),
            "version": date_str,
            "exportedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        with open(rule_path, "w", encoding="utf-8") as f:
            json.dump(rule, f, ensure_ascii=False, indent=2)
    return len(determinations)


def main():
    if len(sys.argv) < 3:
        print("Usage: export_json.py --input-dir <dir> --out <outdir> [--determinations <path>]")
        sys.exit(1)
    args = sys.argv
    in_dir = Path(args[args.index("--input-dir")+1])
    out_dir = Path(args[args.index("--out")+1])
    out_dir.mkdir(parents=True, exist_ok=True)

    canonical = load_csv(in_dir/"Canonical_Schema.csv")
    mapping = load_csv(in_dir/"MP_Mapping.csv")

    with open(out_dir/"schema.normalized.json", "w", encoding="utf-8") as f:
        json.dump(export_canonical(canonical), f, ensure_ascii=False, indent=2)

    with open(out_dir/"mapping.normalized.json", "w", encoding="utf-8") as f:
        json.dump(export_mapping(mapping), f, ensure_ascii=False, indent=2)

    if "--determinations" in args:
        det_path = Path(args[args.index("--determinations")+1])
        if det_path.exists():
            with open(det_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            determinations = data if isinstance(data, list) else data.get("determinations", [])
            n = export_determination_rules(determinations, out_dir)
            print(f"Exported {n} determination rules to {out_dir}/rules/")

if __name__ == "__main__":
    main()






