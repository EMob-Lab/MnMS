"""
This example illustrates how to run a MnMS simulation in step-by-step mode.

This mode allows more flexibility regarding simulation loop control:
the stop condition can be customized, additional operations can be performed
at each iteration step, etc.
"""

import argparse
from pathlib import Path

from runLyon6 import Lyon6Parameters, create_supervisor

from mnms.simulation import Supervisor
from mnms.time import Dt, Time


def run_simulation(parameters: Lyon6Parameters) -> None:

    supervisor_params = parameters.supervisor
    start_time = Time(supervisor_params["start_time"])
    end_time = Time(supervisor_params["end_time"])
    flow_dt = Dt(minutes=supervisor_params["flow_dt"])
    affectation_factor = supervisor_params["affectation_factor"]

    # Initialization.
    supervisor: Supervisor = create_supervisor(parameters)
    supervisor.initialize(start_time, flow_dt)
    try:

        # Simulation loop.
        while supervisor.tcurrent < end_time:
            print(f'Running affectation step {supervisor.affectation_step}...')
            supervisor.run_one_affectation_step(affectation_factor)
        print('Done')

    # Close the files and release the resources
    finally:
        supervisor.finalize()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Lyon6 simulation (in step-by-step mode).")
    parser.add_argument(
        "config_file",
        nargs="?",
        type=Path,
        default=Path(__file__).with_name("param.json"),
        help="path to the JSON parameter file (defaults to param.json)",
    )
    arguments = parser.parse_args()
    run_simulation(Lyon6Parameters(arguments.config_file))
