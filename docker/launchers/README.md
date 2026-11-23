# MnMS-Docker

MnMS-Docker is a way of running MnMS simulations through a Docker image,
so that MnMS can be used without installing Python or MnMS itself:
only [Docker](https://docs.docker.com/get-started/get-docker/) is needed.

MnMS-Docker is used through a launcher script, available for each platform:

| File              | Platform     |
|-------------------|--------------|
| `mnms-docker`     | Linux, MacOS |
| `mnms-docker.cmd` | Windows      |

Both launchers do the same thing:

1. check that Docker is available and running,
2. download the latest version of the MnMS-Docker image if it is not available locally or is outdated,
3. make the current (host) directory from which the launcher is executed visible from inside the image,
4. run the image.


## Installation

Download the launcher for your platform:

- Linux/MacOS: https://raw.githubusercontent.com/EMob-Lab/MnMS/refs/heads/main/docker/launchers/mnms-docker
- Windows: https://raw.githubusercontent.com/EMob-Lab/MnMS/refs/heads/main/docker/launchers/mnms-docker.cmd

On Linux/MacOS, make the launcher executable:

```shell
chmod +x mnms-docker
```

Optionally, put the launcher in a directory listed in your `PATH`, so that it can be called from anywhere.


## Usage

From the directory containing the simulation files:

```shell
mnms-docker <settings>.json          # Run a MnMS simulation configured through a JSON file
mnms-docker <script>.py [args...]    # Run a MnMS simulation defined by a custom Python script
```

On Windows, call `mnms-docker.cmd` the same way. If the launcher is not in your `PATH`,
call it with its path (e.g. `/path/to/mnms-docker` or `C:\path\to\mnms-docker.cmd`).

All files used by the simulation (the JSON settings file or Python script, and any file they reference)
must be located in the current directory or one of its subdirectories, and referenced by relative paths.
Paths written inside the JSON settings file or Python script must use `/` as path separator,
including on Windows.
