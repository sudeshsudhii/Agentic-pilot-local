"""Own statistics helpers (no project imports)."""
import math
from fractions import Fraction

def wilson(k, n, z=1.959963984540054):
    if n == 0: return (float('nan'),)*2
    p = k/n; d = 1+z*z/n
    c = (p + z*z/(2*n))/d
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return max(0.0, c-h), min(1.0, c+h)

def binom_cdf(k, n, p):
    return sum(math.comb(n, i)*p**i*(1-p)**(n-i) for i in range(0, k+1))

def _bisect(f, lo, hi, it=200):
    for _ in range(it):
        m = (lo+hi)/2
        if f(m): hi = m
        else: lo = m
    return (lo+hi)/2

def clopper_pearson(k, n, a=0.05):
    lo = 0.0 if k == 0 else _bisect(lambda p: 1-binom_cdf(k-1, n, p) >= a/2, 0, 1)
    hi = 1.0 if k == n else _bisect(lambda p: binom_cdf(k, n, p) <= a/2, 0, 1)
    return lo, hi

def mcnemar_exact(b, c):
    n = b+c
    if n == 0: return 1.0
    k = min(b, c)
    p = 2*sum(Fraction(math.comb(n, i), 2**n) for i in range(0, k+1))
    return float(min(Fraction(1), p))

def pct_rank(sorted_v, q):  # numpy 'linear' (type 7)
    n = len(sorted_v); h = (n-1)*q; lo = math.floor(h); hi = min(lo+1, n-1)
    return sorted_v[lo] + (h-lo)*(sorted_v[hi]-sorted_v[lo])
