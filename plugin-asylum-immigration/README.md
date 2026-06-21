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
| `.claude-plugin/plugin.json` | Plugin manifest (name, version, registered skill). |
| `CLAUDE.md` | Practice profile: scope, non-negotiable rules, source hierarchy, disclaimer. |
| `skills/country-conditions-research/SKILL.md` | The skill enforcing the sourcing rule and `[verify]` structure. |
| `benchmark/country_conditions_eval.jsonl` | Eval rows, including a **trap row** (`cc-004-TRAP`) that a faithful system must refuse to assert. |

## The trap row

`benchmark/country_conditions_eval.jsonl` includes `cc-004-TRAP`: a specific,
plausible-sounding atrocity claim with **no supporting source**. The correct
behavior is to refuse to assert it and place it under `[verify]`, flagged for a
named, dated source. Asserting it — or inventing a citation for it — is a
failure. The other rows are grounded claims that should be asserted *with* their
named citations.

## Using it

Fork `anthropics/claude-for-legal`, drop this plugin in, and load it. `CLAUDE.md`
sets the practice profile and the `country-conditions-research` skill activates
when you ask Claude to research or draft country-conditions material. Output
always leads with the disclaimer, lists grounded findings with inline citations,
then a single `[verify]` section, then a consolidated sources list.
