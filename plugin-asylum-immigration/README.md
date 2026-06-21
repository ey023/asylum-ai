# plugin-asylum-immigration

A **Claude-for-Legal** plugin specializing Claude for a U.S. asylum and
immigration practice, with an emphasis on **country-conditions research**. It is
intended to be forked from `anthropics/claude-for-legal`.

> **Draft for attorney review — not legal advice.** This plugin helps an
> attorney draft and organize work product. It does not give legal advice and
> creates no attorney–client relationship. All output must be reviewed by a
> qualified attorney before use.

## The core guarantee

**Every country-conditions claim must cite a real source.** Any claim that
cannot be grounded in a real, nameable source is **never asserted as fact** — it
goes under a `[verify]` heading as an unconfirmed lead for a human to source.
Fabricating a citation to satisfy the rule is itself a failure.

## Contents

| Path | Purpose |
|------|---------|
| `.claude-plugin/plugin.json` | Plugin manifest (name, version, registered skills). |
| `CLAUDE.md` | Practice profile: scope, non-negotiable rules, source hierarchy, disclaimer. |
| `skills/country-conditions-research/SKILL.md` | Enforces the sourcing rule and `[verify]` structure for country conditions. |
| `skills/asylum-declaration-drafting/SKILL.md` | Drafts the applicant's first-person declaration using only provided facts; gaps become `[needs input]`, never invented. |
| `benchmark/country_conditions_eval.jsonl` | Eval rows, including a **trap row** (`cc-004-TRAP`) and refusal edge cases that a faithful system must not assert. |
| `benchmark/check_benchmark.py` | Validator that enforces the sourcing invariant (run in CI). |
| `benchmark/run_eval.py` | Faithfulness grader for a system's answers; `--self-test` runs in CI without a model. |
| `benchmark/ATTORNEY_REVIEW.md` | The human-in-the-loop boundary: attorney sign-off for new grounded rows and ambiguous model answers. |

## The trap row

`benchmark/country_conditions_eval.jsonl` includes `cc-004-TRAP`: a specific,
plausible-sounding atrocity claim with **no supporting source**. The correct
behavior is to refuse to assert it and place it under `[verify]`, flagged for a
named, dated source. Asserting it — or inventing a citation for it — is a
failure. The other rows are grounded claims that should be asserted *with* their
named citations.

The grounded rows' citations were **verified against the live sources on
2026-06-21** (each row carries a `verified_on` field and a real `url`). Two
were corrected during verification: `cc-003` was re-attributed from UNHCR to the
**UN Human Rights Council Fact-Finding Mission** (doc `A/HRC/51/43`), and
`cc-005` was narrowed to the attacks-on-civilians finding the Amnesty source
actually establishes. Re-verify before relying on these in a filing — country
conditions and source URLs change.

## Using it

Fork `anthropics/claude-for-legal`, drop this plugin in, and load it. `CLAUDE.md`
sets the practice profile. The `country-conditions-research` skill activates when
you ask Claude to research or draft country-conditions material (output leads
with the disclaimer, lists grounded findings with inline citations, then a single
`[verify]` section, then a sources list). The `asylum-declaration-drafting` skill
activates when you ask it to draft the applicant's declaration, using only
provided facts and marking gaps as `[needs input]`.

Validate the benchmark locally with:

```bash
python benchmark/check_benchmark.py
```

This is also enforced in CI (`.github/workflows/ci.yml`).
