from __future__ import annotations

import re
import os
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CommandStatus:
    command: list[str]
    available: bool
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class WindowsGpuInfo:
    available: bool
    gpus: list[dict[str, Any]] = field(default_factory=list)
    command: CommandStatus | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class WslInfo:
    available: bool
    distributions: list[dict[str, Any]] = field(default_factory=list)
    command: CommandStatus | None = None
    cuda_probe: CommandStatus | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AccelerationStatus:
    selected_backend: str
    numba_available: bool
    numba_version: str | None
    numba_cuda_available: bool
    cupy_available: bool
    torch_cuda_available: bool
    solver_backends: dict[str, str]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class EngineRuntimeStatus:
    windows_gpu: WindowsGpuInfo
    wsl: WslInfo
    acceleration: AccelerationStatus

    def to_dict(self) -> dict:
        return asdict(self)


def _clean_text(value: str) -> str:
    return value.replace("\x00", "").strip()


def _run_command(args: list[str], timeout: float = 4.0) -> CommandStatus:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return CommandStatus(
            command=args,
            available=completed.returncode == 0,
            returncode=completed.returncode,
            stdout=_clean_text(completed.stdout),
            stderr=_clean_text(completed.stderr),
        )
    except FileNotFoundError as exc:
        return CommandStatus(command=args, available=False, error=str(exc))
    except subprocess.TimeoutExpired as exc:
        return CommandStatus(
            command=args,
            available=False,
            stdout=_clean_text(exc.stdout or ""),
            stderr=_clean_text(exc.stderr or ""),
            error=f"timeout after {timeout:.1f}s",
        )


def detect_windows_gpu() -> WindowsGpuInfo:
    command = _run_command(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        timeout=4.0,
    )

    gpus: list[dict[str, Any]] = []
    if command.available and command.stdout:
        for line in command.stdout.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 4:
                continue
            memory_mb = _parse_float(parts[2])
            utilization = _parse_float(parts[3])
            gpus.append(
                {
                    "name": parts[0],
                    "driver_version": parts[1],
                    "memory_total_mb": memory_mb,
                    "utilization_gpu_percent": utilization,
                }
            )

    return WindowsGpuInfo(available=bool(gpus), gpus=gpus, command=command)


def detect_wsl() -> WslInfo:
    command = _run_command(["wsl", "-l", "-v"], timeout=4.0)
    distributions: list[dict[str, Any]] = []

    if command.available and command.stdout:
        for raw_line in command.stdout.splitlines():
            line = raw_line.strip()
            if not line or line.lower().startswith("name"):
                continue
            match = re.match(r"^(\*)?\s*(.+?)\s{2,}(\S+)\s+(\d+)$", line)
            if not match:
                continue
            distributions.append(
                {
                    "default": bool(match.group(1)),
                    "name": match.group(2).strip(),
                    "state": match.group(3),
                    "version": int(match.group(4)),
                }
            )

    cuda_probe = None
    if distributions:
        cuda_probe = _run_command(["wsl", "nvidia-smi"], timeout=5.0)

    return WslInfo(
        available=command.available and bool(distributions),
        distributions=distributions,
        command=command,
        cuda_probe=cuda_probe,
    )


def detect_acceleration() -> AccelerationStatus:
    notes: list[str] = []
    numba_available = False
    numba_version = None
    numba_cuda_available = False
    cupy_available = False
    torch_cuda_available = False

    try:
        import numba  # type: ignore

        numba_available = True
        numba_version = getattr(numba, "__version__", None)
        try:
            from numba import cuda  # type: ignore

            numba_cuda_available = bool(cuda.is_available())
        except Exception as exc:
            notes.append(f"Numba CUDA probe failed: {exc}")
    except Exception:
        notes.append("Numba is not available; FDTD falls back to NumPy CPU kernels.")

    try:
        import cupy  # noqa: F401  # type: ignore

        cupy_available = True
    except Exception:
        cupy_available = False

    try:
        import torch  # type: ignore

        torch_cuda_available = bool(torch.cuda.is_available())
    except Exception:
        torch_cuda_available = False

    requested_fdtd_backend = os.getenv("ILOVEANTENNAS_FDTD_BACKEND", "auto").strip().lower()
    if requested_fdtd_backend == "cuda" and numba_cuda_available:
        selected_backend = "cuda"
    else:
        selected_backend = "numba-cpu" if numba_available else "numpy-cpu"
    notes.append(
        "FDTD supports an optional Numba CUDA backend when requested with solver_backend='cuda' "
        "or ILOVEANTENNAS_FDTD_BACKEND=cuda; otherwise it uses CPU kernels."
    )
    if requested_fdtd_backend == "cuda" and not numba_cuda_available:
        notes.append("CUDA was requested by environment, but Numba CUDA is not available.")

    return AccelerationStatus(
        selected_backend=selected_backend,
        numba_available=numba_available,
        numba_version=numba_version,
        numba_cuda_available=numba_cuda_available,
        cupy_available=cupy_available,
        torch_cuda_available=torch_cuda_available,
        solver_backends={
            "fdtd": "cuda-optional,numba-cpu,numpy-cpu",
            "fdtd_default": selected_backend,
            "fem": "gmsh/scipy-cpu",
            "propagation": "analytical-cpu",
            "ray_tracing": "geometric-cpu",
            "rendering": "browser-webgl-gpu",
        },
        notes=notes,
    )


def get_runtime_status() -> dict:
    return EngineRuntimeStatus(
        windows_gpu=detect_windows_gpu(),
        wsl=detect_wsl(),
        acceleration=detect_acceleration(),
    ).to_dict()


def _parse_float(value: str) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    if not match:
        return None
    return float(match.group(0))
