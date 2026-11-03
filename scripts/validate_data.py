#!/usr/bin/env python3
"""
FMCG SupplyChainIQ — Data Validation Script

Validates generated JSONL files against their JSON schemas and reports
data quality statistics. Does NOT require Spark or MongoDB.

Usage:
    python scripts/validate_data.py --input data/generated
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fmcg.validation.schema_validator import validate_records


DATASETS = [
    "products",
    "locations",
    "suppliers",
    "batches",
    "sales_transactions",
    "inventory_snapshots",
    "stock_movements",
    "shipments",
]


def load_jsonl(filepath: Path) -> list[dict]:
    """Load JSONL file into a list of dicts."""
    records: list[dict] = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def validate_dataset(input_dir: Path, dataset_name: str) -> dict:
    """Validate a single dataset file."""
    filepath = input_dir / f"{dataset_name}.jsonl"
    if not filepath.exists():
        return {"dataset": dataset_name, "status": "file_not_found", "path": str(filepath)}

    records = load_jsonl(filepath)
    result = validate_records(dataset_name, records)

    return {
        "dataset": dataset_name,
        "total": result["total"],
        "valid": result["valid_count"],
        "invalid": result["invalid_count"],
        "duplicates": result["duplicate_count"],
        "valid_pct": round(result["valid_count"] / max(1, result["total"]) * 100, 2),
        "rejected_samples": [
            {"error": r["error"][:200]}
            for r in result["rejected_records"][:3]
        ] if result["rejected_records"] else [],
    }


def main():
    parser = argparse.ArgumentParser(description="FMCG Data Validator")
    parser.add_argument("--input", default="data/generated",
                        help="Input directory with JSONL files")
    args = parser.parse_args()

    input_dir = Path(args.input)
    print(f"Validating data in: {input_dir}\n")

    all_valid = True
    total_records = 0
    total_valid = 0
    total_invalid = 0

    for ds in DATASETS:
        result = validate_dataset(input_dir, ds)

        if result.get("status") == "file_not_found":
            print(f"  {ds:25s}  [SKIP] file not found")
            continue

        total = result["total"]
        valid = result["valid"]
        invalid = result["invalid"]
        dups = result["duplicates"]

        total_records += total
        total_valid += valid
        total_invalid += invalid

        status = "PASS" if invalid == 0 else "WARN"
        if invalid > 0:
            all_valid = False

        print(f"  {ds:25s}  total={total:>8,}  valid={valid:>8,}  invalid={invalid:>5}  dups={dups:>3}  [{status}]")

        if result["rejected_samples"]:
            for sample in result["rejected_samples"]:
                print(f"    └─ {sample['error']}")

    print(f"\n  {'TOTAL':25s}  total={total_records:>8,}  valid={total_valid:>8,}  invalid={total_invalid:>5}")

    # Validate invalid records file
    invalid_path = input_dir / "invalid_records.jsonl"
    if invalid_path.exists():
        invalid_records = load_jsonl(invalid_path)
        print(f"\n  invalid_records.jsonl: {len(invalid_records)} deliberately invalid test records (expected)")

    print(f"\nValidation {'PASSED' if all_valid else 'COMPLETED WITH WARNINGS'}")
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
