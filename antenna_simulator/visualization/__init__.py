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

from .plots import (
    # Visualização de geometria
    GeometryVisualizer,
    # Visualização de campos
    FieldVisualizer,
    # Diagramas de radiação
    RadiationPatternPlot,
    # Animações
    FieldAnimator,
    # Funções auxiliares
    plot_s_parameters, plot_impedance
)

__all__ = [
    'GeometryVisualizer',
    'FieldVisualizer',
    'RadiationPatternPlot',
    'FieldAnimator',
    'plot_s_parameters',
    'plot_impedance'
]
