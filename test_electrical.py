import unittest

from electrical import analyze_circuit, analyze_dc


class TestDCAnalyzer(unittest.TestCase):
    def test_known_values(self):
        result = analyze_dc(12, 6)
        self.assertAlmostEqual(result["current_a"], 2.0)
        self.assertAlmostEqual(result["power_w"], 24.0)

    def test_zero_voltage(self):
        result = analyze_dc(0, 10)
        self.assertAlmostEqual(result["current_a"], 0.0)
        self.assertAlmostEqual(result["power_w"], 0.0)

    def test_rejects_non_positive_resistance(self):
        for resistance in (0, -5):
            with self.subTest(resistance=resistance):
                with self.assertRaises(ValueError):
                    analyze_dc(12, resistance)


class TestCircuitAnalyzer(unittest.TestCase):
    def test_series_circuit(self):
        result = analyze_circuit(
            12,
            {
                "series": [
                    {"name": "R1", "resistance_ohm": 2},
                    {"name": "R2", "resistance_ohm": 4},
                ]
            },
        )

        self.assertAlmostEqual(result["equivalent_resistance_ohm"], 6)
        self.assertAlmostEqual(result["total_current_a"], 2)
        self.assertAlmostEqual(result["total_power_w"], 24)
        self.assertAlmostEqual(result["resistors"]["R1"]["voltage_v"], 4)
        self.assertAlmostEqual(result["resistors"]["R2"]["voltage_v"], 8)
        self.assertAlmostEqual(result["resistors"]["R2"]["current_a"], 2)

    def test_parallel_circuit(self):
        result = analyze_circuit(
            12,
            {
                "parallel": [
                    {"name": "R1", "resistance_ohm": 6},
                    {"name": "R2", "resistance_ohm": 3},
                ]
            },
        )

        self.assertAlmostEqual(result["equivalent_resistance_ohm"], 2)
        self.assertAlmostEqual(result["total_current_a"], 6)
        self.assertAlmostEqual(result["resistors"]["R1"]["current_a"], 2)
        self.assertAlmostEqual(result["resistors"]["R2"]["current_a"], 4)
        self.assertAlmostEqual(result["resistors"]["R1"]["voltage_v"], 12)

    def test_mixed_circuit(self):
        result = analyze_circuit(
            12,
            {
                "series": [
                    {"name": "R1", "resistance_ohm": 2},
                    {
                        "parallel": [
                            {"name": "R2", "resistance_ohm": 6},
                            {"name": "R3", "resistance_ohm": 3},
                        ]
                    },
                ]
            },
        )

        self.assertAlmostEqual(result["equivalent_resistance_ohm"], 4)
        self.assertAlmostEqual(result["total_current_a"], 3)
        self.assertAlmostEqual(result["resistors"]["R1"]["voltage_v"], 6)
        self.assertAlmostEqual(result["resistors"]["R2"]["current_a"], 1)
        self.assertAlmostEqual(result["resistors"]["R3"]["current_a"], 2)

    def test_assigns_unique_names_to_unnamed_resistors(self):
        result = analyze_circuit(
            12,
            {
                "series": [
                    {"name": "R1", "resistance_ohm": 1},
                    {"resistance_ohm": 2},
                    {"resistance_ohm": 3},
                ]
            },
        )

        self.assertEqual(set(result["resistors"]), {"R1", "R2", "R3"})

    def test_rejects_duplicate_resistor_names(self):
        circuit = {
            "series": [
                {"name": "R1", "resistance_ohm": 2},
                {"name": "R1", "resistance_ohm": 4},
            ]
        }

        with self.assertRaises(ValueError):
            analyze_circuit(12, circuit)

    def test_rejects_empty_network(self):
        for circuit in ({"series": []}, {"parallel": []}):
            with self.subTest(circuit=circuit):
                with self.assertRaises(ValueError):
                    analyze_circuit(12, circuit)


if __name__ == "__main__":
    unittest.main()