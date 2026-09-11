"""
AGROCLIMA CAFÉ
Serviço de Configuração Municipal do Balanço Hídrico
FASE 6.2 — versão 1.0.0

Responsabilidade:
    Fornecer ao backend uma configuração explícita e rastreável para
    o balanço hídrico municipal, sem inventar parâmetros agronômicos.

Princípios:
    - backend é a autoridade da configuração;
    - nenhum valor de CAD é criado por este serviço;
    - nenhum ARM inicial é presumido;
    - ausência de configuração permanece explicitamente identificada;
    - configuração inválida não é silenciosamente corrigida;
    - não há acesso a frontend, API meteorológica ou banco de dados;
    - a configuração é lida exclusivamente de Django settings;
    - o serviço não calcula balanço hídrico;
    - o HydricBalanceService continua responsável pelo cálculo.

Contrato esperado em settings.py:

AGROCLIMA_HYDRIC_BALANCE_CONFIG = {
    "CHAVE_MUNICIPIO": {
        "cad_mm": <valor explícito>,
        "cad_provenance": <objeto ou texto de proveniência>,
        "initial_arm_mm": <valor explícito>,
        "initial_arm_method": "EXPLICIT" ou "HISTORICAL_SPIN_UP",
    },
}

A chave municipal deve ser estável e pode ser o código IBGE ou outro
identificador definido pelo projeto. O serviço não escolhe uma chave
arbitrariamente: a aplicação deve fornecê-la explicitamente.

Nenhum município é configurado neste arquivo.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from django.conf import settings


class HydricBalanceConfigurationService:
    """
    Adaptador de configuração do balanço hídrico municipal.

    Este serviço não contém valores agronômicos padrão.
    """

    VERSION = "1.0.0"

    STATUS_CONFIGURED = "CONFIGURED"
    STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"
    STATUS_INVALID_CONFIG = "INVALID_CONFIG"

    KEY_CAD_MM = "cad_mm"
    KEY_CAD_PROVENANCE = "cad_provenance"
    KEY_INITIAL_ARM_MM = "initial_arm_mm"
    KEY_INITIAL_ARM_METHOD = "initial_arm_method"

    METHOD_EXPLICIT = "EXPLICIT"
    METHOD_HISTORICAL_SPIN_UP = "HISTORICAL_SPIN_UP"

    SETTING_NAME = "AGROCLIMA_HYDRIC_BALANCE_CONFIG"

    REQUIRED_FIELDS = (
        KEY_CAD_MM,
        KEY_CAD_PROVENANCE,
        KEY_INITIAL_ARM_MM,
        KEY_INITIAL_ARM_METHOD,
    )

    def get_configuration(
        self,
        municipality_key: Any,
    ) -> dict[str, Any]:
        """
        Retorna a configuração municipal normalizada.

        Resultado configurado:
            {
                "version": ...,
                "status": "CONFIGURED",
                "municipality_key": ...,
                "cad_mm": ...,
                "cad_provenance": ...,
                "initial_arm_mm": ...,
                "initial_arm_method": ...,
                "validation_error": None,
            }

        Resultado sem configuração:
            status = "NOT_CONFIGURED"

        Resultado inválido:
            status = "INVALID_CONFIG"

        Nenhum valor padrão é aplicado.
        """
        key = self.normalize_municipality_key(municipality_key)

        if key is None:
            return self._result(
                status=self.STATUS_NOT_CONFIGURED,
                municipality_key=None,
                validation_error=(
                    "Chave municipal ausente ou vazia."
                ),
            )

        raw_config = self._read_settings()

        if not raw_config:
            return self._result(
                status=self.STATUS_NOT_CONFIGURED,
                municipality_key=key,
                validation_error=(
                    "AGROCLIMA_HYDRIC_BALANCE_CONFIG não está configurado."
                ),
            )

        if not isinstance(raw_config, Mapping):
            return self._result(
                status=self.STATUS_INVALID_CONFIG,
                municipality_key=key,
                validation_error=(
                    "AGROCLIMA_HYDRIC_BALANCE_CONFIG deve ser um mapping."
                ),
            )

        municipality_config = self._find_municipality_config(
            raw_config,
            key,
        )

        if municipality_config is None:
            return self._result(
                status=self.STATUS_NOT_CONFIGURED,
                municipality_key=key,
                validation_error=(
                    "Não existe configuração hídrica para o município."
                ),
            )

        if not isinstance(municipality_config, Mapping):
            return self._result(
                status=self.STATUS_INVALID_CONFIG,
                municipality_key=key,
                validation_error=(
                    "A configuração municipal deve ser um mapping."
                ),
            )

        normalized, error = self._validate_and_normalize(
            municipality_config
        )

        if error is not None:
            return self._result(
                status=self.STATUS_INVALID_CONFIG,
                municipality_key=key,
                validation_error=error,
            )

        return self._result(
            status=self.STATUS_CONFIGURED,
            municipality_key=key,
            cad_mm=normalized[self.KEY_CAD_MM],
            cad_provenance=normalized[self.KEY_CAD_PROVENANCE],
            initial_arm_mm=normalized[self.KEY_INITIAL_ARM_MM],
            initial_arm_method=normalized[self.KEY_INITIAL_ARM_METHOD],
            validation_error=None,
        )

    def is_configured(self, municipality_key: Any) -> bool:
        """
        Indica se a configuração municipal está válida e completa.
        """
        result = self.get_configuration(municipality_key)
        return result["status"] == self.STATUS_CONFIGURED

    def normalize_municipality_key(
        self,
        municipality_key: Any,
    ) -> str | None:
        """
        Normaliza somente a representação da chave.

        Não transforma um identificador ausente em valor artificial.
        """
        if municipality_key is None:
            return None

        if isinstance(municipality_key, bool):
            return None

        text = str(municipality_key).strip()

        if not text:
            return None

        return text

    def _read_settings(self) -> Any:
        """
        Lê a configuração exclusivamente de Django settings.

        O getattr possui default None para preservar o estado
        NOT_CONFIGURED quando a configuração ainda não existe.
        """
        return getattr(
            settings,
            self.SETTING_NAME,
            None,
        )

    def _find_municipality_config(
        self,
        config: Mapping[Any, Any],
        municipality_key: str,
    ) -> Any:
        """
        Procura a chave municipal sem alterar o conteúdo configurado.

        Primeiro tenta a chave literal. Depois compara as
        representações textuais apenas para tolerar, por exemplo,
        uma chave numérica equivalente à chave recebida como texto.
        """
        if municipality_key in config:
            return config[municipality_key]

        for configured_key, configured_value in config.items():
            normalized_key = self.normalize_municipality_key(
                configured_key
            )

            if normalized_key == municipality_key:
                return configured_value

        return None

    def _validate_and_normalize(
        self,
        municipality_config: Mapping[Any, Any],
    ) -> tuple[dict[str, Any], str | None]:
        """
        Valida os quatro elementos obrigatórios.

        A validação rejeita:
            - campos ausentes;
            - CAD não numérico;
            - CAD <= 0;
            - CAD não finito;
            - proveniência vazia;
            - ARM inicial não numérico;
            - ARM inicial não finito;
            - ARM fora de [0, CAD];
            - método de ARM desconhecido.

        Nenhuma correção automática é realizada.
        """
        missing = [
            field
            for field in self.REQUIRED_FIELDS
            if field not in municipality_config
        ]

        if missing:
            return {}, (
                "Campos obrigatórios ausentes: "
                + ", ".join(missing)
                + "."
            )

        cad_mm = self._to_finite_float(
            municipality_config[self.KEY_CAD_MM]
        )

        if cad_mm is None:
            return {}, "cad_mm deve ser numérico e finito."

        if cad_mm <= 0:
            return {}, "cad_mm deve ser maior que zero."

        provenance = municipality_config[
            self.KEY_CAD_PROVENANCE
        ]

        if self._is_empty_provenance(provenance):
            return {}, (
                "cad_provenance deve identificar a proveniência "
                "da capacidade de água disponível."
            )

        initial_arm_mm = self._to_finite_float(
            municipality_config[self.KEY_INITIAL_ARM_MM]
        )

        if initial_arm_mm is None:
            return {}, "initial_arm_mm deve ser numérico e finito."

        if initial_arm_mm < 0:
            return {}, "initial_arm_mm não pode ser negativo."

        if initial_arm_mm > cad_mm:
            return {}, (
                "initial_arm_mm não pode ser maior que cad_mm."
            )

        initial_arm_method = str(
            municipality_config[self.KEY_INITIAL_ARM_METHOD]
        ).strip().upper()

        if initial_arm_method not in (
            self.METHOD_EXPLICIT,
            self.METHOD_HISTORICAL_SPIN_UP,
        ):
            return {}, (
                "initial_arm_method inválido. "
                "Use EXPLICIT ou HISTORICAL_SPIN_UP."
            )

        return {
            self.KEY_CAD_MM: cad_mm,
            self.KEY_CAD_PROVENANCE: provenance,
            self.KEY_INITIAL_ARM_MM: initial_arm_mm,
            self.KEY_INITIAL_ARM_METHOD: initial_arm_method,
        }, None

    @staticmethod
    def _to_finite_float(value: Any) -> float | None:
        """
        Converte valores numéricos sem aceitar NaN ou infinito.

        Strings vazias e booleanos não são tratados como parâmetros
        numéricos válidos.
        """
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        try:
            number = float(value)
        except (TypeError, ValueError):
            return None

        if not math.isfinite(number):
            return None

        return number

    @staticmethod
    def _is_empty_provenance(value: Any) -> bool:
        """
        Determina se a proveniência está efetivamente ausente.

        Mapping vazio e texto vazio são considerados ausência.
        Outros objetos são preservados para permitir uma proveniência
        estruturada definida pelo projeto.
        """
        if value is None:
            return True

        if isinstance(value, str):
            return not value.strip()

        if isinstance(value, Mapping):
            return not bool(value)

        return False

    def _result(
        self,
        *,
        status: str,
        municipality_key: str | None,
        validation_error: str | None,
        cad_mm: float | None = None,
        cad_provenance: Any = None,
        initial_arm_mm: float | None = None,
        initial_arm_method: str | None = None,
    ) -> dict[str, Any]:
        """
        Monta o contrato estável entregue às camadas superiores.
        """
        return {
            "version": self.VERSION,
            "status": status,
            "municipality_key": municipality_key,
            "cad_mm": cad_mm,
            "cad_provenance": cad_provenance,
            "initial_arm_mm": initial_arm_mm,
            "initial_arm_method": initial_arm_method,
            "validation_error": validation_error,
        }


__all__ = [
    "HydricBalanceConfigurationService",
]
