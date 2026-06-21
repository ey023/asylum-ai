#!/usr/bin/env python3
"""
Medical image-vs-report contradiction detection — baseline harness.

What this does
--------------
1. Loads chest X-ray image + radiology-report pairs from Open-i. If the dataset
   is not present locally, it falls back to a small *synthetic* set so the whole
   pipeline runs end-to-end with zero downloads.
2. Auto-builds genuine contradictions between an image and a report using three
   perturbations: laterality flip, finding negation, and report-swap.
3. Runs an open vision-language model (VLM) through a single `run_vlm()` seam.
   The default implementation is a deterministic STUB so this file runs today;
   you replace the one function later with a real model call.
4. Scores a *silent-contradiction rate*: of the genuinely contradictory pairs,
   the fraction the model wrongly labels "support". A faithful model should
   label those "contradict", so a high silent-contradiction rate is bad.

Run it:
    python run_baseline.py

Everything you are expected to edit is marked with `TODO(you)`.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# ======================================================================
# CONFIG  (edit here, or override on the command line)
# ======================================================================
CONFIG = {
    # Where Open-i pairs live once you download them (see README).
    # Expected layout: DATA_DIR/pairs.jsonl with rows {"id","image","report"}
    # plus the referenced image files under DATA_DIR.
    "DATA_DIR": "data/openi",

    # If the real dataset is missing, generate this many synthetic pairs so the
    # pipeline still runs. Set to 0 to hard-fail when data is absent.
    "SYNTHETIC_PAIRS": 12,

    # Which contradiction builders to apply. Each genuine pair below is paired
    # with a *perturbed* report (or swapped report) that contradicts the image.
    "CONTRADICTION_TYPES": ["laterality_flip", "finding_negation", "report_swap"],

    # Label vocabulary the VLM must choose from.
    "LABELS": ["support", "contradict", "uncertain"],

    # Reproducibility.
    "SEED": 0,

    # Which run_vlm backend to use: "stub" (default, no deps) or "real".
    # TODO(you): flip to "real" once you have wired up a model in run_vlm().
    "VLM_BACKEND": "stub",

    # Optional knobs your real model might read. Ignored by the stub.
    "VLM_MODEL_NAME": "TODO-your-open-vlm",
    "VLM_MAX_NEW_TOKENS": 16,

    # Where to write the per-example results report.
    "RESULTS_PATH": "results.jsonl",
}


# ======================================================================
# Data types
# ======================================================================
@dataclass
class Pair:
    """An (image, report) pair plus optional structured hints."""
    id: str
    image: str            # path to an image file, or a synthetic descriptor
    report: str           # free-text radiology report
    laterality: Optional[str] = None  # "left" | "right" | None
    findings: list[str] = field(default_factory=list)


@dataclass
class Example:
    """A scored unit: an image shown with a (possibly perturbed) report."""
    id: str
    image: str
    report: str
    # "contradict" means the report genuinely contradicts the image.
    # "support" means the report faithfully matches the image (a control).
    gold: str
    contradiction_type: Optional[str]  # which builder produced it, if any
    source_id: str                     # the original pair id


# ======================================================================
# Step 1 — Data loading (real Open-i with synthetic fallback)
# ======================================================================
LATERAL_WORDS = ["left", "right"]

# Findings used both to render synthetic reports and to drive negation.
SYNTH_FINDINGS = [
    "pleural effusion",
    "pneumothorax",
    "consolidation",
    "cardiomegaly",
    "atelectasis",
    "pulmonary edema",
]

NEGATION_TEMPLATES = [
    ("There is {f}.", "There is no {f}."),
    ("{F} is present.", "{F} is absent."),
    ("Findings consistent with {f}.", "No evidence of {f}."),
]


def load_pairs(cfg: dict) -> list[Pair]:
    """Load real Open-i pairs if available; otherwise synthesize."""
    data_dir = Path(cfg["DATA_DIR"])
    manifest = data_dir / "pairs.jsonl"
    if manifest.exists():
        return _load_real_pairs(manifest, data_dir)
    if cfg["SYNTHETIC_PAIRS"] <= 0:
        raise FileNotFoundError(
            f"No dataset at {manifest} and SYNTHETIC_PAIRS=0. "
            "Download Open-i (see README) or raise SYNTHETIC_PAIRS."
        )
    print(
        f"[data] {manifest} not found -> using "
        f"{cfg['SYNTHETIC_PAIRS']} synthetic pairs (offline mode)."
    )
    return _synthesize_pairs(cfg["SYNTHETIC_PAIRS"])


def _load_real_pairs(manifest: Path, data_dir: Path) -> list[Pair]:
    """Read a JSONL manifest of {id, image, report, [laterality], [findings]}.

    TODO(you): adapt this to the exact Open-i export you produce. The Open-i
    distribution ships reports as XML and images as PNG; convert them into a
    pairs.jsonl with one object per study before running this harness.
    """
    pairs: list[Pair] = []
    with manifest.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            img = row["image"]
            # Resolve relative image paths against the data directory.
            if not os.path.isabs(img):
                img = str(data_dir / img)
            pairs.append(
                Pair(
                    id=str(row["id"]),
                    image=img,
                    report=row["report"],
                    laterality=row.get("laterality") or _infer_laterality(row["report"]),
                    findings=row.get("findings") or _infer_findings(row["report"]),
                )
            )
    print(f"[data] loaded {len(pairs)} real Open-i pairs from {manifest}.")
    return pairs


def _synthesize_pairs(n: int) -> list[Pair]:
    """Build small but self-consistent (image, report) pairs with no I/O."""
    rng = random.Random(CONFIG["SEED"])
    pairs: list[Pair] = []
    for i in range(n):
        side = rng.choice(LATERAL_WORDS)
        finding = rng.choice(SYNTH_FINDINGS)
        # The "image" is a textual descriptor so the stub VLM can reason about
        # it without any pixels. A real run replaces these with image paths.
        image_desc = f"[SYNTH-CXR] frontal chest radiograph; {side} {finding}"
        report = (
            f"Frontal chest radiograph. There is {side}-sided {finding}. "
            f"The contralateral lung is clear. No pneumothorax."
        )
        pairs.append(
            Pair(
                id=f"synth-{i:03d}",
                image=image_desc,
                report=report,
                laterality=side,
                findings=[finding],
            )
        )
    return pairs


def _infer_laterality(report: str) -> Optional[str]:
    low = report.lower()
    has_left = "left" in low
    has_right = "right" in low
    if has_left and not has_right:
        return "left"
    if has_right and not has_left:
        return "right"
    return None


def _infer_findings(report: str) -> list[str]:
    low = report.lower()
    return [f for f in SYNTH_FINDINGS if f in low]


# ======================================================================
# Step 2 — Contradiction builders
# ======================================================================
def _flip_laterality(report: str) -> Optional[str]:
    """Swap left<->right. Returns None if the report has no clear laterality."""
    if not re.search(r"\b(left|right)\b", report, flags=re.I):
        return None

    def swap(m: re.Match) -> str:
        word = m.group(0)
        other = "right" if word.lower() == "left" else "left"
        # Preserve capitalization of the original token.
        return other.capitalize() if word[0].isupper() else other

    return re.sub(r"\b(left|right)\b", swap, report, flags=re.I)


def _negate_finding(report: str, findings: list[str]) -> Optional[str]:
    """Turn an asserted finding into its negation (or vice versa)."""
    for f in findings or SYNTH_FINDINGS:
        for pos, neg in NEGATION_TEMPLATES:
            pos_str = pos.format(f=f, F=f.capitalize())
            if pos_str.lower() in report.lower():
                # Case-insensitive single replacement.
                neg_str = neg.format(f=f, F=f.capitalize())
                idx = report.lower().index(pos_str.lower())
                return report[:idx] + neg_str + report[idx + len(pos_str):]
        # Generic fallback: inject a negation for the first finding present.
        if f in report.lower():
            return re.sub(
                rf"\b{re.escape(f)}\b",
                f"no {f}",
                report,
                count=1,
                flags=re.I,
            )
    return None


def _swap_report(_report: str, other_report: str) -> str:
    """Use a different study's report entirely against this image."""
    return other_report


