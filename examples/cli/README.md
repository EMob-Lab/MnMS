# Running a MnMS simulation from the CLI (Command Line Interface)

Installing MnMS provides the `mnms` command, which runs a simulation described
by a JSON configuration file:

```shell
mnms path/to/config.json
```

Run `mnms -h` for more details.


## Example

[`mnms_settings.json`](mnms_settings.json) is an example configuration file,
which simulates multimodal traffic on the Lyon63V network.
It references auxiliary data in [`examples/Lyon63V/INPUTS`](../Lyon63V/INPUTS).
To run it from the repository root:

```shell
mnms examples/cli/mnms_settings.json
```

Results and logs are written to `examples/cli/OUTPUTS`.
