"""
IloveAntenas GUI Module
=====================
Interface gráfica para o simulador de antenas.

Contém:
- MainWindow: Janela principal
- Canvas de visualização 3D
- Painéis de propriedades
"""

from .main_window import (
    MainWindow,
    GeometryCanvas,
    FieldCanvas,
    RadiationCanvas,
    AntennaPropertiesPanel,
    SimulationPanel,
    ResultsPanel,
    AntennaType,
    SimulationConfig,
    AntennaConfig,
    main
)

__all__ = [
    'MainWindow',
    'GeometryCanvas',
    'FieldCanvas',
    'RadiationCanvas',
    'AntennaPropertiesPanel',
    'SimulationPanel',
    'ResultsPanel',
    'AntennaType',
    'SimulationConfig',
    'AntennaConfig',
    'main'
]
