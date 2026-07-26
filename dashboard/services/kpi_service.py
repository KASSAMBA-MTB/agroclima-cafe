"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: kpi_service.py

Autor...........: Walter Junio Pontes Teixeira
Polo............: São João da Boa Vista - SP
Ano.............: 2026

Descrição.......:
Serviço responsável por consolidar os indicadores (KPIs) exibidos no
Dashboard Principal. Os dados são obtidos a partir do serviço
meteorológico, processados pelo Índice AgroClima e disponibilizados para
os componentes visuais da aplicação.

Tecnologias.....:
• Python 3.14
• Django 6.x
• PostgreSQL
• Open-Meteo API

Versão..........: 2.0
===============================================================================
"""

from django.utils import timezone

from core.intelligence.agroclima_index import AgroClimaIndex
from clima.services.weather_service import WeatherService
from municipios.models import Municipio


class KPIService:
    """
    Serviço responsável pelo carregamento dos indicadores do Dashboard.
    """

    def __init__(self):

        self.weather = WeatherService()
        self.iac = AgroClimaIndex()

    # ==========================================================
    # KPIs
    # ==========================================================

    def get_kpis(self):

        municipio = Municipio.objects.first()

        if municipio is None:
            return self._empty()

        observation = self.weather.update_current_weather(municipio)

        indice = self.iac.calculate(
            temperature=float(observation.temperature),
            humidity=float(observation.humidity),
            precipitation=float(observation.precipitation),
            frost_level="low",
            hail_level="low",
        )

        now = timezone.localtime()

        return {

            # =====================================================
            # KPIs VISUAIS
            # =====================================================

            "temperatura_media": round(float(observation.temperature), 1),

            "precipitacao": round(float(observation.precipitation), 1),

            "geadas": 0,

            "granizo": 0,

            "municipios": Municipio.objects.count(),

            "indice_agroclima": indice["index"],

            "classificacao_agroclima": indice["classification"],

            "cor_agroclima": indice["color"],

            "icone_agroclima": indice["icon"],

            "ultima_atualizacao": now,

            "ultima_atualizacao_str": now.strftime("%d/%m/%Y %H:%M"),

            # =====================================================
            # STATUS GERAL
            # =====================================================

            "status_dashboard": {
                "status": "normal",
                "mensagem": f'Condição {indice["classification"]}'
            },

            # =====================================================
            # DADOS PARA MÓDULOS DE INTELIGÊNCIA
            # =====================================================

            "temperature": float(observation.temperature),

            "humidity": float(observation.humidity),

            "wind_speed": float(observation.wind_speed),

            "altitude": int(municipio.altitude),

            "precipitation": float(observation.precipitation),

            # =====================================================
            # AGROCLIMA INDEX
            # =====================================================

            "scores": indice["scores"],

        }

    # ==========================================================
    # RETORNO PADRÃO
    # ==========================================================

    def _empty(self):

        now = timezone.localtime()

        return {

            # KPIs

            "temperatura_media": None,

            "precipitacao": None,

            "geadas": 0,

            "granizo": 0,

            "municipios": 0,

            "indice_agroclima": "--",

            "classificacao_agroclima": "--",

            "cor_agroclima": "#999999",

            "icone_agroclima": "bi-dash-circle",

            "ultima_atualizacao": now,

            "ultima_atualizacao_str": now.strftime("%d/%m/%Y %H:%M"),

            "status_dashboard": {
                "status": "offline",
                "mensagem": "Nenhum município cadastrado."
            },

            # Inteligência

            "temperature": 0.0,

            "humidity": 0.0,

            "wind_speed": 0.0,

            "altitude": 0,

            "precipitation": 0.0,

            # Índice AgroClima

            "scores": {},

        }