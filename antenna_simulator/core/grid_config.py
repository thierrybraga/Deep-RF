from dataclasses import dataclass
from typing import Tuple
import math

from .constants import C0, cfl_time_step
from .geometry import BoundingBox


@dataclass
class GridConfig:
    """
    Configuração da grade FDTD.

    Attributes:
        dx, dy, dz: Tamanho das células [m]
        nx, ny, nz: Número de células em cada direção
        dt: Passo temporal [s]
        pml_layers: Número de camadas PML em cada borda
        courant: Número de Courant (0 < S ≤ 1)
    """
    dx: float
    dy: float = None
    dz: float = None
    nx: int = 100
    ny: int = 100
    nz: int = 100
    dt: float = None
    pml_layers: int = 10
    courant: float = 0.99

    def __post_init__(self):
        if self.dy is None:
            self.dy = self.dx
        if self.dz is None:
            self.dz = self.dx
        if self.dt is None:
            self.dt = cfl_time_step(self.dx, self.dy, self.dz, self.courant)

    @property
    def domain_size(self) -> Tuple[float, float, float]:
        return (self.nx * self.dx, self.ny * self.dy, self.nz * self.dz)

    @property
    def total_cells(self) -> int:
        return self.nx * self.ny * self.nz

    @classmethod
    def from_frequency(
        cls,
        freq_max: float,
        domain: BoundingBox,
        cells_per_lambda: int = 20,
        pml_layers: int = 10,
        padding: float = 0.1
    ) -> "GridConfig":
        wavelength = C0 / freq_max
        dx = wavelength / cells_per_lambda

        pad = padding * wavelength
        size = domain.size

        nx = math.ceil((size.x + 2 * pad) / dx) + 2 * pml_layers
        ny = math.ceil((size.y + 2 * pad) / dx) + 2 * pml_layers
        nz = math.ceil((size.z + 2 * pad) / dx) + 2 * pml_layers

        return cls(dx=dx, nx=nx, ny=ny, nz=nz, pml_layers=pml_layers)


__all__ = ["GridConfig"]

