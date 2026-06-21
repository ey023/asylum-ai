# asylum-ai

This repository hosts **two independent projects**. They share a theme —
making AI systems refuse to silently go along with unsupported claims — but they
have **no shared code, dependencies, or build**. Treat them as separate; work on
either one without touching the other.

| Project | What it is | Stack |
|---------|-----------|-------|
| [`medical-contradiction-detection/`](medical-contradiction-detection/) | A Python baseline that measures how often a vision-language model *silently* agrees with a radiology report that contradicts the chest X-ray. | Python (stdlib only for the stub) |
| [`plugin-asylum-immigration/`](plugin-asylum-immigration/) | A Claude-for-Legal plugin for U.S. asylum/immigration whose hard rule is that every country-conditions claim must cite a real source. | Claude plugin (Markdown/JSON) |

## Which to start with

- **Want to see something run right now?** Start with
  **`medical-contradiction-detection/`**. It executes end-to-end on the Python
  standard library with a synthetic dataset and a stub model — no downloads, no
  installs:

  ```bash
  cd medical-contradiction-detection
  python run_baseline.py
  ```

  Then swap in real Open-i data and a real VLM at the two `TODO(you)` seams.

- **Working on the legal assistant?** Go to **`plugin-asylum-immigration/`**. It
  is configuration and prose (a plugin manifest, a practice profile, one skill,
  and an eval set), meant to be forked into `anthropics/claude-for-legal`. There
  is nothing to "run"; read its `README.md` and `CLAUDE.md`.

## Continuous integration

`.github/workflows/ci.yml` runs on every push: it executes the medical baseline's
stdlib smoke tests + stub run, and validates the legal plugin's manifest and the
country-conditions sourcing invariant (`benchmark/check_benchmark.py`). Both jobs
need only Python 3.11 and the standard library.

## Shared disclaimer

Neither project is professional advice. The medical project is an evaluation
harness, **not** a clinical tool. The legal plugin produces **drafts for
attorney review — not legal advice**, and creates no attorney–client
relationship.
