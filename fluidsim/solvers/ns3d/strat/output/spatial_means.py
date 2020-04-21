"""Spatial means (:mod:`fluidsim.solvers.ns3d.strat.output.spatial_means`)
==========================================================================

.. autoclass:: SpatialMeansNS3DStrat
   :members:
   :private-members:

"""

import os
import numpy as np


from fluiddyn.util import mpi

from fluidsim.base.output.spatial_means import SpatialMeansBase


class SpatialMeansNS3DStrat(SpatialMeansBase):
    """Spatial means output."""

    def __init__(self, output):
        self.one_over_N2 = 1.0 / output.sim.params.N ** 2
        super().__init__(output)

    def _save_one_time(self):
        tsim = self.sim.time_stepping.t
        self.t_last_save = tsim
        nrj_A, nrj_Kz, nrj_Khr, nrj_Khd = self.output.compute_energies_fft()
        energyK_fft = nrj_Kz + nrj_Khr + nrj_Khd
        # shear modes
        COND_SHEAR = self.oper.Kx ** 2 + self.oper.Ky ** 2 == 0.0
        nrj_Khs = nrj_Khr * COND_SHEAR
        energyA_fft = nrj_A
        nrj_A = self.sum_wavenumbers(nrj_A)
        nrj_Kz = self.sum_wavenumbers(nrj_Kz)
        nrj_Khs = self.sum_wavenumbers(nrj_Khs)
        nrj_Khr = self.sum_wavenumbers(nrj_Khr)
        nrj_Khr = nrj_Khr - nrj_Khs
        nrj_Khd = self.sum_wavenumbers(nrj_Khd)
        energy = nrj_A + nrj_Kz + nrj_Khr + nrj_Khd + nrj_Khs

        f_d, f_d_hypo = self.sim.compute_freq_diss()
        epsK = self.sum_wavenumbers(f_d * 2 * energyK_fft)
        epsK_hypo = self.sum_wavenumbers(f_d_hypo * 2 * energyK_fft)
        epsA = self.sum_wavenumbers(f_d * 2 * energyA_fft)
        epsA_hypo = self.sum_wavenumbers(f_d_hypo * 2 * energyA_fft)

        if self.sim.params.forcing.enable:
            deltat = self.sim.time_stepping.deltat
            forcing_fft = self.sim.forcing.get_forcing()

            fx_fft = forcing_fft.get_var("vx_fft")
            fy_fft = forcing_fft.get_var("vy_fft")
            fz_fft = forcing_fft.get_var("vz_fft")
            fb_fft = forcing_fft.get_var("b_fft")

            get_var = self.sim.state.state_spect.get_var
            vx_fft = get_var("vx_fft")
            vy_fft = get_var("vy_fft")
            vz_fft = get_var("vz_fft")
            b_fft = get_var("b_fft")

            PK1_fft = np.real(
                vx_fft.conj() * fx_fft
                + vy_fft.conj() * fy_fft
                + vz_fft.conj() * fz_fft
            )
            PK2_fft = abs(fx_fft) ** 2 + abs(fy_fft) ** 2 + abs(fz_fft) ** 2

            PK1 = self.sum_wavenumbers(np.ascontiguousarray(PK1_fft))
            PK2 = self.sum_wavenumbers(PK2_fft) * deltat / 2

            PA1_fft = np.real(b_fft.conj() * fb_fft)
            PA2_fft = abs(fb_fft) ** 2

            PA1 = self.sum_wavenumbers(np.ascontiguousarray(PA1_fft))
            PA2 = self.sum_wavenumbers(PA2_fft) * deltat / 2

            PA1 *= self.one_over_N2
            PA2 *= self.one_over_N2

        if mpi.rank == 0:

            self.file.write(
                f"####\ntime = {tsim:11.5e}\n"
                f"E    = {energy:11.5e}\n"
                f"EA   = {nrj_A:11.5e} ; EKz   = {nrj_Kz:11.5e} ; "
                f"EKhr   = {nrj_Khr:11.5e} ; EKhd   = {nrj_Khd:11.5e} ; "
                f"EKhs   = {nrj_Khs:11.5e}\n"
                f"epsK = {epsK:11.5e} ; epsK_hypo = {epsK_hypo:11.5e} ; "
                f"epsA = {epsA:11.5e} ; epsA_hypo = {epsA_hypo:11.5e} ; "
                f"eps_tot = {epsK + epsK_hypo + epsA + epsA_hypo:11.5e} \n"
            )

            if self.sim.params.forcing.enable:
                self.file.write(
                    f"PK1  = {PK1:11.5e} ; PK2       = {PK2:11.5e} ; "
                    f"PK_tot   = {PK1 + PK2:11.5e} \n"
                    f"PA1  = {PA1:11.5e} ; PA2       = {PA2:11.5e} ; "
                    f"PA_tot   = {PA1 + PA2:11.5e} \n"
                )

            self.file.flush()
            os.fsync(self.file.fileno())

        if self.has_to_plot and mpi.rank == 0:

            self.axe_a.plot(tsim, energy, "k.")

            # self.axe_b.plot(tsim, epsK_tot, 'k.')
            # if self.sim.params.forcing.enable:
            #     self.axe_b.plot(tsim, PK_tot, 'm.')

            if tsim - self.t_last_show >= self.period_show:
                self.t_last_show = tsim
                fig = self.axe_a.get_figure()
                fig.canvas.draw()

    def load(self):
        dict_results = {"name_solver": self.output.name_solver}

        with open(self.path_file) as file_means:
            lines = file_means.readlines()

        lines_t = []
        lines_E = []
        lines_EA = []
        lines_PK = []
        lines_PA = []
        lines_epsK = []

        for il, line in enumerate(lines):
            if line.startswith("time ="):
                lines_t.append(line)
            if line.startswith("E    ="):
                lines_E.append(line)
            if line.startswith("EA   ="):
                lines_EA.append(line)
            if line.startswith("PK1  ="):
                lines_PK.append(line)
            if line.startswith("PA1  ="):
                lines_PA.append(line)
            if line.startswith("epsK ="):
                lines_epsK.append(line)

        nt = len(lines_t)
        if nt > 1:
            nt -= 1

        t = np.empty(nt)
        E = np.empty(nt)
        EA = np.empty(nt)
        EKz = np.empty(nt)
        EKhr = np.empty(nt)
        EKhd = np.empty(nt)
        EKhs = np.empty(nt)
        PK1 = np.zeros(nt)
        PK2 = np.zeros(nt)
        PK_tot = np.zeros(nt)
        PA1 = np.zeros(nt)
        PA2 = np.zeros(nt)
        PA_tot = np.zeros(nt)
        epsK = np.empty(nt)
        epsK_hypo = np.empty(nt)
        epsA = np.empty(nt)
        epsA_hypo = np.empty(nt)
        eps_tot = np.empty(nt)

        for il in range(nt):
            line = lines_t[il]
            words = line.split()
            t[il] = float(words[2])

            line = lines_E[il]
            words = line.split()
            E[il] = float(words[2])

            line = lines_EA[il]
            words = line.split()
            EA[il] = float(words[2])
            EKz[il] = float(words[6])
            EKhr[il] = float(words[10])
            EKhd[il] = float(words[14])
            EKhs[il] = float(words[18])

            if self.sim.params.forcing.enable:
                line = lines_PK[il]
                words = line.split()
                PK1[il] = float(words[2])
                PK2[il] = float(words[6])
                PK_tot[il] = float(words[10])

                line = lines_PA[il]
                words = line.split()
                PA1[il] = float(words[2])
                PA2[il] = float(words[6])
                PA_tot[il] = float(words[10])

            line = lines_epsK[il]
            words = line.split()
            epsK[il] = float(words[2])
            epsK_hypo[il] = float(words[6])
            epsA[il] = float(words[10])
            epsA_hypo[il] = float(words[14])
            eps_tot[il] = float(words[18])

        dict_results["t"] = t
        dict_results["E"] = E
        dict_results["EA"] = EA
        dict_results["EKz"] = EKz
        dict_results["EKhr"] = EKhr
        dict_results["EKhd"] = EKhd
        dict_results["EKhs"] = EKhs

        dict_results["PK1"] = PK1
        dict_results["PK2"] = PK2
        dict_results["PK_tot"] = PK_tot

        dict_results["PA1"] = PA1
        dict_results["PA2"] = PA2
        dict_results["PA_tot"] = PA_tot

        dict_results["epsK"] = epsK
        dict_results["epsK_hypo"] = epsK_hypo
        dict_results["epsA"] = epsA
        dict_results["epsA_hypo"] = epsA_hypo
        dict_results["eps_tot"] = eps_tot

        return dict_results

    def plot(self, plot_injection=True):
        dict_results = self.load()

        t = dict_results["t"]
        E = dict_results["E"]
        EA = dict_results["EA"]
        EKz = dict_results["EKz"]
        EKhr = dict_results["EKhr"]
        EKhd = dict_results["EKhd"]
        EKhs = dict_results["EKhs"]
        EK = EKz + EKhr + EKhd + EKhs

        epsK = dict_results["epsK"]
        epsK_hypo = dict_results["epsK_hypo"]
        epsA = dict_results["epsA"]
        epsA_hypo = dict_results["epsA_hypo"]
        eps_tot = dict_results["eps_tot"]

        # fig 1 : energies
        fig, ax = self.output.figure_axe()
        fig.suptitle("Energy")
        ax.set_ylabel("$E(t)$")
        ax.plot(t, E, "k", linewidth=2, label="$E$")
        ax.plot(t, EA, "b", label="$E_A$")
        ax.plot(t, EK, "r", label="$E_K$")
        ax.plot(t, EKhr, "r:", label="$E_{Khr}$")
        ax.plot(t, EKhs, "m:", label="$E_{Khs}$")

        ax.legend()

        # figure 2 : dissipations
        fig, ax = self.output.figure_axe()
        fig.suptitle("Dissipation of energy")
        ax.set_ylabel(r"$\epsilon_K(t)$")

        ax.plot(t, epsK, "r", linewidth=1, label=r"$\epsilon_K$", zorder=10)
        ax.plot(t, epsA, "b", linewidth=1, label=r"$\epsilon_A$", zorder=10)
        ax.plot(t, eps_tot, "k", linewidth=2, label=r"$\epsilon$", zorder=10)

        eps_hypo = epsK_hypo + epsA_hypo
        if max(eps_hypo) > 0:
            ax.plot(t, eps_hypo, "g", linewidth=1, label=r"$\epsilon_{hypo}$")

        if "PK_tot" in dict_results and plot_injection:
            PK_tot = dict_results["PK_tot"]
            PA_tot = dict_results["PA_tot"]

            ax.plot(t, PK_tot, "r--", label=r"$P_K$", zorder=0)
            ax.plot(t, PA_tot, "b--", label=r"$P_A$", zorder=0)

        ax.legend()
