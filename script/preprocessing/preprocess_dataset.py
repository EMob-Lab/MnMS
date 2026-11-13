"""Command-line entry point for preprocessing one MnMS dataset directory.

The reusable validation and transformation functions live in ``preprocessing.py``.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .preprocessing import (
        QualityReport,
        preprocess_demand,
        sha256_file,
        validate_network,
        validate_odlayer,
        write_review_logs,
        write_simulation_demand as _write_simulation_demand,
    )
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from script.preprocessing.preprocessing import (
    QualityReport,
    preprocess_demand,
    sha256_file,
    validate_network,
    validate_odlayer,
    write_review_logs,
        write_simulation_demand as _write_simulation_demand,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check and prepare an MnMS dataset without modifying source files or deleting records. "
            "Provide an input directory and, if needed, custom input filenames."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input-dir", type=Path, help="Directory containing the three input files")
    parser.add_argument("--demand-file", default="demand.csv", help="Demand CSV filename inside --input-dir")
    parser.add_argument("--network-file", default="network.json", help="Network JSON filename inside --input-dir")
    parser.add_argument("--odlayer-file", default="odlayer.json", help="OD-layer JSON filename inside --input-dir")
    parser.add_argument("--demand", type=Path, help="Explicit demand CSV path (alternative to --input-dir)")
    parser.add_argument("--network", type=Path, help="Explicit network JSON path (alternative to --input-dir)")
    parser.add_argument("--odlayer", type=Path, help="Explicit OD-layer JSON path (alternative to --input-dir)")
    parser.add_argument("--output-dir", type=Path, help="Output directory; defaults to <input-dir>/PREPROCESSED")
    parser.add_argument(
        "--write-simulation-demand",
        action="store_true",
        help="Also write a stable departure-time-sorted demand copy if demand checks pass",
    )
    return parser


def _resolve_input_paths(args: argparse.Namespace) -> tuple[dict[str, Path], Path]:
    explicit = (args.demand, args.network, args.odlayer)
    if args.input_dir is not None and any(path is not None for path in explicit):
        raise SystemExit("Use either --input-dir or --demand/--network/--odlayer, not both.")
    if args.input_dir is None:
        if not all(path is not None for path in explicit):
            raise SystemExit("Provide --input-dir or all three options --demand, --network, and --odlayer.")
        paths = {name: path.expanduser().resolve() for name, path in zip(("demand", "network", "odlayer"), explicit)}
        default_output = None
    else:
        input_dir = args.input_dir.expanduser().resolve()
        paths = {
            "demand": input_dir / args.demand_file,
            "network": input_dir / args.network_file,
            "odlayer": input_dir / args.odlayer_file,
        }
        default_output = input_dir / "PREPROCESSED"

    output_dir = args.output_dir.expanduser().resolve() if args.output_dir else default_output
    if output_dir is None:
        raise SystemExit("When using explicit input paths, also provide --output-dir.")

    generated_names = (
        "demand_normalized.csv",
        "demand_qa.csv",
        "network_qa.csv",
        "odlayer_qa.csv",
        "review_log.csv",
        "review_decisions_template.csv",
        "demand_for_simulation.csv",
        "preprocessing_summary.json",
    )
    source_paths = {path.resolve() for path in paths.values()}
    collisions = [name for name in generated_names if (output_dir / name).resolve() in source_paths]
    if collisions:
        raise SystemExit(
            "The output directory would overwrite an input file ("
            + ", ".join(collisions)
            + "). Choose a different --output-dir."
        )
    return paths, output_dir


def run_preprocessing(input_paths: dict[str, Path], output_dir: Path, write_simulation_demand: bool = False) -> int:
    """Run checks, create reports, and optionally export simulation demand."""
    report = QualityReport()
    output_dir.mkdir(parents=True, exist_ok=True)
    input_metadata: dict[str, dict[str, str]] = {}
    for name, path in input_paths.items():
        if not path.is_file():
            report.add(name, "ERROR", "FILE_NOT_FOUND", f"File not found: {path}.", record_type="file")
        else:
            input_metadata[name] = {"path": str(path.resolve()), "sha256": sha256_file(path)}

    demand_result: dict[str, Any] = {"data_rows": 0, "header": [], "rows": [], "blocking_rows": 0}
    network_counts = {"nodes": 0, "sections": 0, "stops": 0, "layers": 0}
    od_counts = {"origins": 0, "destinations": 0}
    demand_path = input_paths["demand"]
    network_path = input_paths["network"]
    odlayer_path = input_paths["odlayer"]

    if demand_path.is_file():
        try:
            demand_result = preprocess_demand(demand_path, output_dir, report)
        except csv.Error as error:
            report.add("demand", "ERROR", "CSV_PARSE_ERROR", f"Malformed CSV: {error}.", record_type="file")
        except (OSError, UnicodeError) as error:
            report.add("demand", "ERROR", "READ_ERROR", f"Cannot process CSV: {error}.", record_type="file")
    if network_path.is_file():
        network_counts = validate_network(network_path, report)
    if odlayer_path.is_file():
        od_counts = validate_odlayer(odlayer_path, report)

    report.write_csv(output_dir / "demand_qa.csv", "demand")
    report.write_csv(output_dir / "network_qa.csv", "network")
    report.write_csv(output_dir / "odlayer_qa.csv", "odlayer")

    simulation_export_written = False
    if write_simulation_demand and demand_path.is_file() and (output_dir / "demand_normalized.csv").is_file():
        simulation_export_written = _write_simulation_demand(
            output_dir / "demand_for_simulation.csv", demand_result, report
        )
        report.write_csv(output_dir / "demand_qa.csv", "demand")
    write_review_logs(report, output_dir)

    output_names = [
        "demand_normalized.csv",
        "demand_qa.csv",
        "network_qa.csv",
        "odlayer_qa.csv",
        "review_log.csv",
        "review_decisions_template.csv",
        "demand_for_simulation.csv",
    ]
    output_names = [name for name in output_names if (output_dir / name).is_file()]
    output_names.append("preprocessing_summary.json")
    summary = {
        "inputs": input_metadata,
        "policy": {
            "source_files_modified": False,
            "records_automatically_deleted": 0,
            "short_trips_removed": 0,
            "duplicate_rows_removed": 0,
            "duplicate_ids_removed": 0,
            "coordinate_snapping_applied": False,
            "simulation_demand_export_written": simulation_export_written,
        },
        "counts": {
            "demand_rows": demand_result["data_rows"],
            "demand_rows_with_blocking_issues": demand_result["blocking_rows"],
            **network_counts,
            **od_counts,
            "errors": report.count("ERROR"),
            "warnings": report.count("WARNING"),
            "information": report.count("INFO"),
        },
        "outputs": output_names,
    }
    with (output_dir / "preprocessing_summary.json").open("w", encoding="utf-8") as summary_file:
        json.dump(summary, summary_file, ensure_ascii=False, indent=2)
        summary_file.write("\n")

    print(f"Preprocessing complete: {output_dir}")
    print(
        f"Demand: {demand_result['data_rows']} records retained; "
        f"{report.count('ERROR', 'demand')} error(s), {report.count('WARNING', 'demand')} warning(s)."
    )
    print(f"All inputs: {report.count('ERROR')} error(s); {report.count('WARNING')} warning(s).")
    print(f"Review files: {output_dir / 'review_log.csv'} and {output_dir / 'review_decisions_template.csv'}")
    if write_simulation_demand and not simulation_export_written:
        print("Simulation demand export not created. Review the QA reports; no records were removed.")
    return 1 if report.count("ERROR") else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_paths, output_dir = _resolve_input_paths(args)
    return run_preprocessing(input_paths, output_dir, args.write_simulation_demand)


if __name__ == "__main__":
    sys.exit(main())
