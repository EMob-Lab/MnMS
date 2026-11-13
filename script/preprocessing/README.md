# MnMS dataset preprocessing

This utility checks and prepares MnMS demand, network, and origin–destination (OD) layer inputs. The command-line workflow is in `preprocess_dataset.py`; reusable parsing, validation, and report functions are in `preprocessing.py`. Run the CLI for each dataset directory; there is no dataset-specific copy of the functions to maintain. It is intended for transport and mobility researchers; detailed Python knowledge is not required, but the input files must follow the MnMS formats supported by the checks.

The process is non-destructive: source files are never edited and records are not automatically removed. It reports structural issues and provides a review log so that domain experts can assess flagged data before deciding whether a derived copy needs correction or exclusion.

## How the two Python files work together

The preprocessing is split into a command-line part and a reusable-functions part:

1. **`preprocess_dataset.py` is the entry point.** It reads the command-line options, finds the three input files in the selected dataset directory (or uses explicit file paths), chooses the output directory, and starts the run. It also prevents the selected output filenames from directly overwriting the input files.
2. **`preprocessing.py` contains the data-processing functions.** It reads and checks the demand CSV, checks network and OD-layer structure and references, writes quality reports and review files, and can write the optional simulation-demand copy.
3. **The entry point combines the results.** It writes `preprocessing_summary.json` and returns a status code: `0` when no errors were reported, or `1` when at least one error was reported. Warnings and informational findings do not by themselves change the status to an error.

The usual workflow is therefore to call the same `preprocess_dataset.py` for each dataset and provide that dataset’s directory and filenames. You do not need to copy or rewrite the functions for Lyon63V or another compatible dataset. The test suite checks the reusable functions with synthetic cases and runs the command-line entry point on Lyon63V as an integration test.

## Python environment

Python 3.10 or later is required. **A virtual environment is recommended, but not mandatory for running the preprocessing command.** The preprocessing modules use Python's standard library only. You can run them with an available Python 3.10+ interpreter, for example `python3`, provided you are at the repository root.

The commands below use `.venv/bin/python`. This path works only after a `.venv` environment has been created and set up; it is not created automatically by the preprocessing script. To create and prepare it once, follow the developer setup in [DEVELOPMENT.md](../../DEVELOPMENT.md), or run from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --group dev --editable .
```

The test command requires `pytest` and `pytest-cov`. Installing the `dev` dependency group above provides them. Without a virtual environment, you can instead install the test dependencies in the Python environment you intend to use; then run the test command with that environment's `python` executable. Avoid mixing Python interpreters between setup and test runs.

## Inputs

Place the following files in one dataset directory:

| Dataset component | Default filename | Required format |
|---|---|---|
| Travel demand | `demand.csv` | Semicolon-separated CSV with `ID`, `DEPARTURE`, `ORIGIN`, and `DESTINATION` columns |
| Mobility network | `network.json` | MnMS network JSON |
| Origin–destination layer | `odlayer.json` | MnMS OD layer JSON |

Filenames can be customized. The checks cover the MnMS structures implemented by this utility; they do not establish that values are suitable for every research question or that coordinates use the correct CRS.

## Run the preprocessing

From the repository root, provide the dataset directory. If your files use different names, set the corresponding filename options. If you have not created `.venv`, replace `.venv/bin/python` with `python3` (or the path to another Python 3.10+ interpreter):

```bash
.venv/bin/python script/preprocessing/preprocess_dataset.py \
  --input-dir /path/to/dataset \
  --demand-file trips.csv \
  --network-file mobility_network.json \
  --odlayer-file od_layer.json \
  --write-simulation-demand
```

If the files use the default names, the command can be shortened:

```bash
.venv/bin/python script/preprocessing/preprocess_dataset.py --input-dir /path/to/dataset
```

By default, outputs are written to `<dataset directory>/PREPROCESSED`. Use `--output-dir /path/to/output` to choose another location. The utility refuses an output directory that would overwrite one of the specified input files.

`--write-simulation-demand` requests an additional demand copy sorted by departure time. It is created only if the demand has no structural errors. Sorting does not remove or merge records. For all options, run the script with `--help`.

Alternatively, provide all three input file paths with `--demand`, `--network`, and `--odlayer`; this mode requires an explicit `--output-dir`.

### Example: Lyon63V

From the repository root, this command runs the preprocessing on the Lyon63V inputs and writes the results to `examples/Lyon63V/PREPROCESSED`:

```bash
.venv/bin/python script/preprocessing/preprocess_dataset.py \
  --input-dir examples/Lyon63V/INPUTS \
  --demand-file demand-Lyon63V-coords.csv \
  --network-file network-Lyon63V.json \
  --odlayer-file odlayer-Lyon63V.json \
  --output-dir examples/Lyon63V/PREPROCESSED \
  --write-simulation-demand
```

To run the preprocessing test suite, also from the repository root:

```bash
.venv/bin/python -m pytest -q --no-cov tests/preprocessing/test_preprocess_lyon63v.py
```

## Outputs

The output directory contains the following files where applicable:

- `demand_normalized.csv`: a parsed copy of the demand. Leading/trailing whitespace is trimmed from IDs and departure values, coordinate whitespace is normalized, and all parsed records are retained.
- `demand_qa.csv`, `network_qa.csv`, `odlayer_qa.csv`: input-specific quality checks.
- `review_log.csv`: unified issue log with a stable review ID, severity, code, message, record location, and conservative review guidance.
- `review_decisions_template.csv`: blank fields for recording a reviewer’s decision, proposed corrected value, reviewer and validator, and rationale.
- `preprocessing_summary.json`: input paths, SHA-256 checksums, issue counts, and produced files.
- `demand_for_simulation.csv`: optional stable time-sorted demand copy, produced only when demand checks pass.

## Reviewing flagged data

Severity levels indicate the kind of follow-up:

- `ERROR`: a structural or parsing issue. Demand errors prevent creation of the simulation demand copy.
- `WARNING`: a case to review in context, such as a repeated ID or an unusual network value.
- `INFO`: notable information that is not treated as an error, such as identical origin and destination coordinates.

These levels describe the checks implemented by the utility, not a complete judgement of data validity. A short trip, repeated OD pair, repeated ID, identical origin and destination, or zero-length connector may be legitimate. Such records are retained; the log supports review rather than automatic filtering.

`review_decisions_template.csv` is a record-keeping aid. The suggested decision values are `KEEP`, `CORRECT_IN_DERIVED_COPY`, and `EXCLUDE_FROM_DERIVED_COPY`. The utility does **not** read or apply those decisions. Any correction or exclusion should be validated by the research team, applied only to a separate derived dataset, and documented with its rationale. Keep the original data unchanged for reproducibility.

## Scope and limitations

- The utility checks selected structural properties of MnMS demand, network, and OD files; it does not validate every schema variant or every domain-specific constraint.
- It does not confirm the coordinate reference system (CRS), units, map-matching quality, or whether demand values represent observed travel behavior.
- Network and OD-layer issues are reported separately. The optional simulation demand copy is currently gated by demand errors only; inspect all three QA reports before running a simulation.
- The current tests cover Lyon63V and synthetic edge cases. A new dataset should be reviewed against its source documentation and independently validated before research use.

See [REMAINING_TESTS.md](../../tests/preprocessing/REMAINING_TESTS.md) for additional validation tasks and known limitations.
