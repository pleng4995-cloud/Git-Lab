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


if __name__ == "__main__":
    unittest.main()
