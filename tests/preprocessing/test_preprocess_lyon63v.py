"""Exercise the generic dataset preprocessor with synthetic cases and Lyon63V."""

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from script.preprocessing.preprocessing import (
    QualityReport,
    parse_coordinate,
    parse_departure,
    preprocess_demand,
    validate_network,
    validate_odlayer,
    write_simulation_demand,
)
from script.preprocessing.preprocess_dataset import main


DEMAND_HEADER = "ID;DEPARTURE;ORIGIN;DESTINATION"


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def read_semicolon_csv(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.reader(source, delimiter=";"))


def valid_network() -> dict:
    return {
        "ROADS": {
            "NODES": {
                "n0": {"id": "n0", "position": [0, 0]},
                "n1": {"id": "n1", "position": [1, 0]},
            },
            "SECTIONS": {
                "s01": {
                    "id": "s01",
                    "upstream": "n0",
                    "downstream": "n1",
                    "length": 1,
                }
            },
            "STOPS": {
                "stop0": {
                    "id": "stop0",
                    "section": "s01",
                    "relative_position": 0.5,
                    "absolute_position": [0.5, 0],
                }
            },
            "ZONES": {},
        },
        "LAYERS": [
            {"ID": "BUSLayer", "LINES": [{"ID": "L1", "STOPS": ["stop0"], "SECTIONS": [["s01"]]}]}
        ],
    }


def run_demand(tmp_path: Path, content: str):
    source = write_text(tmp_path / "demand.csv", content)
    output_dir = tmp_path / "processed"
    output_dir.mkdir()
    report = QualityReport()
    result = preprocess_demand(source, output_dir, report)
    return source, output_dir, report, result


def issue_codes(report: QualityReport, dataset: str | None = None) -> set[str]:
    return {issue["code"] for issue in report.issues if dataset is None or issue["dataset"] == dataset}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1 2", (1, 2)),
        ("  -1.25\t2e1  ", (-1.25, 20)),
    ],
)
def test_parse_coordinate_accepts_two_finite_numbers(value, expected):
    parsed = parse_coordinate(value)
    assert parsed is not None
    assert tuple(float(number) for number in parsed) == expected


@pytest.mark.parametrize("value", ["", "1", "1 2 3", "x 2", "NaN 2", "Infinity 0"])
def test_parse_coordinate_rejects_malformed_or_nonfinite_values(value):
    assert parse_coordinate(value) is None


@pytest.mark.parametrize(
    ("value", "valid"),
    [("00:00:00", True), ("23:59:59.5", True), ("24:00:00", False), ("8:00:00", False), ("08:60:00", False), ("", False)],
)
def test_parse_departure_strictly_checks_clock_time(value, valid):
    assert (parse_departure(value) is not None) is valid


def test_normalization_preserves_rows_and_optional_columns(tmp_path):
    source, output_dir, report, result = run_demand(
        tmp_path,
        "\ufeffID;DEPARTURE;ORIGIN;DESTINATION;NOTE\n"
        "u1;08:00:00; 001.00   2e0 ;3.5 4;keep this\n",
    )

    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    normalized = read_semicolon_csv(output_dir / "demand_normalized.csv")
    assert result["data_rows"] == 1
    assert normalized[1] == ["u1", "08:00:00", "1 2", "3.5 4", "keep this"]
    assert report.count("ERROR") == 0
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash


def test_short_and_identical_trips_are_never_filtered(tmp_path):
    _, output_dir, report, result = run_demand(
        tmp_path,
        f"{DEMAND_HEADER}\n"
        "same;08:00:00;1 1;1 1\n"
        "short;08:00:01;1 1;1.01 1\n",
    )

    rows = read_semicolon_csv(output_dir / "demand_normalized.csv")
    assert result["data_rows"] == 2
    assert len(rows) == 3
    assert report.count("ERROR") == 0
    assert [issue["code"] for issue in report.issues] == ["IDENTICAL_ORIGIN_DESTINATION"]


def test_repeated_ids_and_exact_duplicate_rows_are_warned_but_kept(tmp_path):
    _, output_dir, report, result = run_demand(
        tmp_path,
        f"{DEMAND_HEADER}\n"
        "dup;08:00:00;0 0;1 1\n"
        "dup;08:00:00;0 0;1 1\n"
        "dup;08:01:00;0 0;2 2\n",
    )

    assert result["data_rows"] == 3
    assert len(read_semicolon_csv(output_dir / "demand_normalized.csv")) == 4
    assert report.count("WARNING") == 5
    assert issue_codes(report) == {"REPEATED_ID", "EXACT_DUPLICATE_ROW"}
    assert report.count("ERROR") == 0


