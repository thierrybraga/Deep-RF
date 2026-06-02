import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import numpy as np
from iloveantennas.simulator.solver import FDTDSolver, FieldProbe, GaussianSource

from iloveantennas.simulator.core.constants import C0
from iloveantennas.simulator.core.geometry import AntennaFactory
from iloveantennas.simulator.core.grid import FDTDGrid, GridConfig, create_grid_for_antenna
from iloveantennas.simulator.visualization.smith_chart import (
    ImpedanceResult,
    calculate_impedance_from_fdtd,
)


@dataclass
class OptimizationResult:
    success: bool
    iterations: int
    final_length: float
    final_vswr: float
    final_resonance: float
    history: List[dict]
    message: str


class AntennaOptimizer:
    def __init__(self):
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def optimize_length(
        self,
        antenna_type: str,
        target_freq: float,
        start_length: float = None,
        radius: float = 0.001,
        target_vswr: float = 1.5,
        max_iter: int = 5,
        callback: Callable = None,
    ) -> OptimizationResult:

        current_length = start_length
        if current_length is None or current_length <= 0:
            # Initial guess based on type
            wavelength = C0 / target_freq
            if antenna_type == "dipole":
                current_length = 0.48 * wavelength
            elif antenna_type == "monopole":
                current_length = 0.24 * wavelength
            else:
                current_length = 0.5 * wavelength

        history = []
        best_vswr = float("inf")
        best_length = current_length

        for i in range(max_iter):
            if self._stop_requested:
                break

            if callback:
                callback(
                    {
                        "status": "running",
                        "progress": int((i / max_iter) * 100),
                        "message": f"Iteração {i+1}/{max_iter}: Simulando L={(current_length*100):.2f}cm...",
                    }
                )

            try:
                # Run fast simulation
                result = self._run_simulation(antenna_type, current_length, radius, target_freq)

                # Find resonance and VSWR at target
                res_data = result.find_resonance(
                    freq_min=target_freq * 0.5, freq_max=target_freq * 1.5
                )
                f_res = res_data["frequency"]

                match_data = result.get_at_frequency(target_freq)
                vswr_at_target = match_data["vswr"]

                history.append(
                    {
                        "iteration": i + 1,
                        "length": current_length,
                        "f_res": f_res,
                        "vswr": vswr_at_target,
                    }
                )

                if vswr_at_target < best_vswr:
                    best_vswr = vswr_at_target
                    best_length = current_length

                if callback:
                    callback(
                        {
                            "status": "running",
                            "progress": int((i + 0.8) / max_iter * 100),
                            "message": f"Iteração {i+1}: VSWR={vswr_at_target:.2f} @ {target_freq/1e6:.1f}MHz",
                        }
                    )

                # Check convergence
                if vswr_at_target <= target_vswr:
                    return OptimizationResult(
                        success=True,
                        iterations=i + 1,
                        final_length=current_length,
                        final_vswr=vswr_at_target,
                        final_resonance=f_res,
                        history=history,
                        message="Alvo de VSWR atingido!",
                    )

                # Update length using scaling
                # L_new = L_old * (f_res / f_target)
                if f_res > 0:
                    ratio = f_res / target_freq
                    # Limit changes to avoid instability (max 20% change per step)
                    ratio = max(0.8, min(1.2, ratio))
                    new_length = current_length * ratio
                else:
                    # Fallback if resonance not found
                    new_length = current_length * 0.95

                # Stop if change is negligible (< 0.5%)
                if abs(new_length - current_length) < current_length * 0.005:
                    return OptimizationResult(
                        success=best_vswr < 3.0,  # Consider success if "decent"
                        iterations=i + 1,
                        final_length=current_length,
                        final_vswr=vswr_at_target,
                        final_resonance=f_res,
                        history=history,
                        message="Convergência alcançada (mudança mínima).",
                    )

                current_length = new_length

            except Exception as e:
                print(f"Erro na otimização: {e}")
                return OptimizationResult(False, i + 1, current_length, 0, 0, history, str(e))

        return OptimizationResult(
            success=False,
            iterations=max_iter,
            final_length=best_length,
            final_vswr=best_vswr,
            final_resonance=0,  # Unknown
            history=history,
            message="Número máximo de iterações atingido.",
        )

    def _run_simulation(
        self, type: str, length: float, radius: float, freq: float
    ) -> ImpedanceResult:
        # Create minimal simulation
        if type == "dipole":
            antenna = AntennaFactory.create_dipole(length=length, radius=radius)
        elif type == "monopole":
            antenna = AntennaFactory.create_monopole(length=length, radius=radius)
        else:
            antenna = AntennaFactory.create_dipole(length=length, radius=radius)

        # Create Grid
        # Use lower resolution for speed (10 cells/lambda is bare minimum for FDTD, but maybe ok for resonance check)
        wavelength = C0 / freq
        grid = create_grid_for_antenna(
            antenna, freq_max=freq, cells_per_wavelength=15, pml_layers=6
        )

        solver = FDTDSolver(grid, use_numba=True)  # Force numba if possible

        # Source (Broadband Gaussian)
        center = (grid.nx // 2, grid.ny // 2, grid.nz // 2)
        # tau ~ 0.5/f ensures bandwidth covers f
        source = GaussianSource(
            position=center, component="Ez", amplitude=1.0, tau=1.0 / (2 * freq)
        )
        solver.add_source(source)

        probe = FieldProbe(position=center, component="Ez")
        solver.add_probe(probe)

        # Run
        # We need enough time for resonance to settle.
        # Q factor determines decay.
        # 400 steps is usually enough for simple dipoles at coarse grid
        num_steps = 400

        for _ in range(num_steps):
            solver.step()

        # Calc Impedance
        # Frequencies around target
        freqs = np.linspace(freq * 0.5, freq * 1.5, 100)
        return calculate_impedance_from_fdtd(solver, freqs)
