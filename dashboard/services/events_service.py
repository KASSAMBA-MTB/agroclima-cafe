"""
===============================================================================
AGROCLIMA CAFÉ
Events Service

Serviço responsável pela geração da linha do tempo de eventos climáticos
observados no Dashboard Principal.

Fonte factual:
    HistoricalWeatherDaily

Princípios:
    - Não cria eventos fictícios.
    - Não utiliza KPIs como fonte de eventos.
    - Não utiliza alertas como eventos históricos.
    - Não calcula FRI.
    - Não executa Inteligência.
    - Eventos somente são produzidos a partir de dados persistidos.
    - Diferencia registro meteorológico de evento climático relevante.
    - O período é limitado ao intervalo solicitado.
    - Granizo somente é exibido quando houver dado factual persistido.
===============================================================================
"""

from datetime import timedelta

from django.utils import timezone

from clima.models import HistoricalWeatherDaily


class EventsService:
    """Consolida eventos climáticos históricos observados."""

    PERIOD_DAYS = 30

    FROST_THRESHOLD = 0.0
    COLD_THRESHOLD = 5.0
    RAIN_THRESHOLD = 20.0
    RAIN_MODERATE_THRESHOLD = 10.0

    def get_events(self, days=PERIOD_DAYS):
        """
        Retorna somente eventos climáticos relevantes observados no período.

        A fonte factual é exclusivamente HistoricalWeatherDaily.
        Um registro meteorológico comum não é transformado automaticamente
        em evento. O evento precisa satisfazer um critério factual explícito.
        """

        try:
            days = int(days)
        except (TypeError, ValueError):
            days = self.PERIOD_DAYS

        days = max(1, min(days, 30))

        hoje = timezone.localdate()
        inicio = hoje - timedelta(days=days - 1)

        records = (
            HistoricalWeatherDaily.objects
            .select_related(
                "station",
                "station__municipio",
            )
            .filter(
                data__gte=inicio,
                data__lte=hoje,
            )
            .order_by(
                "-data",
                "station__municipio__nome",
            )
        )

        daily = {}

        model_fields = {
            field.name
            for field in HistoricalWeatherDaily._meta.get_fields()
        }

        granizo_field = next(
            (
                field
                for field in (
                    "granizo",
                    "hail",
                    "hail_occurrence",
                    "ocorrencia_granizo",
                    "granizo_ocorrencia",
                )
                if field in model_fields
            ),
            None,
        )

        for record in records:
            station = getattr(record, "station", None)
            municipio = getattr(station, "municipio", None)

            if municipio is None or record.data is None:
                continue

            key = (municipio.pk, record.data)

            item = daily.setdefault(
                key,
                {
                    "municipio": municipio.nome,
                    "data": record.data,
                    "temperatura_minima": None,
                    "precipitacao": None,
                    "granizo": False,
                },
            )

            minimum = self._to_float(
                getattr(record, "temperatura_minima", None)
            )

            precipitation = self._to_float(
                getattr(record, "precipitacao", None)
            )

            if minimum is not None:
                current = item["temperatura_minima"]
                if current is None or minimum < current:
                    item["temperatura_minima"] = minimum

            if precipitation is not None:
                current = item["precipitacao"]
                if current is None or precipitation > current:
                    item["precipitacao"] = precipitation

            if granizo_field and self._is_hail_observed(
                getattr(record, granizo_field, None)
            ):
                item["granizo"] = True

        eventos = []

        for item in daily.values():
            date = item["data"]
            municipio = item["municipio"]
            minimum = item["temperatura_minima"]
            precipitation = item["precipitacao"]

            if minimum is not None and minimum <= self.FROST_THRESHOLD:
                eventos.append(
                    self._event(
                        date=date,
                        municipio=municipio,
                        titulo="Geada registrada",
                        intensidade=f"{minimum:.1f} °C",
                        icone="bi-snow",
                        tipo="geada",
                    )
                )

            elif minimum is not None and minimum <= self.COLD_THRESHOLD:
                eventos.append(
                    self._event(
                        date=date,
                        municipio=municipio,
                        titulo="Temperatura baixa registrada",
                        intensidade=f"{minimum:.1f} °C",
                        icone="bi-thermometer-snow",
                        tipo="temperatura",
                    )
                )

            if precipitation is not None and precipitation >= self.RAIN_THRESHOLD:
                eventos.append(
                    self._event(
                        date=date,
                        municipio=municipio,
                        titulo="Precipitação elevada registrada",
                        intensidade=f"{precipitation:.1f} mm",
                        icone="bi-cloud-rain-heavy",
                        tipo="precipitacao",
                    )
                )

            elif (
                precipitation is not None
                and precipitation >= self.RAIN_MODERATE_THRESHOLD
            ):
                eventos.append(
                    self._event(
                        date=date,
                        municipio=municipio,
                        titulo="Precipitação relevante registrada",
                        intensidade=f"{precipitation:.1f} mm",
                        icone="bi-cloud-rain",
                        tipo="precipitacao",
                    )
                )

            if item["granizo"]:
                eventos.append(
                    self._event(
                        date=date,
                        municipio=municipio,
                        titulo="Granizo registrado",
                        intensidade="Ocorrência observada",
                        icone="bi-cloud-hail",
                        tipo="granizo",
                    )
                )

        eventos.sort(
            key=lambda event: (
                event["data_iso"],
                event["municipio"],
                event["tipo"],
            ),
            reverse=True,
        )

        return eventos

    @staticmethod
    def _event(date, municipio, titulo, intensidade, icone, tipo):
        return {
            "data": date,
            "data_iso": date.isoformat(),
            "data_str": date.strftime("%d/%m/%Y"),
            "municipio": municipio,
            "titulo": titulo,
            "tipo": tipo,
            "intensidade": intensidade,
            "status": "historico",
            "status_label": "Registrado",
            "origem": "HistoricalWeatherDaily",
            "ativo": False,
            "icone": icone,
        }

    @staticmethod
    def _to_float(value):
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _is_hail_observed(value):
        """Considera somente ocorrência de granizo explicitamente persistida."""

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return value > 0

        if isinstance(value, str):
            return value.strip().lower() in {
                "true",
                "1",
                "sim",
                "yes",
                "ocorreu",
                "registrado",
                "presente",
            }

        return False
