"""
==============================================================================
AGROCLIMA CAFE
Fase 6.2 - Balanço Hídrico de Referência
Arquivo: dashboard/services/hydric_balance_service.py
Versão: 1.0.0

Serviço de backend responsável pelo cálculo do balanço hídrico de referência
em escala diária, utilizando precipitação diária, ETo diária e uma capacidade
de água disponível (CAD) explicitamente configurada.

PRINCÍPIO ARQUITETURAL
----------------------
Este serviço:
    - recebe séries meteorológicas já estruturadas;
    - não consulta banco de dados;
    - não consulta API externa;
    - não conhece frontend;
    - não calcula FRI, geada ou indicadores térmicos;
    - não cria limiares agronômicos arbitrários;
    - não transforma ausência de dados em zero.

BASE METODOLÓGICA
-----------------
O cálculo implementado é um BALANÇO HÍDRICO DE REFERÊNCIA POR RESERVATÓRIO
DIÁRIO SIMPLIFICADO. A ETo é utilizada como demanda atmosférica de referência.

A implementação não se apresenta como um modelo completo de balanço de cultura
FAO-56, pois ainda não foram parametrizados Kc, Ks, profundidade radicular,
características específicas do solo, evapotranspiração real ou outros
componentes necessários para uma modelagem específica da cafeicultura.

EQUAÇÕES
--------
Para cada dia t:

    saldo_t = ARM_(t-1) + P_t - ETo_t
    ARM_t   = min(max(saldo_t, 0), CAD)
    DEF_t   = max(0, -saldo_t)
    EXC_t   = max(0, saldo_t - CAD)

onde:
    P_t       = precipitação diária (mm/dia)
    ETo_t     = evapotranspiração de referência (mm/dia)
    ARM_t     = armazenamento de água no reservatório de referência (mm)
    CAD       = capacidade de água disponível (mm)
    DEF_t     = deficiência hídrica de referência do dia (mm)
    EXC_t     = excedente hídrico de referência do dia (mm)

O armazenamento percentual é:

    ARM% = (ARM / CAD) * 100

A CAD não é fixada internamente em 100 mm. Seu valor deve ser fornecido pela
camada de configuração/metodologia com sua respectiva procedência.

TRATAMENTO DE DADOS AUSENTES
----------------------------
None, NaN, infinito, texto inválido e valores fisicamente inválidos não são
convertidos em zero. Uma lacuna de precipitação ou ETo interrompe a continuidade
do balanço. O serviço não reinicia silenciosamente o reservatório depois da
lacuna.

O cálculo agregado só é considerado completo quando toda a série solicitada
possui entradas válidas. Em caso de lacuna, o status passa a INSUFFICIENT_DATA
e os agregados de período permanecem indisponíveis.

ARMAZENAMENTO INICIAL
---------------------
O serviço não assume silenciosamente ARM inicial igual a CAD ou zero. A camada
orquestradora deve fornecer o armazenamento inicial e declarar sua procedência.
Uma futura etapa poderá fornecer esse valor por período de aquecimento
(spin-up) historicamente definido.

ESCOPO
------
O balanço exige escopo MUNICIPAL para impedir que precipitações de municípios
ou estações diferentes sejam somadas como se representassem uma única lâmina
de chuva. Consolidações regionais do HistoryService permanecem apropriadas
para indicadores descritivos, mas não são entrada automática deste balanço.

LIMITAÇÕES INTENCIONAIS
-----------------------
Não são calculados neste serviço:
    - ETc;
    - ETa;
    - Kc;
    - Ks;
    - déficit específico da cultura do café;
    - runoff separado;
    - percolação profunda separada;
    - classificação agronômica por faixas arbitrárias;
    - recomendação de manejo.

Essas limitações preservam a rastreabilidade e impedem que ETo seja confundida
com demanda hídrica específica do cafeeiro.
==============================================================================
"""

from math import isfinite


