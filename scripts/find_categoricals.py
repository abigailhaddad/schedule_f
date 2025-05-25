#!/usr/bin/env python3
"""
Identify low-cardinality string fields in a JSON array of objects.

Usage:
    python find_categoricals.py <json_file> [max_unique=10]
"""

import json, sys
from pathlib import Path
from collections import defaultdict, Counter

def load_records(path):
    with Path(path).open() as f:
        data = json.load(f)
    # Normalise to a list
    return data if isinstance(data, list) else [data]

def collect_uniques(records):
    uniques = defaultdict(set)
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, str):
                uniques[k].add(v.strip())
    return {k: vals for k, vals in uniques.items()}

def main():
    if len(sys.argv) < 2:
        sys.exit("Need JSON file path (and optional max_unique).")
    json_path = sys.argv[1]
    max_unique = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    records = load_records(json_path)
    uniques  = collect_uniques(records)

    print(f"Fields with ≤ {max_unique} unique string values:\n")
    for key, vals in sorted(uniques.items(), key=lambda kv: len(kv[1])):
        if len(vals) <= max_unique:
            joined = ", ".join(sorted(vals))
            print(f"{key:20} ({len(vals)} values) -> {joined}")

if __name__ == "__main__":
    main()
