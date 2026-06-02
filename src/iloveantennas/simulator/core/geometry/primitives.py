"""
Módulo de Primitivas Geométricas
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from ..constants import Material, MaterialLibrary

# =============================================================================
# TIPOS BÁSICOS
# =============================================================================


@dataclass
class Vector3D:
    """Vetor 3D com operações básicas"""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __array__(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])

    def __add__(self, other: "Vector3D") -> "Vector3D":
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vector3D") -> "Vector3D":
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vector3D":
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> "Vector3D":
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> "Vector3D":
        return Vector3D(self.x / scalar, self.y / scalar, self.z / scalar)

    @property
    def magnitude(self) -> float:
        return np.sqrt(self.x**2 + self.y**2 + self.z**2)

    @property
    def normalized(self) -> "Vector3D":
        mag = self.magnitude
        if mag == 0:
            return Vector3D(0, 0, 0)
        return self / mag

    def dot(self, other: "Vector3D") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vector3D") -> "Vector3D":
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def rotate_around_axis(self, axis: "Vector3D", angle: float) -> "Vector3D":
        """Rotação usando fórmula de Rodrigues"""
        k = axis.normalized
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)

        return self * cos_a + k.cross(self) * sin_a + k * k.dot(self) * (1 - cos_a)


@dataclass
class BoundingBox:
    """Caixa delimitadora 3D"""

    min_point: Vector3D
    max_point: Vector3D

    @property
    def size(self) -> Vector3D:
        return self.max_point - self.min_point

    @property
    def center(self) -> Vector3D:
        return (self.min_point + self.max_point) / 2

    @property
    def volume(self) -> float:
        s = self.size
        return s.x * s.y * s.z

    def contains(self, point: Vector3D) -> bool:
        return (
            self.min_point.x <= point.x <= self.max_point.x
            and self.min_point.y <= point.y <= self.max_point.y
            and self.min_point.z <= point.z <= self.max_point.z
        )

    def intersects(self, other: "BoundingBox") -> bool:
        return (
            self.min_point.x <= other.max_point.x
            and self.max_point.x >= other.min_point.x
            and self.min_point.y <= other.max_point.y
            and self.max_point.y >= other.min_point.y
            and self.min_point.z <= other.max_point.z
            and self.max_point.z >= other.min_point.z
        )

    def expand(self, amount: float) -> "BoundingBox":
        """Expande a bounding box uniformemente"""
        return BoundingBox(
            self.min_point - Vector3D(amount, amount, amount),
            self.max_point + Vector3D(amount, amount, amount),
        )

    @staticmethod
    def union(boxes: List["BoundingBox"]) -> "BoundingBox":
        """Cria bounding box que engloba todas as outras"""
        if not boxes:
            return BoundingBox(Vector3D(), Vector3D())

        min_x = min(b.min_point.x for b in boxes)
        min_y = min(b.min_point.y for b in boxes)
        min_z = min(b.min_point.z for b in boxes)
        max_x = max(b.max_point.x for b in boxes)
        max_y = max(b.max_point.y for b in boxes)
        max_z = max(b.max_point.z for b in boxes)

        return BoundingBox(Vector3D(min_x, min_y, min_z), Vector3D(max_x, max_y, max_z))

    def to_dict(self) -> dict:
        return {
            "min": self.min_point.to_tuple(),
            "max": self.max_point.to_tuple(),
            "center": self.center.to_tuple(),
            "size": self.size.to_tuple(),
        }


# =============================================================================
# PRIMITIVAS GEOMÉTRICAS
# =============================================================================


class GeometryPrimitive(ABC):
    """Classe base abstrata para primitivas geométricas"""

    def __init__(self, name: str = "", material: Material = None):
        self.name = name
        self.material = material or MaterialLibrary.PEC
        self.id = id(self)

    @abstractmethod
    def get_bounding_box(self) -> BoundingBox:
        """Retorna bounding box da geometria"""
        pass

    @abstractmethod
    def contains_point(self, point: Vector3D) -> bool:
        """Verifica se ponto está dentro da geometria"""
        pass

    @abstractmethod
    def sample_surface(self, resolution: float) -> List[Vector3D]:
        """Amostra pontos na superfície para discretização"""
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        """Serializa para dicionário"""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "GeometryPrimitive":
        """Deserializa de dicionário"""
        pass


@dataclass
class Wire(GeometryPrimitive):
    """
    Fio condutor (cilindro fino).

    Attributes:
        start: Ponto inicial
        end: Ponto final
        radius: Raio do fio [m]
        segments: Número de segmentos para discretização
    """

    start: Vector3D = field(default_factory=Vector3D)
    end: Vector3D = field(default_factory=Vector3D)
    radius: float = 0.001  # 1mm padrão
    segments: int = 1

    def __post_init__(self):
        super().__init__()

    @property
    def length(self) -> float:
        return (self.end - self.start).magnitude

    @property
    def direction(self) -> Vector3D:
        return (self.end - self.start).normalized

    @property
    def center(self) -> Vector3D:
        return (self.start + self.end) / 2

    def get_bounding_box(self) -> BoundingBox:
        r = self.radius
        return BoundingBox(
            Vector3D(
                min(self.start.x, self.end.x) - r,
                min(self.start.y, self.end.y) - r,
                min(self.start.z, self.end.z) - r,
            ),
            Vector3D(
                max(self.start.x, self.end.x) + r,
                max(self.start.y, self.end.y) + r,
                max(self.start.z, self.end.z) + r,
            ),
        )

    def contains_point(self, point: Vector3D) -> bool:
        """Verifica se ponto está dentro do cilindro do fio"""
        # Vetor do início ao ponto
        ap = point - self.start
        ab = self.end - self.start

        # Projeção do ponto na linha
        t = ap.dot(ab) / ab.dot(ab)

        if t < 0 or t > 1:
            return False

        # Ponto mais próximo na linha
        closest = self.start + ab * t
        distance = (point - closest).magnitude

        return distance <= self.radius

    def sample_surface(self, resolution: float) -> List[Vector3D]:
        """Amostra pontos ao longo do fio"""
        points = []
        num_points = max(2, int(self.length / resolution) + 1)

        for i in range(num_points):
            t = i / (num_points - 1)
            point = self.start + (self.end - self.start) * t
            points.append(point)

        return points

    def get_segment_endpoints(self) -> List[Tuple[Vector3D, Vector3D]]:
        """Retorna lista de segmentos (início, fim)"""
        if self.segments <= 1:
            return [(self.start, self.end)]

        segments = []
        for i in range(self.segments):
            t1 = i / self.segments
            t2 = (i + 1) / self.segments
            p1 = self.start + (self.end - self.start) * t1
            p2 = self.start + (self.end - self.start) * t2
            segments.append((p1, p2))

        return segments

    def to_dict(self) -> dict:
        return {
            "type": "wire",
            "name": self.name,
            "start": self.start.to_tuple(),
            "end": self.end.to_tuple(),
            "radius": self.radius,
            "segments": self.segments,
            "material": self.material.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Wire":
        wire = cls(
            start=Vector3D(*data["start"]),
            end=Vector3D(*data["end"]),
            radius=data.get("radius", 0.001),
            segments=data.get("segments", 1),
        )
        wire.name = data.get("name", "")
        return wire


@dataclass
class Rectangle(GeometryPrimitive):
    """
    Retângulo planar (patch).

    Attributes:
        center: Centro do retângulo
        width: Largura (direção x)
        height: Altura (direção y)
        thickness: Espessura (direção z)
        normal: Normal da superfície
    """

    center: Vector3D = field(default_factory=Vector3D)
    width: float = 0.01  # 10mm
    height: float = 0.01
    thickness: float = 0.001
    normal: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))

    def __post_init__(self):
        super().__init__()

    @property
    def area(self) -> float:
        return self.width * self.height

    def get_bounding_box(self) -> BoundingBox:
        # Simplificado para orientação padrão (normal em z)
        hw, hh, ht = self.width / 2, self.height / 2, self.thickness / 2
        return BoundingBox(
            Vector3D(self.center.x - hw, self.center.y - hh, self.center.z - ht),
            Vector3D(self.center.x + hw, self.center.y + hh, self.center.z + ht),
        )

    def contains_point(self, point: Vector3D) -> bool:
        hw, hh, ht = self.width / 2, self.height / 2, self.thickness / 2
        return (
            abs(point.x - self.center.x) <= hw
            and abs(point.y - self.center.y) <= hh
            and abs(point.z - self.center.z) <= ht
        )

    def sample_surface(self, resolution: float) -> List[Vector3D]:
        points = []
        nx = max(2, int(self.width / resolution) + 1)
        ny = max(2, int(self.height / resolution) + 1)

        for i in range(nx):
            for j in range(ny):
                x = self.center.x - self.width / 2 + i * self.width / (nx - 1)
                y = self.center.y - self.height / 2 + j * self.height / (ny - 1)
                z = self.center.z
                points.append(Vector3D(x, y, z))

        return points

    def get_corners(self) -> List[Vector3D]:
        """Retorna os 4 cantos do retângulo"""
        hw, hh = self.width / 2, self.height / 2
        c = self.center
        return [
            Vector3D(c.x - hw, c.y - hh, c.z),
            Vector3D(c.x + hw, c.y - hh, c.z),
            Vector3D(c.x + hw, c.y + hh, c.z),
            Vector3D(c.x - hw, c.y + hh, c.z),
        ]

    def to_dict(self) -> dict:
        return {
            "type": "rectangle",
            "name": self.name,
            "center": self.center.to_tuple(),
            "width": self.width,
            "height": self.height,
            "thickness": self.thickness,
            "normal": self.normal.to_tuple(),
            "material": self.material.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Rectangle":
        rect = cls(
            center=Vector3D(*data["center"]),
            width=data["width"],
            height=data["height"],
            thickness=data.get("thickness", 0.001),
            normal=Vector3D(*data.get("normal", (0, 0, 1))),
        )
        rect.name = data.get("name", "")
        return rect


@dataclass
class Cylinder(GeometryPrimitive):
    """
    Cilindro sólido.

    Attributes:
        center: Centro do cilindro
        radius: Raio
        height: Altura
        axis: Direção do eixo
    """

    center: Vector3D = field(default_factory=Vector3D)
    radius: float = 0.01
    height: float = 0.02
    axis: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))

    def __post_init__(self):
        super().__init__()

    @property
    def volume(self) -> float:
        return np.pi * self.radius**2 * self.height

    def get_bounding_box(self) -> BoundingBox:
        r = self.radius
        h = self.height / 2
        return BoundingBox(
            Vector3D(self.center.x - r, self.center.y - r, self.center.z - h),
            Vector3D(self.center.x + r, self.center.y + r, self.center.z + h),
        )

    def contains_point(self, point: Vector3D) -> bool:
        # Distância radial
        dx = point.x - self.center.x
        dy = point.y - self.center.y
        radial_dist = np.sqrt(dx**2 + dy**2)

        # Distância axial
        dz = abs(point.z - self.center.z)

        return radial_dist <= self.radius and dz <= self.height / 2

    def sample_surface(self, resolution: float) -> List[Vector3D]:
        points = []
        # Amostra a superfície lateral
        n_theta = max(8, int(2 * np.pi * self.radius / resolution))
        n_z = max(2, int(self.height / resolution) + 1)

        for i in range(n_theta):
            theta = 2 * np.pi * i / n_theta
            for j in range(n_z):
                z = self.center.z - self.height / 2 + j * self.height / (n_z - 1)
                x = self.center.x + self.radius * np.cos(theta)
                y = self.center.y + self.radius * np.sin(theta)
                points.append(Vector3D(x, y, z))

        return points

    def to_dict(self) -> dict:
        return {
            "type": "cylinder",
            "name": self.name,
            "center": self.center.to_tuple(),
            "radius": self.radius,
            "height": self.height,
            "axis": self.axis.to_tuple(),
            "material": self.material.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Cylinder":
        cyl = cls(
            center=Vector3D(*data["center"]),
            radius=data["radius"],
            height=data["height"],
            axis=Vector3D(*data.get("axis", (0, 0, 1))),
        )
        cyl.name = data.get("name", "")
        return cyl


@dataclass
class Helix(GeometryPrimitive):
    """
    Hélice (antena helicoidal).

    Attributes:
        center: Centro da base
        radius: Raio da hélice
        pitch: Passo (distância entre espiras)
        turns: Número de voltas
        wire_radius: Raio do fio
        direction: 1 para mão direita, -1 para mão esquerda
    """

    center: Vector3D = field(default_factory=Vector3D)
    radius: float = 0.01
    pitch: float = 0.01
    turns: float = 5.0
    wire_radius: float = 0.001
    direction: int = 1  # 1: right-hand, -1: left-hand

    def __post_init__(self):
        super().__init__()

    @property
    def total_height(self) -> float:
        return self.pitch * self.turns

    @property
    def total_length(self) -> float:
        """Comprimento total do fio"""
        circumference = 2 * np.pi * self.radius
        length_per_turn = np.sqrt(circumference**2 + self.pitch**2)
        return length_per_turn * self.turns

    def get_bounding_box(self) -> BoundingBox:
        r = self.radius + self.wire_radius
        h = self.total_height
        return BoundingBox(
            Vector3D(self.center.x - r, self.center.y - r, self.center.z),
            Vector3D(self.center.x + r, self.center.y + r, self.center.z + h),
        )

    def contains_point(self, point: Vector3D) -> bool:
        # Aproximação: verifica distância ao caminho da hélice
        min_dist = float("inf")

        for p in self.sample_surface(self.wire_radius):
            dist = (point - p).magnitude
            min_dist = min(min_dist, dist)

        return min_dist <= self.wire_radius

    def sample_surface(self, resolution: float) -> List[Vector3D]:
        """Gera pontos ao longo da hélice"""
        points = []
        total_angle = 2 * np.pi * self.turns
        num_points = max(int(self.total_length / resolution), int(36 * self.turns))

        for i in range(num_points + 1):
            t = i / num_points
            theta = total_angle * t * self.direction
            z = self.pitch * self.turns * t

            x = self.center.x + self.radius * np.cos(theta)
            y = self.center.y + self.radius * np.sin(theta)

            points.append(Vector3D(x, y, self.center.z + z))

        return points

    def to_dict(self) -> dict:
        return {
            "type": "Helix",
            "name": self.name,
            "center": self.center.to_tuple(),
            "radius": self.radius,
            "pitch": self.pitch,
            "turns": self.turns,
            "wire_radius": self.wire_radius,
            "direction": self.direction,
            "material": self.material.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Helix":
        helix = cls(
            center=Vector3D(*data["center"]),
            radius=data["radius"],
            pitch=data["pitch"],
            turns=data["turns"],
            wire_radius=data.get("wire_radius", 0.001),
            direction=data.get("direction", 1),
        )
        helix.name = data.get("name", "")
        return helix


@dataclass
class Horn(GeometryPrimitive):
    """
    Antena Corneta (Pyramidal Horn).

    Attributes:
        center: Centro da base (throat)
        aperture_width: Largura da abertura (eixo x)
        aperture_height: Altura da abertura (eixo y)
        throat_width: Largura da garganta (feed)
        throat_height: Altura da garganta (feed)
        length: Comprimento axial (eixo z)
        wall_thickness: Espessura da parede
    """

    center: Vector3D = field(default_factory=Vector3D)
    aperture_width: float = 0.1
    aperture_height: float = 0.08
    throat_width: float = 0.02
    throat_height: float = 0.01
    length: float = 0.15
    wall_thickness: float = 0.001

    def __post_init__(self):
        super().__init__()

    def get_bounding_box(self) -> BoundingBox:
        max_w = max(self.aperture_width, self.throat_width)
        max_h = max(self.aperture_height, self.throat_height)
        return BoundingBox(
            Vector3D(self.center.x - max_w / 2, self.center.y - max_h / 2, self.center.z),
            Vector3D(
                self.center.x + max_w / 2, self.center.y + max_h / 2, self.center.z + self.length
            ),
        )

    def contains_point(self, point: Vector3D) -> bool:
        # Verifica se está dentro da bounding box primeiro
        if not self.get_bounding_box().contains(point):
            return False

        # Posição relativa em Z (0 a 1)
        dz = point.z - self.center.z
        if dz < 0 or dz > self.length:
            return False

        t = dz / self.length

        # Dimensões na altura z
        curr_w = self.throat_width + (self.aperture_width - self.throat_width) * t
        curr_h = self.throat_height + (self.aperture_height - self.throat_height) * t

        # Verifica se está "dentro" das paredes (casca)
        # Simplificação: verifica se está próximo da superfície
        # Idealmente deveria ser uma verificação volumétrica da casca

        in_outer = (
            abs(point.x - self.center.x) <= curr_w / 2 + self.wall_thickness
            and abs(point.y - self.center.y) <= curr_h / 2 + self.wall_thickness
        )

        in_inner = (
            abs(point.x - self.center.x) <= curr_w / 2 - self.wall_thickness
            and abs(point.y - self.center.y) <= curr_h / 2 - self.wall_thickness
        )

        return in_outer and not in_inner

    def sample_surface(self, resolution: float) -> List[Vector3D]:
        points = []
        # Amostra as 4 faces laterais
        n_z = max(2, int(self.length / resolution) + 1)

        for k in range(n_z):
            t = k / (n_z - 1)
            z = self.center.z + self.length * t
            w = self.throat_width + (self.aperture_width - self.throat_width) * t
            h = self.throat_height + (self.aperture_height - self.throat_height) * t

            # Perímetro retangular na altura z
            n_w = max(2, int(w / resolution) + 1)
            n_h = max(2, int(h / resolution) + 1)

            # Paredes superior e inferior
            for i in range(n_w):
                x = self.center.x - w / 2 + w * i / (n_w - 1)
                points.append(Vector3D(x, self.center.y + h / 2, z))
                points.append(Vector3D(x, self.center.y - h / 2, z))

            # Paredes laterais
            for j in range(n_h):
                y = self.center.y - h / 2 + h * j / (n_h - 1)
                points.append(Vector3D(self.center.x + w / 2, y, z))
                points.append(Vector3D(self.center.x - w / 2, y, z))

        return points

    def to_dict(self) -> dict:
        return {
            "type": "Horn",
            "name": self.name,
            "center": self.center.to_tuple(),
            "aperture_width": self.aperture_width,
            "aperture_height": self.aperture_height,
            "throat_width": self.throat_width,
            "throat_height": self.throat_height,
            "length": self.length,
            "wall_thickness": self.wall_thickness,
            "material": self.material.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Horn":
        horn = cls(
            center=Vector3D(*data["center"]),
            aperture_width=data["aperture_width"],
            aperture_height=data["aperture_height"],
            throat_width=data.get("throat_width", data["aperture_width"] * 0.1),
            throat_height=data.get("throat_height", data["aperture_height"] * 0.1),
            length=data["length"],
            wall_thickness=data.get("wall_thickness", 0.001),
        )
        horn.name = data.get("name", "")
        return horn


@dataclass
class ParabolicDish(GeometryPrimitive):
    """
    Antena Parabólica (Refletor).

    Attributes:
        center: Centro do vértice (fundo do prato)
        diameter: Diâmetro da abertura
        focal_length: Distância focal
        axis: Eixo de apontamento
        thickness: Espessura do prato
    """

    center: Vector3D = field(default_factory=Vector3D)
    diameter: float = 1.0
    focal_length: float = 0.4
    axis: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))
    thickness: float = 0.002

    def __post_init__(self):
        super().__init__()

    @property
    def depth(self) -> float:
        return (self.diameter**2) / (16 * self.focal_length)

    def get_bounding_box(self) -> BoundingBox:
        r = self.diameter / 2
        d = self.depth
        # Assumindo eixo z por simplicidade no bounding box inicial
        return BoundingBox(
            Vector3D(self.center.x - r, self.center.y - r, self.center.z),
            Vector3D(self.center.x + r, self.center.y + r, self.center.z + d),
        )

    def contains_point(self, point: Vector3D) -> bool:
        # Simplificação: verifica proximidade da superfície
        # Equação: z = (x^2 + y^2) / 4f
        dx = point.x - self.center.x
        dy = point.y - self.center.y
        dz = point.z - self.center.z

        r2 = dx * dx + dy * dy
        target_z = r2 / (4 * self.focal_length)

        return abs(dz - target_z) <= self.thickness / 2 and r2 <= (self.diameter / 2) ** 2

    def sample_surface(self, resolution: float) -> List[Vector3D]:
        points = []
        r_max = self.diameter / 2
        n_r = max(2, int(r_max / resolution) + 1)

        for i in range(n_r):
            r = r_max * i / (n_r - 1)
            circumference = 2 * np.pi * r
            n_theta = max(4, int(circumference / resolution)) if r > 0 else 1

            z = (r**2) / (4 * self.focal_length)

            for j in range(n_theta):
                theta = 2 * np.pi * j / n_theta
                x = self.center.x + r * np.cos(theta)
                y = self.center.y + r * np.sin(theta)
                points.append(Vector3D(x, y, self.center.z + z))

        return points

    def to_dict(self) -> dict:
        return {
            "type": "dish",
            "name": self.name,
            "center": self.center.to_tuple(),
            "diameter": self.diameter,
            "focal_length": self.focal_length,
            "axis": self.axis.to_tuple(),
            "thickness": self.thickness,
            "material": self.material.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ParabolicDish":
        dish = cls(
            center=Vector3D(*data["center"]),
            diameter=data["diameter"],
            focal_length=data["focal_length"],
            axis=Vector3D(*data.get("axis", (0, 0, 1))),
            thickness=data.get("thickness", 0.002),
        )
        dish.name = data.get("name", "")
        return dish
