"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: events_service.py

Descrição.......:
Serviço responsável pela geração da linha do tempo (Timeline)
do Dashboard Principal.

Versão..........: 1.0
===============================================================================
"""


class EventsService:
    """
    Gera os eventos exibidos na Timeline da Dashboard.
    """

    def get_events(self, kpis):

        eventos = []

        temperatura = kpis.get("temperature", 0)
        precipitacao = kpis.get("precipitation", 0)
        umidade = kpis.get("humidity", 0)
        indice = kpis.get("indice_agroclima", 0)

        # ==========================================================
        # TEMPERATURA
        # ==========================================================

        if temperatura <= 5:

            eventos.append({

                "hora": "Agora",

                "titulo": "Queda de temperatura",

                "descricao": (
                    f"Temperatura registrada de {temperatura:.1f}°C."
                ),

                "icone": "bi-thermometer-snow"

            })

        # ==========================================================
        # PRECIPITAÇÃO
        # ==========================================================

        if precipitacao >= 20:

            eventos.append({

                "hora": "Agora",

                "titulo": "Registro de precipitação",

                "descricao": (
                    f"Acumulado de {precipitacao:.1f} mm."
                ),

                "icone": "bi-cloud-rain"

            })

        # ==========================================================
        # UMIDADE
        # ==========================================================

        if umidade <= 30:

            eventos.append({

                "hora": "Agora",

                "titulo": "Baixa umidade",

                "descricao": (
                    f"Umidade relativa de {umidade:.1f}%."
                ),

                "icone": "bi-droplet-half"

            })

        # ==========================================================
        # ÍNDICE AGROCLIMA
        # ==========================================================

        eventos.append({

            "hora": "Atualizado",

            "titulo": "Índice AgroClima",

            "descricao": (
                f"Índice calculado: {indice}"
            ),

            "icone": "bi-speedometer2"

        })

        # ==========================================================
        # NENHUM EVENTO
        # ==========================================================

        if not eventos:

            eventos.append({

                "hora": "--",

                "titulo": "Nenhum evento",

                "descricao": "Nenhum evento registrado.",

                "icone": "bi-calendar-check"

            })

        return eventos