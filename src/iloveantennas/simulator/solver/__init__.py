"""
IloveAntenas Solver Module
========================
Implementação do solver FDTD para simulação eletromagnética.

Contém:
- FDTDSolver: Loop temporal principal
- Fontes de excitação (Gaussiana, Senoidal, Modulada, Ricker)
- Probes e monitores de campo
- Transformação Near-to-Far Field
"""

from .farfield import NearToFarField, calculate_directivity, calculate_gain, dB, dBi
from .fdtd import FDTDSolver
from .monitors import FieldProbe, NearFieldBox
from .sources import (
    GaussianSource,
    ModulatedGaussianSource,
    RickerSource,
    SineSource,
    Source,
    SourceType,
)

__all__ = [
    # Fontes
    "Source",
    "GaussianSource",
    "SineSource",
    "ModulatedGaussianSource",
    "RickerSource",
    "SourceType",
    # Monitores
    "FieldProbe",
    "NearFieldBox",
    # Solver
    "FDTDSolver",
    # Far-field
    "NearToFarField",
    # Análise
    "calculate_directivity",
    "calculate_gain",
    "dB",
    "dBi",
]
