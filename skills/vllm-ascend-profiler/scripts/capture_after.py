"""Trigger vLLM profiling from a serial, dedicated AISBench streaming run."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import signal
import time
from urllib.request import Request, urlopen


def event(name, **fields):
    print(json.dumps(dict(time=datetime.now(timezone.utc).isoformat(),
                          event=name, **fields)), flush=True)


def complete_lines(stream):
    while True:
        pos = stream.tell()
        line = stream.readline()
        if not line.endswith(b"\n"):
            stream.seek(pos)
            return
        yield line


def formal_results(root):
    ids = set()
    for path in root.glob("**/tmp/tmp_*.jsonl"):
        with path.open("rb") as stream:
            for line in complete_lines(stream):
                row = json.loads(line)
                if row["success"] is not True:
                    raise RuntimeError(f"Failed formal result in {path}: {row['id']}")
                ids.add((row["data_abbr"], row["id"]))
    return ids


def wait_for_window(args):
    if args.results.exists() and any(args.results.iterdir()):
        raise ValueError("Use a new or empty AISBench results directory.")
    wanted = args.warmups + args.after + 1
    deadline = time.monotonic() + args.timeout
    with args.access_log.open("rb") as log:
        log.seek(0, 2)
        accepted = 0
        event("ready", results=str(args.results))
        while time.monotonic() < deadline:
            ids = formal_results(args.results)
            accepted += sum(b'"POST /v1/chat/completions HTTP/1.1" 200' in line
                            for line in complete_lines(log))
            if len(ids) > args.after or accepted > wanted:
                raise RuntimeError("Target window missed or extra traffic observed.")
            if len(ids) == args.after and accepted == wanted:
                event("trigger", formal_ids=sorted(ids), accepted_streams=accepted)
                return
            time.sleep(0.1)
    raise TimeoutError("Timed out waiting for formal completions and the next stream.")


def post(root, endpoint):
    request = Request(root.rstrip("/") + "/" + endpoint, data=b"", method="POST")
    with urlopen(request, timeout=600) as response:
        if response.status != 200:
            raise RuntimeError(f"{endpoint}: HTTP {response.status}")
        event(endpoint, status=response.status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--access-log", type=Path, required=True)
    parser.add_argument("--api-root", required=True)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--after", type=int, default=8)
    parser.add_argument("--seconds", type=float, default=1)
    parser.add_argument("--timeout", type=int, default=1800, help="Trigger wait in seconds")
    args = parser.parse_args()
    if args.warmups < 0 or args.after < 1 or args.timeout < 1:
        parser.error("Require warmups >= 0, after >= 1 and timeout >= 1.")
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error("Duration must be positive and finite.")
    wait_for_window(args)
    post(args.api_root, "start_profile")
    started = time.monotonic()
    try:
        time.sleep(args.seconds)
    finally:
        event("sending_stop", seconds_since_start_response=time.monotonic() - started)
        post(args.api_root, "stop_profile")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    main()
