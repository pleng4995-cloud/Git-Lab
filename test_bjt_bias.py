import unittest

from bjt_bias.bias import (
    analyze_bias,
    cutoff_operating_point,
    max_normalized_difference,
    solve_linear_system,
    solve_method1,
    solve_method2,
    validate_inputs,
)


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


GOLDEN = dict(vcc=12.0, r1=47000.0, r2=10000.0, rc=2200.0, re=1000.0, beta=150.0, vbe=0.7)


class TestValidation(unittest.TestCase):
    def test_accepts_golden_inputs(self):
        validate_inputs(**GOLDEN)

    def test_rejects_non_positive_supply_and_resistors(self):
        for field in ("vcc", "r1", "r2", "rc", "re", "beta"):
            for bad in (0, -5):
                with self.subTest(field=field, bad=bad):
                    with self.assertRaises(ValueError):
                        validate_inputs(**{**GOLDEN, field: bad})

    def test_rejects_non_numbers(self):
        for bad in ("12", None, True, float("nan"), float("inf")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validate_inputs(**{**GOLDEN, "vcc": bad})

    def test_rejects_vbe_outside_supply(self):
        for bad in (-0.1, 12.0, 13.0):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validate_inputs(**{**GOLDEN, "vbe": bad})


class TestMethod1(unittest.TestCase):
    def test_golden_operating_point(self):
        result = solve_method1(**GOLDEN)
        self.assertAlmostEqual(result["i_b_a"], 8.8245e-6, delta=1e-9)
        self.assertAlmostEqual(result["i_c_a"], 1.323675e-3, delta=1e-9)
        self.assertAlmostEqual(result["i_e_a"], 1.3325e-3, delta=1e-9)
        self.assertAlmostEqual(result["v_b_v"], 2.0325, delta=1e-6)
        self.assertAlmostEqual(result["v_e_v"], 1.3325, delta=1e-6)
        self.assertAlmostEqual(result["v_c_v"], 9.087915, delta=1e-6)
        self.assertAlmostEqual(result["v_ce_v"], 7.755415, delta=1e-6)


SATURATING = dict(vcc=12.0, r1=47000.0, r2=10000.0, rc=10000.0, re=100.0, beta=150.0, vbe=0.7)
CUTOFF = dict(vcc=12.0, r1=47000.0, r2=2200.0, rc=2200.0, re=1000.0, beta=150.0, vbe=0.7)


class TestMethod2(unittest.TestCase):
    def test_agrees_with_method1_on_golden(self):
        diff = max_normalized_difference(solve_method1(**GOLDEN), solve_method2(**GOLDEN))
        self.assertLess(diff, 1e-6)

    def test_agrees_with_method1_on_saturation_case(self):
        diff = max_normalized_difference(solve_method1(**SATURATING), solve_method2(**SATURATING))
        self.assertLess(diff, 1e-6)

    def test_agrees_with_method1_on_cutoff_case(self):
        diff = max_normalized_difference(solve_method1(**CUTOFF), solve_method2(**CUTOFF))
        self.assertLess(diff, 1e-6)

    def test_does_not_use_divider_helpers(self):
        import inspect

        source = inspect.getsource(solve_method2)
        self.assertNotIn("vbb", source.lower())
        self.assertNotIn("r_b", source.lower())


class TestAgreementRule(unittest.TestCase):
    def test_zero_against_zero_is_agreement(self):
        zeros = {"i_b_a": 0.0, "i_c_a": 0.0}
        self.assertEqual(max_normalized_difference(zeros, dict(zeros)), 0.0)

    def test_zero_against_non_zero_does_not_divide_by_zero(self):
        self.assertEqual(max_normalized_difference({"i_b_a": 0.0}, {"i_b_a": 1e-12}), 1e-12)


class TestRegions(unittest.TestCase):
    def test_golden_case_is_active(self):
        result = analyze_bias(**GOLDEN)
        self.assertEqual(result["region"], "active")
        self.assertEqual(result["warnings"], [])
        self.assertTrue(result["verification"]["agrees"])
        self.assertAlmostEqual(result["operating_point"]["v_ce_v"], 7.755415, delta=1e-6)

    def test_cutoff_reports_physical_values(self):
        result = analyze_bias(**CUTOFF)
        self.assertEqual(result["region"], "cutoff")
        self.assertEqual(result["operating_point"]["i_c_a"], 0.0)
        self.assertEqual(result["operating_point"]["v_c_v"], 12.0)
        self.assertEqual(result["operating_point"]["v_ce_v"], 12.0)
        self.assertAlmostEqual(result["operating_point"]["v_b_v"], 12 * 2200 / 49200, delta=1e-9)
        self.assertTrue(any("cutoff" in w.lower() for w in result["warnings"]))

    def test_saturation_warns_and_keeps_linear_values(self):
        result = analyze_bias(**SATURATING)
        self.assertEqual(result["region"], "saturation")
        self.assertLess(result["operating_point"]["v_ce_v"], 0.2)
        self.assertTrue(any("saturation" in w.lower() for w in result["warnings"]))

    def test_vbe_outside_plausible_range_warns_but_computes(self):
        result = analyze_bias(**{**GOLDEN, "vbe": 0.95})
        self.assertEqual(result["region"], "active")
        self.assertTrue(any("0.5" in w and "0.9" in w for w in result["warnings"]))

    def test_extreme_but_valid_magnitudes_do_not_raise(self):
        result = analyze_bias(**{**GOLDEN, "rc": 1e12, "re": 1e-6, "beta": 1e9})
        self.assertIn(result["region"], {"active", "cutoff", "saturation"})
        self.assertTrue(result["verification"]["agrees"])

    def test_vbb_equal_to_vbe_does_not_divide_by_zero(self):
        result = analyze_bias(vcc=12.0, r1=113000.0, r2=7000.0, rc=2200.0, re=1000.0, beta=150.0, vbe=0.7)
        self.assertIn(result["region"], {"cutoff", "active"})


class TestCutoffOperatingPoint(unittest.TestCase):
    def test_cutoff_has_no_current(self):
        point = cutoff_operating_point(12.0, 47000.0, 2200.0)
        self.assertEqual(point["i_b_a"], 0.0)
        self.assertEqual(point["i_e_a"], 0.0)
        self.assertEqual(point["v_e_v"], 0.0)


if __name__ == "__main__":
    unittest.main()
