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

from .sources import (
    Source, GaussianSource, SineSource, ModulatedGaussianSource, RickerSource, SourceType
)

from .monitors import (
    FieldProbe, NearFieldBox
)

from .fdtd import (
    FDTDSolver
)

from .farfield import (
    NearToFarField, calculate_directivity, calculate_gain, dB, dBi
)

__all__ = [
    # Fontes
    'Source', 'GaussianSource', 'SineSource', 'ModulatedGaussianSource', 'RickerSource', 'SourceType',
    # Monitores
    'FieldProbe', 'NearFieldBox',
    # Solver
    'FDTDSolver',
    # Far-field
    'NearToFarField',
    # Análise
    'calculate_directivity', 'calculate_gain', 'dB', 'dBi'
]
