from django.shortcuts import render
from django.db.models import Avg, Sum

from municipios.models import Municipio
from clima.models import Clima
from geadas.models import Geada


def dashboard_home(request):

    temperatura_minima = Clima.objects.aggregate(
        media=Avg('temperatura')
    )['media']

    precipitacao_acumulada = Clima.objects.aggregate(
        total=Sum('precipitacao')
    )['total']

    ocorrencias_geada = Geada.objects.count()

    dias_temperatura_zero = Clima.objects.filter(
        temperatura__lte=0
    ).count()

    municipios = []
    temperaturas = []
    precipitacoes = []

    for municipio in Municipio.objects.all():

        ultimo_clima = (
            Clima.objects
            .filter(municipio=municipio)
            .order_by('-data_coleta')
            .first()
        )

        if ultimo_clima:

            municipios.append(municipio.nome)

            temperaturas.append(
                float(ultimo_clima.temperatura)
            )

            precipitacoes.append(
                float(ultimo_clima.precipitacao)
            )

    context = {
        'temperatura_minima': round(
            float(temperatura_minima), 1
        ) if temperatura_minima else 0,

        'precipitacao_acumulada': round(
            float(precipitacao_acumulada), 1
        ) if precipitacao_acumulada else 0,

        'ocorrencias_geada': ocorrencias_geada,

        'dias_temperatura_zero': dias_temperatura_zero,

        'municipios': municipios,

        'temperaturas': temperaturas,

        'precipitacoes': precipitacoes,
    }

    return render(
        request,
        'dashboard/home.html',
        context
    )