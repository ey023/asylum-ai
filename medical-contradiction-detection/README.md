# medical-contradiction-detection

A small, dependency-free **baseline** for measuring whether a vision-language
model (VLM) *silently agrees* with a radiology report that contradicts the
chest X-ray it is shown.

It is deliberately runnable **before you download anything**: a synthetic
fallback dataset and a stub model let the whole pipeline execute on the Python
standard library alone. You then swap in real Open-i data and a real VLM at two
clearly marked seams.

> This is a research/evaluation harness, not a clinical tool. It must not be
> used to make or support patient-care decisions.

## What it measures

The headline metric is the **silent-contradiction rate**:

```
silent-contradiction rate = (# genuine contradictions the model labels "support")
                            / (# genuine contradictions)
```

A faithful model should label a contradictory report `contradict`. Every time
it instead says `support`, it has *silently* gone along with a wrong report —
the dangerous failure mode this project exists to quantify. Lower is better.

Supporting controls (a report that faithfully matches its image) are included
so you can also read off `support_accuracy` and `contradiction_recall`.

## How it works

1. **Load pairs** — reads `data/openi/pairs.jsonl` if present; otherwise
   synthesizes self-consistent `(image, report)` pairs so the run is offline.
2. **Build contradictions** — for each pair it emits one faithful control plus
   genuine contradictions via three builders:
   - `laterality_flip` — swap left ↔ right in the report.
   - `finding_negation` — assert/negate a finding (e.g. "pleural effusion"
     → "no pleural effusion").
   - `report_swap` — pair the image with a *different* study's report.
3. **Run the VLM** — every example goes through one `run_vlm()` function that
   returns `support` / `contradict` / `uncertain`.
4. **Score** — computes the silent-contradiction rate overall and per builder,
   and writes per-example predictions to `results.jsonl`.

## Quickstart (stub, no installs)

```bash
python run_baseline.py
```

You'll see a results table and a `results.jsonl`. Nothing is downloaded.

Useful overrides:

```bash
python run_baseline.py --synthetic-pairs 30        # more synthetic data
python run_baseline.py --data-dir data/openi       # point at real data
python run_baseline.py --backend real              # use your real VLM
```

## Editing seams — search the code for `TODO(you)`

There are two things you replace, both marked `TODO(you)`:

1. **`run_vlm()` (real backend)** — a working reference implementation is
   already provided in `_run_vlm_real()` / `_load_real_vlm()`: it lazily loads a
   Qwen2-VL-style chat VLM via `transformers` (`AutoModelForVision2Seq`),
   renders `PROMPT_TEMPLATE`, runs greedy inference, and returns text that
   `_normalize_label()` maps to the label vocabulary. To use it:
   - install the real-VLM deps (see `requirements.txt`),
   - set `CONFIG["VLM_MODEL_NAME"]` to a real id (e.g.
     `"Qwen/Qwen2-VL-2B-Instruct"`),
   - run with `--backend real`.
   Adjust the message schema / model classes if your checkpoint differs. The
   heavy imports live *inside* these functions, so the stub path stays
   dependency-free.
2. **Real data loader** — `_load_real_pairs()`. Convert the Open-i export into
   `data/openi/pairs.jsonl`, one JSON object per study. The real backend opens
   each row's `image` path with PIL, so point `image` at actual image files.

All other tunables live in the **`CONFIG` block** at the top of
`run_baseline.py` (data dir, contradiction types, label set, seed, model name).

## Getting Open-i data

Open-i (Indiana University Chest X-ray Collection) ships reports as XML and
images as PNG. Download it from the NLM Open-i service, then convert each study
into a row of `data/openi/pairs.jsonl`:

```json
{"id": "CXR123", "image": "images/CXR123.png", "report": "Frontal chest radiograph. ...", "laterality": "left", "findings": ["pleural effusion"]}
```

`image` may be relative to `data/openi/`. `laterality` and `findings` are
optional — the loader infers them from the report text when omitted. Dataset
files are git-ignored; do not commit images or weights.

## Requirements

See `requirements.txt`. Stub mode needs **nothing** beyond the standard
library; the real-VLM dependencies are listed separately and commented out
until you opt in.

## Industry context

[**OpenEvidence**](https://www.openevidence.com/about) is the de facto industry
standard for evidence-grounded clinical AI: a clinician-facing copilot that
answers point-of-care questions with **every statement linked back to
peer-reviewed sources** (PubMed, major guidelines), used daily by a large share
of U.S. physicians ([NBC News](https://www.nbcnews.com/tech/tech-news/openevidence-ai-doctor-medical-physician-login-app-what-npi-uptodate-rcna341064),
[PR Newswire](https://www.prnewswire.com/news-releases/openevidence-the-fastest-growing-application-for-physicians-in-history-announces-210-million-round-at-3-5-billion-valuation-302505806.html)).
Its defining principle — never assert a clinical claim without a traceable
citation — is exactly the faithfulness property this project measures from the
opposite direction. Where OpenEvidence enforces grounding on its **output**,
this harness quantifies how often a VLM **silently endorses** a report that
contradicts the image. We treat that transparent-sourcing standard as the bar a
deployed image/report system should clear; the silent-contradiction rate is one
way to check whether it does.

## Files

| File | Purpose |
|------|---------|
| `run_baseline.py` | The whole pipeline: CONFIG, data, builders, `run_vlm()`, scoring. |
| `test_baseline.py` | Stdlib smoke tests (`python test_baseline.py`); also run in CI. |
| `requirements.txt` | Stub deps (none) vs real-VLM deps (commented). |
| `.gitignore` | Keeps datasets, weights, and run outputs out of git. |
| `data/` | Where you place `openi/pairs.jsonl` (git-ignored contents). |
| `labeling/` | Hand-off for the radiologist: `make_labeling_sheet.py`, task spec, `template.csv`. |
