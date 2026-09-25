"""
AgroClima Café

Pressão Hídrica Agroclimática — MP-01.5

Esta regra não cria uma nova fórmula de estresse hídrico.
Ela transforma o resultado canônico do balanço hídrico diário
de reservatório em uma interpretação agroclimática formal.

Fonte canônica:
    HydricBalanceService

Método aceito:
    REFERENCE_DAILY_RESERVOIR_BALANCE

Princípios:
    - não recalcula P, ETo, ARM, DEF ou EXC;
    - não cria limiares agronômicos arbitrários;
    - não transforma ausência em zero;
    - não utiliza P/ETo como índice de estresse;
    - não altera FROST_001 ou METEO_ALERT_001;
    - preserva município e data do contexto;
    - produz interpretação quantitativa rastreável.

Versão: 1.0
"""

from core.intelligence.base_rule import BaseRule


class HydricPressureRule(BaseRule):
    """Interpreta o estado produzido pelo balanço hídrico canônico."""

    id = "HYDRIC_PRESSURE_001"
    name = "Agroclimatic Hydric Pressure Rule"
    description = (
        "Interpretação do balanço hídrico de referência sem criação "
        "de índice ou limiar agronômico adicional."
    )
    VERSION = "1.0"

    REQUIRED_METHOD = "REFERENCE_DAILY_RESERVOIR_BALANCE"
    REQUIRED_SCOPE = "MUNICIPAL"
    REQUIRED_STATUS = "VALID"
    CHANNEL = "context"

    def evaluate(self, context):
        """
        Converte o resultado válido do balanço hídrico em interpretação.

        O resultado é deliberadamente quantitativo: a regra identifica
        a ocorrência de déficit/excedente observados no próprio balanço,
        mas não atribui faixas de severidade ou score.
        """
        if not isinstance(context, dict):
            return None

        if context.get("hydric_balance_method") != self.REQUIRED_METHOD:
            return None

        if context.get("hydric_balance_scope") != self.REQUIRED_SCOPE:
            return None

        if context.get("hydric_balance_status") != self.REQUIRED_STATUS:
            return None

        cad = self._number(context.get("cad_mm"))
        arm_final = self._number(context.get("arm_final_mm"))
        arm_percentual = self._number(
            context.get("arm_final_percentual")
        )

        deficit = self._number(
            context.get("deficit_hidrico_acumulado")
        )
        if deficit is None:
            deficit = self._number(
                context.get("deficit_hidrico_mm")
            )

        excess = self._number(
            context.get("excedente_hidrico_acumulado")
        )
        if excess is None:
            excess = self._number(
                context.get("excedente_hidrico_mm")
            )

        # Um balanço válido precisa preservar os principais valores
        # quantitativos. Sem eles, a regra não inventa interpretação.
        if cad is None or arm_final is None:
            return None

        has_deficit = deficit is not None and deficit > 0
        has_excess = excess is not None and excess > 0

        if has_deficit and has_excess:
            state = "DEFICIT_AND_EXCESS_OBSERVED"
            pressure_status = "OBSERVED"
            condition = "DEFICIT_HIDRICO_OBSERVADO"
            title = "Pressão hídrica agroclimática observada"
        elif has_deficit:
            state = "DEFICIT_OBSERVED"
            pressure_status = "OBSERVED"
            condition = "DEFICIT_HIDRICO_OBSERVADO"
            title = "Pressão hídrica agroclimática observada"
        elif has_excess:
            state = "EXCESS_OBSERVED"
            pressure_status = "NOT_OBSERVED"
            condition = "EXCEDENTE_HIDRICO_OBSERVADO"
            title = "Excedente hídrico observado"
        else:
            state = "NO_DEFICIT_OBSERVED"
            pressure_status = "NOT_OBSERVED"
            condition = "SEM_DEFICIT_HIDRICO_OBSERVADO"
            title = "Sem déficit hídrico observado"

        factors = [
            f"ARM final: {arm_final:.1f} mm",
            f"CAD: {cad:.1f} mm",
        ]

        if arm_percentual is not None:
            factors.append(
                f"ARM final: {arm_percentual:.1f}% da CAD"
            )

        if deficit is not None:
            factors.append(
                f"Déficit hídrico acumulado: {deficit:.1f} mm"
            )

        if excess is not None:
            factors.append(
                f"Excedente hídrico acumulado: {excess:.1f} mm"
            )

        return {
            "id": self.id,
            "rule_id": self.id,
            "rule_version": self.VERSION,
            "engine": self.name,
            "channel": self.CHANNEL,
            "interpretation_type": "AGROCLIMATIC_HYDRIC_PRESSURE",
            "title": title,
            "pressure_status": pressure_status,
            "hydric_state": state,
            "condition": condition,
            "metric": "arm_final_mm",
            "metric_value": arm_final,
            "unit": "mm",
            "arm_final_mm": arm_final,
            "arm_final_percentual": arm_percentual,
            "cad_mm": cad,
            "deficit_hidrico_mm": deficit,
            "excedente_hidrico_mm": excess,
            "confidence": 1.0,
            "factors": factors,
            "municipio_id": context.get("municipio_id"),
            "municipio_nome": context.get("municipio_nome"),
            "analysis_date": context.get("analysis_date"),
            "provenance": {
                "source": "HydricBalanceService",
                "method": self.REQUIRED_METHOD,
                "scope": self.REQUIRED_SCOPE,
            },
        }

    @staticmethod
    def _number(value):
        if value is None:
            return None

        try:
            number = float(value)
        except (TypeError, ValueError):
            return None

        if number != number:
            return None

        if number in (float("inf"), float("-inf")):
            return None

        return number
