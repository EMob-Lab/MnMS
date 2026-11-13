"""Reusable, dataset-agnostic preprocessing functions for MnMS inputs.

This module contains parsing, validation, normalization, and report helpers.
Use ``preprocess_dataset.py`` as the command-line entry point.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

REQUIRED_DEMAND_COLUMNS = ("ID", "DEPARTURE", "ORIGIN", "DESTINATION")
COORDINATE_COLUMNS = ("ORIGIN", "DESTINATION")
TIME_PATTERN = re.compile(r"^\d{2}:\d{2}:\d{2}(?:\.\d+)?$")
ISSUE_FIELDS = ("dataset", "record_type", "record_id", "source_row", "severity", "code", "message")
REVIEW_LOG_FIELDS = (
    "review_id", "dataset", "record_type", "record_id", "source_row",
    "severity", "code", "message", "review_guidance",
)
REVIEW_DECISION_FIELDS = ("review_id", "decision", "corrected_value", "reviewer", "validated_by", "rationale")


class QualityReport:
    """Collect structured issues without altering or discarding source data."""

    def __init__(self) -> None:
        self.issues: list[dict[str, str]] = []

    def add(
        self,
        dataset: str,
        severity: str,
        code: str,
        message: str,
        *,
        record_type: str = "file",
        record_id: str = "",
        source_row: int | str = "",
    ) -> None:
        self.issues.append({
            "dataset": dataset,
            "record_type": record_type,
            "record_id": str(record_id),
            "source_row": str(source_row),
            "severity": severity,
            "code": code,
            "message": message,
        })

    def write_csv(self, destination: Path, dataset: str) -> None:
        with destination.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=ISSUE_FIELDS, delimiter=";")
            writer.writeheader()
            writer.writerows(issue for issue in self.issues if issue["dataset"] == dataset)

    def count(self, severity: str, dataset: str | None = None) -> int:
        return sum(
            issue["severity"] == severity and (dataset is None or issue["dataset"] == dataset)
            for issue in self.issues
        )


def review_guidance(issue: dict[str, str]) -> str:
    """Suggest a conservative human review; this never performs the action."""
    code = issue["code"]
    if code in {"MISSING_ORIGIN", "INVALID_ORIGIN", "MISSING_DESTINATION", "INVALID_DESTINATION", "INVALID_COORDINATE"}:
        return (
            "Vérifier le format et le SCR auprès de la source. Si une valeur fiable existe, la reporter uniquement "
            "dans une copie dérivée avec provenance ; sinon proposer l'exclusion de cette ligne pour validation."
        )
    if code in {"REPEATED_ID", "EXACT_DUPLICATE_ROW"}:
        return "Comparer à la source et vérifier la signification de l'ID ; conserver par défaut, ne proposer une exclusion qu'après confirmation."
    if code == "DEPARTURES_NOT_SORTED":
        return "Vérifier si l'ordre est attendu ; le CSV source reste inchangé et l'export simulation peut être trié stablement."
    if code == "IDENTICAL_ORIGIN_DESTINATION":
        return "Cas potentiellement valide ; conserver sauf confirmation métier contraire."
    if code in {"UNKNOWN_UPSTREAM_NODE", "UNKNOWN_DOWNSTREAM_NODE", "UNKNOWN_STOP_SECTION", "UNKNOWN_LINE_STOP"}:
        return "Vérifier les identifiants contre la source de référence et le réseau ; ne pas remapper ni supprimer automatiquement."
    if code in {"ZERO_SECTION_LENGTH", "STOP_RELATIVE_POSITION_OUT_OF_RANGE", "INVALID_SECTION_LENGTH", "NEGATIVE_SECTION_LENGTH"}:
        return "Vérifier les unités, la géométrie et les règles du format source ; conserver jusqu'à validation."
    if issue["severity"] == "INFO":
        return "Information seulement ; aucune correction recommandée."
    if issue["severity"] == "WARNING":
        return "Vérifier le contexte ; conserver par défaut, documenter toute correction ou exclusion proposée."
    return (
        "Erreur structurelle potentielle : retrouver la valeur dans la source autoritative. "
        "Corriger dans une copie dérivée ou proposer l'exclusion uniquement après validation documentée."
    )


def _review_id(issue: dict[str, str]) -> str:
    identity = "|".join(issue[field] for field in ("dataset", "record_type", "record_id", "source_row", "code"))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def write_review_logs(report: QualityReport, output_dir: Path) -> None:
    """Write issue explanations and a blank human-validation decision template."""
    with (output_dir / "review_log.csv").open("w", encoding="utf-8", newline="") as log_file:
        writer = csv.DictWriter(log_file, fieldnames=REVIEW_LOG_FIELDS, delimiter=";")
        writer.writeheader()
        for issue in report.issues:
            writer.writerow({"review_id": _review_id(issue), **issue, "review_guidance": review_guidance(issue)})

    with (output_dir / "review_decisions_template.csv").open("w", encoding="utf-8", newline="") as decisions_file:
        writer = csv.DictWriter(decisions_file, fieldnames=REVIEW_DECISION_FIELDS, delimiter=";")
        writer.writeheader()
        for issue in report.issues:
            writer.writerow({
                "review_id": _review_id(issue),
                "decision": "",
                "corrected_value": "",
                "reviewer": "",
                "validated_by": "",
                "rationale": "",
            })


def parse_coordinate(value: str) -> tuple[Decimal, Decimal] | None:
    """Parse the MnMS ``x y`` coordinate format, accepting any whitespace."""
    parts = value.split()
    if len(parts) != 2:
        return None
    try:
        x, y = (Decimal(part) for part in parts)
    except InvalidOperation:
        return None
    if not x.is_finite() or not y.is_finite():
        return None
    return x, y


def format_coordinate(point: tuple[Decimal, Decimal]) -> str:
    """Return a whitespace-normalized coordinate without float conversion."""
    return " ".join(format(value.normalize(), "f") for value in point)


def parse_departure(value: str) -> tuple[time, float] | None:
    """Parse HH:MM:SS[.fraction] strictly, for validation and stable sorting."""
    if not TIME_PATTERN.fullmatch(value):
        return None
    try:
        parsed = time.fromisoformat(value)
    except ValueError:
        return None
    seconds = parsed.hour * 3600 + parsed.minute * 60 + parsed.second + parsed.microsecond / 1_000_000
    return parsed, seconds


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _field_indexes(header: list[str], report: QualityReport) -> dict[str, int]:
    duplicates = [name for name, count in Counter(header).items() if count > 1]
    if duplicates:
        report.add(
            "demand", "ERROR", "DUPLICATE_COLUMN_NAMES",
            f"En-têtes répétés, interprétation ambiguë : {', '.join(duplicates)}. Aucune colonne ne sera réécrite.",
        )
    indexes: dict[str, int] = {}
    for name in REQUIRED_DEMAND_COLUMNS:
        if name not in header:
            report.add("demand", "ERROR", "MISSING_REQUIRED_COLUMN", f"Colonne obligatoire absente : {name}.")
        elif header.count(name) == 1:
            indexes[name] = header.index(name)
    return indexes


def preprocess_demand(source: Path, output_dir: Path, report: QualityReport) -> dict[str, Any]:
    """Validate and normalize demand while retaining every parsed CSV row."""
    with source.open("r", encoding="utf-8-sig", newline="") as input_file:
        rows = list(csv.reader(input_file, delimiter=";", strict=True))
    if not rows:
        report.add("demand", "ERROR", "EMPTY_FILE", "Le fichier de demande est vide.")
        (output_dir / "demand_normalized.csv").write_text("", encoding="utf-8")
        return {"data_rows": 0, "header": [], "rows": [], "blocking_rows": 0}

    header = rows[0]
    indexes = _field_indexes(header, report)
    if not header:
        report.add("demand", "ERROR", "EMPTY_HEADER", "La ligne d'en-tête est vide.")

    seen_ids: dict[str, list[int]] = defaultdict(list)
    seen_rows: dict[tuple[str, ...], list[int]] = defaultdict(list)
    parsed_departures: list[tuple[int, float]] = []
    records: list[dict[str, Any]] = []
    blocking_rows = 0

    for source_row, original in enumerate(rows[1:], start=2):
        fields = list(original)
        row_issue_start = len(report.issues)
        if not fields:
            report.add("demand", "ERROR", "EMPTY_ROW", "Ligne vide conservée dans la copie normalisée.", source_row=source_row)
            records.append({"row": fields, "source_row": source_row, "departure_seconds": None})
            blocking_rows += 1
            continue
        if len(fields) != len(header):
            report.add(
                "demand", "ERROR", "COLUMN_COUNT_MISMATCH",
                f"{len(fields)} valeurs pour {len(header)} colonnes ; ligne conservée telle quelle.",
                source_row=source_row,
            )

        record_id = fields[indexes["ID"]].strip() if "ID" in indexes and indexes["ID"] < len(fields) else ""
        if "ID" in indexes:
            fields[indexes["ID"]] = record_id
            if not record_id:
                report.add("demand", "ERROR", "MISSING_ID", "Identifiant vide.", source_row=source_row)
            else:
                seen_ids[record_id].append(source_row)

        departure_seconds: float | None = None
        if "DEPARTURE" in indexes and indexes["DEPARTURE"] < len(fields):
            departure = fields[indexes["DEPARTURE"]].strip()
            fields[indexes["DEPARTURE"]] = departure
            parsed = parse_departure(departure)
            if not departure:
                report.add("demand", "ERROR", "MISSING_DEPARTURE", "Horaire de départ vide.", record_id=record_id, source_row=source_row)
            elif parsed is None:
                report.add("demand", "ERROR", "INVALID_DEPARTURE", f"Horaire illisible ou invalide : {departure!r}.", record_id=record_id, source_row=source_row)
            else:
                departure_seconds = parsed[1]
                parsed_departures.append((source_row, departure_seconds))

        parsed_points: dict[str, tuple[Decimal, Decimal]] = {}
        for column in COORDINATE_COLUMNS:
            if column not in indexes or indexes[column] >= len(fields):
                continue
            index = indexes[column]
            original_value = fields[index].strip()
            point = parse_coordinate(original_value)
            if not original_value:
                report.add("demand", "ERROR", f"MISSING_{column}", f"Coordonnée {column} vide.", record_id=record_id, source_row=source_row)
            elif point is None:
                report.add(
                    "demand", "ERROR", f"INVALID_{column}",
                    f"Coordonnée {column} non interprétable comme deux nombres finis : {original_value!r}.",
                    record_id=record_id, source_row=source_row,
                )
            else:
                parsed_points[column] = point
                fields[index] = format_coordinate(point)

        if len(parsed_points) == 2 and parsed_points["ORIGIN"] == parsed_points["DESTINATION"]:
            report.add(
                "demand", "INFO", "IDENTICAL_ORIGIN_DESTINATION",
                "Origine et destination identiques ; conservé, à interpréter selon le besoin métier.",
                record_id=record_id, source_row=source_row,
            )

        row_key = tuple(original)
        seen_rows[row_key].append(source_row)
        if len(report.issues) > row_issue_start and any(
            issue["severity"] == "ERROR" and issue["source_row"] == str(source_row)
            for issue in report.issues[row_issue_start:]
        ):
            blocking_rows += 1
        records.append({"row": fields, "source_row": source_row, "departure_seconds": departure_seconds})

    for record_id, source_rows in seen_ids.items():
        if len(source_rows) > 1:
            for source_row in source_rows:
                report.add(
                    "demand", "WARNING", "REPEATED_ID",
                    f"Identifiant présent sur les lignes {', '.join(map(str, source_rows))} ; aucune occurrence supprimée.",
                    record_id=record_id, source_row=source_row,
                )
    for source_rows in seen_rows.values():
        if len(source_rows) > 1:
            for source_row in source_rows:
                report.add(
                    "demand", "WARNING", "EXACT_DUPLICATE_ROW",
                    f"Ligne entièrement répétée aux lignes {', '.join(map(str, source_rows))} ; conservée.",
                    source_row=source_row,
                )
    for previous, current in zip(parsed_departures, parsed_departures[1:]):
        if current[1] < previous[1]:
            report.add(
                "demand", "WARNING", "DEPARTURES_NOT_SORTED",
                f"Départ antérieur à celui de la ligne précédente parsable {previous[0]} ; aucune ligne n'est supprimée.",
                source_row=current[0],
            )

    with (output_dir / "demand_normalized.csv").open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file, delimiter=";", lineterminator="\n")
        writer.writerows(rows[:1])
        writer.writerows(record["row"] for record in records)

    if records and any(
        issue["dataset"] == "demand" and issue["severity"] == "ERROR" and not issue["source_row"]
        for issue in report.issues
    ):
        blocking_rows = len(records)
    return {"data_rows": len(records), "header": header, "rows": records, "blocking_rows": blocking_rows}


def _finite_number(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def _position_is_valid(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and len(value) == 2 and all(_finite_number(v) for v in value)


def _network_issue(
    report: QualityReport,
    code: str,
    message: str,
    *,
    severity: str = "ERROR",
    record_type: str = "record",
    record_id: str = "",
) -> None:
    report.add("network", severity, code, message, record_type=record_type, record_id=record_id)


def validate_network(source: Path, report: QualityReport) -> dict[str, int]:
    """Check structural network references; do not edit or deduplicate the network."""
    try:
        with source.open("r", encoding="utf-8") as input_file:
            network = json.load(input_file)
    except (OSError, json.JSONDecodeError) as error:
        _network_issue(report, "UNREADABLE_JSON", f"Impossible de lire le JSON : {error}.", record_type="file")
        return {"nodes": 0, "sections": 0, "stops": 0, "layers": 0}
    if not isinstance(network, dict):
        _network_issue(report, "INVALID_ROOT", "La racine du réseau JSON doit être un objet.", record_type="file")
        return {"nodes": 0, "sections": 0, "stops": 0, "layers": 0}
    roads = network.get("ROADS")
    if not isinstance(roads, dict):
        _network_issue(report, "MISSING_ROADS", "Bloc ROADS absent ou invalide.", record_type="file")
        return {"nodes": 0, "sections": 0, "stops": 0, "layers": 0}

    nodes, sections, stops = roads.get("NODES"), roads.get("SECTIONS"), roads.get("STOPS")
    for name, value in (("NODES", nodes), ("SECTIONS", sections), ("STOPS", stops)):
        if not isinstance(value, dict):
            _network_issue(report, f"INVALID_{name}", f"ROADS.{name} absent ou n'est pas un objet.", record_type="file")
    if not all(isinstance(value, dict) for value in (nodes, sections, stops)):
        return {
            "nodes": len(nodes) if isinstance(nodes, dict) else 0,
            "sections": len(sections) if isinstance(sections, dict) else 0,
            "stops": len(stops) if isinstance(stops, dict) else 0,
            "layers": len(network.get("LAYERS", [])) if isinstance(network.get("LAYERS"), list) else 0,
        }

    node_ids: set[str] = set()
    for key, node in nodes.items():
        if not isinstance(node, dict):
            _network_issue(report, "INVALID_NODE", "Le nœud n'est pas un objet JSON.", record_id=key)
            continue
        node_id = str(node.get("id", key))
        node_ids.add(node_id)
        if not _position_is_valid(node.get("position")):
            _network_issue(report, "INVALID_NODE_POSITION", "Position absente ou différente de deux nombres finis.", record_id=node_id)

    section_ids = set(map(str, sections.keys()))
    for key, section in sections.items():
        if not isinstance(section, dict):
            _network_issue(report, "INVALID_SECTION", "Le tronçon n'est pas un objet JSON.", record_id=key)
            continue
        section_id = str(section.get("id", key))
        upstream, downstream = section.get("upstream", section.get("UPSTREAM")), section.get("downstream", section.get("DOWNSTREAM"))
        if upstream is None or downstream is None:
            _network_issue(report, "MISSING_SECTION_ENDPOINT", "Extrémité amont ou aval absente.", record_id=section_id)
        else:
            if str(upstream) not in node_ids:
                _network_issue(report, "UNKNOWN_UPSTREAM_NODE", f"Nœud amont {upstream!r} introuvable.", record_id=section_id)
            if str(downstream) not in node_ids:
                _network_issue(report, "UNKNOWN_DOWNSTREAM_NODE", f"Nœud aval {downstream!r} introuvable.", record_id=section_id)
        length = section.get("length", section.get("LENGTH"))
        if length is None or not _finite_number(length):
            _network_issue(report, "INVALID_SECTION_LENGTH", "Longueur absente ou non finie.", record_id=section_id)
        elif float(length) < 0:
            _network_issue(report, "NEGATIVE_SECTION_LENGTH", f"Longueur négative : {length}.", record_id=section_id)
        elif float(length) == 0:
            _network_issue(report, "ZERO_SECTION_LENGTH", "Longueur nulle à vérifier ; conservée, car elle peut correspondre à un connecteur.", severity="WARNING", record_id=section_id)

    for key, stop in stops.items():
        if not isinstance(stop, dict):
            _network_issue(report, "INVALID_STOP", "L'arrêt n'est pas un objet JSON.", record_id=key)
            continue
        stop_id = str(stop.get("id", key))
        section_id = stop.get("section")
        if section_id is not None and str(section_id) not in section_ids:
            _network_issue(report, "UNKNOWN_STOP_SECTION", f"Section de rattachement {section_id!r} introuvable.", record_id=stop_id)
        if "absolute_position" in stop and not _position_is_valid(stop["absolute_position"]):
            _network_issue(report, "INVALID_STOP_POSITION", "Position absolue absente ou différente de deux nombres finis.", record_id=stop_id)
        relative_position = stop.get("relative_position")
        if relative_position is not None and not _finite_number(relative_position):
            _network_issue(report, "INVALID_STOP_RELATIVE_POSITION", "Position relative non finie.", record_id=stop_id)
        elif relative_position is not None and not 0 <= float(relative_position) <= 1:
            _network_issue(report, "STOP_RELATIVE_POSITION_OUT_OF_RANGE", f"Position relative {relative_position} hors de [0, 1] ; à vérifier sans suppression automatique.", severity="WARNING", record_id=stop_id)

    layers = network.get("LAYERS", [])
    if not isinstance(layers, list):
        _network_issue(report, "INVALID_LAYERS", "LAYERS doit être une liste.", record_type="file")
        layers = []
    for layer in layers:
        if not isinstance(layer, dict):
            _network_issue(report, "INVALID_LAYER", "Une couche n'est pas un objet JSON.", record_type="layer")
            continue
        for line in layer.get("LINES", []) or []:
            if not isinstance(line, dict):
                _network_issue(report, "INVALID_TRANSIT_LINE", "Une ligne n'est pas un objet JSON.", record_type="line")
                continue
            line_id = str(line.get("ID", ""))
            for stop_id in line.get("STOPS", []) or []:
                if str(stop_id) not in stops:
                    _network_issue(report, "UNKNOWN_LINE_STOP", f"Arrêt {stop_id!r} de la ligne absent de ROADS.STOPS.", record_type="line", record_id=line_id)
    return {"nodes": len(nodes), "sections": len(sections), "stops": len(stops), "layers": len(layers)}


def validate_odlayer(source: Path, report: QualityReport) -> dict[str, int]:
    """Check origin/destination coordinate syntax without snapping or filtering."""
    try:
        with source.open("r", encoding="utf-8") as input_file:
            odlayer = json.load(input_file)
    except (OSError, json.JSONDecodeError) as error:
        report.add("odlayer", "ERROR", "UNREADABLE_JSON", f"Impossible de lire le JSON : {error}.")
        return {"origins": 0, "destinations": 0}
    if not isinstance(odlayer, dict):
        report.add("odlayer", "ERROR", "INVALID_ROOT", "La racine ODLayer doit être un objet.")
        return {"origins": 0, "destinations": 0}
    counts: dict[str, int] = {}
    for key, label in (("ORIGINS", "origins"), ("DESTINATIONS", "destinations")):
        values = odlayer.get(key)
        if not isinstance(values, dict):
            report.add("odlayer", "ERROR", f"INVALID_{key}", f"Bloc {key} absent ou invalide.")
            counts[label] = 0
            continue
        counts[label] = len(values)
        for record_id, position in values.items():
            if not _position_is_valid(position):
                report.add("odlayer", "ERROR", "INVALID_COORDINATE", f"Coordonnée de {key} absente ou différente de deux nombres finis : {position!r}.", record_type=label, record_id=record_id)
    return counts


def write_simulation_demand(destination: Path, demand_result: dict[str, Any], report: QualityReport) -> bool:
    """Write a stable time-sorted copy only if all demand rows parse cleanly."""
    if report.count("ERROR", "demand"):
        report.add("demand", "INFO", "SIMULATION_EXPORT_NOT_WRITTEN", "Export MnMS non créé : corriger ou examiner les erreurs, puis relancer. Aucune ligne n'a été écartée.")
        return False
    indexed_records = list(enumerate(demand_result["rows"]))
    indexed_records.sort(key=lambda item: (item[1]["departure_seconds"], item[0]))
    with destination.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file, delimiter=";", lineterminator="\n")
        writer.writerow(demand_result["header"])
        for _, record in indexed_records:
            writer.writerow(record["row"])
    return True
