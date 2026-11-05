"""Print the project version, as defined in `pyproject.toml`."""

from pathlib import Path

import tomllib  # Requires python >= 3.11

pyproject_path = Path(__file__).parents[2] / "pyproject.toml"
with pyproject_path.open("rb") as f:
    data = tomllib.load(f)
    print(data["project"]["version"])
