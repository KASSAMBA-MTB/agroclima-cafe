"""Testes unitarios isolados para a sondagem G7.4 de evidencias de granizo."""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("g74_p0_hail_evidence_probe.py")
SPEC = importlib.util.spec_from_file_location("hail_evidence_probe", SCRIPT)
PROBE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PROBE)


def fixture_payload():
    times = [f"2026-10-03T{hour:02d}:00" for hour in range(3)]
    hourly = {"time": times}
    units = {}
    for variable, unit in PROBE.EXPECTED_UNITS.items():
        hourly[variable] = [100.0, 200.0, 300.0]
        units[variable] = unit
    return {"hourly": hourly, "hourly_units": units}


class HailEvidenceProbeTests(unittest.TestCase):
    def test_request_includes_all_required_and_complementary_variables(self):
        params = PROBE.build_params("2026-10-03T00:00")
        requested = params["hourly"].split(",")
        self.assertEqual(set(requested), set(PROBE.VARIABLES))
        self.assertTrue(set(PROBE.REQUIRED_FOR_MP011).issubset(requested))
        self.assertTrue(set(PROBE.COMPLEMENTARY_FOR_MP0112).issubset(requested))
        self.assertEqual(len(requested), 8)

    def test_complete_payload_reports_full_coverage(self):
        result = PROBE.inventory_payload(fixture_payload())
        self.assertTrue(result["required_variables_complete"])
        self.assertTrue(result["complementary_variables_complete"])
        self.assertEqual(result["timestamps"], 3)
        for name in PROBE.VARIABLES:
            self.assertEqual(result["variables"][name]["numeric_count"], 3)
            self.assertEqual(result["variables"][name]["missing_count"], 0)

    def test_missing_values_are_counted_not_replaced_with_zero(self):
        payload = fixture_payload()
        payload["hourly"]["cape"] = [100.0, None, 300.0]
        result = PROBE.inventory_payload(payload)
        self.assertFalse(result["required_variables_complete"])
        self.assertEqual(result["variables"]["cape"]["numeric_count"], 2)
        self.assertEqual(result["variables"]["cape"]["missing_count"], 1)
        self.assertEqual(payload["hourly"]["cape"][1], None)

    def test_missing_series_fails_completeness(self):
        payload = fixture_payload()
        del payload["hourly"]["wind_speed_500hPa"]
        result = PROBE.inventory_payload(payload)
        self.assertFalse(result["required_variables_complete"])
        self.assertFalse(result["variables"]["wind_speed_500hPa"]["series_present"])

    def test_wrong_unit_fails_completeness(self):
        payload = fixture_payload()
        payload["hourly_units"]["wind_speed_925hPa"] = "km/h"
        result = PROBE.inventory_payload(payload)
        self.assertFalse(result["required_variables_complete"])
        self.assertFalse(result["variables"]["wind_speed_925hPa"]["unit_matches"])

    def test_series_length_mismatch_fails_completeness(self):
        payload = fixture_payload()
        payload["hourly"]["cape"] = [100.0, 200.0]
        result = PROBE.inventory_payload(payload)
        self.assertFalse(result["required_variables_complete"])
        self.assertIn("comprimento", " ".join(result["variables"]["cape"]["issues"]))

    def test_nonfinite_values_are_not_numeric(self):
        payload = fixture_payload()
        payload["hourly"]["cape"] = [100.0, float("nan"), float("inf")]
        result = PROBE.inventory_payload(payload)
        self.assertEqual(result["variables"]["cape"]["numeric_count"], 1)
        self.assertEqual(result["variables"]["cape"]["missing_count"], 2)

    def test_bad_payload_shape_is_reported(self):
        result = PROBE.inventory_payload({"hourly": []})
        self.assertFalse(result["valid_structure"])
        self.assertFalse(result["required_variables_complete"])

    def test_expected_api_units_are_explicit(self):
        self.assertEqual(PROBE.EXPECTED_UNITS["cape"], "J/kg")
        self.assertEqual(PROBE.EXPECTED_UNITS["wind_speed_925hPa"], "m/s")
        self.assertEqual(PROBE.EXPECTED_UNITS["wind_direction_500hPa"], "°")
        self.assertEqual(PROBE.EXPECTED_UNITS["wet_bulb_temperature_2m"], "°C")


if __name__ == "__main__":
    unittest.main(verbosity=2)
