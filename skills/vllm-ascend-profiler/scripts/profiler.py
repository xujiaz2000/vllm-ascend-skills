"""Parse one TorchNPU capture and verify the captured worker ranks."""
import argparse
import csv
import json
from pathlib import Path


def rank_directories(root, expected):
    found = {}
    for directory in sorted(root.glob("*_ascend_pt")):
        metadata = list(directory.glob("profiler_info*.json"))
        if len(metadata) != 1:
            raise ValueError(f"Expected one profiler_info file in {directory}")
        with metadata[0].open(encoding="utf-8") as stream:
            rank = json.load(stream).get("rank_id")
        # A standalone, non-distributed worker can omit its global rank.
        if rank in (None, -1) and expected == {0}:
            rank = 0
        if rank in found:
            raise ValueError(f"Multiple captures for rank {rank} in {root}")
        found[rank] = directory
    if found.keys() != expected:
        raise ValueError(f"Expected ranks {sorted(expected)}, found {list(found)} in {root}")
    return found


def verify(directory):
    output = directory / "ASCEND_PROFILER_OUTPUT"
    trace = output / "trace_view.json"
    with trace.open(encoding="utf-8") as stream:
        data = json.load(stream)
    events = data.get("traceEvents") if isinstance(data, dict) else data
    if not isinstance(events, list) or not events:
        raise ValueError(f"No trace events in {trace}")
    with (output / "kernel_details.csv").open(newline="", encoding="utf-8-sig") as stream:
        kernels = sum(bool(row.get("Name", "").strip()) for row in csv.DictReader(stream))
    if not kernels:
        raise ValueError(f"No named NPU kernels in {output / 'kernel_details.csv'}")
    return trace, len(events), kernels


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Direct parent of this run's *_ascend_pt folders")
    parser.add_argument("--ranks", nargs="+", type=int, required=True, help="Expected global rank IDs")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    dirs = rank_directories(root, set(args.ranks))
    from torch_npu.profiler.profiler import analyse
    analyse(str(root))
    for rank, directory in sorted(dirs.items()):
        trace, events, kernels = verify(directory)
        print(f"rank {rank}: {events} events, {kernels} kernels, {trace}", flush=True)
    print(f"Verified {len(dirs)} rank(s) in {root}")


if __name__ == "__main__":
    main()
