"""
IloveAntenas Core Module
======================
Módulos fundamentais para simulação eletromagnética de antenas.

Contém:
- constants: Constantes físicas e biblioteca de materiais
- geometry: Sistema de geometria e grafos para antenas
- grid: Implementação da grade FDTD com célula de Yee
"""

from .constants import (  # Constantes físicas; Classes de materiais; Biblioteca de materiais; Funções auxiliares
    C0,
    EPSILON_0,
    ETA_0,
    MU_0,
    AnisotropicMaterial,
    DispersiveMaterial,
    Material,
    MaterialLibrary,
    PMLMaterial,
    cfl_time_step,
    optimal_cell_size,
    wavelength_in_medium,
)
from .geometry import (  # Tipos básicos; Primitivas geométricas; Sistema de grafos; Factory de antenas
    AntennaEdge,
    AntennaFactory,
    AntennaGraph,
    AntennaNode,
    BoundingBox,
    Cylinder,
    Helix,
    Horn,
    ParabolicDish,
    Rectangle,
    Vector3D,
    Wire,
)
from .grid import FDTDGrid, GridConfig, create_grid_for_antenna

__all__ = [
    # Constantes
    "C0",
    "EPSILON_0",
    "MU_0",
    "ETA_0",
    # Materiais
    "Material",
    "DispersiveMaterial",
    "AnisotropicMaterial",
    "PMLMaterial",
    "MaterialLibrary",
    # Funções
    "wavelength_in_medium",
    "cfl_time_step",
    "optimal_cell_size",
    # Geometria
    "Vector3D",
    "BoundingBox",
    "Wire",
    "Rectangle",
    "Cylinder",
    "Helix",
    "Horn",
    "ParabolicDish",
    "AntennaGraph",
    "AntennaNode",
    "AntennaEdge",
    "AntennaFactory",
    # Grid
    "GridConfig",
    "FDTDGrid",
    "create_grid_for_antenna",
]
