"""
IloveAntenas Visualization Module
===============================
Ferramentas de visualização para geometria, campos e diagramas de radiação.

Contém:
- GeometryVisualizer: Visualização 3D de antenas
- FieldVisualizer: Campos eletromagnéticos
- RadiationPatternPlot: Diagramas de radiação
- FieldAnimator: Animações de propagação
"""

from .plots import (  # Visualização de geometria; Visualização de campos; Diagramas de radiação; Animações; Funções auxiliares
    FieldAnimator,
    FieldVisualizer,
    GeometryVisualizer,
    RadiationPatternPlot,
    plot_impedance,
    plot_s_parameters,
)

__all__ = [
    "GeometryVisualizer",
    "FieldVisualizer",
    "RadiationPatternPlot",
    "FieldAnimator",
    "plot_s_parameters",
    "plot_impedance",
]
