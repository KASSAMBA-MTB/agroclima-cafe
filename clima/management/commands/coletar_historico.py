"""
==========================================================
AgroClima Café

Management Command
Coleta Histórica Meteorológica

==========================================================

Consulta a série histórica diária da Open-Meteo para
os municípios monitorados pelo AgroClima Café e persiste
os resultados em HistoricalWeatherDaily.

Uso:

    python manage.py coletar_historico

    python manage.py coletar_historico --days 7

    python manage.py coletar_historico --days 30

==========================================================
"""

from datetime import date

from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.db import transaction

from municipios.models import Municipio

from clima.models import (
    HistoricalWeatherDaily,
    Provider,
    WeatherStation,
)

from clima.services.openmeteo_provider import (
    OpenMeteoProvider,
)


class Command(BaseCommand):

    help = (
        "Consulta e persiste dados históricos "
        "meteorológicos dos municípios monitorados."
    )

    # ======================================================
    # ARGUMENTOS
    # ======================================================

    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help=(
                "Quantidade de dias históricos "
                "a consultar. Padrão: 7."
            ),
        )

    # ======================================================
    # EXECUÇÃO
    # ======================================================

    def handle(
        self,
        *args,
        **options,
    ):

        days = options["days"]

        # ==================================================
        # VALIDAÇÃO
        # ==================================================

        if days < 1:

            raise CommandError(
                "A quantidade de dias deve ser "
                "maior ou igual a 1."
            )

        if days > 92:

            raise CommandError(
                "A Open-Meteo permite no máximo "
                "92 dias nesta rotina."
            )

        # ==================================================
        # MUNICÍPIOS
        # ==================================================

        municipios = (
            Municipio.objects
            .all()
            .order_by(
                "nome",
            )
        )

        total = municipios.count()

        if total == 0:

            self.stdout.write(
                self.style.WARNING(
                    "Nenhum município cadastrado."
                )
            )

            return

        # ==================================================
        # PROVIDER
        # ==================================================

        provider = OpenMeteoProvider()

        # ==================================================
        # CABEÇALHO
        # ==================================================

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "=================================================="
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                " AgroClima Café"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                " Coleta Histórica — Open-Meteo"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "=================================================="
            )
        )

        self.stdout.write("")

        self.stdout.write(
            f"Municípios encontrados: {total}"
        )

        self.stdout.write(
            f"Período solicitado: {days} dias"
        )

        self.stdout.write("")

        # ==================================================
        # CONTADORES
        # ==================================================

        total_registros = 0

        total_novos = 0

        total_atualizados = 0

        municipios_processados = 0

        erros = 0

        # ==================================================
        # COLETA DOS MUNICÍPIOS
        # ==================================================

        for municipio in municipios:

            self.stdout.write(
                f"Consultando "
                f"{municipio.nome}/{municipio.estado}..."
            )

            try:

                # ==========================================
                # ESTAÇÃO
                # ==========================================

                station, _ = (
                    WeatherStation.objects
                    .get_or_create(

                        municipio=municipio,

                        provider=(
                            Provider.OPEN_METEO
                        ),

                        defaults={
                            "ativa": True,
                        },

                    )
                )

                # ==========================================
                # COLETA NA OPEN-METEO
                # ==========================================

                historico = (
                    provider.historical_weather(
                        municipio=municipio,
                        days=days,
                    )
                )

                # ==========================================
                # PERSISTÊNCIA
                # ==========================================

                municipio_novos = 0

                municipio_atualizados = 0

                with transaction.atomic():

                    for registro in historico:

                        data_string = (
                            registro.get(
                                "data"
                            )
                        )

                        if not data_string:

                            continue

                        data_historica = (
                            date.fromisoformat(
                                data_string
                            )
                        )

                        (
                            objeto,
                            criado,
                        ) = (
                            HistoricalWeatherDaily
                            .objects
                            .update_or_create(

                                station=station,

                                data=data_historica,

                                defaults={

                                    "temperatura_media": (
                                        registro[
                                            "temperatura"
                                        ]
                                    ),

                                    "temperatura_minima": (
                                        registro[
                                            "temperatura_min"
                                        ]
                                    ),

                                    "temperatura_maxima": (
                                        registro[
                                            "temperatura_max"
                                        ]
                                    ),

                                    "precipitacao": (
                                        registro[
                                            "precipitacao"
                                        ]
                                    ),

                                },

                            )
                        )

                        if criado:

                            municipio_novos += 1

                            total_novos += 1

                        else:

                            municipio_atualizados += 1

                            total_atualizados += 1

                        total_registros += 1

                # ==========================================
                # MUNICÍPIO PROCESSADO
                # ==========================================

                municipios_processados += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  OK — "
                        f"{len(historico)} registros recebidos | "
                        f"{municipio_novos} novos | "
                        f"{municipio_atualizados} atualizados."
                    )
                )

                # ==========================================
                # DETALHAMENTO
                # ==========================================

                for registro in historico:

                    self.stdout.write(
                        "    "
                        f"{registro['data']} | "
                        f"T média: "
                        f"{registro['temperatura']} °C | "
                        f"T mín: "
                        f"{registro['temperatura_min']} °C | "
                        f"T máx: "
                        f"{registro['temperatura_max']} °C | "
                        f"Precipitação: "
                        f"{registro['precipitacao']} mm"
                    )

            except Exception as exc:

                erros += 1

                self.stdout.write(
                    self.style.ERROR(
                        f"  ERRO: {exc}"
                    )
                )

        # ==================================================
        # RESULTADO
        # ==================================================

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "=================================================="
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                " Resultado da Coleta"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "=================================================="
            )
        )

        self.stdout.write(
            f"Municípios encontrados: "
            f"{total}"
        )

        self.stdout.write(
            f"Municípios processados: "
            f"{municipios_processados}"
        )

        self.stdout.write(
            f"Registros históricos recebidos: "
            f"{total_registros}"
        )

        self.stdout.write(
            f"Novos registros persistidos: "
            f"{total_novos}"
        )

        self.stdout.write(
            f"Registros atualizados: "
            f"{total_atualizados}"
        )

        self.stdout.write(
            f"Municípios com erro: "
            f"{erros}"
        )

        self.stdout.write("")

        if erros:

            self.stdout.write(
                self.style.WARNING(
                    "A coleta terminou com "
                    "ocorrências de erro."
                )
            )

        else:

            self.stdout.write(
                self.style.SUCCESS(
                    "Coleta histórica concluída "
                    "com sucesso."
                )
            )

        self.stdout.write("")