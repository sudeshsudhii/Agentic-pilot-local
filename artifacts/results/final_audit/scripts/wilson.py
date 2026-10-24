import math, sys
def w(k, n, z=1.959963984540054):
    p = k/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d; h = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return c-h, c+h
for a in sys.argv[1:]:
    k, n = map(int, a.split("/")); lo, hi = w(k, n); print(f"{a}: {k/n:.4f} [{lo:.4f},{hi:.4f}] -> [{lo:.2f},{hi:.2f}]")
