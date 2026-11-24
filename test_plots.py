"""Tests for SVG plots drawn from real ngspice arrays."""

import unittest

from bjt_bias import plots


class TestPlots(unittest.TestCase):
    def test_bode_has_axes_units_and_run_id(self):
        svg = plots.bode_svg(
            [10, 100, 1000], [4.8, 5.0, 5.1], [178, 179, 179.5], run_id="abc123"
        )
        for fragment in ("Frequency (Hz)", "Gain (dB)", "Phase (deg)",
                         "abc123", "<path"):
            self.assertIn(fragment, svg)

    def test_bode_changes_with_data(self):
        a = plots.bode_svg([10, 1000], [0, 5], [180, 180], run_id="r1")
        b = plots.bode_svg([10, 1000], [0, 15], [180, 180], run_id="r1")
        self.assertNotEqual(a, b)

    def test_transient_has_two_traces_and_units(self):
        svg = plots.transient_svg(
            [0, 1e-3, 2e-3], [0, 0.01, 0], [0, -0.018, 0], run_id="t1"
        )
        self.assertIn("Time (ms)", svg)
        self.assertIn("mV", svg)
        self.assertIn("Vin", svg)
        self.assertIn("Vout", svg)

    def test_empty_data_rejected(self):
        with self.assertRaises(ValueError):
            plots.bode_svg([], [], [])
        with self.assertRaises(ValueError):
            plots.transient_svg([0, 1], [0], [0, 1])


if __name__ == "__main__":
    unittest.main()
