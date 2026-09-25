"""
AgroClima Café
MP-01.4.7 — Testes da persistência governada das interpretações.

Objetivos:
    - validar a criação de uma interpretação;
    - validar idempotência;
    - validar isolamento entre municípios;
    - validar preservação do resultado produzido;
    - validar histórico entre ciclos;
    - validar persistência de explainability.
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.intelligence.models import IntelligenceInterpretation
from core.intelligence.persistence.service import (
    IntelligencePersistenceService,
)
from municipios.models import Municipio


class MP0147PersistenceTests(TestCase):
    """Testes do contrato de persistência MP-01.4.7."""

    @classmethod
    def setUpTestData(cls):
        cls.municipio_a = Municipio.objects.create(
            nome="Município MP0147 A",
            estado="MG",
            latitude=-21.78,
            longitude=-46.56,
            altitude=1000,
        )

        cls.municipio_b = Municipio.objects.create(
            nome="Município MP0147 B",
            estado="MG",
            latitude=-21.79,
            longitude=-46.57,
            altitude=1001,
        )

    def setUp(self):
        self.service = IntelligencePersistenceService()

        self.timestamp = timezone.now().replace(microsecond=0)

        self.context_a = {
            "municipio_id": self.municipio_a.id,
            "analysis_timestamp": self.timestamp,
        }

        self.interpretation = {
            "rule_id": "FROST_001",
            "rule_version": "2.0",
            "channel": "alert",
            "severity": "high",
            "score": 82.5,
            "confidence": 0.94,
            "factors": {
                "temperature_min": -1.2,
                "days_below_zero": 2,
            },
            "municipio_id": self.municipio_a.id,
            "provenance": {
                "source": "IntelligenceEngine",
            },
            "coordinator_version": "1.2",
            "policy_version": "1.0",
        }

    def test_01_cria_interpretacao(self):
        instance, created = self.service.persist(
            context=self.context_a,
            interpretation=self.interpretation,
        )

        self.assertTrue(created)
        self.assertIsNotNone(instance.pk)
        self.assertEqual(
            IntelligenceInterpretation.objects.count(),
            1,
        )

    def test_02_idempotencia_nao_cria_duplicata(self):
        first, first_created = self.service.persist(
            context=self.context_a,
            interpretation=self.interpretation,
        )

        second, second_created = self.service.persist(
            context=self.context_a,
            interpretation=self.interpretation,
        )

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            IntelligenceInterpretation.objects.count(),
            1,
        )

    def test_03_isolamento_entre_municipios(self):
        context_b = {
            "municipio_id": self.municipio_b.id,
            "analysis_timestamp": self.timestamp,
        }

        interpretation_b = dict(self.interpretation)
        interpretation_b["municipio_id"] = self.municipio_b.id

        instance_a, created_a = self.service.persist(
            context=self.context_a,
            interpretation=self.interpretation,
        )

        instance_b, created_b = self.service.persist(
            context=context_b,
            interpretation=interpretation_b,
        )

        self.assertTrue(created_a)
        self.assertTrue(created_b)
        self.assertNotEqual(instance_a.pk, instance_b.pk)
        self.assertEqual(
            IntelligenceInterpretation.objects.count(),
            2,
        )

    def test_04_preserva_resultado_produzido(self):
        instance, created = self.service.persist(
            context=self.context_a,
            interpretation=self.interpretation,
        )

        self.assertTrue(created)
        self.assertEqual(
            instance.result,
            self.interpretation,
        )
        self.assertEqual(
            instance.score,
            self.interpretation["score"],
        )
        self.assertEqual(
            instance.confidence,
            self.interpretation["confidence"],
        )
        self.assertEqual(
            instance.factors,
            self.interpretation["factors"],
        )
        self.assertEqual(
            instance.provenance,
            self.interpretation["provenance"],
        )

    def test_05_preserva_historico_de_ciclos(self):
        first_timestamp = self.timestamp
        second_timestamp = self.timestamp + timedelta(hours=1)

        first_context = {
            "municipio_id": self.municipio_a.id,
            "analysis_timestamp": first_timestamp,
        }

        second_context = {
            "municipio_id": self.municipio_a.id,
            "analysis_timestamp": second_timestamp,
        }

        first, first_created = self.service.persist(
            context=first_context,
            interpretation=self.interpretation,
        )

        second, second_created = self.service.persist(
            context=second_context,
            interpretation=self.interpretation,
        )

        self.assertTrue(first_created)
        self.assertTrue(second_created)
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(
            IntelligenceInterpretation.objects.count(),
            2,
        )

    def test_06_persiste_explainability(self):
        explainability = {
            "version": "2.0",
            "rule_count": 1,
            "rules": [
                {
                    "rule_id": "FROST_001",
                    "rule_version": "2.0",
                    "score": 82.5,
                    "severity": "high",
                }
            ],
        }

        instance, created = self.service.persist(
            context=self.context_a,
            interpretation=self.interpretation,
            explainability=explainability,
        )

        self.assertTrue(created)
        self.assertEqual(
            instance.explainability,
            explainability,
        )
