"""Restart a fluidsim simulation (:mod:`fluidsim.util.scripts.restart`)

.. autoclass:: RestarterABC
   :members:
   :private-members:
   :undoc-members:

"""

from abc import ABCMeta, abstractmethod
import argparse
import sys
from pathlib import Path
from time import sleep
from textwrap import dedent

# import potentially needed for the exec
from math import pi

from fluiddyn.util import mpi

from fluidsim_core.scripts import parse_args


class RestarterABC(metaclass=ABCMeta):
    def create_parser(self):
        """Create the argument parser with default arguments"""
        parser = argparse.ArgumentParser(
            description="Restart a fluidsim simulation",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        parser.add_argument(
            "path",
            type=str,
            help="Path of the directory or file from which to restart",
        )
        parser.add_argument(
            "--t_approx",
            type=float,
            default=None,
            help="Approximate time to choose the file from which to restart",
        )

        parser.add_argument(
            "--merge-missing-params",
            action="store_true",
            help=(
                "Can be used to load old simulations carried out with "
                "an old fluidsim version."
            ),
        )

        parser.add_argument(
            "-oc",
            "--only-check",
            action="store_true",
            help="Only check what should be done",
        )

        parser.add_argument(
            "-oi",
            "--only-init",
            action="store_true",
            help="Only run initialization phase",
        )

        parser.add_argument(
            "--new-dir-results",
            action="store_true",
            help="Create a new directory for the new simulation",
        )

        parser.add_argument(
            "--add-to-t_end",
            type=float,
            default=None,
            help="Time added to params.time_stepping.t_end",
        )
        parser.add_argument(
            "--add-to-it_end",
            type=int,
            default=None,
            help="Number of steps added to params.time_stepping.it_end",
        )

        parser.add_argument(
            "--t_end",
            type=float,
            default=None,
            help="params.time_stepping.t_end",
        )
        parser.add_argument(
            "--it_end",
            type=int,
            default=None,
            help="params.time_stepping.it_end",
        )

        parser.add_argument(
            "--modify-params",
            type=str,
            default=None,
            help="Code modifying the `params` object.",
        )

        parser.add_argument(
            "--max-elapsed",
            type=str,
            default=None,
            help="Maximum elapsed time.",
        )

        return parser

    def restart(self, args=None, **defaults):
        """Restart a simulation"""
        parser = self.create_parser()

        if defaults:
            parser.set_defaults(**defaults)

        args = parse_args(parser, args)

        params, Simul = self._get_params_simul_class(args)

        params.NEW_DIR_RESULTS = args.new_dir_results

        if args.add_to_t_end is not None:
            params.time_stepping.t_end += args.add_to_t_end

        if args.add_to_it_end is not None:
            params.time_stepping.it_end += args.add_to_it_end

        if args.t_end is not None:
            params.time_stepping.t_end = args.t_end

        if args.it_end is not None:
            params.time_stepping.it_end += args.it_end

        if args.only_check or args.only_init:
            params.output.HAS_TO_SAVE = False

        if args.max_elapsed is not None:
            params.time_stepping.max_elapsed = args.max_elapsed

        path_file = Path(params.init_fields.from_file.path)
        mpi.printby0(path_file)

        if args.modify_params is not None:
            exec(args.modify_params)

        if args.only_check:
            mpi.printby0(params)
            return params, None

        try:
            self._check_params_time_stepping(params, path_file, args)
        except ValueError:
            return params, None

        sim = Simul(params)

        if args.only_init:
            return params, sim

        self._start_sim(sim, args)

        mpi.printby0(self._str_command_after_simul.format(path_run=sim.output.path_run))

        return params, sim

    _str_command_after_simul = dedent("""
        # To visualize with IPython:

        cd {path_run}
        ipython --matplotlib -i -c "from fluidsim import load; sim = load()"
    """)

    @abstractmethod
    def _get_params_simul_class(self, args):
        "Create params object and Simul class"

    @abstractmethod
    def _start_sim(self, sim, args):
        "Start the new simulation"

    @abstractmethod
    def _check_params_time_stepping(self, params, path_file, args):
        "Check time stepping parameters"

    def main(self):
        """Entry point fluidsim-restart"""
        params, sim = self.restart()

        if sim is not None and sim.time_stepping._has_to_stop:

            if mpi.rank == 0:
                # processes with rank 0 exits early with exit code 99 or 0
                exit_code = 99
                if (
                    Path(sim.output.path_run) / "IDEMPOTENT_NO_RELAUNCH"
                ).exists():
                    exit_code = 0
                print("Simulation is not completed and could be relaunched")

            if mpi.nb_proc > 1:
                mpi.comm.barrier()

            if mpi.rank == 0:
                sys.exit(exit_code)

            sleep(0.5)
            sys.exit()