class HydricBalanceService:
    """
    Calcula balanço hídrico de referência por reservatório diário simplificado.

    O serviço é deliberadamente puro: recebe dados estruturados e devolve um
    contrato estruturado, sem dependência de ORM, API ou apresentação.
    """

    BALANCE_VERSION = "1.0.0"
    METHOD = "REFERENCE_DAILY_RESERVOIR_BALANCE"

    STATUS_VALID = "VALID"
    STATUS_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"
    STATUS_INVALID_INPUT = "INVALID_INPUT"

    REQUIRED_SCOPE = "MUNICIPAL"
    PRECIPITATION_UNIT = "mm/dia"
    ETO_UNIT = "mm/dia"
    STORAGE_UNIT = "mm"
    PERCENT_UNIT = "%"

    def calculate(
        self,
        precipitation_series,
        eto_series,
        cad_mm,
        initial_arm_mm,
        scope=REQUIRED_SCOPE,
        cad_provenance=None,
        initial_arm_method="EXPLICIT",
        dates=None,
    ):
        """
        Executa o balanço diário para um município.

        Parâmetros
        ----------
        precipitation_series : iterable
            Precipitação diária em mm/dia. None representa ausência de dado.
        eto_series : iterable
            ETo diária em mm/dia. None representa ausência de dado.
        cad_mm : number
            Capacidade de água disponível em mm. Deve ser > 0.
        initial_arm_mm : number
            Armazenamento inicial em mm. Deve estar entre 0 e CAD.
        scope : str
            Deve ser MUNICIPAL para cálculo hidrológico do projeto.
        cad_provenance : dict, optional
            Metadados de origem da CAD.
        initial_arm_method : str
            Método/procedência do armazenamento inicial.
        dates : iterable, optional
            Datas correspondentes às séries, sem qualquer interpretação interna.

        Retorno
        -------
        dict
            Contrato estruturado do balanço hídrico.
        """
        precipitation = self._as_list(precipitation_series)
        eto = self._as_list(eto_series)
        date_values = self._as_list(dates) if dates is not None else None

        base = self._base_result(
            cad_mm=cad_mm,
            cad_provenance=cad_provenance,
            initial_arm_mm=initial_arm_mm,
            initial_arm_method=initial_arm_method,
            scope=scope,
            dates=date_values,
        )

        if scope != self.REQUIRED_SCOPE:
            base["hydric_balance_status"] = self.STATUS_INVALID_INPUT
            base["validation_error"] = "O balanço hídrico exige escopo MUNICIPAL."
            return base

        cad = self._finite_number(cad_mm)
        if cad is None or cad <= 0:
            base["hydric_balance_status"] = (
                self.STATUS_NOT_CONFIGURED
                if cad_mm is None
                else self.STATUS_INVALID_INPUT
            )
            base["validation_error"] = "CAD deve ser um valor finito maior que zero."
            return base

        initial_arm = self._finite_number(initial_arm_mm)
        if initial_arm is None:
            base["hydric_balance_status"] = (
                self.STATUS_NOT_CONFIGURED
                if initial_arm_mm is None
                else self.STATUS_INVALID_INPUT
            )
            base["validation_error"] = (
                "O armazenamento inicial deve ser fornecido e ser numérico."
            )
            return base

        if initial_arm < 0 or initial_arm > cad:
            base["hydric_balance_status"] = self.STATUS_INVALID_INPUT
            base["validation_error"] = (
                "O armazenamento inicial deve estar entre 0 e CAD."
            )
            return base

        if not precipitation or not eto:
            base["hydric_balance_status"] = self.STATUS_INSUFFICIENT_DATA
            base["validation_error"] = "As séries diárias não podem estar vazias."
            return base

        if len(precipitation) != len(eto):
            base["hydric_balance_status"] = self.STATUS_INVALID_INPUT
            base["validation_error"] = (
                "Precipitação e ETo devem possuir a mesma quantidade de dias."
            )
            return base

        if date_values is not None and len(date_values) != len(precipitation):
            base["hydric_balance_status"] = self.STATUS_INVALID_INPUT
            base["validation_error"] = (
                "A série de datas deve possuir o mesmo tamanho das séries climáticas."
            )
            return base

        daily = self._calculate_daily(
            precipitation,
            eto,
            cad,
            initial_arm,
        )

        base.update(daily)
        base["cad_mm"] = self._round(cad)
        base["cad_provenance"] = cad_provenance or {}
        base["initial_arm_mm"] = self._round(initial_arm)
        base["initial_arm_method"] = initial_arm_method

        if daily["hydric_balance_status"] == self.STATUS_VALID:
            base.update(
                self._calculate_period_aggregates(
                    precipitation,
                    eto,
                    daily,
                )
            )
            base["condition_hidrica"] = self._build_hydric_condition(
                daily["arm_final_mm"],
                cad,
                daily["deficit_hidrico_acumulado"],
                daily["excedente_hidrico_acumulado"],
            )
        else:
            base["deficit_hidrico_mm"] = None
            base["excedente_hidrico_mm"] = None
            base["deficit_hidrico_acumulado"] = None
            base["excedente_hidrico_acumulado"] = None
            base["precipitacao_acumulada"] = None
            base["eto_acumulada"] = None
            base["arm_final_mm"] = daily.get("arm_final_mm")
            base["arm_final_percentual"] = daily.get("arm_final_percentual")
            base["condition_hidrica"] = None

        return base

    # ======================================================================
    # CÁLCULO DIÁRIO
    # ======================================================================

    def _calculate_daily(
        self,
        precipitation,
        eto,
        cad,
        initial_arm,
    ):
        """Calcula o reservatório sequencial sem reinício silencioso."""
        arm = initial_arm
        saldo_series = []
        arm_series = []
        arm_percentual_series = []
        deficit_series = []
        excess_series = []

        for precipitation_value, eto_value in zip(precipitation, eto):
            p = self._finite_number(precipitation_value)
            e = self._finite_number(eto_value)

            if p is None or e is None or p < 0 or e < 0:
                return {
                    "hydric_balance_status": self.STATUS_INSUFFICIENT_DATA,
                    "saldo_hidrico_diario_mm": saldo_series + [None] * (
                        len(precipitation) - len(saldo_series)
                    ),
                    "arm_diario_mm": arm_series + [None] * (
                        len(precipitation) - len(arm_series)
                    ),
                    "arm_percentual_diario": arm_percentual_series + [None] * (
                        len(precipitation) - len(arm_percentual_series)
                    ),
                    "deficit_hidrico_diario_mm": deficit_series + [None] * (
                        len(precipitation) - len(deficit_series)
                    ),
                    "excedente_hidrico_diario_mm": excess_series + [None] * (
                        len(precipitation) - len(excess_series)
                    ),
                    "arm_final_mm": self._round(arm) if arm_series else None,
                    "arm_final_percentual": (
                        self._round((arm / cad) * 100) if arm_series else None
                    ),
                    "validation_error": (
                        "Lacuna ou valor inválido encontrado nas séries de "
                        "precipitação/ETo; a continuidade foi interrompida."
                    ),
                }

            saldo = arm + p - e
            deficit = max(0.0, -saldo)
            excess = max(0.0, saldo - cad)
            arm = min(max(saldo, 0.0), cad)

            saldo_series.append(self._round(saldo))
            arm_series.append(self._round(arm))
            arm_percentual_series.append(
                self._round((arm / cad) * 100)
            )
            deficit_series.append(self._round(deficit))
            excess_series.append(self._round(excess))

        return {
            "hydric_balance_status": self.STATUS_VALID,
            "saldo_hidrico_diario_mm": saldo_series,
            "arm_diario_mm": arm_series,
            "arm_percentual_diario": arm_percentual_series,
            "deficit_hidrico_diario_mm": deficit_series,
            "excedente_hidrico_diario_mm": excess_series,
            "arm_final_mm": self._round(arm),
            "arm_final_percentual": self._round((arm / cad) * 100),
            "deficit_hidrico_acumulado": self._round(sum(deficit_series)),
            "excedente_hidrico_acumulado": self._round(sum(excess_series)),
            "validation_error": None,
        }

    # ======================================================================
    # AGREGADOS
    # ======================================================================

    def _calculate_period_aggregates(
        self,
        precipitation,
        eto,
        daily,
    ):
        """Consolida o período somente depois de validar toda a sequência."""
        return {
            "precipitacao_acumulada": self._round(
                sum(self._finite_number(value) for value in precipitation)
            ),
            "eto_acumulada": self._round(
                sum(self._finite_number(value) for value in eto)
            ),
            "deficit_hidrico_mm": daily["deficit_hidrico_acumulado"],
            "excedente_hidrico_mm": daily["excedente_hidrico_acumulado"],
        }

    def _build_hydric_condition(
        self,
        arm_final,
        cad,
        deficit,
        excess,
    ):
        """
        Retorna estado quantitativo, sem criar faixas agronômicas arbitrárias.
        """
        return {
            "tipo": "QUANTITATIVA_REFERENCIA",
            "arm_mm": arm_final,
            "arm_percentual": self._round((arm_final / cad) * 100),
            "cad_mm": self._round(cad),
            "deficit_hidrico_mm": deficit,
            "excedente_hidrico_mm": excess,
            "classificacao": None,
        }

    # ======================================================================
    # CONTRATO BASE
    # ======================================================================

    def _base_result(
        self,
        cad_mm,
        cad_provenance,
        initial_arm_mm,
        initial_arm_method,
        scope,
        dates,
    ):
        return {
            "hydric_balance_version": self.BALANCE_VERSION,
            "hydric_balance_method": self.METHOD,
            "hydric_balance_status": self.STATUS_NOT_CONFIGURED,
            "hydric_balance_scope": scope,
            "precipitation_unit": self.PRECIPITATION_UNIT,
            "eto_unit": self.ETO_UNIT,
            "storage_unit": self.STORAGE_UNIT,
            "percent_unit": self.PERCENT_UNIT,
            "cad_mm": self._round(cad_mm),
            "cad_provenance": cad_provenance or {},
            "initial_arm_mm": self._round(initial_arm_mm),
            "initial_arm_method": initial_arm_method,
            "dates": dates,
            "saldo_hidrico_diario_mm": [],
            "arm_diario_mm": [],
            "arm_percentual_diario": [],
            "deficit_hidrico_diario_mm": [],
            "excedente_hidrico_diario_mm": [],
            "arm_final_mm": None,
            "arm_final_percentual": None,
            "precipitacao_acumulada": None,
            "eto_acumulada": None,
            "deficit_hidrico_mm": None,
            "excedente_hidrico_mm": None,
            "deficit_hidrico_acumulado": None,
            "excedente_hidrico_acumulado": None,
            "condition_hidrica": None,
            "validation_error": None,
        }

    # ======================================================================
    # VALIDAÇÃO E UTILITÁRIOS
    # ======================================================================

    @staticmethod
    def _as_list(value):
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return list(value)
        try:
            return list(value)
        except TypeError:
            return [value]

    @staticmethod
    def _finite_number(value):
        if value is None or isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not isfinite(number):
            return None
        return number

    @staticmethod
    def _round(value):
        if value is None:
            return None
        return round(float(value), 2)


