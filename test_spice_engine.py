"""Unit tests for the ngspice adapter (Lab 04)."""

import unittest

from bjt_bias import spice_engine


class TestModelFile(unittest.TestCase):
    def test_model_file_defines_q2n3904(self):
        text = spice_engine.MODEL_PATH.read_text(encoding="utf-8")
        self.assertIn(".model Q2N3904 NPN", text)
        for param in ("IS=6.734f", "BF=416.4", "VAF=74.03"):
            self.assertIn(param, text)

    def test_model_path_is_inside_package(self):
        self.assertTrue(spice_engine.MODEL_PATH.is_file())
        self.assertEqual(spice_engine.MODEL_PATH.parent.name, "spice_models")


class TestNetlist(unittest.TestCase):
    def circuit(self, **overrides):
        values = dict(spice_engine.CIRCUIT_DEFAULTS)
        values.update(overrides)
        return values

    def test_number_formatting_is_spice_safe(self):
        self.assertEqual(spice_engine.format_spice_number(100000.0), "100000")
        self.assertEqual(spice_engine.format_spice_number(2200.0), "2200")
        self.assertEqual(spice_engine.format_spice_number(0.01), "0.01")
        self.assertNotIn("e+", spice_engine.format_spice_number(1e6))

    def test_dc_netlist_contains_reference_circuit(self):
        text = spice_engine.build_netlist(self.circuit(re=2000.0), "dc")
        for fragment in ("VCC  vcc  0", "R1   vcc  base", "RE   emit 0   2000",
                         "Q1   coll base emit Q2N3904", "CIN  vin  base",
                         "COUT coll out", "RL   out  0", ".include"):
            self.assertIn(fragment, text)
        self.assertIn("op", text)
        self.assertIn("wrdata op.txt", text)
        self.assertNotIn("ac dec", text)
        self.assertNotIn("tran", text)

    def test_ac_netlist_has_sweep_and_no_transient(self):
        text = spice_engine.build_netlist(self.circuit(), "ac")
        self.assertIn("ac dec 20 10 1e+06", text)
        self.assertIn("wrdata ac.txt vdb(out) vp(out)", text)
        self.assertNotIn("wrdata tran.txt", text)

    def test_tran_netlist_uses_five_cycles(self):
        text = spice_engine.build_netlist(self.circuit(frequency_hz=1000.0), "tran")
        self.assertIn("tran 5e-06 0.005", text)
        self.assertIn("SIN(0 0.01 1000)", text)

    def test_unknown_analysis_rejected(self):
        with self.assertRaises(ValueError):
            spice_engine.build_netlist(self.circuit(), "noise")


OP_OK = "0\t2.101\t1.452\t8.806\t0.00145\t0.00342\t0.00146\n"
AC_OK = "1.000000e+01\t4.9\t178.2\n1.000000e+03\t5.1\t179.0\n"
TRAN_OK = "0.000000e+00\t0.0\t0.0\n1.000000e-06\t0.0006\t-0.0011\n"


class TestParsers(unittest.TestCase):
    def test_op_values(self):
        data = spice_engine.parse_op(OP_OK)
        self.assertAlmostEqual(data["v_b_v"], 2.101)
        self.assertAlmostEqual(data["v_ce_v"], 8.806 - 1.452)
        self.assertAlmostEqual(data["i_c_a"], 0.00145)

    def test_ac_arrays(self):
        data = spice_engine.parse_ac(AC_OK)
        self.assertEqual(data["freq_hz"], [10.0, 1000.0])
        self.assertEqual(data["gain_db"], [4.9, 5.1])
        self.assertEqual(data["phase_deg"], [178.2, 179.0])

    def test_tran_arrays(self):
        data = spice_engine.parse_tran(TRAN_OK)
        self.assertEqual(len(data["time_s"]), 2)
        self.assertEqual(data["vout_v"][1], -0.0011)

    def test_wrong_column_count_raises(self):
        with self.assertRaises(spice_engine.SpiceParseError):
            spice_engine.parse_ac_safe("10 4.9\n")

    def test_nan_and_empty_raise(self):
        for bad in ("", "nan nan nan\n", "abc def ghi\n"):
            with self.subTest(bad=bad):
                with self.assertRaises(spice_engine.SpiceParseError):
                    spice_engine.parse_ac_safe(bad)

    def test_non_increasing_sweep_raises(self):
        with self.assertRaises(spice_engine.SpiceParseError):
            spice_engine.parse_ac_safe("1000 5 180\n10 5 180\n")


if __name__ == "__main__":
    unittest.main()
