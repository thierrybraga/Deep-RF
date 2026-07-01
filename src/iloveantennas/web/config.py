from dataclasses import asdict, dataclass


@dataclass
class AntennaConfig:
    """Configuração de antena"""

    type: str = "dipole"
    frequency: float = 300e6
    length: float = None
    radius: float = 0.001
    num_directors: int = 3
    substrate_er: float = 4.4
    substrate_h: float = 1.6e-3
    turns: int = 5
    # Horn
    aperture_width: float = None
    aperture_height: float = None
    flare_length: float = None
    # Dish
    dish_diameter: float = None
    focal_length: float = None
    # LPDA
    tau: float = 0.86
    sigma: float = 0.15
    # Loop
    loop_radius: float = None
    # Biquad
    side_length: float = None
    reflector_distance: float = None
    # Discone
    disc_radius: float = None
    cone_radius: float = None
    cone_height: float = None

    def to_dict(self):
        return asdict(self)


@dataclass
class SimulationConfig:
    """Configuração de simulação"""

    cells_per_wavelength: int = 20  # Aumentado para 20 para melhor resolução
    num_steps: int = 200
    pml_layers: int = 8
    courant: float = 0.99
    source_type: str = "gaussian"
    source_amplitude: float = 1.0
    use_optimized: bool = True  # Nova opção para usar solver otimizado
    solver_backend: str = "auto"  # 'auto', 'cuda', 'numba' or 'numpy'
    method: str = "fdtd"  # 'fdtd' or 'fem'

    def to_dict(self):
        return asdict(self)
