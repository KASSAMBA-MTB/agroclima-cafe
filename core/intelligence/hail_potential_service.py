"""
MP-01.11 — Serviço de avaliação do potencial meteorológico de granizo.

Versão 1.0

Responsabilidade:
- consumir o contrato meteorológico já validado;
- verificar os dados mínimos;
- calcular cisalhamento vetorial 925–500 hPa;
- calcular CAPE-SHEAR;
- produzir drivers, qualidade e proveniência;
- retornar ASSESSED ou INSUFFICIENT_DATA.

Não responsabilidade:
- não define threshold de granizo;
- não calcula probabilidade;
- não cria score 0–100;
- não altera FRI;
- não acessa ORM;
- não chama API;
- não altera DashboardService.
"""

from math import cos, radians, sin, sqrt

from core.intelligence.hail_potential_contract import (
    ASSESSMENT_ASSESSED,
    ASSESSMENT_INSUFFICIENT,
    HailPotentialContract,
    REQUIRED_VARIABLES,
    is_number,
    METHOD_VERSION,
)


class HailPotentialService:
    """Avalia o ambiente meteorológico necessário ao MP-01.11."""

    METHOD_VERSION = METHOD_VERSION
    RULE_ID = "HAIL_POTENTIAL_001"

    def evaluate(self, context):
        if not isinstance(context, dict):
            context = {}

        series = self._extract_series(context)

        missing = tuple(
            variable
            for variable in REQUIRED_VARIABLES
            if not self._has_usable_value(series.get(variable))
        )

        provenance = self._provenance(context)

        if missing:
            return HailPotentialContract(
                assessment_status=ASSESSMENT_INSUFFICIENT,
                potential_level=None,
                method_version=self.METHOD_VERSION,
                source=provenance["source"],
                model=provenance["model"],
                source_run=provenance["source_run"],
                valid_from=context.get("valid_from"),
                valid_to=context.get("valid_to"),
                required_variables=REQUIRED_VARIABLES,
                missing_variables=missing,
                drivers=(),
                data_quality={
                    "required_variables_complete": False,
                    "missing_variables": list(missing),
                    "available_required_variables": [
                        v for v in REQUIRED_VARIABLES if v not in missing
                    ],
                },
                derived={},
                complementary_values=self._complementary_values(series),
            )

        shear = self._calculate_shear(
            series["wind_speed_925hPa"],
            series["wind_direction_925hPa"],
            series["wind_speed_500hPa"],
            series["wind_direction_500hPa"],
        )

        cape = float(series["cape"])
        cape_shear = cape * shear

        drivers = (
            {
                "variable": "cape",
                "observed_value": cape,
                "unit": "J/kg",
                "rule_id": self.RULE_ID,
                "rule_version": self.METHOD_VERSION,
                "role": "instability",
            },
            {
                "variable": "shear_925_500",
                "observed_value": shear,
                "unit": "m/s",
                "rule_id": self.RULE_ID,
                "rule_version": self.METHOD_VERSION,
                "role": "vertical_wind_shear",
            },
            {
                "variable": "cape_shear",
                "observed_value": cape_shear,
                "unit": "J/kg*m/s",
                "rule_id": self.RULE_ID,
                "rule_version": self.METHOD_VERSION,
                "role": "combined_environment",
            },
        )

        return HailPotentialContract(
            assessment_status=ASSESSMENT_ASSESSED,
            # Classificação normativa deliberadamente não atribuída.
            potential_level=None,
            method_version=self.METHOD_VERSION,
            source=provenance["source"],
            model=provenance["model"],
            source_run=provenance["source_run"],
            valid_from=context.get("valid_from"),
            valid_to=context.get("valid_to"),
            required_variables=REQUIRED_VARIABLES,
            missing_variables=(),
            drivers=drivers,
            data_quality={
                "required_variables_complete": True,
                "missing_variables": [],
                "complementary_variables": {
                    variable: value is not None
                    for variable, value in self._complementary_values(series).items()
                },
            },
            derived={
                "shear_925_500_ms": shear,
                "cape_shear": cape_shear,
            },
            complementary_values=self._complementary_values(series),
        )

    @staticmethod
    def _extract_series(context):
        series = context.get("series")
        if isinstance(series, dict):
            return {
                key: HailPotentialService._extract_value(value)
                for key, value in series.items()
            }

        # Compatibilidade com contexto plano.
        return {
            key: HailPotentialService._extract_value(context.get(key))
            for key in REQUIRED_VARIABLES
        } | {
            key: HailPotentialService._extract_value(context.get(key))
            for key in (
                "wet_bulb_temperature_2m",
                "temperature_850hPa",
                "relative_humidity_850hPa",
            )
        }

    @staticmethod
    def _extract_value(value):
        if isinstance(value, dict):
            if "value" in value:
                return value.get("value")
            if "values" in value and isinstance(value["values"], list):
                values = value["values"]
                return values[0] if values else None
        return value

    @staticmethod
    def _has_usable_value(value):
        return is_number(value)

    @staticmethod
    def _complementary_values(series):
        """Preserva valores numéricos; dados ausentes não viram zero."""
        variables = (
            "wet_bulb_temperature_2m",
            "temperature_850hPa",
            "relative_humidity_850hPa",
        )
        return {
            variable: float(series[variable])
            if HailPotentialService._has_usable_value(series.get(variable))
            else None
            for variable in variables
        }

    @staticmethod
    def _vector(speed, direction):
        angle = radians(float(direction))
        return (
            float(speed) * sin(angle),
            float(speed) * cos(angle),
        )

    @classmethod
    def _calculate_shear(
        cls,
        speed_925,
        direction_925,
        speed_500,
        direction_500,
    ):
        u925, v925 = cls._vector(speed_925, direction_925)
        u500, v500 = cls._vector(speed_500, direction_500)
        return sqrt((u500 - u925) ** 2 + (v500 - v925) ** 2)

    @staticmethod
    def _provenance(context):
        provenance = context.get("provenance")
        if not isinstance(provenance, dict):
            provenance = {}

        return {
            "source": (
                provenance.get("source")
                or context.get("source")
            ),
            "model": (
                provenance.get("model")
                or context.get("model")
            ),
            "source_run": (
                provenance.get("source_run")
                or context.get("source_run")
            ),
        }
