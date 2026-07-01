from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

import numpy as np

from .em_constants import C0, EPSILON_0, MU_0

__all__ = [
    "MaterialType",
    "BoundaryType",
    "Material",
    "DispersiveMaterial",
    "AnisotropicMaterial",
    "PMLMaterial",
    "MaterialLibrary",
]


class MaterialType(Enum):
    VACUUM = "vacuum"
    DIELECTRIC = "dielectric"
    CONDUCTOR = "conductor"
    PEC = "pec"
    PMC = "pmc"
    LOSSY_DIELECTRIC = "lossy_dielectric"
    DISPERSIVE = "dispersive"
    ANISOTROPIC = "anisotropic"


class BoundaryType(Enum):
    PEC = "pec"
    PMC = "pmc"
    ABC = "abc"
    PML = "pml"
    PERIODIC = "periodic"
    SYMMETRIC = "symmetric"
    ANTISYMMETRIC = "antisymmetric"


@dataclass
class Material:
    name: str
    epsilon_r: float = 1.0
    mu_r: float = 1.0
    sigma: float = 0.0
    sigma_m: float = 0.0
    tan_delta: float = 0.0
    material_type: MaterialType = MaterialType.DIELECTRIC
    color: tuple = (0.5, 0.5, 0.5, 1.0)

    @property
    def epsilon(self) -> float:
        return self.epsilon_r * EPSILON_0

    @property
    def mu(self) -> float:
        return self.mu_r * MU_0

    @property
    def impedance(self) -> float:
        return float(np.sqrt(self.mu / self.epsilon))

    @property
    def velocity(self) -> float:
        return C0 / np.sqrt(self.epsilon_r * self.mu_r)

    @property
    def color_hex(self) -> str:
        rgb = tuple(max(0, min(255, round(float(channel) * 255))) for channel in self.color[:3])
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    @property
    def api_sigma(self) -> float:
        return float(self.sigma) if np.isfinite(self.sigma) else 1e30

    @property
    def wavelength(self) -> Callable[[float], float]:
        return lambda freq: self.velocity / freq

    @property
    def skin_depth(self) -> Callable[[float], float]:
        def calc_skin_depth(freq: float) -> float:
            if self.sigma <= 0:
                return np.inf
            omega = 2 * np.pi * freq
            return float(np.sqrt(2 / (omega * self.mu * self.sigma)))

        return calc_skin_depth

    @property
    def loss_tangent(self) -> Callable[[float], float]:
        def calc_loss_tangent(freq: float) -> float:
            omega = 2 * np.pi * freq
            return float(self.sigma / (omega * self.epsilon))

        return calc_loss_tangent


@dataclass
class DispersiveMaterial(Material):
    epsilon_inf: float = 1.0
    debye_poles: list = field(default_factory=list)

    def __post_init__(self) -> None:
        self.material_type = MaterialType.DISPERSIVE

    def epsilon_complex(self, freq: float) -> complex:
        omega = 2 * np.pi * freq
        eps = self.epsilon_inf
        for delta_eps, tau in self.debye_poles:
            eps += delta_eps / (1 + 1j * omega * tau)
        if self.sigma > 0:
            eps -= 1j * self.sigma / (omega * EPSILON_0)
        return eps


@dataclass
class AnisotropicMaterial(Material):
    epsilon_tensor: np.ndarray = field(default_factory=lambda: np.eye(3))
    mu_tensor: np.ndarray = field(default_factory=lambda: np.eye(3))

    def __post_init__(self) -> None:
        self.material_type = MaterialType.ANISOTROPIC
        self.epsilon_tensor = np.array(self.epsilon_tensor)
        self.mu_tensor = np.array(self.mu_tensor)


@dataclass
class PMLMaterial:
    thickness: int = 10
    sigma_max: float | None = None
    order: int = 3
    kappa_max: float = 1.0
    alpha_max: float = 0.0

    def calculate_optimal_sigma(self, dx: float) -> float:
        return (self.order + 1) / (150 * np.pi * dx)

    def sigma_profile(self, position: float, d: float) -> float:
        if position <= 0:
            return 0.0
        ratio = min(position / d, 1.0)
        return float(self.sigma_max * (ratio**self.order))

    def kappa_profile(self, position: float, d: float) -> float:
        if position <= 0:
            return 1.0
        ratio = min(position / d, 1.0)
        return float(1.0 + (self.kappa_max - 1.0) * (ratio**self.order))


