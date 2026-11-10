"""DC bias engineering logic for a BJT common-emitter amplifier."""

import math


def solve_linear_system(a, b):
    """Solve ``a . x = b`` with Gaussian elimination and partial pivoting.

    ``a`` must be a square matrix and ``b`` a vector of the same size.
    Raises ``ValueError`` for a non-square matrix, a mismatched vector, or a
    singular matrix.
    """
    size = len(a)
    if any(len(row) != size for row in a):
        raise ValueError("Matrix must be square.")
    if len(b) != size:
        raise ValueError("Matrix and vector sizes differ.")

    matrix = [[float(value) for value in row] for row in a]
    rhs = [float(value) for value in b]

    for column in range(size):
        pivot_row = max(
            range(column, size), key=lambda row: abs(matrix[row][column])
        )
        if matrix[pivot_row][column] == 0:
            raise ValueError("Matrix is singular.")
        if pivot_row != column:
            matrix[column], matrix[pivot_row] = matrix[pivot_row], matrix[column]
            rhs[column], rhs[pivot_row] = rhs[pivot_row], rhs[column]

        pivot = matrix[column][column]
        for row in range(column + 1, size):
            factor = matrix[row][column] / pivot
            if factor == 0:
                continue
            for index in range(column, size):
                matrix[row][index] -= factor * matrix[column][index]
            rhs[row] -= factor * rhs[column]

    solution = [0.0] * size
    for row in range(size - 1, -1, -1):
        remainder = sum(
            matrix[row][index] * solution[index]
            for index in range(row + 1, size)
        )
        solution[row] = (rhs[row] - remainder) / matrix[row][row]
    return solution


def _finite_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number.")
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(f"{name} must be finite.") from error
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite.")
    return number


def _positive_number(value, name):
    number = _finite_number(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be a finite number greater than zero.")
    return number


def validate_inputs(vcc, r1, r2, rc, re, beta, vbe):
    """Validate the seven bias inputs, raising ``ValueError`` when invalid."""
    vcc = _positive_number(vcc, "VCC")
    _positive_number(r1, "R1")
    _positive_number(r2, "R2")
    _positive_number(rc, "RC")
    _positive_number(re, "RE")
    _positive_number(beta, "beta")
    vbe = _finite_number(vbe, "VBE")
    if vbe < 0 or vbe >= vcc:
        raise ValueError("VBE must be between 0 and VCC.")


def solve_method1(vcc, r1, r2, rc, re, beta, vbe):
    """Solve the bias point with the standard Thevenin divider method.

    Assumes the inputs were already validated; returns SI-unit values.
    """
    vbb = vcc * r2 / (r1 + r2)
    r_b = r1 * r2 / (r1 + r2)
    i_b = (vbb - vbe) / (r_b + (beta + 1) * re)
    i_c = beta * i_b
    i_e = (beta + 1) * i_b
    v_e = i_e * re
    v_c = vcc - i_c * rc
    return {
        "i_b_a": i_b,
        "i_c_a": i_c,
        "i_e_a": i_e,
        "v_b_v": v_e + vbe,
        "v_e_v": v_e,
        "v_c_v": v_c,
        "v_ce_v": v_c - v_e,
    }


OPERATING_POINT_FIELDS = (
    ("i_b_a", "I_B", "µA", 1e6),
    ("i_c_a", "I_C", "mA", 1e3),
    ("i_e_a", "I_E", "mA", 1e3),
    ("v_b_v", "V_B", "V", 1.0),
    ("v_e_v", "V_E", "V", 1.0),
    ("v_c_v", "V_C", "V", 1.0),
    ("v_ce_v", "V_CE", "V", 1.0),
)


def solve_method2(vcc, r1, r2, rc, re, beta, vbe):
    """Solve the bias point by nodal analysis (KCL) and linear algebra.

    Independent of the divider reduction: the three node equations plus the
    device constraints are solved as one linear system. Assumes the inputs
    were already validated; returns SI-unit values.
    """
    matrix = [
        [1 / r1 + 1 / r2, 0.0, 0.0, 1.0, 0.0, 0.0],
        [0.0, 1 / rc, 0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, -1 / re, 0.0, 0.0, 1.0],
        [0.0, 0.0, 0.0, -1.0, -1.0, 1.0],
        [0.0, 0.0, 0.0, -beta, 1.0, 0.0],
        [1.0, 0.0, -1.0, 0.0, 0.0, 0.0],
    ]
    rhs = [vcc / r1, vcc / rc, 0.0, 0.0, 0.0, vbe]
    v_b, v_c, v_e, i_b, i_c, i_e = solve_linear_system(matrix, rhs)
    return {
        "i_b_a": i_b,
        "i_c_a": i_c,
        "i_e_a": i_e,
        "v_b_v": v_b,
        "v_e_v": v_e,
        "v_c_v": v_c,
        "v_ce_v": v_c - v_e,
    }


def max_normalized_difference(left, right):
    """Largest normalized difference between two operating points.

    Uses ``|a - b| / max(1, |a|, |b|)`` so values near zero cannot divide by
    zero, and returns ``0.0`` when the two agree or carry no shared keys.
    """
    difference = 0.0
    for key, _symbol, _unit, _scale in OPERATING_POINT_FIELDS:
        if key not in left or key not in right:
            continue
        denominator = max(1.0, abs(left[key]), abs(right[key]))
        difference = max(difference, abs(left[key] - right[key]) / denominator)
    return difference
