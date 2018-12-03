"""Multidimensional spectra output (:mod:`fluidsim.solvers.ns2d.strat.output.spectra_multidim`)
===============================================================================================

.. autoclass:: SpectraMultiDimNS2DStrat
   :members:
   :private-members:

"""

import h5py
import numpy as np

from fluidsim.base.output.spectra_multidim import SpectraMultiDim


class SpectraMultiDimNS2DStrat(SpectraMultiDim):
    """Save and plot the spectra."""

    def compute(self):
        """Computes multidimensional spectra at one time."""

        # Get variables
        energyK_fft, energyA_fft = self.output.compute_energies_fft()
        energy_fft = energyK_fft + energyA_fft

        ap_fft = self.sim.state.compute("ap_fft")
        am_fft = self.sim.state.compute("am_fft")

        # Computes multidimensional spectra
        spectrumkykx_E = self.oper.compute_spectrum_kykx(energy_fft)
        spectrumkykx_EK = self.oper.compute_spectrum_kykx(energyK_fft)
        spectrumkykx_EA = self.oper.compute_spectrum_kykx(energyA_fft)

        # The function compute_spectrum_kykx does not supports complex variable...
        # Only works for the energy!

        # spectrumkykx_ap_fft = self.oper.compute_spectrum_kykx(ap_fft)
        # spectrumkykx_am_fft = self.oper.compute_spectrum_kykx(am_fft)

        # Saves dictionary
        dict_spectra = {
            "spectrumkykx_E": spectrumkykx_E,
            "spectrumkykx_EK": spectrumkykx_EK,
            "spectrumkykx_EA": spectrumkykx_EA
        }

        # dict_spectra = {
        #     "spectrumkykx_E": spectrumkykx_E,
        #     "spectrumkykx_EK": spectrumkykx_EK,
        #     "spectrumkykx_EA": spectrumkykx_EA,
        #     "spectrumkykx_ap_fft": spectrumkykx_ap_fft,
        #     "spectrumkykx_am_fft": spectrumkykx_am_fft
        # }

        return dict_spectra

    def _online_plot_saving(self, dict_spectra):
        raise NotImplementedError("_online_plot_saving in not implemented.")

    def plot(self, tmin=0, tmax=1000):
        """Plots spectrumkykx averaged between tmin and tmax."""

        dict_results = self.load_mean(tmin, tmax)
        kx = dict_results["kxE"]
        ky = dict_results["kyE"]
        spectrumkykx_E = dict_results["spectrumkykx_E"]

        fig, ax = self.output.figure_axe()
        ax.set_xlabel("$k_x$")
        ax.set_ylabel("$k_z$")

        KX, KY = np.meshgrid(kx, ky)
        ax.pcolormesh(
            KX,
            KY,
            spectrumkykx_E,
            vmin=spectrumkykx_E.min(),
            vmax=spectrumkykx_E.max(),
        )
