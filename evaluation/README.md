
This directory provides simplified evaluation scripts for CreativeBench outputs.

## Combo

Evaluate a combo run (requires `model_output.jsonl` and `exec_results.jsonl`):

```bash
bash evaluation/combo/run_combo_eval.sh /path/to/model_output.jsonl
```

Outputs (written next to the run folder):
- `evaluation.json`
- `creativity_details.jsonl`

Note: novelty is a proxy based on 4-gram Jaccard distance between generated code
and `canonical_solution`.

## Exploration

Evaluate an exploration run:

```bash
bash evaluation/exploration/run_explore_eval.sh /path/to/model_output.jsonl
```

Outputs:
- `evaluation.json`
- `creativity_details.jsonl`

Note: novelty is a proxy based on 4-gram Jaccard distance to the level-0 baseline
generated code (fallback to `reference_solution` if missing).