def test_unordered_departures_are_sorted_stably_only_in_simulation_copy(tmp_path):
    _, output_dir, report, result = run_demand(
        tmp_path,
        f"{DEMAND_HEADER};NOTE\n"
        "late;08:02:00;0 0;1 1;first\n"
        "early-a;08:01:00;0 0;1 1;second\n"
        "early-b;08:01:00;0 0;1 1;third\n",
    )
    export = output_dir / "demand_for_simulation.csv"

    assert report.count("WARNING") == 1
    assert write_simulation_demand(export, result, report)
    assert [row[0] for row in read_semicolon_csv(export)[1:]] == ["early-a", "early-b", "late"]
    assert len(read_semicolon_csv(export)) == 4
    assert [row[0] for row in read_semicolon_csv(output_dir / "demand_normalized.csv")[1:]] == [
        "late",
        "early-a",
        "early-b",
    ]


@pytest.mark.parametrize("bad_origin", ["", "1", "x 2", "NaN 2", "Infinity 0", "1 2 3"])
def test_invalid_origin_is_reported_and_row_is_retained(tmp_path, bad_origin):
    _, output_dir, report, result = run_demand(
        tmp_path,
        f"{DEMAND_HEADER}\nu1;08:00:00;{bad_origin};3 4\n",
    )

    assert result["data_rows"] == 1
    assert len(read_semicolon_csv(output_dir / "demand_normalized.csv")) == 2
    assert report.count("ERROR") >= 1
    assert "MISSING_ORIGIN" in issue_codes(report) or "INVALID_ORIGIN" in issue_codes(report)
    assert not write_simulation_demand(output_dir / "simulation.csv", result, report)
    assert not (output_dir / "simulation.csv").exists()


@pytest.mark.parametrize("bad_departure", ["", "8:00:00", "24:00:00", "08:60:00", "yesterday"])
def test_invalid_departure_is_reported_and_row_is_retained(tmp_path, bad_departure):
    _, output_dir, report, result = run_demand(
        tmp_path,
        f"{DEMAND_HEADER}\nu1;{bad_departure};1 2;3 4\n",
    )

    assert result["data_rows"] == 1
    assert len(read_semicolon_csv(output_dir / "demand_normalized.csv")) == 2
    assert "MISSING_DEPARTURE" in issue_codes(report) or "INVALID_DEPARTURE" in issue_codes(report)


def test_missing_required_values_are_each_reported(tmp_path):
    _, _, report, result = run_demand(tmp_path, f"{DEMAND_HEADER}\n; ; ;\n")

    assert result["blocking_rows"] == 1
    assert {"MISSING_ID", "MISSING_DEPARTURE", "MISSING_ORIGIN", "MISSING_DESTINATION"} <= issue_codes(report)


@pytest.mark.parametrize("row", ["u1;08:00:00;1 2", "u1;08:00:00;1 2;3 4;extra"])
def test_wrong_column_count_is_reported_without_dropping_row(tmp_path, row):
    _, output_dir, report, result = run_demand(tmp_path, f"{DEMAND_HEADER}\n{row}\n")

    assert result["data_rows"] == 1
    assert result["blocking_rows"] == 1
    assert "COLUMN_COUNT_MISMATCH" in issue_codes(report)
    assert len(read_semicolon_csv(output_dir / "demand_normalized.csv")) == 2


def test_missing_required_header_marks_all_records_as_blocked(tmp_path):
    _, _, report, result = run_demand(tmp_path, "ID;DEPARTURE;ORIGIN\nu1;08:00:00;1 2\n")

    assert "MISSING_REQUIRED_COLUMN" in issue_codes(report)
    assert result["blocking_rows"] == 1


def test_duplicate_header_is_reported_without_column_rewrite(tmp_path):
    _, output_dir, report, result = run_demand(
        tmp_path,
        "ID;DEPARTURE;ORIGIN;DESTINATION;ORIGIN\nu1;08:00:00;1 2;3 4;5 6\n",
    )

    assert "DUPLICATE_COLUMN_NAMES" in issue_codes(report)
    assert result["blocking_rows"] == 1
    assert read_semicolon_csv(output_dir / "demand_normalized.csv")[1] == [
        "u1",
        "08:00:00",
        "1 2",
        "3 4",
        "5 6",
    ]


