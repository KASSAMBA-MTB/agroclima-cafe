import csv
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from core.intelligence.hail_s2id_reference_importer import (
    HailS2IDReferenceImporter,
)


class HailS2IDReferenceImporterTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "s2id.csv"
        self.importer = HailS2IDReferenceImporter()

    def tearDown(self):
        self.temp.cleanup()

    def write_rows(self, rows):
        fields = [
            "protocolo", "codigo_ibge", "municipio", "cobrade",
            "data_ocorrencia",
        ]
        with self.path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def row(self, protocol, cobrade="1.3.2.1.3", municipality="3500402"):
        return {
            "protocolo": protocol,
            "codigo_ibge": municipality,
            "municipio": "Águas da Prata",
            "cobrade": cobrade,
            "data_ocorrencia": "2024-10-15",
        }

    def mapping(self):
        return {
            "protocol": "protocolo",
            "municipality_code": "codigo_ibge",
            "municipality_name": "municipio",
            "cobrade_code": "cobrade",
            "occurrence_date": "data_ocorrencia",
        }

    def test_importa_apenas_granizo_e_preserva_precisao_administrativa(self):
        self.write_rows([
            self.row("MG-001"),
            self.row("MG-002", cobrade="1.3.2.1.4"),
        ])

        records, errors, received = self.importer.import_csv(
            self.path, column_map=self.mapping(),
            municipality_codes=["3500402"],
        )

        self.assertEqual(received, 2)
        self.assertEqual(errors, [])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["cobrade_code"], "13213")
        self.assertEqual(records[0]["occurrence_date"], "2024-10-15")
        self.assertEqual(records[0]["spatial_precision"], "MUNICIPALITY_ONLY")
        self.assertEqual(records[0]["temporal_precision"], "DATE_ONLY")
        self.assertFalse(records[0]["eligible_for_meteorological_training"])

    def test_normaliza_codigo_cobrade_com_pontuacao(self):
        self.write_rows([self.row("MG-001")])
        records, errors, _ = self.importer.import_csv(
            self.path, column_map=self.mapping()
        )
        self.assertEqual(errors, [])
        self.assertEqual(records[0]["cobrade_code"], "13213")

    def test_rejeita_codigo_municipal_invalido(self):
        self.write_rows([self.row("MG-001", municipality="123")])
        records, errors, _ = self.importer.import_csv(
            self.path, column_map=self.mapping()
        )
        self.assertEqual(records, [])
        self.assertEqual(errors[0]["reason"], "MUNICIPALITY_CODE_INVALID")

    def test_rejeita_protocolo_duplicado(self):
        self.write_rows([self.row("MG-001"), self.row("MG-001")])
        records, errors, _ = self.importer.import_csv(
            self.path, column_map=self.mapping()
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(errors[0]["reason"], "DUPLICATE_PROTOCOL")

    def test_filtro_municipal_nao_confunde_registros_de_outros_municipios(self):
        self.write_rows([
            self.row("MG-001", municipality="3500402"),
            self.row("MG-002", municipality="3500907"),
        ])
        records, errors, _ = self.importer.import_csv(
            self.path, column_map=self.mapping(),
            municipality_codes=["3500402"],
        )
        self.assertEqual(errors, [])
        self.assertEqual([item["protocol"] for item in records], ["MG-001"])

    def test_data_invalida_e_reportada_sem_inventar_horario(self):
        row = self.row("MG-001")
        row["data_ocorrencia"] = "data desconhecida"
        self.write_rows([row])
        records, errors, _ = self.importer.import_csv(
            self.path, column_map=self.mapping()
        )
        self.assertEqual(records, [])
        self.assertEqual(errors[0]["reason"], "OCCURRENCE_DATE_INVALID")
