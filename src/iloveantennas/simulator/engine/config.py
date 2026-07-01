from __future__ import annotations

from dataclasses import asdict, dataclass

from iloveantennas.simulator.core.constants import C0


@dataclass(frozen=True)
class GridPolicy:
    """Numerical grid limits shared by simulation orchestrators."""

    min_x: int = 30
    min_y: int = 30
    min_z: int = 40
    max_x: int = 400
    max_y: int = 400
    max_z: int = 500
    margin_wavelengths: float = 1.0
    min_cells_per_wavelength: int = 6

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class FramePolicy:
    """Controls how much field data is recorded from long simulations."""

    target_frames: int = 100

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class GridPlan:
    wavelength: float
    dx: float
    margin: float
    nx: int
    ny: int
    nz: int
    requested_nx: int
    requested_ny: int
    requested_nz: int
    cells_per_wavelength: int
    clamped: bool
    policy: GridPolicy

    def to_dict(self) -> dict:
        data = asdict(self)
        data["policy"] = self.policy.to_dict()
        return data


FDTD_GRID_POLICY = GridPolicy()
FEM_GRID_POLICY = GridPolicy(max_x=100, max_y=100, max_z=100)
DEFAULT_FRAME_POLICY = FramePolicy()

FDTD_BACKENDS = ("auto", "cuda", "numba", "numpy")
FDTD_BACKEND_ALIASES = {
    "cpu": "numba",
    "numba-cpu": "numba",
    "numpy-cpu": "numpy",
    "gpu": "cuda",
    "cuda-gpu": "cuda",
}


def normalize_fdtd_backend(backend: str | None) -> str:
    value = (backend or "auto").strip().lower().replace("_", "-")
    return FDTD_BACKEND_ALIASES.get(value, value)


def _axis_size(size: float, margin: float, dx: float, minimum: int, maximum: int) -> tuple[int, int]:
    requested = max(minimum, int((float(size) + 2.0 * margin) / dx))
    return requested, min(requested, maximum)


def plan_grid_from_bbox(
    bbox,
    frequency_hz: float,
    cells_per_wavelength: int,
    policy: GridPolicy = FDTD_GRID_POLICY,
) -> GridPlan:
    """Create a bounded FDTD/FEM grid plan from antenna bounds and frequency."""

    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be positive")

    cells = max(int(cells_per_wavelength), policy.min_cells_per_wavelength)
    wavelength = C0 / float(frequency_hz)
    dx = wavelength / cells
    margin = wavelength * policy.margin_wavelengths

    requested_nx, nx = _axis_size(bbox.size.x, margin, dx, policy.min_x, policy.max_x)
    requested_ny, ny = _axis_size(bbox.size.y, margin, dx, policy.min_y, policy.max_y)
    requested_nz, nz = _axis_size(bbox.size.z, margin, dx, policy.min_z, policy.max_z)

    return GridPlan(
        wavelength=wavelength,
        dx=dx,
        margin=margin,
        nx=nx,
        ny=ny,
        nz=nz,
        requested_nx=requested_nx,
        requested_ny=requested_ny,
        requested_nz=requested_nz,
        cells_per_wavelength=cells,
        clamped=(nx != requested_nx or ny != requested_ny or nz != requested_nz),
        policy=policy,
    )


def frame_record_interval(num_steps: int, policy: FramePolicy = DEFAULT_FRAME_POLICY) -> int:
    if num_steps <= 0:
        return 1
    return max(1, int(num_steps) // max(1, int(policy.target_frames)))