def build_examples(pairs: list[Pair], cfg: dict) -> list[Example]:
    """Produce a balanced set of supporting controls + genuine contradictions.

    For every original pair we always emit one faithful "support" control, then
    add one contradictory example per enabled builder (when applicable).
    """
    rng = random.Random(cfg["SEED"])
    types = cfg["CONTRADICTION_TYPES"]
    examples: list[Example] = []

    for idx, p in enumerate(pairs):
        # Faithful control: the report matches its own image.
        examples.append(
            Example(
                id=f"{p.id}::support",
                image=p.image,
                report=p.report,
                gold="support",
                contradiction_type=None,
                source_id=p.id,
            )
        )

        if "laterality_flip" in types:
            flipped = _flip_laterality(p.report)
            if flipped and flipped != p.report:
                examples.append(
                    Example(
                        id=f"{p.id}::laterality_flip",
                        image=p.image,
                        report=flipped,
                        gold="contradict",
                        contradiction_type="laterality_flip",
                        source_id=p.id,
                    )
                )

        if "finding_negation" in types:
            negated = _negate_finding(p.report, p.findings)
            if negated and negated != p.report:
                examples.append(
                    Example(
                        id=f"{p.id}::finding_negation",
                        image=p.image,
                        report=negated,
                        gold="contradict",
                        contradiction_type="finding_negation",
                        source_id=p.id,
                    )
                )

        if "report_swap" in types and len(pairs) > 1:
            # Pick a different pair whose report describes a different finding.
            candidates = [q for q in pairs if q.id != p.id and q.report != p.report]
            if candidates:
                other = rng.choice(candidates)
                examples.append(
                    Example(
                        id=f"{p.id}::report_swap",
                        image=p.image,
                        report=_swap_report(p.report, other.report),
                        gold="contradict",
                        contradiction_type="report_swap",
                        source_id=p.id,
                    )
                )

    return examples


