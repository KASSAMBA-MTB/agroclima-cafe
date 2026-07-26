"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: alert_service.py

Descrição.......:
Serviço responsável pela geração dos alertas inteligentes do Dashboard.

Versão..........: 1.0
===============================================================================
"""


class AlertService:
    """
    Gera alertas automáticos a partir dos indicadores climáticos.
    """

    def get_alerts(self, kpis):

        alerts = []

        temperatura = kpis.get("temperature", 0)
        precipitacao = kpis.get("precipitation", 0)
        vento = kpis.get("wind_speed", 0)
        umidade = kpis.get("humidity", 0)

        # ==========================================================
        # GEADA
        # ==========================================================

        if temperatura <= 2:

            alerts.append({

                "level": "danger",

                "icon": "bi-snow",

                "title": "Risco elevado de geada",

                "message": (
                    f"Temperatura prevista de {temperatura:.1f}°C."
                ),

                "location": "Região monitorada",

                "time": "Agora"

            })

        elif temperatura <= 5:

            alerts.append({

                "level": "warning",

                "icon": "bi-thermometer-snow",

                "title": "Possibilidade de geada",

                "message": (
                    f"Temperatura de {temperatura:.1f}°C."
                ),

                "location": "Região monitorada",

                "time": "Agora"

            })

        # ==========================================================
        # CHUVA
        # ==========================================================

        if precipitacao >= 50:

            alerts.append({

                "level": "danger",

                "icon": "bi-cloud-rain-heavy",

                "title": "Chuva intensa",

                "message": (
                    f"Precipitação de {precipitacao:.1f} mm."
                ),

                "location": "Região monitorada",

                "time": "Agora"

            })

        elif precipitacao >= 20:

            alerts.append({

                "level": "info",

                "icon": "bi-cloud-rain",

                "title": "Precipitação moderada",

                "message": (
                    f"Precipitação de {precipitacao:.1f} mm."
                ),

                "location": "Região monitorada",

                "time": "Agora"

            })

        # ==========================================================
        # VENTO
        # ==========================================================

        if vento >= 60:

            alerts.append({

                "level": "warning",

                "icon": "bi-wind",

                "title": "Ventos fortes",

                "message": (
                    f"Velocidade de {vento:.1f} km/h."
                ),

                "location": "Região monitorada",

                "time": "Agora"

            })

        # ==========================================================
        # UMIDADE
        # ==========================================================

        if umidade <= 30:

            alerts.append({

                "level": "warning",

                "icon": "bi-droplet-half",

                "title": "Baixa umidade",

                "message": (
                    f"Umidade relativa de {umidade:.1f}%."
                ),

                "location": "Região monitorada",

                "time": "Agora"

            })

        # ==========================================================
        # SEM ALERTAS
        # ==========================================================

        if not alerts:

            alerts.append({

                "level": "success",

                "icon": "bi-check-circle",

                "title": "Condições favoráveis",

                "message": (
                    "Nenhum alerta meteorológico ativo."
                ),

                "location": "Região monitorada",

                "time": "Atualizado"

            })

        return alerts