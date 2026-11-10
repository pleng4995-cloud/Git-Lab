import unittest

from bjt_bias.bias import solve_linear_system


class TestLinearSolver(unittest.TestCase):
    def test_solves_two_by_two(self):
        self.assertEqual(solve_linear_system([[2, 1], [1, 3]], [5, 10]), [1.0, 3.0])

    def test_swaps_rows_when_pivot_is_zero(self):
        # แถวแรกมี pivot เป็น 0 ต้องสลับแถว
        solution = solve_linear_system([[0, 2], [1, 1]], [4, 3])
        self.assertAlmostEqual(solution[0], 1.0)
        self.assertAlmostEqual(solution[1], 2.0)

    def test_rejects_non_square_matrix(self):
        with self.assertRaises(ValueError):
            solve_linear_system([[1, 2, 3], [4, 5, 6]], [1, 2])

    def test_rejects_mismatched_vector(self):
        with self.assertRaises(ValueError):
            solve_linear_system([[1, 0], [0, 1]], [1, 2, 3])

    def test_rejects_singular_matrix(self):
        with self.assertRaises(ValueError):
            solve_linear_system([[1, 1], [1, 1]], [1, 2])


if __name__ == "__main__":
    unittest.main()
