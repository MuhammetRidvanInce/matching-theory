# College Admission Matching Simulations

This repository contains the Python implementation and computational results accompanying the article **“College Admission Problem Revisited: Analyzing Matching Mechanisms by Python Algorithms Using a Special Utility Index.”**

The code implements and compares:

- Gale–Shapley Student-Optimal Stable Mechanism (GSSOSM)
- Gale–Shapley College-Optimal Stable Mechanism (GSCOSM)
- Multi-Category Serial Dictatorship Mechanism (MCSDM)

## Repository structure

```text
.
├── figures/                 # Figures reported in the article
├── results/                 # Robustness outputs and manuscript-ready Table 7
├── scripts/
│   ├── matching_mechanisms_and_utility_analysis.ipynb
│   ├── run_main_simulations.py
│   └── run_robustness.py
├── src/
│   └── matching_model.py    # Matching mechanisms and utility calculations
├── requirements.txt
└── README.md
```

## Installation

Python 3.10 or later is recommended.

```bash
python -m venv .venv
```

Activate the environment and install the dependencies:

```bash
pip install -r requirements.txt
```

## Reproducing the main simulations

The article reports 700 simulations: 100 seeds for each of seven market configurations.

The publication notebook containing the mechanism implementation and a worked example is available at `scripts/matching_mechanisms_and_utility_analysis.ipynb`.

```bash
python scripts/run_main_simulations.py
```

The script writes seed-level results and a configuration-level summary to `results/`. The original algorithms favor transparency over computational optimization, so the complete run can take a considerable amount of time. For a quick check, use:

```bash
python scripts/run_main_simulations.py --seeds 3 --workers 1
```

## Reproducing the robustness check

The baseline model generates heterogeneous student preferences independently. The robustness scenario introduces a common college-quality component, making student preferences positively correlated while retaining student-specific variation.

```bash
python scripts/run_robustness.py
```

The script reproduces the correlated-preference row of Table 7 and writes:

- `results/robustness_seed_results.csv`
- `results/robustness_summary.json`

The manuscript-ready table and explanatory text are available in `results/table_7_robustness.md`.

## Reproducibility notes

- Simulation seeds are fixed at integers 1–100.
- The robustness check uses the 100-student / 10-college configuration.
- Quotas, college types, scores, the outside-option convention, and the utility-index definition are held fixed across preference scenarios.
- Student utility is the reciprocal of the assigned preference rank; an unmatched student receives zero utility.

## Citation

Please cite the accompanying article when using this code or its results. Full bibliographic metadata can be added here after publication.
