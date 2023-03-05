"""Simulations with the solver ns3d.strat and the forcing tcrandom_anisotropic.

.. autofunction:: create_parser

.. autofunction:: main

"""

from math import pi, asin, sin
import argparse
import sys

import matplotlib.pyplot as plt

from fluiddyn.util import mpi
from fluidsim.util.scripts import parse_args

doc = """Launcher for simulations with the solver ns3d and
the forcing tcrandom_anisotropic.

Examples
--------

```
./run_simul.py --only-print-params
./run_simul.py --only-print-params-as-code

./run_simul.py -F 0.3 --delta-F 0.1 --ratio-kfmin-kf 0.8 --ratio-kfmax-kf 1.5 -opf
./run_simul.py -F 1.0 --delta-F 0.1 --ratio-kfmin-kf 0.8 --ratio-kfmax-kf 1.5 -opf

mpirun -np 2 ./run_simul.py
```

Notes
-----

This script is designed to study rotating turbulence forced with an
anisotropic forcing in toroidal or poloidal modes.

The regime depends on the value of the Rossby number Ro and Reynolds numbers Re and R4:

- Ro = U / (f L)
- Re = U L / nu
- Re4 = U L^3 / nu4

Ro has to be very small to be in a strong rotation regime. Re and Re4 has to
be "large" to be in a turbulent regime.

For this forcing, we fix the injection rate P (equal to epsK). We will
work at P = 1.0.

Note that U is not directly fixed by the forcing but should be a function of
the other input parameters. Dimensionally, we can write U = (P L)**(1/3).

The flow is forced at large spatial scales (compared to the size of the numerical domain). 

"""

keys_versus_kind = {
    "toro": "vt_fft",
    "polo": "vp_fft",
    "vert": "vz_fft",
}


