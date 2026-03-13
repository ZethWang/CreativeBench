<p align="center">
  <img src="assets/creativebench_logo.png" alt="CreativeBench logo" width="180" />
</p>

<p align="center">
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge" alt="MIT License" />
  </a>
  <a href="https://huggingface.co/datasets/Zethive/CreativeBench">
    <img src="https://img.shields.io/badge/Dataset-CreativeBench-f6c344?style=for-the-badge&logo=huggingface&logoColor=white" alt="Dataset" />
  </a>
  <a href="https://arxiv.org/abs/2603.11863">
    <img src="https://img.shields.io/badge/arXiv-2603.11863-b31b1b?style=for-the-badge&logo=arxiv&logoColor=white" alt="arXiv" />
  </a>
</p>

# CreativeBench: Benchmarking and Enhancing Machine Creativity via Self-Evolving Challenges

CreativeBench is an open-source benchmark and data synthesis framework for **creative code generation**, featuring two complementary pipelines:

- **Combo (reverse-engineering)**: Combines solutions from different domains to synthesize new problems and tests.
- **Explore (self-play)**: Evolves problems through progressive constraints to elicit novel solutions.

This repository provides the pipelines, templates, and artifacts needed to reproduce the dataset generation process.

---

## Contents

- [Introduction](#introduction)
- [Project Structure](#project-structure)
- [Data Resources](#data-resources)
- [Combo Pipeline (Reverse-Engineering)](#combo-pipeline-reverse-engineering)
- [Explore Pipeline (Self-Play)](#explore-pipeline-self-play)
- [Evaluation](#evaluation)
- [Reproducibility Checklist](#reproducibility-checklist)
- [License](#license)

---

## Introduction

**CreativeBench** targets *creative code generation*: the ability to produce correct, novel solutions under new constraints or from cross-domain recombination. We provide:

- **Combo**: cross-domain code recombination + sandbox feedback, yielding novel tasks with verified tests.
- **Explore**: progressive constraint self-play, encouraging diverse solution strategies beyond the baseline.

The framework is designed for reproducibility and extensibility, and can be adapted to other languages or models.

---

## Project Structure

```
.
├── CreativeGen/
│   ├── combo/                 # reverse-engineering pipeline
│   └── explore/               # self-play pipeline
├── datasets-subset/           # sampled datasets only
├── evaluation/                # evaluation utilities
└── inference/                 # inference utilities
```

---

## Data Resources

We provide sampled datasets in `datasets-subset/`.

**Field definitions** (each JSONL line):

- `question`: problem statement
- `canonical_solution`: reference solution
- `demo_test_func`: public tests
- `full_test_func`: comprehensive tests
- `language`: programming language
- `difficulty`: difficulty label

---

## Combo Pipeline (Reverse-Engineering)

### Overview

1. Select domain pairs and build combo prompts
2. Generate combined solutions
3. Validate in sandbox
4. Fix failed solutions using feedback
5. Generate tests and questions
6. Format final dataset

### Run

```bash
bash CreativeGen/combo/run_combo_pipeline.sh \
  <num_combos> <max_fix_attempts> <input_jsonl>
```

**Example**:

```bash
bash CreativeGen/combo/run_combo_pipeline.sh 5 3 /path/to/input.jsonl
```

### Outputs

A run folder is created under:

```
CreativeGen/combo/runs/run_YYYYMMDD_HHMMSS/
```

Key artifacts:

- `combo_final_success.jsonl`
- `test_func.jsonl`
- `combo_final_dataset.jsonl`
- `combo_final_formatted.jsonl`

---

## Explore Pipeline (Self-Play)

### Overview

1. Filter source dataset to Python-only (or target language)
2. Identify key techniques in baseline solutions
3. Add progressive constraints
4. Generate constrained solutions
5. Verify compliance and run sandbox validation
6. Compute creativity scores
7. Convert results to inference-ready flat dataset

### Run

```bash
bash CreativeGen/explore/run_explore_pipeline.sh \
  /path/to/autocodebench.jsonl
```

### Outputs

```
CreativeGen/explore/runs/run_YYYYMMDD_HHMMSS/
  creativity_evolution_results.json
  creativity_analysis.png
CreativeGen/explore/data/converted/*_infer_*.jsonl
```

---

## Evaluation

If you have the sandbox server running, you can validate solutions with:

```bash
python3 CreativeGen/combo/src/call_sandbox.py \
  --input_file path/to/data.jsonl \
  --output path/to/output.jsonl \
  --solution_key canonical_solution
```

Sandbox usage details will be documented here.

---

## Reproducibility Checklist

- [ ] Set `MODEL_API_KEY` (and optional `MODEL_BASE_URL`)
- [ ] Prepare input JSONL files with `question/canonical_solution/test_func` fields
- [ ] Start sandbox service if validation is needed
- [ ] Run `combo` or `explore` pipeline
- [ ] Verify outputs and artifact counts

---

---

## License

This project is released under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## Citation

If you use CreativeBench in your work, please cite:

```bibtex
@misc{wang2026creativebenchbenchmarkingenhancingmachine,
  title={CreativeBench: Benchmarking and Enhancing Machine Creativity via Self-Evolving Challenges},
  author={Zi-Han Wang and Lam Nguyen and Zhengyang Zhao and Mengyue Yang and Chengwei Qin and Yujiu Yang and Linyi Yang},
  year={2026},
  eprint={2603.11863},
  archivePrefix={arXiv},
  primaryClass={cs.AI},
  url={https://arxiv.org/abs/2603.11863},
}
```
