import unittest

import fluiddyn as fld
from fluiddyn.io import stdout_redirected
from fluiddyn.util import mpi

# to get fld.show
import fluiddyn.output

from fluidsim.base.solvers.base import SimulBase as Simul

from fluidsim.test import TestSimul


@unittest.skipIf(mpi.nb_proc > 1, "Od solvers do not work with mpi")
class TestBaseSolver(TestSimul):
    Simul = Simul

    def test_simul(self):
        """Should be able to run a base experiment."""
        with stdout_redirected():
            self.sim.time_stepping.start()

        fld.show()


if __name__ == "__main__":
    unittest.main()
