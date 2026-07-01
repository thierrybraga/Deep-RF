"""
CUDA kernels for the FDTD solver.

The CPU/Numba kernels remain the default path. This module is imported lazily by
the solver when the caller explicitly requests the CUDA backend.
"""

from __future__ import annotations

import math

import numpy as np

try:
    from numba import cuda

    CUDA_IMPORT_AVAILABLE = True
except Exception:
    cuda = None
    CUDA_IMPORT_AVAILABLE = False


class CudaBackendUnavailable(RuntimeError):
    """Raised when CUDA cannot be used for the current FDTD run."""


if CUDA_IMPORT_AVAILABLE:

    @cuda.jit
    def update_hx_cuda(Hx, Ey, Ez, Da_x, Db_x, dx, dy, dz):
        i, j, k = cuda.grid(3)
        nx, ny, nz = Hx.shape
        if i < nx and j < ny - 1 and k < nz - 1:
            curl_e = (Ez[i, j + 1, k] - Ez[i, j, k]) / dy - (
                Ey[i, j, k + 1] - Ey[i, j, k]
            ) / dz
            Hx[i, j, k] = Da_x[i, j, k] * Hx[i, j, k] - Db_x[i, j, k] * curl_e

    @cuda.jit
    def update_hy_cuda(Hy, Ex, Ez, Da_y, Db_y, dx, dy, dz):
        i, j, k = cuda.grid(3)
        nx, ny, nz = Hy.shape
        if i < nx - 1 and j < ny and k < nz - 1:
            curl_e = (Ex[i, j, k + 1] - Ex[i, j, k]) / dz - (
                Ez[i + 1, j, k] - Ez[i, j, k]
            ) / dx
            Hy[i, j, k] = Da_y[i, j, k] * Hy[i, j, k] - Db_y[i, j, k] * curl_e

    @cuda.jit
    def update_hz_cuda(Hz, Ex, Ey, Da_z, Db_z, dx, dy, dz):
        i, j, k = cuda.grid(3)
        nx, ny, nz = Hz.shape
        if i < nx - 1 and j < ny - 1 and k < nz:
            curl_e = (Ey[i + 1, j, k] - Ey[i, j, k]) / dx - (
                Ex[i, j + 1, k] - Ex[i, j, k]
            ) / dy
            Hz[i, j, k] = Da_z[i, j, k] * Hz[i, j, k] - Db_z[i, j, k] * curl_e

    @cuda.jit
    def update_ex_cuda(Ex, Hy, Hz, Ca_x, Cb_x, dx, dy, dz):
        i, j, k = cuda.grid(3)
        nx, ny, nz = Ex.shape
        if i < nx and 1 <= j < ny - 1 and 1 <= k < nz - 1:
            curl_h = (Hz[i, j, k] - Hz[i, j - 1, k]) / dy - (
                Hy[i, j, k] - Hy[i, j, k - 1]
            ) / dz
            Ex[i, j, k] = Ca_x[i, j, k] * Ex[i, j, k] + Cb_x[i, j, k] * curl_h

    @cuda.jit
    def update_ey_cuda(Ey, Hx, Hz, Ca_y, Cb_y, dx, dy, dz):
        i, j, k = cuda.grid(3)
        nx, ny, nz = Ey.shape
        if 1 <= i < nx - 1 and j < ny and 1 <= k < nz - 1:
            curl_h = (Hx[i, j, k] - Hx[i, j, k - 1]) / dz - (
                Hz[i, j, k] - Hz[i - 1, j, k]
            ) / dx
            Ey[i, j, k] = Ca_y[i, j, k] * Ey[i, j, k] + Cb_y[i, j, k] * curl_h

    @cuda.jit
    def update_ez_cuda(Ez, Hx, Hy, Ca_z, Cb_z, dx, dy, dz):
        i, j, k = cuda.grid(3)
        nx, ny, nz = Ez.shape
        if 1 <= i < nx - 1 and 1 <= j < ny - 1 and k < nz:
            curl_h = (Hy[i, j, k] - Hy[i - 1, j, k]) / dx - (
                Hx[i, j, k] - Hx[i, j - 1, k]
            ) / dy
            Ez[i, j, k] = Ca_z[i, j, k] * Ez[i, j, k] + Cb_z[i, j, k] * curl_h

    @cuda.jit
    def add_source_cuda(field, i, j, k, value):
        if (
            0 <= i < field.shape[0]
            and 0 <= j < field.shape[1]
            and 0 <= k < field.shape[2]
        ):
            field[i, j, k] += value

    @cuda.jit
    def read_point_cuda(field, i, j, k, out):
        if (
            0 <= i < field.shape[0]
            and 0 <= j < field.shape[1]
            and 0 <= k < field.shape[2]
        ):
            out[0] = field[i, j, k]
        else:
            out[0] = 0.0


