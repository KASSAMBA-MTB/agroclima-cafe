"""
==========================================================
AgroClima Café

Cache Service

Gerencia o cache das respostas dos provedores climáticos.

Autor:
Walter Junio Pontes Teixeira

Curso:
Ciência de Dados - UNIVESP
==========================================================
"""

from django.utils import timezone

from clima.models import ClimateCache


class CacheService:
    """
    Serviço responsável pelo gerenciamento do cache
    das consultas aos provedores climáticos.
    """

    def get(self, municipio, provider):
        """
        Retorna o cache válido para um município/provedor.

        Caso o cache esteja expirado, ele é removido.
        """

        try:

            cache = ClimateCache.objects.get(

                municipio=municipio,

                provider=provider

            )

        except ClimateCache.DoesNotExist:

            return None

        if cache.expires_at <= timezone.now():

            cache.delete()

            return None

        return cache.payload

    def save(
        self,
        municipio,
        provider,
        payload,
        expires_at
    ):
        """
        Cria ou atualiza o cache.
        """

        ClimateCache.objects.update_or_create(

            municipio=municipio,

            provider=provider,

            defaults={

                "payload": payload,

                "collected_at": timezone.now(),

                "expires_at": expires_at,

            },

        )

    def clear(self, municipio=None, provider=None):
        """
        Remove registros do cache.

        Pode remover:

        • todo o cache;
        • apenas de um município;
        • apenas de um provedor;
        • município + provedor.
        """

        queryset = ClimateCache.objects.all()

        if municipio is not None:

            queryset = queryset.filter(

                municipio=municipio

            )

        if provider is not None:

            queryset = queryset.filter(

                provider=provider

            )

        deleted, _ = queryset.delete()

        return deleted

    def cleanup_expired(self):
        """
        Remove automaticamente todos os registros
        expirados do cache.
        """

        queryset = ClimateCache.objects.filter(

            expires_at__lte=timezone.now()

        )

        deleted, _ = queryset.delete()

        return deleted