class MaterialLibrary:
    VACUUM = Material(
        name="Vacuum",
        epsilon_r=1.0,
        mu_r=1.0,
        sigma=0.0,
        material_type=MaterialType.VACUUM,
        color=(1.0, 1.0, 1.0, 0.0),
    )

    AIR = Material(
        name="Air",
        epsilon_r=1.00059,
        mu_r=1.0,
        sigma=0.0,
        material_type=MaterialType.DIELECTRIC,
        color=(0.9, 0.95, 1.0, 0.1),
    )

    COPPER = Material(
        name="Copper",
        epsilon_r=1.0,
        mu_r=0.999994,
        sigma=5.96e7,
        material_type=MaterialType.CONDUCTOR,
        color=(0.72, 0.45, 0.2, 1.0),
    )

    ALUMINUM = Material(
        name="Aluminum",
        epsilon_r=1.0,
        mu_r=1.000022,
        sigma=3.77e7,
        material_type=MaterialType.CONDUCTOR,
        color=(0.77, 0.77, 0.8, 1.0),
    )

    GOLD = Material(
        name="Gold",
        epsilon_r=1.0,
        mu_r=1.0,
        sigma=4.11e7,
        material_type=MaterialType.CONDUCTOR,
        color=(1.0, 0.84, 0.0, 1.0),
    )

    SILVER = Material(
        name="Silver",
        epsilon_r=1.0,
        mu_r=0.99998,
        sigma=6.30e7,
        material_type=MaterialType.CONDUCTOR,
        color=(0.75, 0.75, 0.75, 1.0),
    )

    PEC = Material(
        name="PEC",
        epsilon_r=1.0,
        mu_r=1.0,
        sigma=np.inf,
        material_type=MaterialType.PEC,
        color=(0.2, 0.2, 0.2, 1.0),
    )

    FR4 = Material(
        name="FR-4",
        epsilon_r=4.4,
        mu_r=1.0,
        sigma=0.0,
        tan_delta=0.02,
        material_type=MaterialType.LOSSY_DIELECTRIC,
        color=(0.0, 0.5, 0.0, 0.8),
    )

    ROGERS_4003C = Material(
        name="Rogers RO4003C",
        epsilon_r=3.55,
        mu_r=1.0,
        sigma=0.0,
        tan_delta=0.0027,
        material_type=MaterialType.DIELECTRIC,
        color=(0.9, 0.85, 0.7, 0.9),
    )

    TEFLON = Material(
        name="PTFE/Teflon",
        epsilon_r=2.1,
        mu_r=1.0,
        sigma=0.0,
        tan_delta=0.0002,
        material_type=MaterialType.DIELECTRIC,
        color=(0.95, 0.95, 0.95, 0.8),
    )

    SILICON = Material(
        name="Silicon",
        epsilon_r=11.7,
        mu_r=1.0,
        sigma=0.0,
        material_type=MaterialType.DIELECTRIC,
        color=(0.4, 0.4, 0.45, 0.9),
    )

    GLASS = Material(
        name="Glass",
        epsilon_r=4.0,
        mu_r=1.0,
        sigma=0.0,
        material_type=MaterialType.DIELECTRIC,
        color=(0.7, 0.85, 0.9, 0.5),
    )

    WATER = Material(
        name="Water",
        epsilon_r=80.0,
        mu_r=1.0,
        sigma=0.01,
        material_type=MaterialType.LOSSY_DIELECTRIC,
        color=(0.0, 0.4, 0.8, 0.6),
    )

    DRY_SOIL = Material(
        name="Dry Soil",
        epsilon_r=3.0,
        mu_r=1.0,
        sigma=0.001,
        material_type=MaterialType.LOSSY_DIELECTRIC,
        color=(0.6, 0.4, 0.2, 1.0),
    )

    WET_SOIL = Material(
        name="Wet Soil",
        epsilon_r=25.0,
        mu_r=1.0,
        sigma=0.02,
        material_type=MaterialType.LOSSY_DIELECTRIC,
        color=(0.4, 0.25, 0.1, 1.0),
    )

    @classmethod
    def get_all_materials(cls) -> dict:
        return {name: value for name, value in vars(cls).items() if isinstance(value, Material)}

    @classmethod
    def create_custom(
        cls,
        name: str,
        epsilon_r: float = 1.0,
        mu_r: float = 1.0,
        sigma: float = 0.0,
    ) -> Material:
        if sigma > 1e6:
            mat_type = MaterialType.CONDUCTOR
        elif sigma > 0:
            mat_type = MaterialType.LOSSY_DIELECTRIC
        else:
            mat_type = MaterialType.DIELECTRIC
        return Material(
            name=name,
            epsilon_r=epsilon_r,
            mu_r=mu_r,
            sigma=sigma,
            material_type=mat_type,
        )
