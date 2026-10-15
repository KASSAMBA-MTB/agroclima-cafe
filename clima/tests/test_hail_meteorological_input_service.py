from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from clima.services.hail_meteorological_input_service import (
    HailMeteorologicalInputService,
)


class HailMeteorologicalInputServiceTests(SimpleTestCase):
    @staticmethod
    def _location(offset=0, missing=None):
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        variables = HailMeteorologicalInputService.HOURLY_VARIABLES
        now = datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)
        hourly = {
            "time": [
                (now + timedelta(hours=1)).isoformat(timespec="minutes"),
                (now + timedelta(hours=2)).isoformat(timespec="minutes"),
            ]
        }
        for index, variable in enumerate(variables):
            hourly[variable] = [None if variable == missing else index + offset + 1,
                                index + offset + 2]
        return {
            "latitude": -21.75,
            "longitude": -46.55,
            "timezone": "America/Sao_Paulo",
            "hourly": hourly,
        }

    def test_selects_future_valid_time_instead_of_first_midnight_value(self):
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)
        times = [
            (now - timedelta(hours=12)).isoformat(timespec="minutes"),
            (now + timedelta(hours=1)).isoformat(timespec="minutes"),
            (now + timedelta(hours=2)).isoformat(timespec="minutes"),
        ]

        self.assertEqual(
            HailMeteorologicalInputService._select_valid_index(times),
            1,
        )

    def test_returns_no_index_when_no_valid_time_is_available(self):
        self.assertIsNone(
            HailMeteorologicalInputService._select_valid_index([])
        )
        self.assertIsNone(
            HailMeteorologicalInputService._select_valid_index(["not-a-date"])
        )

    @patch("clima.services.hail_meteorological_input_service.cache.set")
    @patch("clima.services.hail_meteorological_input_service.cache.get", return_value=None)
    def test_requests_all_municipalities_in_one_batch_and_normalises_required_values(
        self, _cache_get, cache_set
    ):
        response = Mock()
        response.json.return_value = [self._location(0), self._location(10)]
        response.raise_for_status.return_value = None
        http_get = Mock(return_value=response)
        service = HailMeteorologicalInputService(http_get=http_get)
        points = [
            {"id": 17, "latitude": -21.9, "longitude": -46.9},
            {"id": 18, "latitude": -22.0, "longitude": -47.0},
        ]

        result = service.fetch_for_points(points)

        self.assertEqual(set(result), {17, 18})
        self.assertEqual(http_get.call_count, 1)
        self.assertEqual(
            http_get.call_args.kwargs["params"]["models"],
            "ecmwf_ifs025",
        )
        self.assertEqual(
            result[17]["series"]["wind_speed_925hPa"],
            2.0,
        )
        self.assertEqual(
            result[18]["series"]["wind_speed_925hPa"],
            12.0,
        )
        self.assertEqual(
            result[17]["valid_from"],
            response.json.return_value[0]["hourly"]["time"][0],
        )
        self.assertTrue(
            result[17]["provenance"]["required_variables_complete"]
        )
        cache_set.assert_called_once()

    @patch("clima.services.hail_meteorological_input_service.cache.set")
    @patch("clima.services.hail_meteorological_input_service.cache.get", return_value=None)
    def test_missing_values_remain_none_and_are_marked_incomplete(
        self, _cache_get, _cache_set
    ):
        response = Mock()
        response.json.return_value = [self._location(missing="cape")]
        response.raise_for_status.return_value = None
        service = HailMeteorologicalInputService(http_get=Mock(return_value=response))

        result = service.fetch_for_points([
            {"id": 17, "latitude": -21.9, "longitude": -46.9},
        ])

        self.assertIsNone(result[17]["series"]["cape"])
        self.assertFalse(
            result[17]["provenance"]["required_variables_complete"]
        )

    @patch("clima.services.hail_meteorological_input_service.cache.get", return_value=None)
    def test_invalid_coordinates_do_not_trigger_api_request(self, _cache_get):
        http_get = Mock()
        service = HailMeteorologicalInputService(http_get=http_get)

        self.assertEqual(
            service.fetch_for_points([{"id": 17, "latitude": None, "longitude": -46.9}]),
            {},
        )
        http_get.assert_not_called()

    @patch("clima.services.hail_meteorological_input_service.cache.set")
    @patch("clima.services.hail_meteorological_input_service.cache.get")
    def test_cached_batch_avoids_a_second_api_request(self, cache_get, _cache_set):
        cached = {17: {"series": {"cape": 500}}}
        cache_get.return_value = cached
        http_get = Mock()
        service = HailMeteorologicalInputService(http_get=http_get)

        result = service.fetch_for_points([
            {"id": 17, "latitude": -21.9, "longitude": -46.9},
        ])

        self.assertEqual(result, cached)
        http_get.assert_not_called()
