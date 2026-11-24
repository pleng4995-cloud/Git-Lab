"""Tests for SPICE dispatch, validation and provenance in the Flask app."""

import unittest
from unittest import mock

from bjt_bias import app as app_module
from bjt_bias import plots

ENGINE_OK = {
    "available": True,
    "path": "C:\\Tools\\ngspice-47\\bin\\ngspice_con.exe",
    "version": "ngspice-47",
    "source": "test",
    "error": None,
}
MODEL = {
    "name": "2N3904",
    "spice_name": "Q2N3904",
    "file": "2n3904.lib",
    "sha256": "e3b36b89c491c09e24986692e556095403e3d4cce1eeb1a71da06daea3c5e589",
}


def make_result(**overrides):
    base = {
        "status": "ok",
        "analysis": "dc",
        "run_id": "run-ok-1",
        "run_dir": "runs/run-ok-1",
        "netlist": "* generated netlist",
        "command": ["ngspice", "-b", "-o", "run.log", "circuit.cir"],
        "returncode": 0,
        "duration_s": 0.12,
        "engine": dict(ENGINE_OK),
        "model": dict(MODEL),
        "data": {},
        "warnings": [],
        "stdout_tail": "",
        "stderr_tail": "",
    }
    base.update(overrides)
    return base


FAKE_ENGINE_MISSING = make_result(
    status="engine_missing",
    run_id="",
    run_dir="",
    engine={
        "available": False,
        "path": None,
        "version": None,
        "source": "NGSPICE_BIN=C:\\does-not-exist\\ngspice.exe",
        "error": "ngspice not found (C:\\does-not-exist\\ngspice.exe (missing))",
    },
    stderr_tail="ngspice not found (C:\\does-not-exist\\ngspice.exe (missing))",
)

FAKE_DC_OK = make_result(
    data={
        "v_b_v": 2.05,
        "v_e_v": 1.35,
        "v_c_v": 9.10,
        "v_ce_v": 7.75,
        "i_b_a": 9.0e-6,
        "i_c_a": 1.450e-3,
        "i_e_a": -1.459e-3,
    },
)

FAKE_AC_OK = make_result(
    analysis="ac",
    run_id="run-ac-1",
    data={
        "freq_hz": [10.0, 100.0, 1000.0],
        "gain_db": [4.7, 4.9, 4.89],
        "phase_deg": [-167.0, 178.0, 178.5],
    },
    plots={
        "bode": plots.bode_svg(
            [10.0, 100.0, 1000.0],
            [4.7, 4.9, 4.89],
            [-167.0, 178.0, 178.5],
            run_id="run-ac-1",
        )
    },
)

DIVIDER_FORM = {
    "mode": "divider",
    "vcc": "12",
    "r1": "100",
    "r1_unit": "kohm",
    "r2": "22",
    "r2_unit": "kohm",
    "rc": "2.2",
    "rc_unit": "kohm",
    "re": "1",
    "re_unit": "kohm",
    "beta": "100",
    "vbe": "0.7",
}


class TestAnalysisValidation(unittest.TestCase):
    def test_missing_analysis_means_analytical(self):
        self.assertEqual(app_module._resolve_analysis(None), ("analytical", None))

    def test_unknown_analysis_rejected(self):
        analysis, error = app_module._resolve_analysis("noise")
        self.assertEqual(analysis, "analytical")
        self.assertIn("Unknown analysis", error)

    def test_dc_ignores_source_fields(self):
        values, parsed, errors = app_module._read_source(
            {"amplitude_mv": "0", "frequency_hz": "0"}, "dc"
        )
        self.assertEqual((values, parsed, errors), ({}, {}, []))

    def test_tran_rejects_zero_amplitude_and_frequency(self):
        _, _, errors = app_module._read_source(
            {"amplitude_mv": "0", "frequency_hz": "0"}, "tran"
        )
        self.assertEqual(len(errors), 2)

    def test_tran_rejects_too_slow_frequency(self):
        _, _, errors = app_module._read_source(
            {"amplitude_mv": "10", "frequency_hz": "1"}, "tran"
        )
        self.assertIn("5 cycles", errors[0])

    def test_ac_rejects_reversed_sweep(self):
        _, _, errors = app_module._read_source(
            {"ac_start_hz": "1000", "ac_stop_hz": "10", "ac_points_dec": "20"}, "ac"
        )
        self.assertTrue(any("greater than" in error for error in errors))


class TestRouteDispatch(unittest.TestCase):
    def setUp(self):
        self.client = app_module.create_app().test_client()
        self.form = dict(DIVIDER_FORM)

    def test_default_post_never_calls_engine(self):
        with mock.patch.object(
            app_module,
            "run_spice_simulation",
            side_effect=AssertionError("engine called"),
        ):
            body = self.client.post("/", data=self.form).get_data(as_text=True)
        self.assertIn("1.230", body)

    def test_spice_in_fixed_mode_is_rejected(self):
        body = self.client.post(
            "/",
            data={
                **self.form,
                "mode": "fixed",
                "rb": "1",
                "rb_unit": "mohm",
                "analysis": "dc",
            },
        ).get_data(as_text=True)
        self.assertIn("Voltage Divider reference only", body)

    def test_engine_missing_shows_status_without_plots(self):
        with mock.patch.object(
            app_module, "run_spice_simulation", return_value=FAKE_ENGINE_MISSING
        ):
            body = self.client.post(
                "/", data={**self.form, "analysis": "dc"}
            ).get_data(as_text=True)
        self.assertIn("ngspice not found", body)
        self.assertNotIn('class="spice-plot"', body)

    def test_ok_dc_shows_both_provenances_and_delta(self):
        with mock.patch.object(
            app_module, "run_spice_simulation", return_value=FAKE_DC_OK
        ):
            body = self.client.post(
                "/", data={**self.form, "analysis": "dc"}
            ).get_data(as_text=True)
        self.assertIn("ANALYTICAL", body)
        self.assertIn("SPICE", body)
        for text in ("1.450", "Delta", "2N3904", "run-ok-1"):
            self.assertIn(text, body)


if __name__ == "__main__":
    unittest.main()
