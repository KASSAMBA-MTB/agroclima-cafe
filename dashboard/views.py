from django.shortcuts import render

from municipios.models import Municipio
from clima.models import Clima
from geadas.models import Geada

from django.db.models import Avg


def dashboard_home(request):

    total_municipios = Municipio.objects.count()

    total_climas = Clima.objects.count()

    total_geadas = Geada.objects.count()

    temperatura_media = (
        Clima.objects.aggregate(
            media=Avg('temperatura')
        )['media']
    )

    context = {

        'total_municipios': total_municipios,

        'total_climas': total_climas,

        'total_geadas': total_geadas,

        'temperatura_media': round(
            temperatura_media,
            2
        ) if temperatura_media else 0
    }

    return render(
        request,
        'dashboard/home.html',
        context
    )