#!/usr/bin/env python3
"""
FMCG SupplyChainIQ — Performance Benchmarking

Measures execution time and throughput across increasing dataset sizes.
Records actual measurements to CSV/JSON — never fabricates numbers.

Usage (remote):
    python scripts/pipeline/benchmark.py
    python scripts/pipeline/benchmark.py --sizes small,medium
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SIZES = ["small", "medium", "large", "xlarge"]
BENCHMARK_STAGES = [
    ("data_generation", "python scripts/generate_data.py --size {size} --output data/generated"),
    ("data_validation", "python scripts/validate_data.py --input data/generated"),
]


def run_benchmark(sizes: list[str], output_dir: str = "artifacts/metrics") -> list[dict]:
    """Run benchmarks for each dataset size and collect measurements."""
    results: list[dict] = []
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for size in sizes:
        print(f"\n{'='*50}")
        print(f"  Benchmarking size: {size}")
        print(f"{'='*50}")

        run_result: dict = {
            "size": size,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        for stage_name, command_template in BENCHMARK_STAGES:
            command = command_template.format(size=size)
            print(f"\n  [{stage_name}] Running: {command}")

            start = time.time()
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=3600,
            )
            duration = time.time() - start

            run_result[f"{stage_name}_duration_seconds"] = round(duration, 2)
            run_result[f"{stage_name}_exit_code"] = proc.returncode

            if proc.returncode == 0:
                print(f"  [{stage_name}] Completed in {duration:.2f}s")
            else:
                print(f"  [{stage_name}] FAILED (exit {proc.returncode})")
                print(f"  stderr: {proc.stderr[-200:]}")
                run_result[f"{stage_name}_error"] = proc.stderr[-200:]

            # Parse record count from manifest
            manifest_path = Path("data/generated/_manifest.json")
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest = json.load(f)
                run_result["total_records"] = sum(
                    manifest.get("counts", {}).values()
                )
                run_result["transactions"] = manifest.get("counts", {}).get(
                    "sales_transactions", 0
                )

        # Calculate throughput
        if run_result.get("total_records") and run_result.get("data_generation_duration_seconds"):
            throughput = run_result["total_records"] / run_result["data_generation_duration_seconds"]
            run_result["generation_throughput_rps"] = round(throughput, 1)

        results.append(run_result)

    # Save results
    csv_path = out_path / "benchmark_results.csv"
    if results:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"\nResults saved to {csv_path}")

    json_path = out_path / "benchmark_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {json_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="FMCG SupplyChainIQ Performance Benchmark")
    parser.add_argument("--sizes", default="small,medium,large,xlarge",
                        help="Comma-separated dataset sizes to benchmark")
    parser.add_argument("--output", default="artifacts/metrics",
                        help="Output directory for results")
    args = parser.parse_args()

    sizes = [s.strip() for s in args.sizes.split(",")]
    results = run_benchmark(sizes, args.output)

    print(f"\n{'='*50}")
    print("  Benchmark Summary")
    print(f"{'='*50}")
    for r in results:
        print(f"  {r['size']:8s}  records={r.get('total_records', 0):>10,}  "
              f"gen={r.get('data_generation_duration_seconds', 0):>8.2f}s  "
              f"validate={r.get('data_validation_duration_seconds', 0):>8.2f}s")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
