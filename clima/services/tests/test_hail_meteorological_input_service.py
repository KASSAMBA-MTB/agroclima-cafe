from copy import deepcopy
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase
from django.core.cache import cache

from clima.services.hail_meteorological_input_service import (
    HailMeteorologicalInputService,
)
from core.intelligence.hail_potential_experimental_evaluator import (
    HailPotentialExperimentalEvaluator,
)
from core.intelligence.hail_potential_service import HailPotentialService


class HailMeteorologicalInputServiceTests(SimpleTestCase):
    MUNICIPALITIES = (
        (3, "Águas da Prata", -21.9319, -46.7178),
        (5, "Andradas", -22.0686, -46.5724),
        (2, "Espírito Santo do Pinhal", -22.1900, -46.7478),
        (6, "Poços de Caldas", -21.7874, -46.5614),
        (1, "São João da Boa Vista", -21.9699, -46.7981),
        (4, "Vargem Grande do Sul", -21.8322, -46.8925),
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        local_now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        cls.valid_time = (local_now + timedelta(hours=3)).replace(
            minute=0, second=0, microsecond=0, tzinfo=None
        ).isoformat(timespec="minutes")

    def setUp(self):
        # Tests isolate this process-local cache; the application server's
        # separate LocMemCache process is never touched.
        cache.clear()

    def _point_inputs(self):
        return [
            {"id": pk, "nome": name, "latitude": lat, "longitude": lon}
            for pk, name, lat, lon in self.MUNICIPALITIES
        ]

    def _api_location(self, latitude, longitude, cape):
        return {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "America/Sao_Paulo",
            "hourly": {
                "time": [self.valid_time],
                "cape": [cape],
                "wind_speed_925hPa": [4.0],
                "wind_direction_925hPa": [0.0],
                "wind_speed_500hPa": [14.0],
                "wind_direction_500hPa": [90.0],
                "wet_bulb_temperature_2m": [15.0],
                "temperature_850hPa": [9.0],
                "relative_humidity_850hPa": [75.0],
            },
        }

    @staticmethod
    def _http_response(locations):
        response = Mock()
        response.json.return_value = locations
        return response

    def test_six_municipalities_are_associated_by_grid_not_response_order(self):
        points = self._point_inputs()
        capes = (650.0, 740.0, 1070.0, 560.0, 650.0, 390.0)
        locations = [
            self._api_location(point["latitude"], point["longitude"], cape)
            for point, cape in zip(points, capes)
        ]
        response = self._http_response(list(reversed(locations)))
        service = HailMeteorologicalInputService(http_get=Mock(return_value=response))

        acquired = service.fetch_for_points(points)

        self.assertEqual(len(acquired), 6)
        for point, expected_cape in zip(points, capes):
            with self.subTest(municipality=point["nome"]):
                entry = acquired[point["id"]]
                self.assertEqual(entry["series"]["cape"], expected_cape)
                self.assertEqual(
                    entry["provenance"]["requested_latitude"],
                    point["latitude"],
                )
                self.assertEqual(
                    entry["provenance"]["model_grid_latitude"],
                    point["latitude"],
                )

        # Equal observations for two municipalities are valid evidence, not
        # proof of a swapped association.
        self.assertEqual(acquired[3]["series"]["cape"], acquired[1]["series"]["cape"])

    def test_two_municipalities_on_same_grid_receive_same_grid_series(self):
        points = self._point_inputs()
        shared_grid = (-21.95, -46.75)
        locations = []
        for point in points:
            grid = (
                shared_grid
                if point["id"] in {3, 1}
                else (point["latitude"], point["longitude"])
            )
            locations.append(
                self._api_location(grid[0], grid[1], 500.0 if grid == shared_grid else 100.0 + point["id"])
            )
        acquired = HailMeteorologicalInputService(
            http_get=Mock(return_value=self._http_response(locations))
        ).fetch_for_points(points)

        self.assertEqual(acquired[3]["series"]["cape"], 500.0)
        self.assertEqual(acquired[1]["series"]["cape"], 500.0)
        self.assertEqual(
            acquired[3]["provenance"]["model_grid_longitude"],
            acquired[1]["provenance"]["model_grid_longitude"],
        )
        self.assertNotEqual(
            acquired[3]["provenance"]["requested_longitude"],
            acquired[1]["provenance"]["requested_longitude"],
        )

    def test_grid_association_ambiguity_fails_closed(self):
        points = [
            {"id": 1, "latitude": 0.0, "longitude": -1.0},
            {"id": 2, "latitude": 0.0, "longitude": 0.0},
        ]
        locations = [
            self._api_location(0.0, -0.5, 100.0),
            self._api_location(0.0, 0.5, 100.0),
        ]
        service = HailMeteorologicalInputService(
            http_get=Mock(return_value=self._http_response(locations))
        )
        with self.assertRaisesRegex(ValueError, "ambígua"):
            service.fetch_for_points(points)

    def test_missing_grid_coordinates_fail_without_positional_fallback(self):
        points = self._point_inputs()
        locations = [
            self._api_location(point["latitude"], point["longitude"], 100.0)
            for point in points
        ]
        locations[0].pop("latitude")
        service = HailMeteorologicalInputService(
            http_get=Mock(return_value=self._http_response(locations))
        )
        with self.assertRaisesRegex(ValueError, "coordenadas de grade"):
            service.fetch_for_points(points)

    def test_source_run_is_preserved_only_when_returned(self):
        service = HailMeteorologicalInputService(http_get=Mock())
        payload = self._api_location(-21.9, -46.7, 200.0)
        self.assertIsNone(service._normalise_location(payload)["provenance"]["source_run"])
        payload["model_run"] = "2026-10-15T00:00Z"
        self.assertEqual(
            service._normalise_location(payload)["provenance"]["source_run"],
            "2026-10-15T00:00Z",
        )

    def test_six_acquired_series_flow_independently_through_evaluator(self):
        points = self._point_inputs()
        capes = (650.0, 740.0, 1070.0, 560.0, 650.0, 390.0)
        locations = [
            self._api_location(point["latitude"], point["longitude"], cape)
            for point, cape in zip(points, capes)
        ]
        acquired = HailMeteorologicalInputService(
            http_get=Mock(return_value=self._http_response(locations))
        ).fetch_for_points(points)
        canonical_service = HailPotentialService()
        evaluator = HailPotentialExperimentalEvaluator()
        outputs = {}
        for point in points:
            canonical = canonical_service.evaluate(acquired[point["id"]]).as_dict()
            outputs[point["id"]] = evaluator.evaluate(canonical)

        self.assertEqual(len(outputs), 6)
        for point, expected_cape in zip(points, capes):
            output = outputs[point["id"]]
            self.assertEqual(output["axes"]["instability"]["evidence"]["value"], expected_cape)
            self.assertTrue(output["diagnostics_complete"])
            self.assertIsNone(output["potential_level"])
        self.assertEqual(
            outputs[3]["axes"]["instability"]["evidence"]["value"],
            outputs[1]["axes"]["instability"]["evidence"]["value"],
        )

    def test_transient_http_failure_is_retried(self):
        import requests
        from unittest.mock import Mock, patch

        points = self._point_inputs()
        locations = [
            self._api_location(point["latitude"], point["longitude"], 100.0)
            for point in points
        ]
        response = self._http_response(locations)
        http_get = Mock(
            side_effect=[
                requests.ConnectionError("falha transit?ria"),
                response,
            ]
        )
        service = HailMeteorologicalInputService(http_get=http_get)

        with patch(
            "clima.services.hail_meteorological_input_service.cache.get",
            return_value=None,
        ), patch(
            "clima.services.hail_meteorological_input_service.cache.set"
        ), patch("time.sleep"):
            result = service.fetch_for_points(points)

        self.assertEqual(http_get.call_count, 2)
        self.assertEqual(set(result), {point["id"] for point in points})

    def test_cache_keeps_900_second_ttl_and_avoids_second_http_call(self):
        points = self._point_inputs()
        locations = [
            self._api_location(point["latitude"], point["longitude"], 100.0)
            for point in points
        ]
        response = self._http_response(locations)
        http_get = Mock(return_value=response)
        service = HailMeteorologicalInputService(http_get=http_get)
        cache_value = {}
        cache_get = Mock(side_effect=lambda key: deepcopy(cache_value) or None)

        def cache_set(key, value, timeout):
            self.assertEqual(timeout, 900)
            cache_value.update(deepcopy(value))

        with patch("clima.services.hail_meteorological_input_service.cache.get", cache_get), patch(
            "clima.services.hail_meteorological_input_service.cache.set", cache_set
        ):
            first = service.fetch_for_points(points)
            second = service.fetch_for_points(points)

        self.assertEqual(http_get.call_count, 1)
        self.assertEqual(first[3]["provenance"]["cache_status"], "MISS")
        self.assertEqual(second[3]["provenance"]["cache_status"], "HIT")
        self.assertIn("cache_created_at", second[3]["provenance"])
        self.assertEqual(second[3]["provenance"]["cache_ttl_seconds"], 900)

    def test_same_grid_entries_with_different_values_fail_closed(self):
        points = self._point_inputs()
        locations = [
            self._api_location(point["latitude"], point["longitude"], 100.0)
            for point in points
        ]
        locations[1]["latitude"] = locations[0]["latitude"]
        locations[1]["longitude"] = locations[0]["longitude"]
        locations[1]["hourly"]["cape"] = [999.0]
        service = HailMeteorologicalInputService(
            http_get=Mock(return_value=self._http_response(locations))
        )
        with self.assertRaisesRegex(ValueError, "séries divergentes"):
            service.fetch_for_points(points)