def test_empty_file_and_blank_record_are_explicit_errors(tmp_path):
    empty_source, empty_output, empty_report, empty_result = run_demand(tmp_path / "empty", "")
    assert empty_source.exists()
    assert empty_result["data_rows"] == 0
    assert "EMPTY_FILE" in issue_codes(empty_report)
    assert (empty_output / "demand_normalized.csv").read_text(encoding="utf-8") == ""

    _, blank_output, blank_report, blank_result = run_demand(tmp_path / "blank", f"{DEMAND_HEADER}\n\n")
    assert blank_result["data_rows"] == 1
    assert blank_result["blocking_rows"] == 1
    assert "EMPTY_ROW" in issue_codes(blank_report)
    assert len(read_semicolon_csv(blank_output / "demand_normalized.csv")) == 2


def test_network_valid_fixture_has_no_issues(tmp_path):
    source = write_json(tmp_path / "network.json", valid_network())
    report = QualityReport()

    counts = validate_network(source, report)

    assert counts == {"nodes": 2, "sections": 1, "stops": 1, "layers": 1}
    assert report.count("ERROR", "network") == 0
    assert report.count("WARNING", "network") == 0


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        (lambda network: network["ROADS"]["NODES"]["n0"].update(position=[0]), "INVALID_NODE_POSITION"),
        (lambda network: network["ROADS"]["SECTIONS"]["s01"].update(upstream="absent"), "UNKNOWN_UPSTREAM_NODE"),
        (lambda network: network["ROADS"]["SECTIONS"]["s01"].update(length=-1), "NEGATIVE_SECTION_LENGTH"),
        (lambda network: network["ROADS"]["STOPS"]["stop0"].update(section="absent"), "UNKNOWN_STOP_SECTION"),
        (lambda network: network["LAYERS"][0]["LINES"][0].update(STOPS=["absent"]), "UNKNOWN_LINE_STOP"),
    ],
)
def test_network_semantic_errors_are_reported(tmp_path, mutate, expected_code):
    payload = valid_network()
    mutate(payload)
    source = write_json(tmp_path / "network.json", payload)
    report = QualityReport()

    validate_network(source, report)

    assert expected_code in issue_codes(report, "network")


def test_zero_length_section_and_out_of_range_stop_are_warnings(tmp_path):
    payload = valid_network()
    payload["ROADS"]["SECTIONS"]["s01"]["length"] = 0
    payload["ROADS"]["STOPS"]["stop0"]["relative_position"] = 1.5
    source = write_json(tmp_path / "network.json", payload)
    report = QualityReport()

    validate_network(source, report)

    assert {"ZERO_SECTION_LENGTH", "STOP_RELATIVE_POSITION_OUT_OF_RANGE"} <= issue_codes(report, "network")
    assert report.count("ERROR", "network") == 0


@pytest.mark.parametrize("payload", [[], {"OTHER": {}}])
def test_network_invalid_roots_and_missing_roads_are_reported(tmp_path, payload):
    source = write_json(tmp_path / "network.json", payload)
    report = QualityReport()

    validate_network(source, report)

    assert report.count("ERROR", "network") >= 1


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        ({"ROADS": {"NODES": {}, "SECTIONS": {}}}, "INVALID_STOPS"),
        ({"ROADS": {"NODES": {}, "STOPS": {}}}, "INVALID_SECTIONS"),
        ({"ROADS": {"SECTIONS": {}, "STOPS": {}}}, "INVALID_NODES"),
    ],
)
def test_network_missing_roads_components_are_reported(tmp_path, payload, expected_code):
    source = write_json(tmp_path / "network.json", payload)
    report = QualityReport()

    validate_network(source, report)

    assert expected_code in issue_codes(report, "network")


def test_network_malformed_json_is_reported_without_exception(tmp_path):
    source = write_text(tmp_path / "network.json", '{"ROADS": ')
    report = QualityReport()

    counts = validate_network(source, report)

    assert counts == {"nodes": 0, "sections": 0, "stops": 0, "layers": 0}
    assert "UNREADABLE_JSON" in issue_codes(report, "network")