def cuda_is_available() -> bool:
    if not CUDA_IMPORT_AVAILABLE:
        return False
    try:
        return bool(cuda.is_available())
    except Exception:
        return False


def _blocks_for(shape: tuple[int, int, int], threads: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(math.ceil(max(1, dim) / block) for dim, block in zip(shape, threads))


class CudaFDTDBackend:
    """Keeps FDTD fields on the GPU and launches CUDA update kernels."""

    threads = (8, 8, 8)

    def __init__(self, grid):
        if not cuda_is_available():
            raise CudaBackendUnavailable("Numba CUDA is not available in this environment.")
        self.grid = grid
        self._validate_coefficients()
        self._scratch = cuda.device_array(1, dtype=np.float64)
        self.arrays = {}
        self.sync_from_host()

    def _validate_coefficients(self):
        required = [
            "_Ca_x",
            "_Cb_x",
            "_Ca_y",
            "_Cb_y",
            "_Ca_z",
            "_Cb_z",
            "_Da_x",
            "_Db_x",
            "_Da_y",
            "_Db_y",
            "_Da_z",
            "_Db_z",
        ]
        missing = [name for name in required if getattr(self.grid, name, None) is None]
        if missing:
            raise CudaBackendUnavailable(
                "Grid coefficients must be calculated before enabling CUDA: "
                + ", ".join(missing)
            )

    def sync_from_host(self, components: list[str] | tuple[str, ...] | None = None):
        names = components or [
            "Ex",
            "Ey",
            "Ez",
            "Hx",
            "Hy",
            "Hz",
            "_Ca_x",
            "_Cb_x",
            "_Ca_y",
            "_Cb_y",
            "_Ca_z",
            "_Cb_z",
            "_Da_x",
            "_Db_x",
            "_Da_y",
            "_Db_y",
            "_Da_z",
            "_Db_z",
        ]
        for name in names:
            self.arrays[name] = cuda.to_device(getattr(self.grid, name))
        cuda.synchronize()

    def sync_to_host(self, components: list[str] | tuple[str, ...] | None = None):
        names = components or ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"]
        for name in names:
            self.arrays[name].copy_to_host(getattr(self.grid, name))
        cuda.synchronize()

    def update_h(self):
        dx, dy, dz = self.grid.config.dx, self.grid.config.dy, self.grid.config.dz
        threads = self.threads
        update_hx_cuda[_blocks_for(self.grid.Hx.shape, threads), threads](
            self.arrays["Hx"],
            self.arrays["Ey"],
            self.arrays["Ez"],
            self.arrays["_Da_x"],
            self.arrays["_Db_x"],
            dx,
            dy,
            dz,
        )
        update_hy_cuda[_blocks_for(self.grid.Hy.shape, threads), threads](
            self.arrays["Hy"],
            self.arrays["Ex"],
            self.arrays["Ez"],
            self.arrays["_Da_y"],
            self.arrays["_Db_y"],
            dx,
            dy,
            dz,
        )
        update_hz_cuda[_blocks_for(self.grid.Hz.shape, threads), threads](
            self.arrays["Hz"],
            self.arrays["Ex"],
            self.arrays["Ey"],
            self.arrays["_Da_z"],
            self.arrays["_Db_z"],
            dx,
            dy,
            dz,
        )
        cuda.synchronize()

    def update_e(self):
        dx, dy, dz = self.grid.config.dx, self.grid.config.dy, self.grid.config.dz
        threads = self.threads
        update_ex_cuda[_blocks_for(self.grid.Ex.shape, threads), threads](
            self.arrays["Ex"],
            self.arrays["Hy"],
            self.arrays["Hz"],
            self.arrays["_Ca_x"],
            self.arrays["_Cb_x"],
            dx,
            dy,
            dz,
        )
        update_ey_cuda[_blocks_for(self.grid.Ey.shape, threads), threads](
            self.arrays["Ey"],
            self.arrays["Hx"],
            self.arrays["Hz"],
            self.arrays["_Ca_y"],
            self.arrays["_Cb_y"],
            dx,
            dy,
            dz,
        )
        update_ez_cuda[_blocks_for(self.grid.Ez.shape, threads), threads](
            self.arrays["Ez"],
            self.arrays["Hx"],
            self.arrays["Hy"],
            self.arrays["_Ca_z"],
            self.arrays["_Cb_z"],
            dx,
            dy,
            dz,
        )
        cuda.synchronize()

    def add_source(self, component: str, i: int, j: int, k: int, value: float):
        add_source_cuda[1, 1](self.arrays[component], int(i), int(j), int(k), float(value))
        cuda.synchronize()

    def read_point(self, component: str, i: int, j: int, k: int) -> float:
        read_point_cuda[1, 1](self.arrays[component], int(i), int(j), int(k), self._scratch)
        return float(self._scratch.copy_to_host()[0])
