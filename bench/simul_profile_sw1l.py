#!/usr/bin/env python
"""
python simul_profile.py
mpirun -np 8 python simul_profile_sw1l.py

FLUIDSIM_PRIORITY_FLUIDFFT=1 mpirun -np 2 python simul_profile_sw1l.py

with gprof2dot and graphviz (command dot):

gprof2dot -f pstats profile.pstats | dot -Tpng -o profile.png



"""

import os

from fluidsim.solvers.sw1l import solver

params = solver.Simul.create_default_params()

params.short_name_type_run = 'profile'

nh = 512
params.oper.nx = nh
params.oper.ny = nh
Lh = 6.
params.oper.Lx = Lh
params.oper.Ly = Lh

if 'FLUIDSIM_PRIORITY_FLUIDFFT' in os.environ:
    # params.oper.type_fft = 'fft2d.mpi_with_fftwmpi2d'
    pass

params.oper.coef_dealiasing = 2./3

params.FORCING = True
params.forcing.type = 'tcrandom'
params.forcing.nkmax_forcing = 5
params.forcing.nkmin_forcing = 4
params.forcing.forcing_rate = 1.

delta_x = Lh/nh
params.nu_8 = 2.*10e-1*params.forcing.forcing_rate**(1./3)*delta_x**8

params.f = 1.
params.c2 = 200.

params.time_stepping.deltat0 = 1.e-4
params.time_stepping.USE_CFL = False

params.time_stepping.it_end = 10
params.time_stepping.USE_T_END = False


params.output.periods_print.print_stdout = 0

params.output.HAS_TO_SAVE = 0
# params.output.periods_save.phys_fields = 0.1
# params.output.periods_save.spatial_means = 0.1
# params.output.periods_save.spectra = 0.1
# params.output.periods_save.spect_energy_budg = 0.1
# params.output.periods_save.increments = 0.1


sim = solver.Simul(params)

if __name__ == '__main__':
    from time import time
    import pstats
    import cProfile

    t0 = time()

    cProfile.runctx('sim.time_stepping.start()',
                    globals(), locals(), 'profile.pstats')

    if sim.oper.rank == 0:
        print('t1 - t0 =', time() - t0, '\n')
        s = pstats.Stats('profile.pstats')
        s.strip_dirs().sort_stats('time').print_stats(16)
        print(
            'with gprof2dot and graphviz (command dot):\n'
            'gprof2dot -f pstats profile.pstats | dot -Tpng -o profile.png')
