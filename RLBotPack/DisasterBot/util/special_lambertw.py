import cmath
from numba import jit, f8, c8

twopi = 6.2831853071795864769252842  # 2*pi
EXPN1 = 0.36787944117144232159553  # exp(-1)
OMEGA = 0.56714329040978387299997  # W(1, 0)


@jit(c8(c8, c8, c8), nopython=True, cache=True)
def sc_fma(x, y, z):
    return x * y + z


@jit(c8(f8, f8, f8, f8, c8), nopython=True, cache=True)
def cevalpoly(a, b, c, degree, z):
    """Evaluate a polynomial with real coefficients at a complex point.
    Note that it is more efficient than Horner's method.
    """
    coeffs = [a, b, c]
    j = 0
    r = 2 * z
    s = z * z
    tmp = 0.0

    for j in range(2, degree + 1):
        tmp = b
        b = sc_fma(-s, a, coeffs[j])
        a = sc_fma(r, a, tmp)
    return z * a + b


@jit(c8(c8), nopython=True, cache=True)
def lambertw_branchpt(z):
    """Series for W(z, 0) around the branch point."""
    a, b, c = -1.0 / 3.0, 1.0, -1.0
    p = cmath.sqrt(2 * (cmath.e * z + 1))

    return cevalpoly(a, b, c, 2, p)


@jit(c8(c8), nopython=True, cache=True)
def lambertw_pade0(z):
    """(3, 2) Pade approximation for W(z, 0) around 0."""

    num_a, num_b, num_c = 12.85106382978723404255, 12.34042553191489361902, 1.0

    denom_a, denom_b, denom_c = 32.53191489361702127660, 14.34042553191489361702, 1.0

    # This only gets evaluated close to 0, so we don't need a more
    # careful algorithm that avoids overflow in the numerator for
    # large z.
    return z * cevalpoly(num_a, num_b, num_c, 2, z) / cevalpoly(denom_a, denom_b, denom_c, 2, z)


@jit(c8(c8), nopython=True, cache=True)
def lambertw_asy(z):
    """Compute the W function using the first two terms of the
    asymptotic series.
    """
    w = cmath.log(z)
    return w - cmath.log(w)


@jit(c8(c8), nopython=True, cache=True)
def lambertw0_scalar(z):

    tol = 1e-3

    if z.real > 1e9:
        return z
    elif z.real < -1e9:
        return -z
    elif z == 0:
        return z
    elif z == 1:
        # Split out this case because the asymptotic series blows up
        return OMEGA

    # Get an initial guess for Halley's method
    if abs(z + EXPN1) < 0.3:
        w = lambertw_branchpt(z)
    elif -1.0 < z.real < 1.5 and abs(z.imag) < 1.0 and -2.5 * abs(z.imag) - 0.2 < z.real:
        # Empirically determined decision boundary where the Pade
        # approximation is more accurate.
        w = lambertw_pade0(z)
    else:
        w = lambertw_asy(z)

    # Halley's method
    if w.real >= 0:
        # Rearrange the formula to avoid overflow in exp
        for i in range(100):
            ew = cmath.exp(-w)
            wewz = w - z * ew
            wn = w - wewz / (w + 1 - (w + 2) * wewz / (2 * w + 2))
            if abs(wn - w) < tol * abs(wn):
                return wn
            else:
                w = wn
    else:
        for i in range(100):
            ew = cmath.exp(w)
            wew = w * ew
            wewz = wew - z
            wn = w - wewz / (wew + ew - (w + 2) * wewz / (2 * w + 2))
            if abs(wn - w) < tol * abs(wn):
                return wn
            else:
                w = wn

    # failed to converge
    return wn


@jit(f8(f8), nopython=True, cache=True)
def lambertw(x):
    return lambertw0_scalar(x).real


def main():

    from timeit import timeit
    import numpy as np

    x = np.linspace(-6, 6, 360)

    def test_function():
        return lambertw(x)

    print(test_function())

    fps = 120
    n_times = 10000
    time_taken = timeit(test_function, number=n_times)
    percentage = time_taken * fps / n_times * 100

    print(f"Took {time_taken} seconds to run {n_times} times.")
    print(f"That's {percentage:.5f} % of our time budget.")


if __name__ == "__main__":
    main()
