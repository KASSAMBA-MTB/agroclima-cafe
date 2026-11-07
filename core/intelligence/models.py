"""
AgroClima Café

Modelo de persistência das interpretações produzidas pela camada de
Inteligência.

MP..............: MP-01.4.7
Responsabilidade: persistir o resultado canônico já produzido pelo
                  IntelligenceEngine, sem recalcular indicadores ou
                  alterar a interpretação original.
"""

import uuid

from django.db import models

from municipios.models import Municipio


class IntelligenceInterpretation(models.Model):
    """
    Registro histórico de uma interpretação agroclimática produzida pela
    camada de Inteligência.

    O modelo armazena a interpretação já produzida. Nenhum cálculo de FRI,
    severidade, score ou confiança é realizado aqui.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT,
        related_name="intelligence_interpretations",
        verbose_name="Município",
    )

    rule_id = models.CharField(
        max_length=100,
        verbose_name="Identificação da regra",
    )

    rule_version = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Versão da regra",
    )

    result = models.JSONField(
        verbose_name="Resultado canônico",
    )

    channel = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Canal",
    )

    severity = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Severidade",
    )

    score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Score",
    )

    confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Confiança",
    )

    factors = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Fatores",
    )

    analysis_timestamp = models.DateTimeField(
        verbose_name="Data/hora da análise",
    )

    provenance = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Proveniência",
    )

    coordinator_version = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Versão do coordenador",
    )

    policy_version = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Versão da política",
    )

    explainability = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Explicabilidade",
    )

    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Chave de idempotência",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )

    class Meta:
        db_table = "intelligence_interpretation"
        ordering = ["-analysis_timestamp", "-created_at"]
        indexes = [
            models.Index(
                fields=["municipio", "analysis_timestamp"],
                name="intel_interp_mun_date_idx",
            ),
            models.Index(
                fields=["rule_id", "analysis_timestamp"],
                name="intel_interp_rule_date_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(confidence__gte=0.0)
                | models.Q(confidence__isnull=True),
                name="intel_confidence_nonnegative",
            ),
        ]
        verbose_name = "Interpretação de Inteligência"
        verbose_name_plural = "Interpretações de Inteligência"

    def __str__(self):
        return (
            f"{self.rule_id} - {self.municipio.nome} - "
            f"{self.analysis_timestamp:%Y-%m-%d %H:%M:%S}"
        )

class HailThresholdSet(models.Model):
    """
    Conjunto versionado de limiares para classificação experimental
    do potencial de granizo.

    A persistência não homologa automaticamente critérios científicos.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho"
        PROVISIONAL = "PROVISIONAL", "Provisório"
        HOMOLOGATED = "HOMOLOGATED", "Homologado"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    identifier = models.CharField(
        max_length=100,
        verbose_name="Identificador do conjunto",
    )

    version = models.CharField(
        max_length=50,
        verbose_name="Versão",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Estado científico",
    )

    variables = models.JSONField(
        default=dict,
        verbose_name="Variáveis utilizadas",
    )

    threshold_bands = models.JSONField(
        default=dict,
        verbose_name="Faixas de limiares",
    )

    combination_rule = models.JSONField(
        default=dict,
        verbose_name="Regra de combinação",
    )

    domain = models.JSONField(
        default=dict,
        verbose_name="Domínio de aplicação",
    )

    references = models.JSONField(
        default=list,
        verbose_name="Referências científicas",
    )

    source = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Fonte",
    )

    origin = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Origem",
    )

    limitations = models.JSONField(
        default=list,
        verbose_name="Limitações",
    )

    validation_reference = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Referência da validação",
    )

    operational_authorization = models.BooleanField(
        default=False,
        verbose_name="Autorização operacional",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em",
    )

    class Meta:
        db_table = "hail_threshold_set"
        ordering = ["identifier", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["identifier", "version"],
                name="hail_threshold_identifier_version_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "identifier"],
                name="hail_threshold_status_idx",
            ),
        ]
        verbose_name = "Conjunto de limiares de granizo"
        verbose_name_plural = "Conjuntos de limiares de granizo"

    def save(self, *args, **kwargs):
        """
        Proteção convencional contra edição de registros HOMOLOGATED.
        Não substitui restrições de banco ou controle de acesso.
        """
        if self.pk and not self._state.adding:
            anterior = type(self).objects.filter(pk=self.pk).first()

            if anterior and anterior.status == self.Status.HOMOLOGATED:
                campos_protegidos = [
                    "identifier",
                    "version",
                    "status",
                    "variables",
                    "threshold_bands",
                    "combination_rule",
                    "domain",
                    "references",
                    "source",
                    "origin",
                    "limitations",
                    "validation_reference",
                    "operational_authorization",
                ]

                alterados = [
                    campo for campo in campos_protegidos
                    if getattr(anterior, campo) != getattr(self, campo)
                ]

                if alterados:
                    raise ValueError(
                        "HailThresholdSet homologado é imutável. "
                        f"Campos alterados: {alterados}"
                    )

        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.identifier} v{self.version} [{self.status}]"
