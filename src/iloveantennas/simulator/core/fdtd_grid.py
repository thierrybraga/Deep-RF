from typing import Tuple

import numpy as np

from .constants import (
    EPSILON_0,
    MU_0,
    Material,
    PMLMaterial,
)
from .geometry import AntennaGraph, BoundingBox, GeometryPrimitive, Vector3D
from .grid_config import GridConfig


class FDTDGrid:
    """
    Grade FDTD 3D com célula de Yee.

    Na célula de Yee, os campos são posicionados de forma intercalada:

    - Ex está na face x (i+½, j, k)
    - Ey está na face y (i, j+½, k)
    - Ez está na face z (i, j, k+½)
    - Hx está na aresta x (i, j+½, k+½)
    - Hy está na aresta y (i+½, j, k+½)
    - Hz está na aresta z (i+½, j+½, k)

    Attributes:
        config: Configuração da grade
        Ex, Ey, Ez: Componentes do campo elétrico
        Hx, Hy, Hz: Componentes do campo magnético
        eps_x, eps_y, eps_z: Permissividade em cada componente
        sigma_x, sigma_y, sigma_z: Condutividade em cada componente
    """

    def __init__(self, config: GridConfig):
        self.config = config
        self.time_step = 0

        nx, ny, nz = config.nx, config.ny, config.nz

        self.Ex = np.zeros((nx, ny + 1, nz + 1), dtype=np.float64)
        self.Ey = np.zeros((nx + 1, ny, nz + 1), dtype=np.float64)
        self.Ez = np.zeros((nx + 1, ny + 1, nz), dtype=np.float64)

        self.Hx = np.zeros((nx + 1, ny, nz), dtype=np.float64)
        self.Hy = np.zeros((nx, ny + 1, nz), dtype=np.float64)
        self.Hz = np.zeros((nx, ny, nz + 1), dtype=np.float64)

        self.eps_x = np.ones((nx, ny + 1, nz + 1), dtype=np.float32)
        self.eps_x *= EPSILON_0
        self.sigma_x = np.zeros((nx, ny + 1, nz + 1), dtype=np.float32)

        self.eps_y = np.ones((nx + 1, ny, nz + 1), dtype=np.float32)
        self.eps_y *= EPSILON_0
        self.sigma_y = np.zeros((nx + 1, ny, nz + 1), dtype=np.float32)

        self.eps_z = np.ones((nx + 1, ny + 1, nz), dtype=np.float32)
        self.eps_z *= EPSILON_0
        self.sigma_z = np.zeros((nx + 1, ny + 1, nz), dtype=np.float32)

        self.mu_x = np.ones((nx + 1, ny, nz), dtype=np.float32) * MU_0
        self.mu_y = np.ones((nx, ny + 1, nz), dtype=np.float32) * MU_0
        self.mu_z = np.ones((nx, ny, nz + 1), dtype=np.float32) * MU_0

        self._Ca_x = None
        self._Cb_x = None
        self._Ca_y = None
        self._Cb_y = None
        self._Ca_z = None
        self._Cb_z = None

        self._Da_x = None
        self._Db_x = None
        self._Da_y = None
        self._Db_y = None
        self._Da_z = None
        self._Db_z = None

        self.pml = None

        self._geometry_origin = Vector3D(0, 0, 0)

    def set_geometry_origin(self, origin: Vector3D):
        """Define a origem da geometria no sistema de coordenadas da grade."""
        self._geometry_origin = origin

    def world_to_grid(self, point: Vector3D) -> Tuple[int, int, int]:
        """
        Converte coordenadas do mundo para índices da grade.

        Args:
            point: Ponto em coordenadas do mundo [m]

        Returns:
            Tupla (i, j, k) de índices
        """
        offset = point - self._geometry_origin
        i = int(offset.x / self.config.dx)
        j = int(offset.y / self.config.dy)
        k = int(offset.z / self.config.dz)

        i = max(0, min(i, self.config.nx - 1))
        j = max(0, min(j, self.config.ny - 1))
        k = max(0, min(k, self.config.nz - 1))

        return (i, j, k)

    def grid_to_world(self, i: int, j: int, k: int) -> Vector3D:
        """
        Converte índices da grade para coordenadas do mundo.

        Args:
            i, j, k: Índices da célula

        Returns:
            Ponto central da célula em coordenadas do mundo
        """
        x = self._geometry_origin.x + (i + 0.5) * self.config.dx
        y = self._geometry_origin.y + (j + 0.5) * self.config.dy
        z = self._geometry_origin.z + (k + 0.5) * self.config.dz
        return Vector3D(x, y, z)

    def apply_material(self, material: Material, region: Tuple[slice, slice, slice]):
        """
        Aplica material a uma região da grade.

        Args:
            material: Material a aplicar
            region: Tupla de slices (i_slice, j_slice, k_slice)
        """
        i_s, j_s, k_s = region

        eps = material.epsilon_r * EPSILON_0
        sigma = material.sigma

        self.eps_x[i_s, j_s, k_s] = eps
        self.sigma_x[i_s, j_s, k_s] = sigma

        self.eps_y[i_s, j_s, k_s] = eps
        self.sigma_y[i_s, j_s, k_s] = sigma

        self.eps_z[i_s, j_s, k_s] = eps
        self.sigma_z[i_s, j_s, k_s] = sigma

    def apply_geometry(self, geometry: GeometryPrimitive, resolution_factor: float = 1.0):
        """
        Mapeia uma geometria para a grade.

        Args:
            geometry: Primitiva geométrica
            resolution_factor: Fator de resolução para amostragem
        """
        bb = geometry.get_bounding_box()

        i_min, j_min, k_min = self.world_to_grid(bb.min_point)
        i_max, j_max, k_max = self.world_to_grid(bb.max_point)

        for i in range(i_min, i_max + 1):
            for j in range(j_min, j_max + 1):
                for k in range(k_min, k_max + 1):
                    cell_center = self.grid_to_world(i, j, k)

                    if geometry.contains_point(cell_center):
                        self.apply_material(
                            geometry.material, (slice(i, i + 1), slice(j, j + 1), slice(k, k + 1))
                        )

    def apply_antenna(self, antenna: AntennaGraph):
        """
        Mapeia uma antena completa para a grade.

        Args:
            antenna: Grafo da antena
        """
        bb = antenna.get_bounding_box()
        grid_center = Vector3D(
            self.config.nx * self.config.dx / 2,
            self.config.ny * self.config.dy / 2,
            self.config.nz * self.config.dz / 2,
        )
        offset = grid_center - bb.center
        self._geometry_origin = Vector3D(0, 0, 0) - offset

        for geom in antenna.geometries:
            self.apply_geometry(geom)

    def apply_pec_box(
        self, i_range: Tuple[int, int], j_range: Tuple[int, int], k_range: Tuple[int, int]
    ):
        """
        Aplica condutor elétrico perfeito (PEC) a uma caixa.

        Em PEC, os campos E tangenciais são zerados.
        """
        i1, i2 = i_range
        j1, j2 = j_range
        k1, k2 = k_range

        sigma_pec = 1e10

        self.sigma_x[i1:i2, j1 : j2 + 1, k1 : k2 + 1] = sigma_pec
        self.sigma_y[i1 : i2 + 1, j1:j2, k1 : k2 + 1] = sigma_pec
        self.sigma_z[i1 : i2 + 1, j1 : j2 + 1, k1:k2] = sigma_pec

    def calculate_coefficients(self):
        """
        Calcula coeficientes de atualização FDTD.

        Para o campo E:
            Ca = (1 - σΔt/2ε) / (1 + σΔt/2ε)
            Cb = (Δt/ε) / (1 + σΔt/2ε)

        Para o campo H (sem perdas magnéticas):
            Da = 1
            Db = Δt/μ
        """
        dt = self.config.dt

        factor = self.sigma_x * dt / (2 * self.eps_x)
        self._Ca_x = (1 - factor) / (1 + factor)
        self._Cb_x = (dt / self.eps_x) / (1 + factor)

        factor = self.sigma_y * dt / (2 * self.eps_y)
        self._Ca_y = (1 - factor) / (1 + factor)
        self._Cb_y = (dt / self.eps_y) / (1 + factor)

        factor = self.sigma_z * dt / (2 * self.eps_z)
        self._Ca_z = (1 - factor) / (1 + factor)
        self._Cb_z = (dt / self.eps_z) / (1 + factor)

        self._Da_x = np.ones_like(self.mu_x)
        self._Db_x = dt / self.mu_x

        self._Da_y = np.ones_like(self.mu_y)
        self._Db_y = dt / self.mu_y

        self._Da_z = np.ones_like(self.mu_z)
        self._Db_z = dt / self.mu_z

    def setup_pml(self, pml_config: PMLMaterial = None):
        """
        Configura camadas PML nas bordas.

        Args:
            pml_config: Configuração PML (usa padrão se None)
        """
        if pml_config is None:
            pml_config = PMLMaterial(thickness=self.config.pml_layers, order=3)
            pml_config.sigma_max = pml_config.calculate_optimal_sigma(self.config.dx)

        self.pml = pml_config
        n = pml_config.thickness

        for i in range(n):
            d = (n - i) * self.config.dx
            sigma = pml_config.sigma_profile(d, n * self.config.dx)
            self.sigma_x[i, :, :] += sigma
            self.sigma_y[i, :, :] += sigma
            self.sigma_z[i, :, :] += sigma

        for i in range(n):
            d = (i + 1) * self.config.dx
            sigma = pml_config.sigma_profile(d, n * self.config.dx)
            idx = self.config.nx - n + i
            self.sigma_x[idx, :, :] += sigma
            self.sigma_y[idx, :, :] += sigma
            self.sigma_z[idx, :, :] += sigma

        for j in range(n):
            d = (n - j) * self.config.dy
            sigma = pml_config.sigma_profile(d, n * self.config.dy)
            self.sigma_x[:, j, :] += sigma
            self.sigma_y[:, j, :] += sigma
            self.sigma_z[:, j, :] += sigma

        for j in range(n):
            d = (j + 1) * self.config.dy
            sigma = pml_config.sigma_profile(d, n * self.config.dy)
            idx = self.config.ny - n + j
            self.sigma_x[:, idx, :] += sigma
            self.sigma_y[:, idx, :] += sigma
            self.sigma_z[:, idx, :] += sigma

        for k in range(n):
            d = (n - k) * self.config.dz
            sigma = pml_config.sigma_profile(d, n * self.config.dz)
            self.sigma_x[:, :, k] += sigma
            self.sigma_y[:, :, k] += sigma
            self.sigma_z[:, :, k] += sigma

        for k in range(n):
            d = (k + 1) * self.config.dz
            sigma = pml_config.sigma_profile(d, n * self.config.dz)
            idx = self.config.nz - n + k
            self.sigma_x[:, :, idx] += sigma
            self.sigma_y[:, :, idx] += sigma
            self.sigma_z[:, :, idx] += sigma

        self.calculate_coefficients()

    def reset_fields(self):
        """Zera todos os campos."""
        self.Ex.fill(0)
        self.Ey.fill(0)
        self.Ez.fill(0)
        self.Hx.fill(0)
        self.Hy.fill(0)
        self.Hz.fill(0)
        self.time_step = 0

    def get_field_at(self, point: Vector3D, field: str = "E") -> Tuple[float, float, float]:
        """
        Obtém valor do campo em um ponto (interpolado).

        Args:
            point: Ponto em coordenadas do mundo
            field: 'E' para elétrico, 'H' para magnético

        Returns:
            Tupla (Fx, Fy, Fz) com componentes do campo
        """
        i, j, k = self.world_to_grid(point)

        if field == "E":
            return (self.Ex[i, j, k], self.Ey[i, j, k], self.Ez[i, j, k])
        else:
            return (self.Hx[i, j, k], self.Hy[i, j, k], self.Hz[i, j, k])

    def get_energy(self) -> Tuple[float, float]:
        """
        Calcula energia eletromagnética total.

        Returns:
            Tupla (energia_E, energia_H)
        """
        dV = self.config.dx * self.config.dy * self.config.dz

        E_energy = (
            0.5
            * dV
            * (
                np.sum(self.Ex**2) * EPSILON_0
                + np.sum(self.Ey**2) * EPSILON_0
                + np.sum(self.Ez**2) * EPSILON_0
            )
        )

        H_energy = (
            0.5
            * dV
            * (np.sum(self.Hx**2) * MU_0 + np.sum(self.Hy**2) * MU_0 + np.sum(self.Hz**2) * MU_0)
        )

        return (E_energy, H_energy)

    def get_slice(self, axis: str, index: int, field: str = "Ez") -> np.ndarray:
        """
        Extrai uma fatia 2D de um campo.

        Args:
            axis: Eixo perpendicular ao plano ('x', 'y', ou 'z')
            index: Índice da fatia
            field: Nome do campo ('Ex', 'Ey', 'Ez', 'Hx', 'Hy', 'Hz')

        Returns:
            Array 2D com valores do campo
        """
        field_array = getattr(self, field)

        if axis == "x":
            return field_array[index, :, :]
        elif axis == "y":
            return field_array[:, index, :]
        else:
            return field_array[:, :, index]

    def memory_usage(self) -> float:
        """Retorna uso de memória estimado em MB."""
        total_cells = self.config.total_cells
        bytes_per_cell = 8
        num_arrays = 24

        return (total_cells * bytes_per_cell * num_arrays) / (1024**2)

    def __repr__(self) -> str:
        dx_mm = self.config.dx * 1e3
        dt_ps = self.config.dt * 1e12
        return (
            f"FDTDGrid({self.config.nx}x{self.config.ny}x{self.config.nz}, "
            f"dx={dx_mm:.3f}mm, dt={dt_ps:.3f}ps)"
        )


def create_grid_for_antenna(
    antenna: AntennaGraph, freq_max: float, cells_per_lambda: int = 20, pml_layers: int = 10
) -> FDTDGrid:
    bb = antenna.get_bounding_box()

    config = GridConfig.from_frequency(
        freq_max=freq_max, domain=bb, cells_per_lambda=cells_per_lambda, pml_layers=pml_layers
    )

    grid = FDTDGrid(config)
    grid.apply_antenna(antenna)
    grid.setup_pml()
    grid.calculate_coefficients()

    return grid


__all__ = ["FDTDGrid", "create_grid_for_antenna"]
