from django.test import TestCase
from django.db import IntegrityError, transaction

from core.intelligence.models import HailThresholdSet
from core.intelligence.hail_threshold_set_service import (
    transition_threshold_set,
    authorize_operational_use,
    HailThresholdSetTransitionError,
)


class HailThresholdSetIntegrityTests(TestCase):

    def create_item(self, version):
        return HailThresholdSet.objects.create(
            identifier="TEST_MP0114_B7",
            version=version,
        )

    def test_default_status_is_draft(self):
        item = self.create_item("1")
        self.assertEqual(item.status, HailThresholdSet.Status.DRAFT)

    def test_operational_authorization_defaults_false(self):
        item = self.create_item("2")
        self.assertFalse(item.operational_authorization)

    def test_scientific_fields_are_empty_by_default(self):
        item = self.create_item("3")
        self.assertEqual(item.variables, {})
        self.assertEqual(item.threshold_bands, {})
        self.assertEqual(item.combination_rule, {})
        self.assertEqual(item.domain, {})
        self.assertEqual(item.references, [])
        self.assertEqual(item.limitations, [])

    def test_identifier_version_is_unique(self):
        self.create_item("4")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_item("4")

    def test_different_versions_are_allowed(self):
        self.create_item("5A")
        self.create_item("5B")
        self.assertEqual(
            HailThresholdSet.objects.filter(
                identifier="TEST_MP0114_B7"
            ).count(),
            2,
        )

    def test_homologation_is_blocked_without_gate_integration(self):
        item = self.create_item("6")
        with self.assertRaises(HailThresholdSetTransitionError):
            transition_threshold_set(
                item.pk,
                HailThresholdSet.Status.HOMOLOGATED,
                validation_reference="GATE-TEST",
            )

    def test_provisional_transition_is_allowed(self):
        item = self.create_item("7")
        item = transition_threshold_set(
            item.pk,
            HailThresholdSet.Status.PROVISIONAL,
        )
        self.assertEqual(item.status, HailThresholdSet.Status.PROVISIONAL)
        self.assertFalse(item.operational_authorization)

    def test_operational_authorization_is_blocked(self):
        item = self.create_item("8")
        with self.assertRaises(HailThresholdSetTransitionError):
            authorize_operational_use(item.pk, "GATE-TEST")

    def test_operational_authorization_cannot_be_requested_in_transition(self):
        item = self.create_item("9")
        with self.assertRaises(HailThresholdSetTransitionError):
            transition_threshold_set(
                item.pk,
                HailThresholdSet.Status.PROVISIONAL,
                operational_authorization=True,
            )

    def test_homologated_set_cannot_be_edited(self):
        item = self.create_item("10")
        item.status = HailThresholdSet.Status.HOMOLOGATED
        item.validation_reference = "GATE-TEST"
        item.save()

        item.source = "alteração proibida"
        with self.assertRaises(ValueError):
            item.save()
