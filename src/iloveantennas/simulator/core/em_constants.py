import numpy as np

__all__ = [
    "C0",
    "EPSILON_0",
    "MU_0",
    "ETA_0",
    "wavelength_in_medium",
    "frequency_to_wavelength",
    "wavelength_to_frequency",
    "cells_per_wavelength",
    "optimal_cell_size",
    "cfl_time_step",
]


C0 = 299792458.0
EPSILON_0 = 8.8541878128e-12
MU_0 = 4 * np.pi * 1e-7
ETA_0 = np.sqrt(MU_0 / EPSILON_0)


def wavelength_in_medium(freq: float, epsilon_r: float = 1.0, mu_r: float = 1.0) -> float:
    return C0 / (freq * np.sqrt(epsilon_r * mu_r))


def frequency_to_wavelength(freq: float) -> float:
    return C0 / freq


def wavelength_to_frequency(wavelength: float) -> float:
    return C0 / wavelength


def cells_per_wavelength(freq: float, dx: float, epsilon_r: float = 1.0) -> float:
    wavelength = wavelength_in_medium(freq, epsilon_r)
    return wavelength / dx


def optimal_cell_size(freq_max: float, cells_per_lambda: int = 20) -> float:
    wavelength_min = C0 / freq_max
    return wavelength_min / cells_per_lambda


def cfl_time_step(
    dx: float, dy: float | None = None, dz: float | None = None, courant: float = 0.99
) -> float:
    if dy is None:
        dy = dx
    if dz is None:
        dz = dx
    sum_inv_sq = 1 / dx**2 + 1 / dy**2 + 1 / dz**2
    dt_max = 1 / (C0 * np.sqrt(sum_inv_sq))
    return courant * dt_max
