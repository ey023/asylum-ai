#!/usr/bin/env python3
"""
Emit a CSV labeling sheet for a medical labeler (radiologist) to fill in.

The auto-built contradictions in run_baseline.py have KNOWN labels (we
constructed them), so they need no human labeling. This sheet is for the other
half of the job: establishing ground truth on REAL (image, report) pairs so the
silent-contradiction metric can be validated against naturally-occurring
agreement/disagreement — which only a qualified labeler can judge.

It reads a pairs.jsonl (the real Open-i export; falls back to synthetic if
absent) and writes one row per pair with blank columns for the human to fill:
  label  in {support, contradict, uncertain}
  notes  free text

Usage:
  python make_labeling_sheet.py --pairs ../data/openi/pairs.jsonl --out sheet.csv
  python make_labeling_sheet.py            # synthetic fallback -> sheet.csv

Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Reuse the loader so real/synthetic behavior matches the baseline exactly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import run_baseline as rb  # noqa: E402

FIELDS = ["id", "image", "report", "label", "notes"]
VALID_LABELS = "support|contradict|uncertain"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs", default=None,
                    help="path to pairs.jsonl (default: CONFIG data dir, else synthetic)")
    ap.add_argument("--out", default="sheet.csv", help="output CSV path")
    ap.add_argument("--limit", type=int, default=0, help="cap number of rows (0 = all)")
    args = ap.parse_args()

    cfg = dict(rb.CONFIG)
    if args.pairs:
        cfg["DATA_DIR"] = str(Path(args.pairs).parent)
    pairs = rb.load_pairs(cfg)
    if args.limit:
        pairs = pairs[: args.limit]

    out = Path(args.out)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for p in pairs:
            w.writerow({
                "id": p.id,
                "image": p.image,
                "report": p.report,
                "label": "",   # labeler fills: support|contradict|uncertain
                "notes": "",
            })
    print(f"[labeling] wrote {len(pairs)} rows to {out}")
    print(f"[labeling] labeler fills 'label' with one of: {VALID_LABELS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
