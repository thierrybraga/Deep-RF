from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from iloveantennas.simulator.engine import normalize_fdtd_backend
from iloveantennas.simulator.propagation import (
    Point2D,
    PropagationEnvironment,
    Segment2D,
)
from iloveantennas.web.config import AntennaConfig, SimulationConfig
from iloveantennas.web.matching import NetworkType


class UserAntennaModel(BaseModel):
    id: Optional[str] = None
    name: str
    brand: str = "Custom"
    technology: str = "General"
    config: dict


class AntennaPayload(BaseModel):
    type: str = "dipole"
    frequency: float = 300e6
    length: Optional[float] = None
    radius: float = 0.001
    num_directors: int = 3
    substrate_er: float = 4.4
    substrate_h: float = 1.6e-3
    turns: int = 5
    aperture_width: Optional[float] = None
    aperture_height: Optional[float] = None
    flare_length: Optional[float] = None
    dish_diameter: Optional[float] = None
    focal_length: Optional[float] = None
    tau: float = 0.86
    sigma: float = 0.15
    loop_radius: Optional[float] = None
    side_length: Optional[float] = None
    reflector_distance: Optional[float] = None
    disc_radius: Optional[float] = None
    cone_radius: Optional[float] = None
    cone_height: Optional[float] = None


class AntennaCreateRequest(AntennaPayload):
    pass


class SimulationStartRequest(AntennaPayload):
    antenna_type: str = "dipole"
    cells_per_wavelength: int = 15
    num_steps: int = 200
    pml_layers: int = 8
    courant: float = 0.99
    source_type: str = "gaussian"
    source_amplitude: float = 1.0
    use_optimized: bool = True
    solver_backend: str = "auto"
    method: str = "fdtd"


class SmithChartRequest(AntennaPayload):
    mode: str = "analytical"


class RadiationPatternRequest(AntennaPayload):
    mode: str = "analytical"


class CalculateParametersRequest(BaseModel):
    frequency: float = 300e6
    directivity_db: float | None = None


class OptimizeRequest(BaseModel):
    antenna_type: str = "dipole"
    target_freq: float = 300e6
    start_length: Optional[float] = None
    radius: float = 0.001
    target_vswr: float = 1.5
    max_iter: int = 5


class MatchingRequest(BaseModel):
    z_load_re: float
    z_load_im: float
    z0: float = 50.0
    frequency: float
    network_type: NetworkType = "L"
    q: float | None = None


class PropagationRequest(BaseModel):
    frequency: float = 900e6
    distance_km: float = 2.0
    tx_height_m: float = 30.0
    rx_height_m: float = 1.5
    city_size: str = "small_medium"
    area: str = "urban"
    system_loss_db: float = 0.0
    tx_power_dbm: float = 30.0
    tx_gain_dbi: float = 0.0
    rx_gain_dbi: float = 0.0
    receiver_sensitivity_dbm: Optional[float] = None


class Point2DRequest(BaseModel):
    x: float
    y: float


class Segment2DRequest(BaseModel):
    start: Point2DRequest
    end: Point2DRequest
    material: str = "reflector"
    reflection_loss_db: float = 6.0


class RayTraceRequest(BaseModel):
    frequency: float = 900e6
    tx: Point2DRequest
    rx: Point2DRequest
    obstacles: list[Segment2DRequest] = Field(default_factory=list)
    max_reflections: int = 1


def optional_float(value: Optional[float]) -> Optional[float]:
    return float(value) if value is not None else None


def antenna_config_from_payload(payload, *, type_field: str = "type") -> AntennaConfig:
    antenna_type = getattr(payload, type_field, getattr(payload, "type", "dipole"))
    return AntennaConfig(
        type=antenna_type,
        frequency=float(payload.frequency),
        length=optional_float(payload.length),
        radius=float(payload.radius),
        num_directors=int(payload.num_directors),
        substrate_er=float(payload.substrate_er),
        substrate_h=float(payload.substrate_h),
        turns=int(payload.turns),
        aperture_width=optional_float(payload.aperture_width),
        aperture_height=optional_float(payload.aperture_height),
        flare_length=optional_float(payload.flare_length),
        dish_diameter=optional_float(payload.dish_diameter),
        focal_length=optional_float(payload.focal_length),
        tau=float(payload.tau),
        sigma=float(payload.sigma),
        loop_radius=optional_float(payload.loop_radius),
        side_length=optional_float(payload.side_length),
        reflector_distance=optional_float(payload.reflector_distance),
        disc_radius=optional_float(payload.disc_radius),
        cone_radius=optional_float(payload.cone_radius),
        cone_height=optional_float(payload.cone_height),
    )


def simulation_config_from_payload(
    payload: SimulationStartRequest,
    *,
    method: str | None = None,
    num_steps: int | None = None,
) -> SimulationConfig:
    return SimulationConfig(
        cells_per_wavelength=int(payload.cells_per_wavelength),
        num_steps=int(num_steps if num_steps is not None else payload.num_steps),
        pml_layers=int(payload.pml_layers),
        courant=float(payload.courant),
        source_type=payload.source_type,
        source_amplitude=float(payload.source_amplitude),
        use_optimized=bool(payload.use_optimized),
        solver_backend=normalize_fdtd_backend(payload.solver_backend),
        method=method or payload.method,
    )


def propagation_environment_from_payload(payload: PropagationRequest) -> PropagationEnvironment:
    return PropagationEnvironment(
        frequency_hz=float(payload.frequency),
        distance_km=float(payload.distance_km),
        tx_height_m=float(payload.tx_height_m),
        rx_height_m=float(payload.rx_height_m),
        city_size=payload.city_size,
        area=payload.area,
        system_loss_db=float(payload.system_loss_db),
    )


def ray_trace_inputs_from_payload(payload: RayTraceRequest) -> tuple[Point2D, Point2D, list[Segment2D]]:
    tx = Point2D(float(payload.tx.x), float(payload.tx.y))
    rx = Point2D(float(payload.rx.x), float(payload.rx.y))
    obstacles = [
        Segment2D(
            start=Point2D(float(item.start.x), float(item.start.y)),
            end=Point2D(float(item.end.x), float(item.end.y)),
            material=item.material,
            reflection_loss_db=float(item.reflection_loss_db),
        )
        for item in payload.obstacles
    ]
    return tx, rx, obstacles


def model_dump(model: BaseModel) -> dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()
