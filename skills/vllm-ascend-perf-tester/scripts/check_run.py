"""Check one single-turn AISBench steady-state run against its request details."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def read_counts(details_path):
    ids = set()
    inputs, outputs = Counter(), Counter()
    failed = 0
    with details_path.open(encoding="utf-8") as details:
        for line_num, line in enumerate(details, 1):
            row = json.loads(line)
            request_id = row["id"]
            if request_id is None or request_id in ids:
                raise ValueError(f"Missing or duplicate request ID on line {line_num}")
            ids.add(request_id)
            success = row["success"]
            if not isinstance(success, bool):
                raise ValueError(f"Invalid success flag on line {line_num}")
            if success:
                for key, counts in (("input_tokens", inputs), ("output_tokens", outputs)):
                    n = row[key]
                    if type(n) is not int or n < 0:
                        raise ValueError(f"Invalid {key} on line {line_num}")
                    counts[n] += 1
            else:
                failed += 1
    return len(ids), failed, inputs, outputs


def check_run(report_path, expected):
    report = json.loads(report_path.read_text(encoding="utf-8"))
    details = report_path.with_name(f"{report_path.stem}_details.jsonl")
    total, failed, inputs, outputs = read_counts(details)
    print(f"Full run: {total} requests, {total - failed} succeeded, {failed} failed")
    for label, lengths in (("Input", inputs), ("Output", outputs)):
        if lengths:
            print(f"{label} tokens per successful request: {min(lengths)}..{max(lengths)}")

    stable = report["Total Requests"]["stable"]
    passed = report["Success Requests"]["stable"]
    errors = report["Failed Requests"]["stable"]
    peak = report["Max Concurrency"]["stable"]
    print(f"Stable stage: {stable} requests, {passed} succeeded, {errors} failed, peak concurrency {peak}")
    if total != expected or failed:
        raise ValueError(f"Expected {expected} successful requests in the full run")
    if not (0 < stable <= total and passed == stable and errors == 0 and 0 < peak <= total):
        raise ValueError("Steady-state counters are inconsistent with the full run")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Native per-dataset performance JSON")
    parser.add_argument("--requests", type=int, required=True, help="Expected full-run request count")
    args = parser.parse_args()
    try:
        check_run(args.report, args.requests)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        sys.exit(f"Could not verify run: {exc}")
