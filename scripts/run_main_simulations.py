"""Reproduce the 700 GSSOSM–MCSDM simulations reported in the article."""

import argparse
import copy
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from matching_model import MT  # noqa: E402


CONFIGURATIONS = [(100, 10), (100, 20), (100, 30), (100, 60),
                  (200, 60), (300, 60), (400, 60)]


class CachedMT(MT):
    """Cache deterministic primitives while returning mutation-safe copies."""

    def _cached(self, name, builder):
        attr = f"_simulation_cache_{name}"
        if not hasattr(self, attr):
            setattr(self, attr, builder())
        return copy.deepcopy(getattr(self, attr))

    def school_information_tables(self):
        return self._cached("school_information", super().school_information_tables)

    def student_scores(self):
        return self._cached("student_scores", super().student_scores)

    def student_order(self):
        return self._cached("student_order", super().student_order)

    def student_prefs(self):
        return self._cached("student_prefs", super().student_prefs)

    def school_prefs(self):
        return self._cached("school_prefs", super().school_prefs)


def student_utility(assignment, number_of_students):
    total = 0.0
    for school_assignments in assignment.iloc[-1]:
        for _, preference_rank in school_assignments:
            total += 1.0 / preference_rank
    return round(total / number_of_students, 3)


def run_one(task):
    students, colleges, seed = task
    model = CachedMT(seed, students, colleges)
    mcsdm = student_utility(model.Serial_Dictatorship(), students)
    gssosm = student_utility(model.GS_Student_Optimal(), students)
    return students, colleges, seed, mcsdm, gssosm


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=100,
                        help="number of sequential seeds starting at 1")
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()

    tasks = [(s, c, seed) for s, c in CONFIGURATIONS
             for seed in range(1, args.seeds + 1)]
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        rows = list(executor.map(run_one, tasks))

    raw = pd.DataFrame(rows, columns=[
        "students", "colleges", "seed", "mcsdm_ui", "gssosm_ui"
    ])
    raw["difference"] = raw["gssosm_ui"] - raw["mcsdm_ui"]

    summary = raw.groupby(["students", "colleges"], as_index=False).agg(
        simulations=("seed", "count"),
        mcsdm_mean=("mcsdm_ui", "mean"),
        mcsdm_sd=("mcsdm_ui", "std"),
        gssosm_mean=("gssosm_ui", "mean"),
        gssosm_sd=("gssosm_ui", "std"),
        mean_difference=("difference", "mean"),
        gssosm_higher=("difference", lambda x: int((x > 0).sum())),
        equal=("difference", lambda x: int((x == 0).sum())),
        gssosm_lower=("difference", lambda x: int((x < 0).sum())),
    )

    output_dir = REPO_ROOT / "results"
    output_dir.mkdir(exist_ok=True)
    raw.to_csv(output_dir / "main_simulation_seed_results.csv", index=False)
    summary.to_csv(output_dir / "main_simulation_summary.csv", index=False)
    metadata = {"seeds": args.seeds, "configurations": CONFIGURATIONS}
    (output_dir / "main_simulation_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
