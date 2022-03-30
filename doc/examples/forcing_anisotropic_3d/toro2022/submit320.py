from pathlib import Path
from time import sleep
from itertools import product

from fluiddyn.clusters.legi import Calcul8 as C
from fluiddyn.clusters.oar import get_job_id
from fluidsim.util import (
    times_start_last_from_path,
    get_last_estimated_remaining_duration,
)

cluster = C()

path_base = Path("/fsnet/project/meige/2022/22STRATURBANIS")

cluster.commands_setting_env = [
    "source /etc/profile",
    ". $HOME/miniconda3/etc/profile.d/conda.sh",
    "conda activate env_fluidsim",
    f"export FLUIDSIM_PATH={path_base}",
]

nh = 320
t_end = 20.0

paths = sorted(path_base.glob(f"aniso/ns3d.strat*_{nh}x{nh}*"))

walltime = "04:00:00"


def get_ratio_nh_nz(N):
    "Get the ratio nh/nz"
    if N == 40:
        return 8
    elif N in [20, 30]:
        return 4
    elif N <= 10:
        return 2
    else:
        raise NotImplementedError


def lprod(a, b):
    return list(product(a, b))


couples = (
    lprod([10, 20, 40], [5, 10, 20, 40, 80, 160])
    + lprod([30], [10, 20, 40])
    + lprod([6.5], [100, 200])
    + lprod([4], [250, 500])
    + lprod([3], [450, 900])
    + lprod([2], [1000, 2000])
    + lprod([0.66], [9000, 18000])
)
couples.remove((40, 160))

for N, Rb in couples:

    ratio_nh_nz = get_ratio_nh_nz(N)
    nz = nh // ratio_nh_nz

    name_1st_run = f"run_simul_toro_nx{nh}_Rb{Rb}_N{N}"
    job_id = get_job_id(name_1st_run)
    try:
        path = [
            p for p in paths if f"_Rb{Rb:.3g}_" in p.name and f"_N{N}_" in p.name
        ][0]
    except IndexError:
        if job_id is None:
            command = f"./run_simul_toro.py -R {Rb} -N {N} --ratio-nh-nz {ratio_nh_nz} -nz {nz} --t_end {t_end}"

            cluster.submit_command(
                command,
                name_run=name_1st_run,
                nb_nodes=1,
                walltime=walltime,
                nb_mpi_processes=10,
                omp_num_threads=1,
                delay_signal_walltime=300,
                ask=False,
            )

            while job_id is None:
                job_id = get_job_id(name_1st_run)
                sleep(1)
        else:
            print(
                f"Nothing to do for nx{nh}_Rb{Rb}_N{N} because first job is "
                "already launched and the simulation directory is not created"
            )
            continue

    else:

        t_start, t_last = times_start_last_from_path(path)
        if t_last > t_end:
            print(f"Nothing to do for {path.name} because t_last > t_end")
            continue

        try:
            estimated_remaining_duration = get_last_estimated_remaining_duration(
                path
            )
        except RuntimeError:
            estimated_remaining_duration = "?"

        print(f"{path.name}: {t_last = }, {estimated_remaining_duration = }")

        command = f"fluidsim-restart {path}"
        name_run = command.split()[0] + f"_nx{nh}_Rb{Rb}_N{N}"

        if get_job_id(name_run) is not None:
            print(f"Nothing to do because the idempotent job is already launched")
            continue

        cluster.submit_command(
            command,
            name_run=name_run,
            nb_nodes=1,
            walltime=walltime,
            nb_mpi_processes=10,
            omp_num_threads=1,
            delay_signal_walltime=300,
            ask=False,
            idempotent=True,
            anterior=job_id,
        )
