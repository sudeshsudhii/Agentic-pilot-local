"""Small, dependency-free statistics used by the gate study and the end-to-end analysis."""

from __future__ import annotations

import math
import random
from typing import Callable, Sequence

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion k/n."""

    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _binom_cdf(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(0, k + 1))


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact (Clopper-Pearson) interval, by bisection on the binomial tails."""

    if n == 0:
        return (float("nan"), float("nan"))

    def solve(f: Callable[[float], float], target: float) -> float:
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2
            if f(mid) > target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    lower = 0.0 if k == 0 else solve(lambda p: 1 - (1 - _binom_cdf(k - 1, n, p)), 1 - alpha / 2)
    upper = 1.0 if k == n else solve(lambda p: _binom_cdf(k, n, p), alpha / 2)
    return (lower, upper)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts b and c."""

    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) / 2**n
    return min(1.0, 2 * tail)


def paired_discordance(a: Sequence[bool], b: Sequence[bool]) -> tuple[int, int]:
    """(a true and b false, a false and b true) over paired outcomes."""

    return (sum(1 for x, y in zip(a, b) if x and not y), sum(1 for x, y in zip(a, b) if y and not x))


def bootstrap_diff_ci(a: Sequence[bool], b: Sequence[bool], clusters: Sequence[str] | None = None,
                      reps: int = 10000, seed: int = 7) -> tuple[float, float, float]:
    """Mean(a) - mean(b) for paired outcomes, with a 95% percentile bootstrap interval.

    If clusters (e.g. task ids) are given, whole clusters are resampled, which respects the
    correlation between trials of the same task.
    """

    rng = random.Random(seed)
    idx = list(range(len(a)))
    groups: dict[str, list[int]] = {}
    for i in idx:
        groups.setdefault(clusters[i] if clusters else str(i), []).append(i)
    keys = list(groups)
    point = (sum(a) - sum(b)) / len(a)
    diffs = []
    for _ in range(reps):
        sample = [i for _ in keys for i in groups[rng.choice(keys)]]
        diffs.append(sum(a[i] - b[i] for i in sample) / len(sample))
    diffs.sort()
    return (point, diffs[int(0.025 * reps)], diffs[int(0.975 * reps) - 1])


def fmt_ci(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} [{lo:.2f}, {hi:.2f}]" if n else "0/0"
