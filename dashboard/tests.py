from django.template import Context, TemplateDoesNotExist, engines
from django.test import SimpleTestCase
from django.template.loader import get_template


class HailDashboardPanelTests(SimpleTestCase):
    def test_panel_renders_real_municipal_hail_evidence_without_operational_classification(self):
        point = {
            "id": 17,
            "nome": "Município de teste",
            "hail_potential_evaluation": {
                "assessment_status": "ASSESSED",
                "potential_level": None,
                "drivers": [
                    {"variable": "cape", "observed_value": 1200, "unit": "J/kg"},
                ],
                "derived": {
                    "shear_925_500_ms": 18.5,
                    "cape_shear": 22200,
                },
                "model": "ecmwf_ifs025",
                "valid_from": "2026-10-15T12:00",
                "missing_variables": [],
            },
        }
        rendered = get_template(
            "dashboard/components/hail_panel.html"
        ).render(Context({"map_points": [point]}))

        self.assertIn("Granizo — evidências meteorológicas", rendered)
        self.assertIn("Município de teste", rendered)
        self.assertIn("1200 J/kg", rendered)
        self.assertIn("18.5 m/s", rendered)
        self.assertIn("22200", rendered)
        self.assertIn("ecmwf_ifs025", rendered)
        self.assertIn("2026-10-15T12:00", rendered)
        self.assertIn("não homologado", rendered.lower())
        self.assertNotIn("probabilidade de granizo: 0", rendered.lower())
