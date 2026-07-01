from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

from iloveantennas.simulator.core.constants import C0
from iloveantennas.simulator.propagation.models import free_space_path_loss_db


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Segment2D:
    start: Point2D
    end: Point2D
    material: str = "reflector"
    reflection_loss_db: float = 6.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RayPath:
    points: list[Point2D]
    distance_m: float
    delay_ns: float
    path_loss_db: float
    reflection_count: int
    interactions: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["points"] = [point.to_dict() for point in self.points]
        return data


def trace_2d_rays(
    tx: Point2D,
    rx: Point2D,
    obstacles: list[Segment2D],
    frequency_hz: float,
    max_reflections: int = 1,
) -> list[RayPath]:
    """Trace direct and first-order reflected 2D geometric paths."""

    paths = [_build_path([tx, rx], frequency_hz, reflection_losses=[])]

    if max_reflections < 1:
        return paths

    for index, segment in enumerate(obstacles):
        mirrored_rx = _reflect_point_across_line(rx, segment.start, segment.end)
        hit = _segment_intersection(tx, mirrored_rx, segment.start, segment.end)
        if hit is None:
            continue

        if _distance(tx, hit) <= 1e-9 or _distance(hit, rx) <= 1e-9:
            continue

        path = _build_path(
            [tx, hit, rx],
            frequency_hz,
            reflection_losses=[segment.reflection_loss_db],
            interactions=[
                {
                    "type": "reflection",
                    "obstacle_index": index,
                    "material": segment.material,
                    "point": hit.to_dict(),
                    "loss_db": segment.reflection_loss_db,
                }
            ],
        )
        paths.append(path)

    paths.sort(key=lambda item: (item.reflection_count, item.path_loss_db, item.distance_m))
    return paths


def _build_path(
    points: list[Point2D],
    frequency_hz: float,
    reflection_losses: list[float],
    interactions: list[dict] | None = None,
) -> RayPath:
    distance = sum(_distance(a, b) for a, b in zip(points, points[1:]))
    path_loss = free_space_path_loss_db(frequency_hz, max(distance, 1e-6)) + sum(
        reflection_losses
    )
    return RayPath(
        points=points,
        distance_m=distance,
        delay_ns=distance / C0 * 1e9,
        path_loss_db=path_loss,
        reflection_count=len(reflection_losses),
        interactions=interactions or [],
    )


def _distance(a: Point2D, b: Point2D) -> float:
    return math.hypot(b.x - a.x, b.y - a.y)


def _reflect_point_across_line(point: Point2D, a: Point2D, b: Point2D) -> Point2D:
    dx = b.x - a.x
    dy = b.y - a.y
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-18:
        return point

    t = ((point.x - a.x) * dx + (point.y - a.y) * dy) / length_sq
    proj = Point2D(a.x + t * dx, a.y + t * dy)
    return Point2D(2.0 * proj.x - point.x, 2.0 * proj.y - point.y)


def _segment_intersection(
    p1: Point2D,
    p2: Point2D,
    q1: Point2D,
    q2: Point2D,
) -> Point2D | None:
    rx = p2.x - p1.x
    ry = p2.y - p1.y
    sx = q2.x - q1.x
    sy = q2.y - q1.y
    denom = rx * sy - ry * sx
    if abs(denom) <= 1e-12:
        return None

    qpx = q1.x - p1.x
    qpy = q1.y - p1.y
    t = (qpx * sy - qpy * sx) / denom
    u = (qpx * ry - qpy * rx) / denom

    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return Point2D(p1.x + t * rx, p1.y + t * ry)
    return None