def create_parser():
    """Create the argument parser with default arguments"""
    parser = argparse.ArgumentParser(
        description=doc, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # parameters to study the input parameters without running the simulation

    parser.add_argument(
        "-oppac",
        "--only-print-params-as-code",
        action="store_true",
        help="Only run initialization phase and print params as code",
    )

    parser.add_argument(
        "-opp",
        "--only-print-params",
        action="store_true",
        help="Only run initialization phase and print params",
    )

    parser.add_argument(
        "-opf",
        "--only-plot-forcing",
        action="store_true",
        help="Only run initialization phase and plot forcing",
    )

    # grid parameter

    parser.add_argument(
        "-n",
        "--n",
        type=int,
        default=32,
        help="Number of numerical points over one axis",
    )

    # physical parameters

    parser.add_argument("--t_end", type=float, default=10.0, help="End time")

    parser.add_argument(
        "-f", type=float, default=None, help="Coriolis parameter 2xOmega (frequency)"
    )
    
    parser.add_argument("-nu", type=float, default=None, help="Viscosity")
    
    parser.add_argument(
        "--Ro",
        type=float,
        default=0.1,
        help="Rossby number",
    )
    
    parser.add_argument(
        "--Re",
        type=float,
        default=100,
        help="Reynolds number",
    )
    
    parser.add_argument(
        "--Re4",
        type=float,
        default=0.0,
        help="order-4 hyper viscosity Reynolds number",
    )
    
    parser.add_argument(
        "--coef-nu4",
        type=float,
        default=None,
        help="Coefficient used to compute the order-4 hyper viscosity",
    )

    parser.add_argument(
        "--forced-field",
        type=str,
        default="polo",
        help='Forced field (can be "polo", "toro", or "vert")',
    )

    parser.add_argument(
        "--init-velo-max",
        type=float,
        default=0.01,
        help="params.init_fields.noise.max",
    )

    # shape of the forcing region in spectral space

    parser.add_argument(
        "--nmin-forcing",
        type=int,
        default=3,
        help="Minimal dimensionless wavenumber forced",
    )

    parser.add_argument(
        "--nmax-forcing",
        type=int,
        default=5,
        help="Maximal dimensionless wavenumber forced",
    )

    parser.add_argument(
        "-F",
        type=float,
        default=0.95,
        help="Ratio omega_f / f, fixing the mean angle between the vertical and the forced wavenumber",
    )

    parser.add_argument(
        "--delta-F",
        type=float,
        default=0.1,
        help="delta F, fixing angle_max - angle_min",
    )

    # Output parameters

    parser.add_argument(
        "--spatiotemporal-spectra",
        action="store_true",
        help="Activate the output spatiotemporal_spectra",
    )

    # Other parameters

    parser.add_argument(
        "--no-vz-kz0",
        type=bool,
        default=False,
        help="params.no_vz_kz0",
    )

    parser.add_argument(
        "--NO_SHEAR_MODES",
        type=bool,
        default=False,
        help="params.oper.NO_SHEAR_MODES",
    )

    parser.add_argument(
        "--max-elapsed",
        type=str,
        default="23:50:00",
        help="Max elapsed time",
    )

    parser.add_argument(
        "--periods_save-phys_fields",
        type=float,
        default=1.0,
        help="params.output.periods_save.phys_fields",
    )

    parser.add_argument(
        "--sub-directory",
        type=str,
        default="aniso_rotation",
        help="Sub directory where the simulation will be saved",
    )

    parser.add_argument(
        "--modify-params",
        type=str,
        default=None,
        help="Code modifying the `params` object.",
    )

    return parser


def create_params(args):
    """Create the params object from the script arguments"""

    from fluidsim.solvers.ns3d.solver import Simul

    params = Simul.create_default_params()

    params.output.sub_directory = args.sub_directory
    params.short_name_type_run = args.forced_field

    if args.projection is not None:
        params.projection = args.projection
        params.short_name_type_run += "_proj"

    params.no_vz_kz0 = args.no_vz_kz0
    params.oper.NO_SHEAR_MODES = args.NO_SHEAR_MODES
    params.oper.coef_dealiasing = 2./3.

    params.oper.truncation_shape = "no_multiple_aliases"

    params.oper.nx = params.oper.ny = params.oper.nz = n = args.n
    params.oper.Lx = params.oper.Ly = params.oper.Lz = L = 2*pi
    params.oper.Lz = Lh / args.ratio_nh_nz
    
    delta_k = 2 * pi / L
    injection_rate = 1.0
    U = (injection_rate * L) ** (1 / 3)

    
    # Coriolis parameter f and Rossby number
    if args.f is not None and args.Ro is not None:
        raise ValueError("args.f is not None and args.Ro is not None")
    if args.f is not None:
        f = args.f
        mpi.printby0(f"Input Coriolis parameter: {f:.3e}")
        if f != 0.0:
            Ro = U / (f * L)
            params.short_name_type_run += f"_Ro{Ro:.3e}"
        else:
            params.short_name_type_run += f"_f{f:.3e}"
    elif args.Ro is not None:
        Ro = args.Ro
        mpi.printby0(f"Input Rossby number: {Ro:.3g}")
        if Ro != 0.0:
            f = U / (Ro * L)
            params.short_name_type_run += f"_Ro{Ro:.3e}"
        else:
            raise ValueError("Ro = 0.0")
    else:
        raise ValueError("args.f is None and args.Ro is None")
   
   
    # Viscosity and Reynolds number
    if args.nu is not None and args.Re is not None:
        raise ValueError("args.nu is not None and args.Re is not None")
    if args.nu is not None:
        nu = args.nu
        mpi.printby0(f"Input viscosity: {nu:.3e}")
        if nu != 0.0:
            Re = U * L / nu
            params.short_name_type_run += f"_Re{Re:.3e}"
        else:
            params.short_name_type_run += f"_nu{nu:.3e}"
    elif args.Re is not None:
        Re = args.Re
        mpi.printby0(f"Input Reynolds number: {Re:.3g}")
        if Re != 0.0:
            nu = U * L / Re
            params.short_name_type_run += f"_Re{Re:.3e}"
        else:
            raise ValueError("Re = 0.0")
    else:
        raise ValueError("args.nu is None and args.Re is None")
        
        
    # Viscosity and Reynolds number
    if args.nu is not None and args.Re is not None:
        raise ValueError("args.nu is not None and args.Re is not None")
    if args.nu is not None:
        nu = args.nu
        mpi.printby0(f"Input viscosity: {nu:.3e}")
        if nu != 0.0:
            Re = U * L / nu
            params.short_name_type_run += f"_Re{Re:.3e}"
        else:
            params.short_name_type_run += f"_nu{nu:.3e}"
    elif args.Re is not None:
        Re = args.Re
        mpi.printby0(f"Input Reynolds number: {Re:.3g}")
        if Re != 0.0:
            nu = U * L / Re
            params.short_name_type_run += f"_Re{Re:.3e}"
        else:
            raise ValueError("Re = 0.0")
    else:
        raise ValueError("args.nu is None and args.Re is None") 
        
        
    # order-4 hyper viscosity and associated Reynolds number
    if args.coef-nu4 is not None and args.Re4 is not None:
        raise ValueError("args.coef-nu4 is not None and args.Re4 is not None")
    if args.nu4 is not None:
        nu4 = args.nu4
        mpi.printby0(f"Input order-4 hyper viscosity: {params.nu_4:.3e}")
        if nu4 != 0.0:
            Re4 = U * L**3 / nu4
            params.short_name_type_run += f"_Re4{Re4:.3e}"
    elif args.coef-nu4 is not None:
        coef-nu4 = args.coef-nu4
        k_max = params.oper.coef_dealiasing * delta_kz * nz / 2
        mpi.printby0(f"Input coef-nu4: {coef-nu4:.3g}")
        if coef-nu4 != 0.0:
            # only valid if R4 >> 1 (isotropic turbulence at small scales)
            params.nu_4 = (
                coef-nu4 * injection_rate ** (1 / 3) / k_max ** (10 / 3)
            )
            Re4 = U * L**3 / params.nu_4
            params.short_name_type_run += f"_Re4{Re4:.3e}"
        else:
            params.nu_4 = 0.0
    else:
        raise ValueError("args.nu is None and args.Re is None") 
    
     

    params.init_fields.type = "noise"
    params.init_fields.noise.length = L / 2
    params.init_fields.noise.velo_max = args.init_velo_max

    params.forcing.enable = True
    params.forcing.type = "tcrandom_anisotropic"
    params.forcing.forcing_rate = injection_rate
    params.forcing.key_forced = keys_versus_kind[args.forced_field]


    kf_min = delta_k * nkmin_forcing
    kf_max = delta_k * nkmax_forcing
    angle = asin(args.F)
    delta_angle = asin(args.delta_F)
    
    
    mpi.printby0(
        f"{params.forcing.nkmin_forcing = }\n{params.forcing.nkmax_forcing = }"
    )
    mpi.printby0(f"angle = {angle / pi * 180:.2f}°")
    
    
    period_f = 2 * pi / args.f
    omega_f = args.f * args.F

    # time_stepping fixed to follow waves
    params.time_stepping.USE_T_END = True
    params.time_stepping.t_end = args.t_end
    params.time_stepping.max_elapsed = args.max_elapsed
    params.time_stepping.deltat_max = min(0.1, period_f / 16)

    # time_correlation is fixed to forced wave period
    params.forcing.tcrandom.time_correlation = 2 * pi / omega_f
    params.forcing.tcrandom_anisotropic.angle = round3(angle)
    params.forcing.tcrandom_anisotropic.delta_angle = round3(delta_angle)
    params.forcing.tcrandom_anisotropic.kz_negative_enable = True

    params.output.periods_print.print_stdout = 1e-1

    params.output.periods_save.phys_fields = args.periods_save_phys_fields
    params.output.periods_save.spatial_means = 0.02
    params.output.periods_save.spectra = 0.05
    params.output.periods_save.spect_energy_budg = 0.1

    params.output.spectra.kzkh_periodicity = 1

    if args.spatiotemporal_spectra:
        params.output.periods_save.spatiotemporal_spectra = period_f / 8

    params.output.spatiotemporal_spectra.file_max_size = 80.0  # (Mo)
    # probes_region in nondimensional units (mode indices).
    ikmax = 30
    params.output.spatiotemporal_spectra.probes_region = (ikmax, ikmax, ikmax)

    if args.modify_params is not None:
        exec(args.modify_params)

    return params


def main(args=None, **defaults):
    """Main function for the scripts based on turb_trandom_anisotropic"""
    parser = create_parser()

    if defaults:
        parser.set_defaults(**defaults)

    args = parse_args(parser, args)

    params = create_params(args)

    if (
        args.only_plot_forcing
        or args.only_print_params_as_code
        or args.only_print_params
    ):
        params.output.HAS_TO_SAVE = False

    sim = None

    if args.only_print_params_as_code:
        params._print_as_code()
        return params, sim

    if args.only_print_params:
        print(params)
        return params, sim

    from fluidsim.solvers.ns3d.strat.solver import Simul

    sim = Simul(params)

    if args.only_plot_forcing:
        sim.forcing.forcing_maker.plot_forcing_region()

        plt.show()
        return params, sim

    sim.time_stepping.start()

    mpi.printby0(
        f"""
# To visualize the output with Paraview, create a file states_phys.xmf with:

fluidsim-create-xml-description {sim.output.path_run}

# To visualize with fluidsim:

cd {sim.output.path_run}; fluidsim-ipy-load

# in IPython:

sim.output.phys_fields.set_equation_crosssection('x={params.oper.Lx/2}')
sim.output.phys_fields.animate('b')
"""
    )

    return params, sim


if "sphinx" in sys.modules:
    from textwrap import indent
    from unittest.mock import patch

    with patch.object(sys, "argv", ["run_simul.py"]):
        parser = create_parser()

    __doc__ += """
Example of help message
-----------------------

.. code-block::

""" + indent(
        parser.format_help(), "    "
    )


if __name__ == "__main__":

    params, sim = main()
