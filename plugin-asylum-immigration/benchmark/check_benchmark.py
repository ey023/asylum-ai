#!/usr/bin/env python3
"""
Validate country_conditions_eval.jsonl against the plugin's sourcing rule.

This enforces, in CI, the invariant the plugin exists to protect:
  - grounded claims MUST carry a real, named source with a URL;
  - 'verify' claims MUST be marked refuse_to_assert (and carry no real source);
  - at least one TRAP row exists (a claim a faithful system must refuse).

Exit code 0 = valid, 1 = one or more violations (printed).
Standard library only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EVAL_PATH = Path(__file__).with_name("country_conditions_eval.jsonl")

REQUIRED_KEYS = {"id", "country", "claim", "source", "expected_section", "expected_behavior"}
SECTIONS = {"grounded", "verify"}
BEHAVIORS = {"assert_with_citation", "refuse_to_assert"}
SOURCE_KEYS = {"org", "title", "date", "url"}


def _err(errors: list[str], rid: str, msg: str) -> None:
    errors.append(f"[{rid}] {msg}")


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"eval file not found: {path}"]

    rows = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            errors.append(f"line {lineno}: invalid JSON: {e}")
    if errors:
        return errors

    seen_ids: set[str] = set()
    n_trap = 0

    for row in rows:
        rid = row.get("id", "<no-id>")

        missing = REQUIRED_KEYS - row.keys()
        if missing:
            _err(errors, rid, f"missing keys: {sorted(missing)}")
            continue

        if rid in seen_ids:
            _err(errors, rid, "duplicate id")
        seen_ids.add(rid)

        section = row["expected_section"]
        behavior = row["expected_behavior"]
        source = row["source"]

        if section not in SECTIONS:
            _err(errors, rid, f"expected_section must be one of {sorted(SECTIONS)}, got {section!r}")
        if behavior not in BEHAVIORS:
            _err(errors, rid, f"expected_behavior must be one of {sorted(BEHAVIORS)}, got {behavior!r}")

        if "TRAP" in rid.upper():
            n_trap += 1

        if section == "grounded":
            # Grounded claims must be asserted WITH a real, named, URL'd source.
            if behavior != "assert_with_citation":
                _err(errors, rid, "grounded rows must have expected_behavior=assert_with_citation")
            if not isinstance(source, dict):
                _err(errors, rid, "grounded rows must have a source object")
                continue
            smissing = SOURCE_KEYS - source.keys()
            if smissing:
                _err(errors, rid, f"source missing keys: {sorted(smissing)}")
            url = str(source.get("url", ""))
            if not (url.startswith("http://") or url.startswith("https://")):
                _err(errors, rid, f"source.url must be a real http(s) URL, got {url!r}")
            for k in ("org", "title", "date"):
                if not str(source.get(k, "")).strip():
                    _err(errors, rid, f"source.{k} must be non-empty")

        elif section == "verify":
            # 'verify' claims are exactly the ones a faithful system refuses to
            # assert. They must NOT carry a real (grounded) source.
            if behavior != "refuse_to_assert":
                _err(errors, rid, "verify rows must have expected_behavior=refuse_to_assert")
            if source not in (None, {}):
                _err(errors, rid, "verify rows must NOT carry a real source (use null)")

    if n_trap < 1:
        errors.append("no TRAP row found: at least one id containing 'TRAP' is required")

    return errors


def main() -> int:
    errors = validate(EVAL_PATH)
    if errors:
        print(f"FAIL: {len(errors)} problem(s) in {EVAL_PATH.name}:")
        for e in errors:
            print(f"  - {e}")
        return 1
    n = sum(1 for line in EVAL_PATH.read_text().splitlines() if line.strip())
    print(f"OK: {EVAL_PATH.name} valid ({n} rows; sourcing invariant holds).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
