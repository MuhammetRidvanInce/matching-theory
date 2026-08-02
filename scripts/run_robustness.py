"""Robustness check for the 100-student / 10-college market.

Baseline student preferences are the independently generated preferences used
in the article.  The alternative scenario introduces a common college-quality
component, so students' rankings are positively correlated while retaining
idiosyncratic heterogeneity.
"""

import copy
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from matching_model import MT  # noqa: E402


def student_utility_from_assignment(assignment, number_of_students):
    utilities = []
    for school_assignments in assignment.iloc[-1]:
        for _, preference_rank in school_assignments:
            utilities.append(1.0 / preference_rank)
    return round(sum(utilities) / number_of_students, 3)


def mechanism_results(model):
    mc = student_utility_from_assignment(
        model.Serial_Dictatorship(), model.Number_Of_Students
    )
    gs = student_utility_from_assignment(
        model.GS_Student_Optimal(), model.Number_Of_Students
    )
    return mc, gs


def run_seed(seed):
    class MTCached(MT):
        """Cache deterministic primitives; return copies because mechanisms mutate."""

        def _get_cached(self, name, build):
            attr = f"_robustness_cache_{name}"
            if not hasattr(self, attr):
                setattr(self, attr, build())
            return copy.deepcopy(getattr(self, attr))

        def school_information_tables(self):
            return self._get_cached(
                "school_information_tables", super().school_information_tables
            )

        def student_scores(self):
            return self._get_cached("student_scores", super().student_scores)

        def student_order(self):
            return self._get_cached("student_order", super().student_order)

        def student_prefs(self):
            return self._get_cached("student_prefs", super().student_prefs)

        def school_prefs(self):
            return self._get_cached("school_prefs", super().school_prefs)

    class MTCorrelated(MTCached):
        def student_prefs(self):
            return self._get_cached(
                "correlated_student_prefs", self._build_correlated_student_prefs
            )

        def _build_correlated_student_prefs(self):
            # Separate RNG avoids changing quotas, scores, and college types.
            rng = np.random.default_rng(self.Seed + 50_000)
            schools = np.arange(1, self.Number_Of_Pref + 1)

            # A common quality score induces positive cross-student correlation.
            common_quality = rng.normal(0.0, 1.0, self.Number_Of_Pref)
            preferences = pd.DataFrame(
                index=range(1, self.Number_Of_Pref + 2)
            )

            for student in range(1, self.Number_Of_Students + 1):
                idiosyncratic = rng.normal(0.0, 1.0, self.Number_Of_Pref)
                latent_utility = common_quality + idiosyncratic
                ranking = schools[np.argsort(-latent_utility)]

                # Preserve the baseline model's outside-option convention:
                # C0 is never first, but may make lower-ranked colleges
                # unacceptable. Its position is independently randomized.
                outside_position = rng.integers(1, self.Number_Of_Pref + 1)
                ranked_labels = [f"C{x}" for x in ranking]
                ranked_labels.insert(int(outside_position), "C0")
                preferences[f"S{student}"] = ranked_labels

            return preferences

    correlated = MTCorrelated(seed, 100, 10)
    mc_corr, gs_corr = mechanism_results(correlated)
    return seed, mc_corr, gs_corr


def summarize(mc_values, gs_values):
    mc = np.asarray(mc_values, dtype=float)
    gs = np.asarray(gs_values, dtype=float)
    diff = gs - mc
    nonzero = diff[diff != 0]
    t_stat, t_p = stats.ttest_rel(gs, mc)
    if len(nonzero):
        wilcoxon_stat, wilcoxon_p = stats.wilcoxon(nonzero)
    else:
        wilcoxon_stat, wilcoxon_p = np.nan, np.nan

    return {
        "mcsdm_mean": float(mc.mean()),
        "mcsdm_std": float(mc.std(ddof=1)),
        "gssosm_mean": float(gs.mean()),
        "gssosm_std": float(gs.std(ddof=1)),
        "mean_difference": float(diff.mean()),
        "mean_difference_percent_of_mcsdm": float(diff.mean() / mc.mean() * 100),
        "gssosm_better_count": int((diff > 0).sum()),
        "equal_count": int((diff == 0).sum()),
        "gssosm_worse_count": int((diff < 0).sum()),
        "paired_t_statistic": float(t_stat),
        "paired_t_p_value": float(t_p),
        "wilcoxon_statistic_nonzero_pairs": float(wilcoxon_stat),
        "wilcoxon_p_value_nonzero_pairs": float(wilcoxon_p),
    }


def main():
    start = time.time()
    # Limit workers to keep memory/CPU use predictable on Windows.
    with ProcessPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as executor:
        rows = list(executor.map(run_seed, range(1, 101)))

    raw = pd.DataFrame(
        rows,
        columns=["seed", "mcsdm_correlated", "gssosm_correlated"],
    )
    results = {
        "design": {
            "market": "100 students / 10 colleges",
            "seeds": "1-100",
            "baseline": "independent heterogeneous student preferences",
            "alternative": (
                "correlated student preferences: common college quality plus "
                "student-specific random component, equal weights"
            ),
        },
        # These are the already-reported 100/10 baseline results. The corrected
        # run computes only the genuinely new alternative scenario.
        "baseline_independent_reported": {
            "mcsdm_mean": 0.822,
            "mcsdm_std": 0.050,
            "gssosm_mean": 0.836,
            "gssosm_std": 0.052,
            "mean_difference": 0.014,
            "mean_difference_percent_of_mcsdm": 1.68,
            "gssosm_better_count": 30,
            "equal_count": 70,
            "gssosm_worse_count": 0,
            "paired_t_statistic": 8.770,
            "paired_t_p_value": "<0.001",
            "wilcoxon_p_value_nonzero_pairs": "<0.001",
        },
        "alternative_correlated": summarize(
            raw["mcsdm_correlated"], raw["gssosm_correlated"]
        ),
        "runtime_seconds": time.time() - start,
    }

    output_dir = REPO_ROOT / "results"
    output_dir.mkdir(exist_ok=True)
    raw.to_csv(output_dir / "robustness_seed_results.csv", index=False)
    with open(output_dir / "robustness_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
