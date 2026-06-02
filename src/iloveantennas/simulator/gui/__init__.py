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
    AntennaConfig,
    AntennaPropertiesPanel,
    AntennaType,
    FieldCanvas,
    GeometryCanvas,
    MainWindow,
    RadiationCanvas,
    ResultsPanel,
    SimulationConfig,
    SimulationPanel,
    main,
)

__all__ = [
    "MainWindow",
    "GeometryCanvas",
    "FieldCanvas",
    "RadiationCanvas",
    "AntennaPropertiesPanel",
    "SimulationPanel",
    "ResultsPanel",
    "AntennaType",
    "SimulationConfig",
    "AntennaConfig",
    "main",
]
