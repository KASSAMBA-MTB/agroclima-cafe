"""
==========================================================
Cache Service

==========================================================
"""

from django.utils import timezone

from clima.models import ClimateCache


class CacheService:

    def get(self, municipio, provider):

        try:

            cache = ClimateCache.objects.get(

                municipio=municipio,

                provider=provider

            )

            if cache.expires_at > timezone.now():

                return cache.payload

            cache.delete()

        except ClimateCache.DoesNotExist:

            pass

        return None

    def save(

        self,

        municipio,

        provider,

        payload,

        expires_at

    ):

        ClimateCache.objects.update_or_create(

            municipio=municipio,

            provider=provider,

            defaults={

                "payload": payload,

                "expires_at": expires_at,

                "collected_at": timezone.now()

            }

        )