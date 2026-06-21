#!/usr/bin/env python3
"""
Smoke tests for the contradiction-detection baseline. Standard library only;
run with `python test_baseline.py` (no pytest required).

These lock in the behavior CI cares about:
  - the stub pipeline runs end-to-end on synthetic data with zero deps;
  - the contradiction builders actually produce genuine contradictions;
  - the silent-contradiction rate is computed and in [0, 1];
  - the 'real' backend fails loudly (not silently) when misconfigured.
"""

from __future__ import annotations

import run_baseline as rb


def _cfg(**overrides) -> dict:
    cfg = dict(rb.CONFIG)
    cfg["SYNTHETIC_PAIRS"] = 8
    cfg["VLM_BACKEND"] = "stub"
    cfg.update(overrides)
    return cfg


def test_synthetic_fallback_loads_pairs():
    cfg = _cfg(DATA_DIR="does/not/exist")
    pairs = rb.load_pairs(cfg)
    assert len(pairs) == cfg["SYNTHETIC_PAIRS"]
    assert all(p.laterality in ("left", "right") for p in pairs)


def test_builders_produce_genuine_contradictions():
    cfg = _cfg()
    pairs = rb.load_pairs(cfg)
    examples = rb.build_examples(pairs, cfg)
    golds = {e.gold for e in examples}
    assert "support" in golds and "contradict" in golds
    # Every enabled builder should fire at least once on synthetic data.
    types = {e.contradiction_type for e in examples if e.gold == "contradict"}
    for t in cfg["CONTRADICTION_TYPES"]:
        assert t in types, f"builder {t} produced no contradictions"


def test_laterality_flip_changes_side():
    flipped = rb._flip_laterality("There is left-sided pleural effusion.")
    assert flipped is not None and "right" in flipped and "left" not in flipped


def test_score_outputs_valid_silent_rate():
    cfg = _cfg()
    examples = rb.build_examples(rb.load_pairs(cfg), cfg)
    out = rb.score(examples, cfg)
    m = out["metrics"]
    assert m["n_contradictions"] > 0
    assert 0.0 <= m["silent_contradiction_rate"] <= 1.0
    # Silent + caught contradictions never exceed total contradictions.
    assert m["silent_contradictions"] + m["caught_contradictions"] <= m["n_contradictions"]
    assert len(out["results"]) == len(examples)


def test_normalize_label_coerces_unknown_to_uncertain():
    cfg = _cfg()
    assert rb._normalize_label("CONTRADICT!", cfg) == "contradict"
    assert rb._normalize_label("the answer is support", cfg) == "support"
    assert rb._normalize_label("banana", cfg) == "uncertain"


def test_real_backend_fails_loudly_when_unconfigured():
    cfg = _cfg(VLM_BACKEND="real")  # VLM_MODEL_NAME still the TODO placeholder
    raised = False
    try:
        rb.run_vlm("img.png", "a report", cfg)
    except Exception:
        raised = True
    assert raised, "real backend must raise, not silently return a label"


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
