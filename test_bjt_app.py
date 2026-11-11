import unittest

from bjt_bias.app import create_app, format_value, parse_resistance

VALID_FORM = {
    "vcc": "12",
    "r1": "47k",
    "r2": "10k",
    "rc": "2.2k",
    "re": "1k",
    "beta": "150",
    "vbe": "0.7",
}


class TestParsing(unittest.TestCase):
    def test_accepts_engineering_suffixes(self):
        self.assertEqual(parse_resistance("47000", "R1"), 47000.0)
        self.assertEqual(parse_resistance("47k", "R1"), 47000.0)
        self.assertEqual(parse_resistance("47K", "R1"), 47000.0)
        self.assertEqual(parse_resistance("2.2k", "R1"), 2200.0)
        self.assertEqual(parse_resistance("1M", "R1"), 1e6)
        self.assertEqual(parse_resistance(" 47k ", "R1"), 47000.0)

    def test_rejects_bad_input(self):
        for bad in ("abc", "", "1,5k"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_resistance(bad, "R1")

    def test_formats_three_decimals(self):
        self.assertEqual(format_value(1.323675e-3, 1e3), "1.324")
        self.assertEqual(format_value(8.8245e-6, 1e6), "8.825")


class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_renders_seven_inputs(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for name in VALID_FORM:
            self.assertIn(f'name="{name}"', response.get_data(as_text=True))

    def test_post_valid_shows_operating_point_and_comparison(self):
        response = self.client.post("/", data=VALID_FORM)
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("1.324", body)
        self.assertIn("7.755", body)
        self.assertIn("active", body)
        self.assertIn("Method 1", body)
        self.assertIn("Method 2", body)

    def test_post_invalid_shows_error_and_keeps_input(self):
        response = self.client.post("/", data={**VALID_FORM, "r1": "0"})
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("greater than zero", body)
        self.assertNotIn("Traceback", body)

    def test_post_cutoff_shows_cutoff(self):
        response = self.client.post("/", data={**VALID_FORM, "r2": "2.2k"})
        self.assertIn("cutoff", response.get_data(as_text=True).lower())

    def test_post_with_comma_decimal_gives_friendly_error(self):
        response = self.client.post("/", data={**VALID_FORM, "vbe": "0,7"})
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("must be a number", body)

    def test_post_empty_form_does_not_crash(self):
        response = self.client.post("/", data={})
        self.assertEqual(response.status_code, 200)
        self.assertIn("must be a number", response.get_data(as_text=True))

    def test_post_missing_fields_does_not_crash(self):
        response = self.client.post("/", data={"vcc": "12"})
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
