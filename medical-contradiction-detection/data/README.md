# data/

Place the Open-i export here as `openi/pairs.jsonl`. The actual dataset files
(`data/openi/`, images, XML) are git-ignored — see the root `.gitignore`.

Expected layout:

```
data/
  openi/
    pairs.jsonl          # one JSON object per study
    images/CXR123.png    # referenced by pairs.jsonl rows
```

Row schema (one per line):

```json
{"id": "CXR123", "image": "images/CXR123.png", "report": "...", "laterality": "left", "findings": ["pleural effusion"]}
```

If this directory has no `openi/pairs.jsonl`, `run_baseline.py` falls back to a
synthetic dataset so the pipeline still runs offline.
