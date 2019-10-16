from typing import Sequence, Tuple

from py_ecc.fields import (
    optimized_bls12_381_FQ2 as FQ2,
)
from py_ecc.typing import (
    Optimized_Field,
    Optimized_Point3D,
)

from .constants import (
    ISO_3_A,
    ISO_3_B,
    ISO_3_Z,
    P_MINUS_9_DIV_16,
    SQRT_I,
    EV1,
    EV2,
    ISO_3_MAP_COEFFICIENTS,
    POSITIVE_EIGTH_ROOTS_OF_UNITY,
)


# Optimized SWU Map - FQ2 to G2': y^2 = x^3 + 240i * x + 1012 + 1012i
# Found in Section 4 of https://eprint.iacr.org/2019/403
def optimized_swu_G2(t: FQ2) -> (FQ2, FQ2, FQ2):
    t2 = t ** 2
    temp = ISO_3_Z * t2
    temp = temp + temp ** 2
    denominator = -(ISO_3_A * temp)  # -a(Z * t^2 + Z^2 * t^4)
    temp = temp + FQ2.one()
    numerator = ISO_3_B * temp  # b(Z * t^2 + Z^2 * t^4 + + 1)

    # Exceptional case
    if denominator == FQ2.zero():
        denominator = ISO_3_Z * ISO_3_A

    # v = D^3
    v = denominator ** 3
    # u = N^3 + a * N * D^2 + b* D^3
    u = (numerator ** 3) + (ISO_3_A * numerator * (denominator ** 2)) + (ISO_3_B * v)

    # Attempt y = sqrt(u / v)
    (success, sqrt_candidate) = sqrt_division_FQ2(u, v)
    y = sqrt_candidate

    # Handle case where (u / v) is not square
    # sqrt_candidate(x1) = sqrt_candidate(x0) * t^3
    sqrt_candidate = sqrt_candidate * t ** 3
    # u(x1) = Z^3 * t^6 * u(x0)
    u = (ISO_3_Z * t2) ** 3 * u
    success_2 = False
    etas = positive_eta_roots()
    for (i, eta) in enumerate(etas):
        # Valid solution if (eta * sqrt_candidate(x1)) ** 2 * v - u == 0
        temp1 = eta * sqrt_candidate
        temp1 = temp1 ** 2 * v - u
        if temp1 == FQ2.zero() and not success and not success_2:
            y = sqrt_candidate * eta
            success_2 = True
        elif i == 3 and not success and not success_2:
            # Unreachable
            raise Exception("Hash to Curve - Optimized SWU failure")

    if not success:
        numerator = numerator * t2 * ISO_3_Z

    if t.sgn0() != y.sgn0():
        y = -y

    y = y * denominator

    return [numerator, y, denominator]


# Square Root Division
# Return: uv^7 * (uv^15)^((p - 9) / 16) * root of unity
# If valid square root is found return true, else false
def sqrt_division_FQ2(u: FQ2, v: FQ2):
    temp1 = u * v ** 7
    temp2 = temp1 * v ** 8

    # sqrt_candidate =  uv^7 * (uv^15)^((p - 9) / 16)
    sqrt_candidate = temp2 ** P_MINUS_9_DIV_16
    sqrt_candidate = sqrt_candidate * temp1

    # Verify sqrt_candidate is a valid root
    valid_root = False
    result = sqrt_candidate
    roots = POSITIVE_EIGTH_ROOTS_OF_UNITY
    for root in roots:
        # Valid if (root * sqrt_candidate)^2 * v - u == 0
        temp1 = (root * sqrt_candidate)
        temp2 = temp1 ** 2 * v - u
        if temp2 == FQ2.zero() and not valid_root:
            valid_root = True
            result = temp1

    return (valid_root, result)


# Setup the four positive roots of eta = sqrt(Z^3 * (-1)^(1 / 4))
def positive_eta_roots() -> Tuple[FQ2]:
    roots = []
    roots.append(FQ2([EV1, 0]))
    roots.append(FQ2([0, EV1]))
    roots.append(FQ2([EV2, EV2]))
    roots.append(FQ2([EV2, -EV2]))
    return roots


# Optimal Map from 3-Isogenous Curve to G2
def iso_map_G2(x: FQ2, y: FQ2, z: FQ2) -> Optimized_Point3D[Optimized_Field]:
    # x-numerator, x-denominator, y-numerator, y-denominator
    mapped_values = [FQ2.zero(), FQ2.zero(), FQ2.zero(), FQ2.zero()]
    z_powers = [z, z ** 2, z ** 3]

    # Horner Polynomial Evaluation
    for (i, k_i) in enumerate(ISO_3_MAP_COEFFICIENTS):
        mapped_values[i] = k_i[-1:][0]
        for (j, k_i_j) in enumerate(reversed(k_i[:-1])):
            mapped_values[i] = mapped_values[i] * x + z_powers[j] * k_i_j

    mapped_values[2] = mapped_values[2] * y  # y-numerator * y
    mapped_values[3] = mapped_values[3] * z  # y-denominator * z

    z_G2 = mapped_values[1] * mapped_values[3]  # x-denominator * y-denominator
    x_G2 = mapped_values[0] * mapped_values[3]  # x-numerator * y-denominator
    y_G2 = mapped_values[1] * mapped_values[2]  # y-numerator * x-denominator

    return (x_G2, y_G2, z_G2)
