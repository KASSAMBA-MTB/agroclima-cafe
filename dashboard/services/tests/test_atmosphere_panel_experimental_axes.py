from django.template.loader import render_to_string
from django.test import SimpleTestCase


class AtmospherePanelExperimentalAxesTests(SimpleTestCase):
    def test_panel_displays_backend_experimental_axes_without_classifying_hail(self):
        html = render_to_string(
            "dashboard/components/atmosphere_panel.html",
            {
                "hail_assessments": [{
                    "municipio_id": 17,
                    "municipio_nome": "Município de teste",
                    "assessment_status": "ASSESSED",
                    "potential_level": None,
                    "context_type": "meteorological_assessment",
                    "source": "open-meteo-forecast-api",
                    "model": "ecmwf_ifs025",
                    "method_version": "MP-01.12.3",
                    "valid_from": "2026-10-30T12:00",
                    "valid_to": "2026-10-30T12:00",
                    "derived": {
                        "shear_925_500_ms": 10.0,
                        "cape_shear": 900.0,
                    },
                    "municipal_result": {
                        "drivers": [
                            {
                                "variable": "cape",
                                "observed_value": 90.0,
                                "unit": "J/kg",
                            },
                            {
                                "variable": "shear_925_500",
                                "observed_value": 10.0,
                                "unit": "m/s",
                            },
                            {
                                "variable": "cape_shear",
                                "observed_value": 900.0,
                                "unit": "J/kg*m/s",
                            },
                        ],
                        "complementary_values": {
                            "wet_bulb_temperature_2m": 15.2,
                            "temperature_850hPa": 8.4,
                            "relative_humidity_850hPa": 78.0,
                        },
                        "experimental_evaluation": {
                            "method_version": "MP-01.12.3",
                            "evaluation_status": "EXPERIMENTAL_NOT_HOMOLOGATED",
                            "classification_status": "NOT_CLASSIFIED_NO_HOMOLOGATED_THRESHOLDS",
                            "diagnostics_complete": True,
                            "axes": {
                                "instability": {
                                    "status": "AVAILABLE",
                                    "evidence": {
                                        "value": 90.0,
                                        "unit": "J/kg",
                                    },
                                    "interpretation": "CAPE numérico recebido do serviço canônico.",
                                },
                                "organization_shear": {
                                    "status": "AVAILABLE",
                                    "evidence": {
                                        "value": 10.0,
                                        "unit": "m/s",
                                    },
                                    "interpretation": "Cisalhamento numérico recebido do serviço canônico.",
                                },
                                "combined_cape_shear": {
                                    "status": "AVAILABLE",
                                    "evidence": {
                                        "value": 900.0,
                                        "unit": "J/kg*m/s",
                                    },
                                    "interpretation": "Indicador informativo, sem classificação.",
                                },
                                "thermodynamics": {
                                    "status": "AVAILABLE",
                                    "values": {
                                        "wet_bulb_temperature_2m": {
                                            "value": 15.2,
                                            "unit": "°C",
                                        },
                                        "temperature_850hPa": {
                                            "value": 8.4,
                                            "unit": "°C",
                                        },
                                        "relative_humidity_850hPa": {
                                            "value": 78.0,
                                            "unit": "%",
                                        },
                                    },
                                    "interpretation": "Valores complementares disponíveis.",
                                },
                            },
                        },
                    },
                    "is_factual_event": False,
                    "classification_status": "NOT_CLASSIFIED",
                }],
            },
        )

        normalized_html = html.replace(",", ".")

        self.assertIn("Diagnóstico experimental", html)
        self.assertIn("MP-01.12.3", html)
        self.assertIn("Diagnóstico meteorológico completo", html)
        self.assertIn("Instabilidade (CAPE)", html)
        self.assertIn("Cisalhamento vertical (925–500 hPa)", html)
        self.assertIn("Indicador combinado CAPE", html)
        self.assertIn("Condições termodinâmicas complementares", html)
        self.assertIn("90.00", normalized_html)
        self.assertIn("10.00", normalized_html)
        self.assertIn("900.00", normalized_html)
        self.assertIn("15.20", normalized_html)
        self.assertIn("8.40", normalized_html)
        self.assertIn("78.00", normalized_html)

        # Cada valor deve aparecer uma unica vez, mesmo quando
        # os contratos legado e experimental possuem o mesmo dado.
        self.assertEqual(normalized_html.count("90.00"), 1)
        self.assertEqual(normalized_html.count("10.00"), 1)
        self.assertEqual(normalized_html.count("900.00"), 1)
        self.assertEqual(normalized_html.count("15.20"), 1)
        self.assertEqual(normalized_html.count("8.40"), 1)
        self.assertEqual(normalized_html.count("78.00"), 1)

        self.assertNotIn("<h4>Indicadores derivados</h4>", html)
        self.assertNotIn("<h4>Variáveis complementares</h4>", html)
        self.assertIn("Classificação de potencial: não homologada.", html)
        self.assertNotIn("ALTO", html)
        self.assertNotIn("CRÍTICO", html)
        self.assertNotIn("<details", html)
