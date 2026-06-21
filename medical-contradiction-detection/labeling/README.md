# Medical labeling — the human-in-the-loop boundary

The pipeline is automated **up to this point**. One task requires a qualified
**medical labeler (radiologist)** and cannot be done by the model or CI:
establishing ground truth on **real** chest-X-ray / report pairs.

> This is a research/evaluation harness, **not** a clinical tool. Labels
> collected here are for measuring a model, not for patient care.

## Why a human is needed here

The contradictions `run_baseline.py` builds (laterality flip, finding negation,
report swap) are **synthetic**: we constructed them, so their labels are known
and need no annotation. They measure whether a model catches *injected*
contradictions.

To measure something stronger — whether the model silently agrees with
*naturally occurring* image/report disagreements — you need real pairs labeled by
someone who can read the X-ray. That judgment is the labeler's; nothing in this
repo can substitute for it.

## The task

For each real `(image, report)` pair, the labeler decides whether the report is
faithful to the image:

- `support` — the report matches the image.
- `contradict` — the report asserts something the image does not show (or
  contradicts), e.g. wrong side, a finding that is absent/present.
- `uncertain` — genuinely indeterminate from the image provided.

Add brief `notes` (what drove the call), especially for `contradict`/`uncertain`.

## Workflow

1. Produce the real export at `../data/openi/pairs.jsonl` (see `../data/README.md`).
2. Generate a sheet:

   ```bash
   python make_labeling_sheet.py --pairs ../data/openi/pairs.jsonl --out sheet.csv
   ```

   (With no `--pairs`, it uses the synthetic fallback so you can see the format.)
3. The radiologist fills the `label` column (`support` / `contradict` /
   `uncertain`) and `notes`. See `template.csv` for the exact shape.
4. Feed the validated labels back as the `gold` field of an examples set, or
   compare them against the model's `results.jsonl` predictions to compute the
   silent-contradiction rate on real, human-labeled data.

## Quality notes for the labeler

- Prefer double-labeling case-pivotal pairs and recording inter-rater
  disagreement.
- `uncertain` is a valid, honest answer — do not force a call the image does not
  support.
- Keep PHI handling consistent with your IRB / data-use agreement; do not commit
  images or filled sheets with identifiers (the repo `.gitignore` excludes image
  types, but review before sharing).
