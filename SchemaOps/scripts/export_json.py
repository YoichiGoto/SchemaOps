#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path
from datetime import datetime

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
    return {"attributes": attrs, "exportedAt": datetime.utcnow().isoformat()+"Z"}

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
    return {"mappings": out, "exportedAt": datetime.utcnow().isoformat()+"Z"}

def main():
    if len(sys.argv) < 3:
        print("Usage: export_json.py --input-dir <dir> --out <outdir>")
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

if __name__ == "__main__":
    main()