# ======================================================================
# Step 3 — The VLM seam
# ======================================================================
PROMPT_TEMPLATE = (
    "You are checking whether a radiology report is faithful to a chest X-ray.\n"
    "IMAGE: {image}\n"
    "REPORT: {report}\n"
    "Does the report SUPPORT, CONTRADICT, or is it UNCERTAIN given the image?\n"
    "Answer with exactly one word: support, contradict, or uncertain."
)


def run_vlm(image: str, report: str, cfg: dict) -> str:
    """Single seam between this harness and a vision-language model.

    Contract:
      input : an image reference (path or descriptor) and a report string
      output: exactly one of cfg["LABELS"] -> "support" | "contradict" | "uncertain"

    The default backend is a dependency-free STUB so this file runs immediately.

    TODO(you): replace the body of `_run_vlm_real` with a real open-VLM call
    (e.g. LLaVA / Qwen-VL / InternVL via transformers). Keep the contract:
    take (image, report), return one lowercase label from cfg["LABELS"].
    """
    if cfg["VLM_BACKEND"] == "real":
        return _normalize_label(_run_vlm_real(image, report, cfg), cfg)
    return _normalize_label(_run_vlm_stub(image, report, cfg), cfg)


def _run_vlm_stub(image: str, report: str, _cfg: dict) -> str:
    """Heuristic, deterministic stand-in for a real VLM.

    It "reads" the synthetic image descriptor and compares laterality/findings
    against the report. It is intentionally imperfect (e.g. it ignores subtle
    negations) so the silent-contradiction metric is non-zero and meaningful.
    """
    img_low = image.lower()
    rep_low = report.lower()

    # Compare laterality if the image descriptor exposes it.
    img_side = _infer_laterality(image)
    rep_side = _infer_laterality(report)
    if img_side and rep_side and img_side != rep_side:
        return "contradict"

    # Compare findings named in the image descriptor.
    img_findings = [f for f in SYNTH_FINDINGS if f in img_low]
    for f in img_findings:
        # Stub weakness: it only catches an explicit "no <finding>" form, so
        # other phrasings of negation slip through as false "support".
        if f"no {f}" in rep_low:
            return "contradict"
        if f in rep_low:
            return "support"

    # No grounded signal -> default to support (the optimistic, unsafe guess).
    return "support"


def _run_vlm_real(image: str, report: str, cfg: dict) -> str:
    """Real open-VLM backend. Not implemented in the stub-only checkout.

    TODO(you): load your model once (cache it on the function or a module
    global), render PROMPT_TEMPLATE, run inference, and map the output text to
    a label. Pseudocode:

        prompt = PROMPT_TEMPLATE.format(image=image, report=report)
        text = your_model.generate(image=load(image), prompt=prompt,
                                    max_new_tokens=cfg["VLM_MAX_NEW_TOKENS"])
        return text  # _normalize_label() will coerce it to the vocabulary
    """
    raise NotImplementedError(
        "VLM_BACKEND='real' but run_vlm._run_vlm_real is not implemented yet. "
        "Wire up your open VLM here, then keep VLM_BACKEND='real'."
    )


def _normalize_label(text: str, cfg: dict) -> str:
    """Coerce arbitrary model output to one of cfg['LABELS']."""
    low = text.strip().lower()
    for label in cfg["LABELS"]:
        if label in low:
            return label
    # Unknown output is treated as 'uncertain' rather than a silent 'support'.
    return "uncertain"