# ============================================================================
# REGISTRO DE AUDITORIA - FASE 6.2
# ============================================================================
#
# Fonte das entradas:
#     HistoryService / contrato histórico estruturado.
#
# Entradas:
#     precipitação diária (mm/dia);
#     ETo diária (mm/dia);
#     CAD configurada e documentada;
#     armazenamento inicial explicitamente fornecido.
#
# Metodologia:
#     balanço hídrico de referência por reservatório diário simplificado.
#
# Regras de segurança:
#     - escala diária;
#     - escopo MUNICIPAL obrigatório;
#     - CAD nunca assume 100 mm automaticamente;
#     - ARM inicial nunca assume CAD ou zero automaticamente;
#     - None não vira zero;
#     - valores negativos são inválidos;
#     - lacuna interrompe a continuidade;
#     - não há reinício silencioso após lacuna;
#     - déficit/excedente somente são produzidos quando a sequência completa é válida;
#     - condição hídrica permanece quantitativa, sem limiares agronômicos arbitrários.
#
# Não implementa:
#     ETc, ETa, Kc, Ks, déficit específico do café, FRI, geada,
#     severidade, confiança, alertas, recomendações ou apresentação.
#
# Compatibilidade:
#     Fase 5 permanece preservada.
#     HistoricalClimateIndicatorService somente deverá receber este contrato
#     após auditoria e validação deste serviço isoladamente.
#
# Próxima etapa autorizada:
#     integração controlada ao HistoricalClimateIndicatorService,
#     com incremento de sua versão para 6.1 somente após teste.
# ============================================================================
