"""
Pacote de Geometria para Antenas
Exporta as classes principais de primitivas, topologia e fábrica.
"""

from .primitives import (
    Vector3D, BoundingBox, GeometryPrimitive, 
    Wire, Rectangle, Cylinder, Helix, Horn, ParabolicDish
)
from .topology import AntennaNode, AntennaEdge, AntennaGraph
from .factory import AntennaFactory
