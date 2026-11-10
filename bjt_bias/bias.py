"""DC bias engineering logic for a BJT common-emitter amplifier."""


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
