"""MP-01.14 — Importação controlada de referências administrativas S2ID.

Registros S2ID de granizo são evidências administrativas municipais.
Este módulo NÃO os converte em rótulos de treinamento meteorológico:
não há coordenada do evento nem horário intradiário confiável.
"""

import csv
import re
from datetime import date, datetime
from pathlib import Path


class S2IDImportError(ValueError):
    """Erro identificável na leitura da referência administrativa S2ID."""


class HailS2IDReferenceImporter:
    """Extrai somente registros COBRADE de granizo com proveniência preservada."""

    METHOD_VERSION = "MP-01.14.0"
    COBRADE_HAIL = "13213"
    REFERENCE_TYPE = "ADMINISTRATIVE_HAIL_RECORD"
    REFERENCE_SOURCE = "S2ID"

    REQUIRED_COLUMN_MAP = {
        "protocol": "protocol",
        "municipality_code": "municipality_code",
        "municipality_name": "municipality_name",
        "cobrade_code": "cobrade_code",
        "occurrence_date": "occurrence_date",
    }

    def import_csv(
        self,
        csv_path,
        column_map=None,
        municipality_codes=None,
        encoding="utf-8-sig",
        delimiter=",",
    ):
        """Retorna (registros, erros, linhas_lidas).

        column_map associa os nomes canônicos acima aos cabeçalhos reais do CSV.
        municipality_codes, quando informado, restringe a seleção aos códigos
        IBGE desejados. Nenhuma coordenada ou hora é inferida.
        """
        path = Path(csv_path)
        if not path.is_file():
            raise FileNotFoundError(f"S2ID_FILE_NOT_FOUND: {path}")

        mapping = dict(self.REQUIRED_COLUMN_MAP)
        if column_map:
            mapping.update(column_map)

        missing_mapping = [
            key for key in self.REQUIRED_COLUMN_MAP
            if not isinstance(mapping.get(key), str) or not mapping[key].strip()
        ]
        if missing_mapping:
            raise S2IDImportError(
                "COLUMN_MAPPING_INVALID:" + ",".join(missing_mapping)
            )

        allowed_municipalities = None
        if municipality_codes is not None:
            allowed_municipalities = {
                self._normalize_code(value) for value in municipality_codes
            }
            if not allowed_municipalities or "" in allowed_municipalities:
                raise S2IDImportError("MUNICIPALITY_FILTER_INVALID")

        records = []
        errors = []
        seen_protocols = set()

        with path.open("r", encoding=encoding, newline="") as stream:
            reader = csv.DictReader(stream, delimiter=delimiter)
            headers = set(reader.fieldnames or [])
            missing_headers = [
                mapping[key] for key in self.REQUIRED_COLUMN_MAP
                if mapping[key] not in headers
            ]
            if missing_headers:
                raise S2IDImportError(
                    "CSV_HEADERS_MISSING:" + ",".join(missing_headers)
                )

            rows = list(reader)

        for line_number, row in enumerate(rows, start=2):
            try:
                record = self._normalize_row(row, mapping)
                if record["cobrade_code"] != self.COBRADE_HAIL:
                    continue
                if (
                    allowed_municipalities is not None
                    and record["municipality_code"] not in allowed_municipalities
                ):
                    continue
                protocol = record["protocol"]
                if protocol in seen_protocols:
                    raise S2IDImportError("DUPLICATE_PROTOCOL")
                seen_protocols.add(protocol)
                records.append(record)
            except (S2IDImportError, ValueError, TypeError) as exc:
                errors.append({
                    "csv_line": line_number,
                    "protocol": (row.get(mapping["protocol"]) or "").strip() or None,
                    "reason": str(exc),
                })

        return records, errors, len(rows)

    def _normalize_row(self, row, mapping):
        protocol = self._required(row, mapping["protocol"], "PROTOCOL_REQUIRED")
        municipality_code = self._normalize_code(
            self._required(
                row, mapping["municipality_code"], "MUNICIPALITY_CODE_REQUIRED"
            )
        )
        if len(municipality_code) != 7:
            raise S2IDImportError("MUNICIPALITY_CODE_INVALID")

        municipality_name = self._required(
            row, mapping["municipality_name"], "MUNICIPALITY_NAME_REQUIRED"
        )
        cobrade_code = self._normalize_code(
            self._required(row, mapping["cobrade_code"], "COBRADE_CODE_REQUIRED")
        )
        occurrence_date = self._parse_date(
            self._required(
                row, mapping["occurrence_date"], "OCCURRENCE_DATE_REQUIRED"
            )
        )

        return {
            "reference_source": self.REFERENCE_SOURCE,
            "reference_type": self.REFERENCE_TYPE,
            "reference_id": protocol,
            "protocol": protocol,
            "municipality_code": municipality_code,
            "municipality_name": municipality_name,
            "cobrade_code": cobrade_code,
            "occurrence_date": occurrence_date.isoformat(),
            "temporal_precision": "DATE_ONLY",
            "spatial_precision": "MUNICIPALITY_ONLY",
            "eligible_for_meteorological_training": False,
            "exclusion_reason": (
                "ADMINISTRATIVE_RECORD_WITHOUT_EVENT_COORDINATE_OR_INTRADAY_TIME"
            ),
            "method_version": self.METHOD_VERSION,
        }

    @staticmethod
    def _required(row, column, error_code):
        value = row.get(column)
        if value is None or not str(value).strip():
            raise S2IDImportError(error_code)
        return str(value).strip()

    @staticmethod
    def _normalize_code(value):
        text = str(value).strip()
        if re.fullmatch(r"\d+\.0+", text):
            text = text.split(".", 1)[0]
        return re.sub(r"[^0-9]", "", text)

    @staticmethod
    def _parse_date(value):
        text = str(value).strip()
        formats = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y")
        for fmt in formats:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                pass
        try:
            return date.fromisoformat(text[:10])
        except ValueError as exc:
            raise S2IDImportError("OCCURRENCE_DATE_INVALID") from exc
