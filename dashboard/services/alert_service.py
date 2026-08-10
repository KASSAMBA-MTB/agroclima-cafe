"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: alert_service.py

Descrição.......:
Serviço responsável pela geração automática dos alertas
meteorológicos exibidos no Dashboard Principal.

Versão..........: 2.0
===============================================================================
"""

from typing import Dict, List, Any


class AlertService:
    """
    Gera alertas meteorológicos a partir dos indicadores climáticos.
    """

    def get_alerts(self, kpis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Gera alertas automaticamente.

        Parameters
        ----------
        kpis : dict

        Returns
        -------
        list
        """

        alerts = []

        temperatura = float(kpis.get("temperature", 0))
        precipitacao = float(kpis.get("precipitation", 0))
        umidade = float(kpis.get("humidity", 0))
        vento = float(kpis.get("wind_speed", 0))
        altitude = float(kpis.get("altitude", 0))

        municipio = kpis.get("municipio", "Região Monitorada")

        # ==========================================================
        # GEADA
        # ==========================================================

        if temperatura <= 2 and altitude >= 1000:

            alerts.append({

                "level": "danger",

                "icon": "bi-snow",

                "title": "Risco elevado de geada",

                "message": (
                    "Temperaturas críticas previstas para regiões "
                    "de maior altitude."
                ),

                "location": municipio,

                "time": "Agora"

            })

        # ==========================================================
        # CHUVA INTENSA
        # ==========================================================

        if precipitacao >= 40:

            alerts.append({

                "level": "warning",

                "icon": "bi-cloud-rain-heavy-fill",

                "title": "Chuva intensa",

                "message": (
                    "Volume elevado de precipitação previsto."
                ),

                "location": municipio,

                "time": "Próximas 24h"

            })

        # ==========================================================
        # VENTOS
        # ==========================================================

        if vento >= 40:

            alerts.append({

                "level": "warning",

                "icon": "bi-wind",

                "title": "Ventos fortes",

                "message": (
                    "Rajadas podem causar danos à lavoura."
                ),

                "location": municipio,

                "time": "Próximas horas"

            })

        # ==========================================================
        # BAIXA UMIDADE
        # ==========================================================

        if umidade < 30:

            alerts.append({

                "level": "info",

                "icon": "bi-droplet-half",

                "title": "Baixa umidade do ar",

                "message": (
                    "Condição favorável ao estresse hídrico."
                ),

                "location": municipio,

                "time": "Monitoramento"

            })

        # ==========================================================
        # SEM ALERTAS
        # ==========================================================

        if not alerts:

            alerts.append({

                "level": "success",

                "icon": "bi-check-circle",

                "title": "Nenhum alerta ativo",

                "message": (
                    "As condições climáticas encontram-se dentro da "
                    "normalidade."
                ),

                "location": municipio,

                "time": "Atual"

            })

        return alerts