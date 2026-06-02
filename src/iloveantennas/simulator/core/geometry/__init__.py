"""
Pacote de Geometria para Antenas
Exporta as classes principais de primitivas, topologia e fábrica.
"""

from .factory import AntennaFactory
from .primitives import (
    BoundingBox,
    Cylinder,
    GeometryPrimitive,
    Helix,
    Horn,
    ParabolicDish,
    Rectangle,
    Vector3D,
    Wire,
)
from .topology import AntennaEdge, AntennaGraph, AntennaNode
