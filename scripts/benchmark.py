"""Generate a large CSV and measure how fast DataForge validates it.

Run it with:

    python scripts/benchmark.py

The dataset is generated from a fixed random seed, so the same command
produces identical input on any machine and numbers can be compared
across runs. Roughly one row in ten is invalid on purpose, so the
validators aren't measured only on the happy path.

The timing covers loading plus validation — the whole pipeline the CLI
runs, minus printing. That's the number that matters for "how long will
this take on my file", and it's honest about I/O being part of the cost
rather than timing validation alone to get a prettier figure.
"""

import argparse
import random
import tempfile
import time
from pathlib import Path

from dataforge.loaders import load_csv
from dataforge.report import build_report
from dataforge.rules import load_rules

SEED = 20260101
RULES = """
rules:
  - field: id
    type: integer
    required: true
  - field: name
    type: string
    required: true
  - field: age
    type: integer
    min: 0
    max: 120
  - field: status
    allowed: [active, inactive]
  - field: email
    pattern: "^[^@]+@[^@]+$"
"""


def write_dataset(path: Path, rows: int) -> None:
    """Write `rows` data rows, about 10% of them breaking some rule."""
    rng = random.Random(SEED)

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("id,name,age,status,email\n")
        for i in range(rows):
            if rng.random() < 0.10:
                # Each bad row trips exactly one rule, cycling through
                # them so no single validator dominates the timing.
                which = i % 4
                age = "not-a-number" if which == 0 else str(rng.randint(0, 120))
                name = "" if which == 1 else f"person{i}"
                status = "unknown" if which == 2 else "active"
                email = "missing-at-sign" if which == 3 else f"p{i}@example.com"
            else:
                age = str(rng.randint(0, 120))
                name = f"person{i}"
                status = rng.choice(["active", "inactive"])
                email = f"p{i}@example.com"

            f.write(f"{i},{name},{age},{status},{email}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument(
        "--repeat",
        type=int,
        default=3,
        help="Timed runs. The best one is reported, since a slower run "
        "means the machine was busy, not that the code got slower.",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "benchmark.csv"
        rules_path = Path(tmp) / "rules.yaml"
        rules_path.write_text(RULES, encoding="utf-8")

        print(f"generating {args.rows:,} rows (seed {SEED})...")
        write_dataset(csv_path, args.rows)
        size_mb = csv_path.stat().st_size / 1_000_000
        print(f"input: {size_mb:.1f} MB")

        rules = load_rules(str(rules_path))

        best = None
        for run in range(1, args.repeat + 1):
            start = time.perf_counter()
            report = build_report(load_csv(str(csv_path)), rules)
            elapsed = time.perf_counter() - start
            print(f"  run {run}: {elapsed:.2f}s")
            best = elapsed if best is None else min(best, elapsed)

        assert best is not None
        print(f"\n{args.rows:,} rows in {best:.2f}s ({args.rows / best:,.0f} rows/sec)")
        print(f"{report.error_count:,} errors in {report.rows_with_errors:,} rows")


if __name__ == "__main__":
    main()
