"""Weighted agreement for stratified validation samples (Sec. 3.1 of the paper).

Each item belongs to a stratum; strata were sampled at different rates, so every estimate is
weighted to the benchmark population. CIs resample items within each stratum.

    w = weights(strata, population, sampled)
    weighted_mean(agree, w), stratified_ci(agree, w, strata, np.random.default_rng(42))
"""
import numpy as np

REPS = 2000


def weights(strata, population, sampled):
    """Population share of each item's stratum divided by its sampled count (sampled strata only)."""
    total = sum(population[s] for s in sampled if sampled[s])
    return np.array([population[s] / total / sampled[s] for s in strata])


def weighted_mean(values, w):
    return float(np.sum(values * w) / np.sum(w))


def stratified_ci(values, w, strata, rng):
    """Percentile CI resampling items within each stratum, keeping stratum weights fixed."""
    strata = np.asarray(strata)
    groups = [np.flatnonzero(strata == s) for s in np.unique(strata)]
    boot = np.empty(REPS)
    for b in range(REPS):
        idx = np.concatenate([rng.choice(g, size=len(g)) for g in groups])
        boot[b] = weighted_mean(values[idx], w[idx])
    return [float(x) for x in np.quantile(boot, [0.025, 0.975])]


def weighted_kappa(human, judge, w):
    """Linearly weighted Cohen's kappa on the 0 / 0.5 / 1 scale, with item weights."""
    cats = [0.0, 0.5, 1.0]
    m = np.zeros((3, 3))
    for h, j, wi in zip(human, judge, w):
        m[cats.index(h), cats.index(j)] += wi
    m /= m.sum()
    disagreement = np.abs(np.subtract.outer(range(3), range(3))) / 2
    expected = np.outer(m.sum(1), m.sum(0))
    return float(1 - (disagreement * m).sum() / (disagreement * expected).sum())


# Strata of the paper's samples: (population in the benchmark, items sampled).
REFERENCE_STRATA = {
    "lesion_present_with_doubt": (137, 15), "lesion_present": (328, 25), "lesion_absent": (493, 25),
    "image_quality": (1069, 25),
}
JUDGE_STRATA = {
    "original|1": (42001, 22), "original|0.5": (7673, 26), "original|0": (41541, 31),
    "enriched|1": (2086, 7), "enriched|0.5": (750, 5), "enriched|0": (3245, 9),
}
