from copy import deepcopy
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import requests
from django.core.cache import cache
from django.test import SimpleTestCase

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
            "elevation": 850.0,
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
        response.raise_for_status.return_value = None
        return response

    def _service_for_locations(self, points, locations):
        """Mock individual responses selected by the originating point ID."""
        locations_by_requested_coordinate = {
            (f"{point['latitude']:.6f}", f"{point['longitude']:.6f}"):
                locations[point["id"]]
            for point in points
        }

        def response_for_request(_url, *, params, timeout):
            self.assertEqual(timeout, HailMeteorologicalInputService.TIMEOUT_SECONDS)
            self.assertNotIn(",", params["latitude"])
            self.assertNotIn(",", params["longitude"])
            key = (params["latitude"], params["longitude"])
            return self._http_response(locations_by_requested_coordinate[key])

        http_get = Mock(side_effect=response_for_request)
        return HailMeteorologicalInputService(http_get=http_get), http_get

    def _locations_for_points(self, points, capes=None):
        capes = capes or [100.0] * len(points)
        return {
            point["id"]: self._api_location(
                point["latitude"],
                point["longitude"],
                capes[index],
            )
            for index, point in enumerate(points)
        }

    def test_six_municipalities_use_six_individual_requests_and_keep_id(self):
        points = self._point_inputs()
        capes = (650.0, 740.0, 1070.0, 560.0, 820.0, 390.0)
        locations = self._locations_for_points(points, capes)

        service, http_get = self._service_for_locations(points, locations)
        with self.assertLogs(
            "clima.services.hail_meteorological_input_service",
            level="INFO",
        ) as captured_logs:
            acquired = service.fetch_for_points(points)

        self.assertEqual(len(acquired), 6)
        self.assertEqual(set(acquired), {point["id"] for point in points})
        self.assertEqual(http_get.call_count, 6)
        log_output = "\n".join(captured_logs.output)
        self.assertIn("requests=6", log_output)
        for point in points:
            self.assertIn(f"municipio_id={point['id']}", log_output)
            self.assertNotIn(point["nome"], log_output)

        requested_coordinates = {
            (call.kwargs["params"]["latitude"], call.kwargs["params"]["longitude"])
            for call in http_get.call_args_list
        }
        self.assertEqual(
            requested_coordinates,
            {
                (f"{point['latitude']:.6f}", f"{point['longitude']:.6f}")
                for point in points
            },
        )

        for index, point in enumerate(points):
            expected_cape = capes[index]
            with self.subTest(municipality=point["nome"]):
                entry = acquired[point["id"]]
                self.assertEqual(entry["series"]["cape"], expected_cape)
                self.assertEqual(
                    entry["provenance"]["requested_latitude"],
                    point["latitude"],
                )
                self.assertEqual(
                    entry["provenance"]["requested_longitude"],
                    point["longitude"],
                )
                self.assertEqual(
                    entry["provenance"]["model_grid_latitude"],
                    point["latitude"],
                )
                self.assertEqual(entry["valid_from"], self.valid_time)
                self.assertEqual(entry["valid_to"], self.valid_time)
                self.assertEqual(
                    entry["provenance"]["unit_contract"]["cape"],
                    "J/kg",
                )
                self.assertEqual(
                    entry["provenance"]["unit_contract"]["wind_speed_925hPa"],
                    "m/s",
                )

    def test_same_grid_municipalities_preserve_distinct_returned_series(self):
        points = self._point_inputs()
        locations = self._locations_for_points(
            points,
            [100.0 + point["id"] for point in points],
        )

        # A mesma grade retornada não autoriza deduplicar nem substituir
        # a série de um município pela série do outro.
        shared_latitude = -21.95
        shared_longitude = -46.75
        locations[points[0]["id"]]["latitude"] = shared_latitude
        locations[points[0]["id"]]["longitude"] = shared_longitude
        locations[points[1]["id"]]["latitude"] = shared_latitude
        locations[points[1]["id"]]["longitude"] = shared_longitude
        locations[points[0]["id"]]["hourly"]["cape"] = [321.0]
        locations[points[1]["id"]]["hourly"]["cape"] = [987.0]

        service, http_get = self._service_for_locations(points, locations)
        acquired = service.fetch_for_points(points)

        self.assertEqual(http_get.call_count, 6)
        self.assertEqual(acquired[points[0]["id"]]["series"]["cape"], 321.0)
        self.assertEqual(acquired[points[1]["id"]]["series"]["cape"], 987.0)
        self.assertEqual(
            acquired[points[0]["id"]]["provenance"]["model_grid_latitude"],
            acquired[points[1]["id"]]["provenance"]["model_grid_latitude"],
        )
        self.assertEqual(
            acquired[points[0]["id"]]["provenance"]["model_grid_longitude"],
            acquired[points[1]["id"]]["provenance"]["model_grid_longitude"],
        )
        self.assertNotEqual(
            acquired[points[0]["id"]]["provenance"]["requested_longitude"],
            acquired[points[1]["id"]]["provenance"]["requested_longitude"],
        )

    def test_malformed_individual_response_is_omitted_without_shifting_others(self):
        points = self._point_inputs()
        locations = self._locations_for_points(points)
        locations[points[2]["id"]] = {
            "error": True,
            "reason": "invalid location response",
        }
        service, http_get = self._service_for_locations(points, locations)

        acquired = service.fetch_for_points(points)

        self.assertEqual(http_get.call_count, 6)
        self.assertNotIn(points[2]["id"], acquired)
        self.assertEqual(
            set(acquired),
            {point["id"] for index, point in enumerate(points) if index != 2},
        )
        for index, point in enumerate(points):
            if index != 2:
                self.assertEqual(acquired[point["id"]]["series"]["cape"], 100.0)

    def test_failure_for_one_municipality_does_not_shift_other_responses(self):
        points = self._point_inputs()
        locations = self._locations_for_points(
            points,
            [200.0 + index for index, _point in enumerate(points)],
        )
        service, http_get = self._service_for_locations(points, locations)
        original_side_effect = http_get.side_effect
        failed_key = (
            f"{points[2]['latitude']:.6f}",
            f"{points[2]['longitude']:.6f}",
        )

        def fail_only_third_request(url, *, params, timeout):
            if (params["latitude"], params["longitude"]) == failed_key:
                response = Mock()
                response.status_code = 400
                raise requests.HTTPError(
                    "invalid request",
                    response=response,
                )
            return original_side_effect(url, params=params, timeout=timeout)

        http_get.side_effect = fail_only_third_request
        acquired = service.fetch_for_points(points)

        self.assertEqual(http_get.call_count, 6)
        self.assertNotIn(points[2]["id"], acquired)
        for index, point in enumerate(points):
            if index != 2:
                self.assertEqual(
                    acquired[point["id"]]["series"]["cape"],
                    200.0 + index,
                )

    def test_single_location_list_response_is_malformed_and_not_associated(self):
        points = self._point_inputs()
        locations = self._locations_for_points(
            points,
            [300.0 + index for index, _point in enumerate(points)],
        )
        locations[points[4]["id"]] = [locations[points[4]["id"]]]
        service, http_get = self._service_for_locations(points, locations)

        acquired = service.fetch_for_points(points)

        self.assertEqual(http_get.call_count, 6)
        self.assertNotIn(points[4]["id"], acquired)
        for index, point in enumerate(points):
            if index != 4:
                self.assertEqual(
                    acquired[point["id"]]["series"]["cape"],
                    300.0 + index,
                )

    def test_missing_grid_coordinates_fail_only_for_that_municipality(self):
        points = self._point_inputs()
        locations = self._locations_for_points(points)
        locations[points[0]["id"]].pop("latitude")
        service, http_get = self._service_for_locations(points, locations)

        acquired = service.fetch_for_points(points)

        self.assertEqual(http_get.call_count, 6)
        self.assertNotIn(points[0]["id"], acquired)
        self.assertEqual(len(acquired), 5)

    def test_invalid_grid_coordinates_fail_only_for_that_municipality(self):
        points = self._point_inputs()
        locations = self._locations_for_points(points)
        locations[points[0]["id"]]["longitude"] = 999.0
        service, http_get = self._service_for_locations(points, locations)

        acquired = service.fetch_for_points(points)

        self.assertEqual(http_get.call_count, 6)
        self.assertNotIn(points[0]["id"], acquired)
        self.assertEqual(len(acquired), 5)

    def test_municipality_without_coordinates_receives_no_data_or_request(self):
        points = self._point_inputs()
        points[0]["latitude"] = None
        valid_points = self._point_inputs()[1:]
        locations = self._locations_for_points(valid_points)
        service, http_get = self._service_for_locations(valid_points, locations)

        acquired = service.fetch_for_points(points)

        self.assertNotIn(points[0]["id"], acquired)
        self.assertEqual(set(acquired), {point["id"] for point in points[1:]})
        self.assertEqual(http_get.call_count, 5)

    def test_duplicate_municipal_ids_fail_closed(self):
        points = self._point_inputs()
        points[1]["id"] = points[0]["id"]
        http_get = Mock()
        service = HailMeteorologicalInputService(http_get=http_get)

        with self.assertRaisesRegex(ValueError, "IDs municipais duplicados"):
            service.fetch_for_points(points)
        http_get.assert_not_called()

    def test_source_run_and_grid_elevation_are_preserved_when_returned(self):
        service = HailMeteorologicalInputService(http_get=Mock())
        payload = self._api_location(-21.9, -46.7, 200.0)

        entry = service._normalise_location(payload)
        self.assertIsNone(entry["provenance"]["source_run"])

        payload["model_run"] = "2026-10-15T00:00Z"
        entry = service._normalise_location(payload)
        self.assertEqual(
            entry["provenance"]["source_run"],
            "2026-10-15T00:00Z",
        )
        self.assertEqual(
            entry["provenance"]["model_grid_elevation"],
            850.0,
        )

    def test_individual_result_keeps_request_and_provider_metadata(self):
        point = self._point_inputs()[0]
        location = self._api_location(
            point["latitude"] + 0.01,
            point["longitude"] - 0.01,
            765.0,
        )
        location["model_run"] = "2026-11-01T00:00Z"
        service, http_get = self._service_for_locations(
            [point],
            {point["id"]: location},
        )

        result = service.fetch_for_points([point])[point["id"]]

        self.assertEqual(http_get.call_count, 1)
        self.assertEqual(
            http_get.call_args.kwargs["params"]["latitude"],
            f"{point['latitude']:.6f}",
        )
        self.assertEqual(
            http_get.call_args.kwargs["params"]["longitude"],
            f"{point['longitude']:.6f}",
        )
        provenance = result["provenance"]
        self.assertEqual(provenance["source"], HailMeteorologicalInputService.SOURCE)
        self.assertEqual(provenance["model"], HailMeteorologicalInputService.MODEL)
        self.assertEqual(provenance["source_run"], "2026-11-01T00:00Z")
        self.assertEqual(provenance["requested_latitude"], point["latitude"])
        self.assertEqual(provenance["requested_longitude"], point["longitude"])
        self.assertEqual(provenance["model_grid_latitude"], location["latitude"])
        self.assertEqual(provenance["model_grid_longitude"], location["longitude"])
        self.assertEqual(provenance["model_grid_elevation"], 850.0)
        self.assertEqual(result["valid_from"], self.valid_time)
        self.assertEqual(result["valid_to"], self.valid_time)

    def test_missing_required_variable_is_marked_incomplete_not_classified(self):
        points = self._point_inputs()
        locations = self._locations_for_points(points)
        locations[points[0]["id"]]["hourly"]["wind_speed_925hPa"] = [None]

        service, http_get = self._service_for_locations(points, locations)
        with patch(
            "clima.services.hail_meteorological_input_service.cache.set"
        ) as cache_set:
            acquired = service.fetch_for_points(points)
        entry = acquired[points[0]["id"]]

        cached_ids = {
            next(iter(call.args[1]))
            for call in cache_set.call_args_list
        }
        self.assertNotIn(points[0]["id"], cached_ids)
        self.assertEqual(
            cached_ids,
            {point["id"] for point in points[1:]},
        )
        self.assertEqual(http_get.call_count, 6)
        self.assertFalse(entry["provenance"]["required_variables_complete"])
        self.assertIsNone(entry["series"]["wind_speed_925hPa"])
        canonical = HailPotentialService().evaluate(entry).as_dict()
        result = HailPotentialExperimentalEvaluator().evaluate(canonical)
        self.assertIsNone(result["potential_level"])

    def test_six_acquired_series_flow_independently_through_evaluator(self):
        points = self._point_inputs()
        capes = (650.0, 740.0, 1070.0, 560.0, 820.0, 390.0)
        locations = self._locations_for_points(points, capes)
        service, http_get = self._service_for_locations(points, locations)
        acquired = service.fetch_for_points(points)
        self.assertEqual(http_get.call_count, 6)

        canonical_service = HailPotentialService()
        evaluator = HailPotentialExperimentalEvaluator()
        outputs = {}

        for point in points:
            canonical = canonical_service.evaluate(
                acquired[point["id"]]
            ).as_dict()
            outputs[point["id"]] = evaluator.evaluate(canonical)

        self.assertEqual(len(outputs), 6)
        for index, point in enumerate(points):
            expected_cape = capes[index]
            output = outputs[point["id"]]
            self.assertEqual(
                output["axes"]["instability"]["evidence"]["value"],
                expected_cape,
            )
            self.assertTrue(output["diagnostics_complete"])
            self.assertIsNone(output["potential_level"])

    def test_transient_http_failure_is_retried(self):
        points = self._point_inputs()
        locations = self._locations_for_points(points)
        service, http_get = self._service_for_locations(points, locations)
        original_side_effect = http_get.side_effect
        first_requested_key = (
            f"{points[0]['latitude']:.6f}",
            f"{points[0]['longitude']:.6f}",
        )
        first_attempt = {"failed": False}

        def fail_once_for_first_municipality(url, *, params, timeout):
            if (
                (params["latitude"], params["longitude"]) == first_requested_key
                and not first_attempt["failed"]
            ):
                first_attempt["failed"] = True
                raise requests.ConnectionError("falha transitória")
            return original_side_effect(url, params=params, timeout=timeout)

        http_get.side_effect = fail_once_for_first_municipality

        with patch(
            "clima.services.hail_meteorological_input_service.cache.get",
            return_value=None,
        ), patch(
            "clima.services.hail_meteorological_input_service.cache.set"
        ), patch(
            "clima.services.hail_meteorological_input_service.time.sleep"
        ):
            result = service.fetch_for_points(points)

        self.assertEqual(http_get.call_count, 7)
        self.assertEqual(set(result), {point["id"] for point in points})
        first_municipality_calls = [
            call for call in http_get.call_args_list
            if call.kwargs["params"]["latitude"] == first_requested_key[0]
        ]
        self.assertEqual(len(first_municipality_calls), 2)
        self.assertEqual(
            {
                (
                    call.kwargs["params"]["latitude"],
                    call.kwargs["params"]["longitude"],
                )
                for call in first_municipality_calls
            },
            {first_requested_key},
        )

    def test_429_and_5xx_retry_only_the_originating_municipality(self):
        points = self._point_inputs()
        locations = self._locations_for_points(points)
        first_key = (
            f"{points[0]['latitude']:.6f}",
            f"{points[0]['longitude']:.6f}",
        )

        for status_code in (429, 500, 503):
            with self.subTest(status_code=status_code):
                service, http_get = self._service_for_locations(points, locations)
                original_side_effect = http_get.side_effect
                first_attempt = {"failed": False}

                def fail_once_for_first_municipality(
                    url,
                    *,
                    params,
                    timeout,
                    _status_code=status_code,
                ):
                    if (
                        (params["latitude"], params["longitude"]) == first_key
                        and not first_attempt["failed"]
                    ):
                        first_attempt["failed"] = True
                        response = Mock()
                        response.status_code = _status_code
                        raise requests.HTTPError(
                            "transient provider status",
                            response=response,
                        )
                    return original_side_effect(
                        url,
                        params=params,
                        timeout=timeout,
                    )

                http_get.side_effect = fail_once_for_first_municipality
                with patch(
                    "clima.services.hail_meteorological_input_service.cache.get",
                    return_value=None,
                ), patch(
                    "clima.services.hail_meteorological_input_service.cache.set"
                ), patch(
                    "clima.services.hail_meteorological_input_service.time.sleep"
                ):
                    acquired = service.fetch_for_points(points)

                self.assertEqual(set(acquired), {point["id"] for point in points})
                self.assertEqual(http_get.call_count, 7)
                repeated_first_requests = [
                    call for call in http_get.call_args_list
                    if call.kwargs["params"]["latitude"] == first_key[0]
                ]
                self.assertEqual(len(repeated_first_requests), 2)
                self.assertEqual(
                    {
                        (
                            call.kwargs["params"]["latitude"],
                            call.kwargs["params"]["longitude"],
                        )
                        for call in repeated_first_requests
                    },
                    {first_key},
                )

    def test_cache_keeps_900_second_ttl_and_avoids_second_http_call(self):
        points = self._point_inputs()
        locations = self._locations_for_points(points)
        service, http_get = self._service_for_locations(points, locations)
        cache_value = {}
        cache_get = Mock(
            side_effect=lambda key: deepcopy(cache_value.get(key))
        )

        def cache_set(key, value, timeout):
            self.assertEqual(timeout, 900)
            self.assertEqual(len(value), 1)
            cache_value[key] = deepcopy(value)

        with patch(
            "clima.services.hail_meteorological_input_service.cache.get",
            cache_get,
        ), patch(
            "clima.services.hail_meteorological_input_service.cache.set",
            cache_set,
        ):
            first = service.fetch_for_points(points)
            second = service.fetch_for_points(points)

        self.assertEqual(http_get.call_count, 6)
        self.assertEqual(first[3]["provenance"]["cache_status"], "MISS")
        self.assertEqual(second[3]["provenance"]["cache_status"], "HIT")
        self.assertIn("cache_created_at", second[3]["provenance"])
        self.assertEqual(
            second[3]["provenance"]["cache_ttl_seconds"],
            900,
        )
        self.assertEqual(len(cache_value), 6)
        self.assertEqual(len(set(cache_get.call_args_list[index].args[0] for index in range(6))), 6)

        # Reusing the same coordinates under another municipal ID is a cache
        # miss; an entry cannot cross the municipal identity boundary.
        other_id_point = {**points[0], "id": 99}
        other_id_result = service.fetch_for_points([other_id_point])
        self.assertEqual(other_id_result[99]["series"]["cape"], 100.0)
        self.assertEqual(other_id_result[99]["provenance"]["cache_status"], "MISS")
        self.assertEqual(http_get.call_count, 7)

    def test_reference_time_selects_same_valid_hour_deterministically(self):
        reference = datetime(2026, 10, 30, 10, 30)
        times = [
            "2026-10-30T10:00",
            "2026-10-30T11:00",
            "2026-10-30T12:00",
        ]

        selected = HailMeteorologicalInputService._select_valid_index(
            times,
            reference_time=reference,
        )

        self.assertEqual(selected, 1)

    def test_no_future_or_current_timestamp_returns_none(self):
        reference = datetime(2026, 10, 30, 12, 30)
        times = [
            "2026-10-30T10:00",
            "2026-10-30T11:00",
        ]

        self.assertIsNone(
            HailMeteorologicalInputService._select_valid_index(
                times,
                reference_time=reference,
            )
        )