def test_odlayer_bad_coordinate_is_reported_and_not_repaired(tmp_path):
    source = write_json(
        tmp_path / "odlayer.json",
        {"ORIGINS": {"o1": [1, 2]}, "DESTINATIONS": {"d1": [float("nan"), 2]}},
    )
    report = QualityReport()
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()

    counts = validate_odlayer(source, report)

    assert counts == {"origins": 1, "destinations": 1}
    assert "INVALID_COORDINATE" in issue_codes(report, "odlayer")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash


@pytest.mark.parametrize("payload", [[], {"ORIGINS": {}}])
def test_odlayer_missing_required_structure_is_reported(tmp_path, payload):
    source = write_json(tmp_path / "odlayer.json", payload)
    report = QualityReport()

    validate_odlayer(source, report)

    assert report.count("ERROR", "odlayer") >= 1


def test_summary_omits_outputs_that_were_not_created(tmp_path):
    output_dir = tmp_path / "out"
    result = main(
        [
            "--demand", str(tmp_path / "missing.csv"),
            "--network", str(tmp_path / "missing-network.json"),
            "--odlayer", str(tmp_path / "missing-od.json"),
            "--output-dir", str(output_dir),
        ]
    )

    assert result == 1
    summary = json.loads((output_dir / "preprocessing_summary.json").read_text(encoding="utf-8"))
    assert summary["outputs"] == [
        "demand_qa.csv",
        "network_qa.csv",
        "odlayer_qa.csv",
        "review_log.csv",
        "review_decisions_template.csv",
        "preprocessing_summary.json",
    ]
    assert not (output_dir / "demand_normalized.csv").exists()


def test_cli_accepts_non_lyon_paths_and_preserves_input_files(tmp_path):
    demand = write_text(tmp_path / "custom_demande.csv", f"{DEMAND_HEADER}\nu1;08:00:00;1 2;3 4\n")
    network = write_json(tmp_path / "custom_network.json", valid_network())
    odlayer = write_json(
        tmp_path / "custom_od.json",
        {"ORIGINS": {"o1": [1, 2]}, "DESTINATIONS": {"d1": [3, 4]}},
    )
    original_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (demand, network, odlayer)}
    output_dir = tmp_path / "custom_output"

    result = main(
        [
            "--demand",
            str(demand),
            "--network",
            str(network),
            "--odlayer",
            str(odlayer),
            "--output-dir",
            str(output_dir),
            "--write-simulation-demand",
        ]
    )

    assert result == 0
    assert (output_dir / "demand_normalized.csv").exists()
    assert (output_dir / "demand_for_simulation.csv").exists()
    assert (output_dir / "demand_qa.csv").exists()
    assert (output_dir / "network_qa.csv").exists()
    assert (output_dir / "odlayer_qa.csv").exists()
    summary = json.loads((output_dir / "preprocessing_summary.json").read_text(encoding="utf-8"))
    assert summary["counts"]["demand_rows"] == 1
    assert summary["policy"]["records_automatically_deleted"] == 0
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in original_hashes.items())


def test_cli_accepts_a_dataset_directory_and_custom_filenames(tmp_path):
    input_dir = tmp_path / "another-city" / "raw"
    input_dir.mkdir(parents=True)
    demand = write_text(input_dir / "trips.csv", f"{DEMAND_HEADER}\nu1;08:00:00;1 2;3 4\n")
    network = write_json(input_dir / "streets.json", valid_network())
    odlayer = write_json(
        input_dir / "connectors.json",
        {"ORIGINS": {"o1": [1, 2]}, "DESTINATIONS": {"d1": [3, 4]}},
    )
    original_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (demand, network, odlayer)}

    result = main(
        [
            "--input-dir", str(input_dir),
            "--demand-file", "trips.csv",
            "--network-file", "streets.json",
            "--odlayer-file", "connectors.json",
            "--write-simulation-demand",
        ]
    )

    output_dir = input_dir / "PREPROCESSED"
    assert result == 0
    assert (output_dir / "demand_for_simulation.csv").exists()
    summary = json.loads((output_dir / "preprocessing_summary.json").read_text(encoding="utf-8"))
    assert summary["counts"]["demand_rows"] == 1
    assert {item["path"] for item in summary["inputs"].values()} == {
        str(demand.resolve()),
        str(network.resolve()),
        str(odlayer.resolve()),
    }
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in original_hashes.items())