# ======================================================================
# Step 4 — Scoring (the silent-contradiction rate)
# ======================================================================
def score(examples: list[Example], cfg: dict) -> dict:
    """Run the VLM over every example and compute metrics.

    silent-contradiction rate = (# genuine contradictions labeled 'support')
                                 / (# genuine contradictions)
    """
    results = []
    n_contra = 0
    n_silent = 0          # contradiction wrongly called 'support'
    n_caught = 0          # contradiction correctly called 'contradict'
    n_support = 0         # supporting controls
    n_support_ok = 0      # controls correctly called 'support'

    by_type: dict[str, dict[str, int]] = {}

    for ex in examples:
        pred = run_vlm(ex.image, ex.report, cfg)
        row = {
            "id": ex.id,
            "source_id": ex.source_id,
            "gold": ex.gold,
            "pred": pred,
            "contradiction_type": ex.contradiction_type,
        }
        results.append(row)

        if ex.gold == "contradict":
            n_contra += 1
            t = ex.contradiction_type or "unknown"
            bucket = by_type.setdefault(t, {"total": 0, "silent": 0, "caught": 0})
            bucket["total"] += 1
            if pred == "support":
                n_silent += 1
                bucket["silent"] += 1
            elif pred == "contradict":
                n_caught += 1
                bucket["caught"] += 1
        elif ex.gold == "support":
            n_support += 1
            if pred == "support":
                n_support_ok += 1

    metrics = {
        "n_examples": len(examples),
        "n_contradictions": n_contra,
        "n_supports": n_support,
        "silent_contradictions": n_silent,
        "caught_contradictions": n_caught,
        "silent_contradiction_rate": (n_silent / n_contra) if n_contra else 0.0,
        "contradiction_recall": (n_caught / n_contra) if n_contra else 0.0,
        "support_accuracy": (n_support_ok / n_support) if n_support else 0.0,
        "by_type": {
            t: {
                **v,
                "silent_rate": (v["silent"] / v["total"]) if v["total"] else 0.0,
            }
            for t, v in by_type.items()
        },
    }
    return {"metrics": metrics, "results": results}


def write_results(path: str, results: list[dict]) -> None:
    with open(path, "w") as fh:
        for row in results:
            fh.write(json.dumps(row) + "\n")


def print_report(metrics: dict) -> None:
    print("\n==================== RESULTS ====================")
    print(f"examples              : {metrics['n_examples']}")
    print(f"contradictions        : {metrics['n_contradictions']}")
    print(f"supports (controls)   : {metrics['n_supports']}")
    print(f"support accuracy      : {metrics['support_accuracy']:.3f}")
    print(f"contradiction recall  : {metrics['contradiction_recall']:.3f}")
    print(f"SILENT-CONTRADICTION RATE : {metrics['silent_contradiction_rate']:.3f}"
          "   <-- lower is better")
    if metrics["by_type"]:
        print("\nby contradiction type:")
        for t, v in sorted(metrics["by_type"].items()):
            print(f"  {t:18s} total={v['total']:3d}  "
                  f"silent={v['silent']:3d}  silent_rate={v['silent_rate']:.3f}")
    print("================================================\n")


# ======================================================================
# Entry point
# ======================================================================
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=None, help="override CONFIG['DATA_DIR']")
    ap.add_argument("--backend", default=None, choices=["stub", "real"],
                    help="override CONFIG['VLM_BACKEND']")
    ap.add_argument("--synthetic-pairs", type=int, default=None,
                    help="override CONFIG['SYNTHETIC_PAIRS']")
    ap.add_argument("--results", default=None, help="override CONFIG['RESULTS_PATH']")
    return ap.parse_args()


def main() -> None:
    cfg = dict(CONFIG)
    args = parse_args()
    if args.data_dir is not None:
        cfg["DATA_DIR"] = args.data_dir
    if args.backend is not None:
        cfg["VLM_BACKEND"] = args.backend
    if args.synthetic_pairs is not None:
        cfg["SYNTHETIC_PAIRS"] = args.synthetic_pairs
    if args.results is not None:
        cfg["RESULTS_PATH"] = args.results

    random.seed(cfg["SEED"])

    pairs = load_pairs(cfg)
    examples = build_examples(pairs, cfg)
    out = score(examples, cfg)
    write_results(cfg["RESULTS_PATH"], out["results"])
    print_report(out["metrics"])
    print(f"[done] per-example results written to {cfg['RESULTS_PATH']}")


if __name__ == "__main__":
    main()
