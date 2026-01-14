"""
IloveAntenas Core Module
======================
Módulos fundamentais para simulação eletromagnética de antenas.

Contém:
- constants: Constantes físicas e biblioteca de materiais
- geometry: Sistema de geometria e grafos para antenas
- grid: Implementação da grade FDTD com célula de Yee
"""

from .constants import (
    # Constantes físicas
    C0, EPSILON_0, MU_0, ETA_0,
    # Classes de materiais
    Material, DispersiveMaterial, AnisotropicMaterial, PMLMaterial,
    # Biblioteca de materiais
    MaterialLibrary,
    # Funções auxiliares
    wavelength_in_medium, cfl_time_step, optimal_cell_size
)

from .geometry import (
    # Tipos básicos
    Vector3D, BoundingBox,
    # Primitivas geométricas
    Wire, Rectangle, Cylinder, Helix, Horn, ParabolicDish,
    # Sistema de grafos
    AntennaGraph, AntennaNode, AntennaEdge,
    # Factory de antenas
    AntennaFactory
)

from .grid import (
    GridConfig, FDTDGrid, create_grid_for_antenna
)

__all__ = [
    # Constantes
    'C0', 'EPSILON_0', 'MU_0', 'ETA_0',
    # Materiais
    'Material', 'DispersiveMaterial', 'AnisotropicMaterial', 'PMLMaterial',
    'MaterialLibrary',
    # Funções
    'wavelength_in_medium', 'cfl_time_step', 'optimal_cell_size',
    # Geometria
    'Vector3D', 'BoundingBox', 'Wire', 'Rectangle', 'Cylinder',
    'Helix', 'Horn', 'ParabolicDish',
    'AntennaGraph', 'AntennaNode', 'AntennaEdge', 'AntennaFactory',
    # Grid
    'GridConfig', 'FDTDGrid', 'create_grid_for_antenna'
]
