import numpy as np

from iloveantennas.simulator.core.grid import FDTDGrid, GridConfig
from iloveantennas.simulator.solver import FDTDSolver
from iloveantennas.simulator.solver.sources import GaussianSource


def _small_grid():
    grid = FDTDGrid(GridConfig(dx=0.05, nx=6, ny=6, nz=6, pml_layers=1))
    grid.calculate_coefficients()
    return grid


def test_fdtd_numpy_backend_runs_one_step():
    grid = _small_grid()
    solver = FDTDSolver(grid, use_numba=False, backend="numpy")
    solver.add_source(GaussianSource(position=(3, 3, 3), component="Ez", amplitude=1.0))

    solver.step()

    assert solver.backend_name == "numpy-cpu"
    assert np.isfinite(grid.Ez).all()
    assert np.any(np.abs(grid.Ez) > 0)


def test_fdtd_cuda_backend_request_falls_back_or_runs():
    grid = _small_grid()
    solver = FDTDSolver(grid, use_numba=True, backend="cuda", defer_host_sync=True)
    solver.add_source(GaussianSource(position=(3, 3, 3), component="Ez", amplitude=1.0))

    solver.step()
    solver.sync_fields_to_host()

    assert solver.backend_name in {"cuda", "numba-cpu", "numpy-cpu"}
    assert np.isfinite(grid.Ez).all()
    assert np.any(np.abs(grid.Ez) > 0)
    if solver.backend_name != "cuda":
        assert solver.backend_warning
