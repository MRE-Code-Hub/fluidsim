from pathlib import Path
from itertools import product
from copy import deepcopy

from fluiddyn.clusters.legi import Calcul8 as C

cluster = C()

path_base = Path("/fsnet/project/meige/2022/22STRATURBANIS")

cluster.commands_setting_env = [
    "source /etc/profile",
    ". $HOME/miniconda3/etc/profile.d/conda.sh",
    "conda activate env_fluidsim",
    f"export FLUIDSIM_PATH={path_base}",
]


def lprod(a, b):
    return list(product(a, b))


couples320 = (
    lprod([10, 20, 40], [5, 10, 20, 40, 80, 160])
    + lprod([30], [10, 20, 40])
    + lprod([6.5], [100, 200])
    + lprod([4], [250, 500])
    + lprod([3], [450, 900])
    + lprod([2], [1000, 2000])
    + lprod([0.66], [9000, 18000])
    + [(14.5, 20), (5.2, 150), (2.9, 475), (1.12, 3200), (0.25, 64000)]
)

couples320.remove((40, 160))

couples640 = deepcopy(couples320)
couples640.remove((10, 5))


def get_ratio_nh_nz(N):
    "Get the ratio nh/nz"
    if N == 40:
        return 8
    elif N in [20, 30]:
        return 4
    elif N <= 15:
        return 2
    else:
        raise NotImplementedError
