import os

from mnms.log import LOGLEVEL, attach_log_file, get_logger, set_all_mnms_logger_level
from mnms.simulation import load_snaphshot
from mnms.time import Dt, Time

if __name__ == '__main__':

    outdir = "OUTPUTS"

    # Outputs
    outdir_path = os.getcwd() + '/' + outdir
    if not os.path.isdir(outdir_path):
        os.mkdir(outdir_path)

    set_all_mnms_logger_level(LOGLEVEL.INFO)
    get_logger("mnms.graph.shortest_path").setLevel(LOGLEVEL.WARNING)
    attach_log_file(outdir_path + '/simulation.log')

    supervisor = load_snaphshot(outdir_path+'/snapshot')

    supervisor.run(Time('08:30:00'), Time('08:45:00'), Dt(seconds=1), 10)
