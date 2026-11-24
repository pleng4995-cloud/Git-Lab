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


if __name__ == "__main__":
    unittest.main()
