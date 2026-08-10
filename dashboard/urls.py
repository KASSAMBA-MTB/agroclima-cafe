"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: urls.py

Descrição.......:
Mapeamento das rotas da Dashboard.

Versão..........: 4.0
===============================================================================
"""

from django.urls import path

from .views import home

app_name = "dashboard"

urlpatterns = [

    path(
        "",
        home,
        name="home"
    ),

]