def test_cli_refuses_output_paths_that_would_overwrite_an_input(tmp_path):
    input_dir = tmp_path / "dataset"
    input_dir.mkdir()
    write_text(input_dir / "demand_normalized.csv", f"{DEMAND_HEADER}\nu1;08:00:00;1 2;3 4\n")
    write_json(input_dir / "network.json", valid_network())
    write_json(input_dir / "odlayer.json", {"ORIGINS": {}, "DESTINATIONS": {}})

    with pytest.raises(SystemExit, match="would overwrite an input file"):
        main(
            [
                "--input-dir",
                str(input_dir),
                "--demand-file",
                "demand_normalized.csv",
                "--output-dir",
                str(input_dir),
            ]
        )


def test_cli_invalid_demand_keeps_normalized_copy_but_blocks_simulation_export(tmp_path):
    demand = write_text(tmp_path / "bad.csv", f"{DEMAND_HEADER}\nu1;not-a-time;1 2;3 4\n")
    network = write_json(tmp_path / "network.json", valid_network())
    odlayer = write_json(tmp_path / "odlayer.json", {"ORIGINS": {}, "DESTINATIONS": {}})
    output_dir = tmp_path / "out"

    result = main(
        [
            "--demand",
            str(demand),
            "--network",
            str(network),
            "--odlayer",
            str(odlayer),
            "--output-dir",
            str(output_dir),
            "--write-simulation-demand",
        ]
    )

    assert result == 1
    assert (output_dir / "demand_normalized.csv").exists()
    assert not (output_dir / "demand_for_simulation.csv").exists()
    summary = json.loads((output_dir / "preprocessing_summary.json").read_text(encoding="utf-8"))
    assert summary["counts"]["demand_rows_with_blocking_issues"] == 1
    assert summary["policy"]["records_automatically_deleted"] == 0
    review_rows = read_semicolon_csv(output_dir / "review_log.csv")
    assert review_rows[0] == [
        "review_id",
        "dataset",
        "record_type",
        "record_id",
        "source_row",
        "severity",
        "code",
        "message",
        "review_guidance",
    ]
    assert any("INVALID_DEPARTURE" in row for row in review_rows)
    decision_rows = read_semicolon_csv(output_dir / "review_decisions_template.csv")
    assert decision_rows[0] == [
        "review_id",
        "decision",
        "corrected_value",
        "reviewer",
        "validated_by",
        "rationale",
    ]
    assert all(not value for row in decision_rows[1:] for value in row[1:])


def test_cli_malformed_csv_is_reported_without_uncaught_exception(tmp_path):
    demand = write_text(tmp_path / "broken.csv", f'{DEMAND_HEADER}\nu1;08:00:00;"unterminated;3 4\n')
    network = write_json(tmp_path / "network.json", valid_network())
    odlayer = write_json(tmp_path / "odlayer.json", {"ORIGINS": {}, "DESTINATIONS": {}})
    output_dir = tmp_path / "out"

    result = main(
        [
            "--demand",
            str(demand),
            "--network",
            str(network),
            "--odlayer",
            str(odlayer),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert result == 1
    qa_rows = read_semicolon_csv(output_dir / "demand_qa.csv")
    assert any("CSV_PARSE_ERROR" in row for row in qa_rows)


def test_preprocess_real_lyon63v_inputs_without_modifying_them(tmp_path):
    repository_root = Path(__file__).resolve().parents[2]
    inputs = repository_root / "examples" / "Lyon63V" / "INPUTS"
    demand = inputs / "demand-Lyon63V-coords.csv"
    network = inputs / "network-Lyon63V.json"
    odlayer = inputs / "odlayer-Lyon63V.json"
    if not all(path.is_file() for path in (demand, network, odlayer)):
        pytest.skip("Jeu de données Lyon63V non présent dans ce checkout.")

    original_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (demand, network, odlayer)}
    output_dir = tmp_path / "lyon63v"
    script = repository_root / "script" / "preprocessing" / "preprocess_dataset.py"
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-dir",
            str(inputs),
            "--demand-file",
            demand.name,
            "--network-file",
            network.name,
            "--odlayer-file",
            odlayer.name,
            "--output-dir",
            str(output_dir),
            "--write-simulation-demand",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    source_row_count = len(read_semicolon_csv(demand))
    assert len(read_semicolon_csv(output_dir / "demand_normalized.csv")) == source_row_count
    assert len(read_semicolon_csv(output_dir / "demand_for_simulation.csv")) == source_row_count
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in original_hashes.items())
