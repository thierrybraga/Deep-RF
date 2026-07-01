"""
Solver FDTD - Implementação das Equações de Maxwell

Este módulo implementa:
- Loop temporal FDTD
- Atualização de campos E e H
"""

import logging
import os
import time
from typing import Callable, List, Optional, Tuple

import numpy as np

from iloveantennas.simulator.core.grid import FDTDGrid
from iloveantennas.simulator.engine import normalize_fdtd_backend

from .cuda_kernels import CudaFDTDBackend
from .farfield import NearToFarField
from .kernels import update_e_kernel, update_h_kernel
from .monitors import FieldProbe, NearFieldBox
from .sources import Source

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# SOLVER FDTD
# =============================================================================


class FDTDSolver:
    """
    Solver FDTD para as equações de Maxwell.

    Implementa o algoritmo de Yee com:
    - Atualização leap-frog de E e H
    - Múltiplas fontes de excitação
    - Monitoramento de campos
    - Condições de contorno
    """

    def __init__(
        self,
        grid: FDTDGrid,
        use_numba: bool = True,
        backend: str = "auto",
        defer_host_sync: bool = False,
    ):
        """
        Inicializa o solver.

        Args:
            grid: Grade FDTD configurada
            use_numba: Se True, usa kernels otimizados CPU quando CUDA nao for usado
            backend: "auto", "cuda", "numba" ou "numpy"
            defer_host_sync: Se True, backend CUDA sincroniza host apenas quando solicitado
        """
        self.grid = grid
        self.sources: List[Source] = []
        self.probes: List[FieldProbe] = []
        self.nf_box: Optional[NearFieldBox] = None

        self.current_time = 0.0
        self.time_step = 0
        self.use_numba = use_numba
        self._cpu_fallback_use_numba = bool(use_numba)
        self.requested_backend = self._normalize_backend(backend)
        self.defer_host_sync = bool(defer_host_sync)
        self._cuda_backend: CudaFDTDBackend | None = None
        self.backend_warning: str | None = None
        self.backend_name = "numba-cpu" if use_numba else "numpy-cpu"
        self._host_fields_current = True
        self._configure_backend()

        # Estatísticas
        self.stats = {
            "max_E": 0.0,
            "max_H": 0.0,
            "total_energy": [],
            "computation_time": 0.0,
            "backend": self.backend_name,
        }

        # Callback para progresso
        self._progress_callback: Optional[Callable[[int, int, float], None]] = None

    @staticmethod
    def _normalize_backend(backend: str | None) -> str:
        return normalize_fdtd_backend(backend)

    def _configure_backend(self):
        env_backend = os.getenv("ILOVEANTENNAS_FDTD_BACKEND", "").strip()
        requested = self._normalize_backend(env_backend) if env_backend else self.requested_backend

        if requested == "auto":
            requested = "numba" if self.use_numba else "numpy"

        if requested == "numpy":
            self.use_numba = False
            self.backend_name = "numpy-cpu"
            return

        if requested == "numba":
            self.use_numba = bool(self.use_numba)
            self.backend_name = "numba-cpu" if self.use_numba else "numpy-cpu"
            return

        if requested == "cuda":
            try:
                self._cuda_backend = CudaFDTDBackend(self.grid)
                self.backend_name = "cuda"
                self._host_fields_current = True
                return
            except Exception as exc:
                self.backend_warning = f"CUDA backend unavailable, using CPU fallback: {exc}"
                logger.warning(self.backend_warning)
                self._cuda_backend = None
                self.backend_name = "numba-cpu" if self._cpu_fallback_use_numba else "numpy-cpu"
                return

        self.backend_warning = f"Unknown backend '{requested}', using CPU fallback."
        logger.warning(self.backend_warning)
        self.backend_name = "numba-cpu" if self._cpu_fallback_use_numba else "numpy-cpu"

    def _fallback_from_cuda(self, exc: Exception):
        self.backend_warning = f"CUDA backend failed during execution, using CPU fallback: {exc}"
        logger.warning(self.backend_warning)
        if self._cuda_backend is not None:
            try:
                self._cuda_backend.sync_to_host()
            except Exception as sync_exc:
                logger.warning("Could not sync CUDA fields before fallback: %s", sync_exc)
        self._cuda_backend = None
        self.backend_name = "numba-cpu" if self._cpu_fallback_use_numba else "numpy-cpu"
        self._host_fields_current = True
        self.stats["backend"] = self.backend_name
        self.stats["backend_warning"] = self.backend_warning

    @property
    def is_cuda_enabled(self) -> bool:
        return self._cuda_backend is not None

    def sync_fields_to_host(self, components: list[str] | tuple[str, ...] | None = None):
        """Synchronize CUDA device fields back to the CPU grid arrays."""
        if self._cuda_backend is None:
            return
        self._cuda_backend.sync_to_host(components)
        if components is None:
            self._host_fields_current = True

    def add_source(self, source: Source):
        """Adiciona fonte de excitação"""
        self.sources.append(source)

    def add_probe(self, probe: FieldProbe):
        """Adiciona monitor de campo"""
        self.probes.append(probe)

    def setup_near_field_box(self, margin: int = 5):
        """
        Configura caixa de near-field para transformação far-field.

        Args:
            margin: Margem em células a partir da PML
        """
        pml = self.grid.config.pml_layers

        self.nf_box = NearFieldBox(
            i_range=(pml + margin, self.grid.config.nx - pml - margin),
            j_range=(pml + margin, self.grid.config.ny - pml - margin),
            k_range=(pml + margin, self.grid.config.nz - pml - margin),
        )

    def set_progress_callback(self, callback: Callable[[int, int, float], None]):
        """Define callback para progresso: callback(step, total_steps, elapsed_time)"""
        self._progress_callback = callback

    def _update_H(self):
        """Atualiza campos magnéticos H"""
        if self._cuda_backend is not None:
            try:
                self._cuda_backend.update_h()
                self._host_fields_current = False
                return
            except Exception as exc:
                self._fallback_from_cuda(exc)

        if self.use_numba:
            update_h_kernel(
                self.grid.Hx,
                self.grid.Hy,
                self.grid.Hz,
                self.grid.Ex,
                self.grid.Ey,
                self.grid.Ez,
                self.grid._Da_x,
                self.grid._Db_x,
                self.grid._Da_y,
                self.grid._Db_y,
                self.grid._Da_z,
                self.grid._Db_z,
                self.grid.config.dx,
                self.grid.config.dy,
                self.grid.config.dz,
            )
        else:
            # Fallback para NumPy puro (se necessário, mas idealmente sempre usamos Numba)
            # Mantendo implementação NumPy para compatibilidade se Numba falhar ou for desativado
            dx, dy, dz = self.grid.config.dx, self.grid.config.dy, self.grid.config.dz

            # Hx
            self.grid.Hx[:, :, :] = self.grid._Da_x * self.grid.Hx - self.grid._Db_x * (
                (self.grid.Ez[:, 1:, :] - self.grid.Ez[:, :-1, :]) / dy
                - (self.grid.Ey[:, :, 1:] - self.grid.Ey[:, :, :-1]) / dz
            )
            # Hy
            self.grid.Hy[:, :, :] = self.grid._Da_y * self.grid.Hy - self.grid._Db_y * (
                (self.grid.Ex[:, :, 1:] - self.grid.Ex[:, :, :-1]) / dz
                - (self.grid.Ez[1:, :, :] - self.grid.Ez[:-1, :, :]) / dx
            )
            # Hz
            self.grid.Hz[:, :, :] = self.grid._Da_z * self.grid.Hz - self.grid._Db_z * (
                (self.grid.Ey[1:, :, :] - self.grid.Ey[:-1, :, :]) / dx
                - (self.grid.Ex[:, 1:, :] - self.grid.Ex[:, :-1, :]) / dy
            )

    def _update_E(self):
        """Atualiza campos elétricos E"""
        if self._cuda_backend is not None:
            try:
                self._cuda_backend.update_e()
                self._host_fields_current = False
                return
            except Exception as exc:
                self._fallback_from_cuda(exc)

        if self.use_numba:
            update_e_kernel(
                self.grid.Ex,
                self.grid.Ey,
                self.grid.Ez,
                self.grid.Hx,
                self.grid.Hy,
                self.grid.Hz,
                self.grid._Ca_x,
                self.grid._Cb_x,
                self.grid._Ca_y,
                self.grid._Cb_y,
                self.grid._Ca_z,
                self.grid._Cb_z,
                self.grid.config.dx,
                self.grid.config.dy,
                self.grid.config.dz,
            )
        else:
            dx, dy, dz = self.grid.config.dx, self.grid.config.dy, self.grid.config.dz

            # Ex (ignora bordas PEC implícitas nos loops Numba, aqui NumPy cuida do shape)
            # Nota: índices 1:-1 correspondem aos loops internos do Numba

            # Ex
            self.grid.Ex[:, 1:-1, 1:-1] = self.grid._Ca_x[:, 1:-1, 1:-1] * self.grid.Ex[
                :, 1:-1, 1:-1
            ] + self.grid._Cb_x[:, 1:-1, 1:-1] * (
                (self.grid.Hz[:, 1:, 1:-1] - self.grid.Hz[:, :-1, 1:-1]) / dy
                - (self.grid.Hy[:, 1:-1, 1:] - self.grid.Hy[:, 1:-1, :-1]) / dz
            )

            # Ey
            self.grid.Ey[1:-1, :, 1:-1] = self.grid._Ca_y[1:-1, :, 1:-1] * self.grid.Ey[
                1:-1, :, 1:-1
            ] + self.grid._Cb_y[1:-1, :, 1:-1] * (
                (self.grid.Hx[1:-1, :, 1:] - self.grid.Hx[1:-1, :, :-1]) / dz
                - (self.grid.Hz[1:, :, 1:-1] - self.grid.Hz[:-1, :, 1:-1]) / dx
            )

            # Ez
            self.grid.Ez[1:-1, 1:-1, :] = self.grid._Ca_z[1:-1, 1:-1, :] * self.grid.Ez[
                1:-1, 1:-1, :
            ] + self.grid._Cb_z[1:-1, 1:-1, :] * (
                (self.grid.Hy[1:, 1:-1, :] - self.grid.Hy[:-1, 1:-1, :]) / dx
                - (self.grid.Hx[1:-1, 1:, :] - self.grid.Hx[1:-1, :-1, :]) / dy
            )

    def _apply_sources(self):
        """Aplica fontes de excitação"""
        for source in self.sources:
            if source.is_active(self.current_time):
                val = source.get_value(self.current_time)
                i, j, k = source.position

                if self._cuda_backend is not None:
                    try:
                        self._cuda_backend.add_source(source.component, i, j, k, val)
                        self._host_fields_current = False
                        continue
                    except Exception as exc:
                        self._fallback_from_cuda(exc)

                # Soft source (adiciona ao campo)
                field_array = getattr(self.grid, source.component)

                # Verifica limites
                if (
                    0 <= i < field_array.shape[0]
                    and 0 <= j < field_array.shape[1]
                    and 0 <= k < field_array.shape[2]
                ):
                    field_array[i, j, k] += val

    def _record_probes(self):
        """Registra valores nos probes"""
        for probe in self.probes:
            i, j, k = probe.position

            if self._cuda_backend is not None:
                try:
                    probe.record(self.current_time, self._cuda_backend.read_point(probe.component, i, j, k))
                    continue
                except Exception as exc:
                    self._fallback_from_cuda(exc)

            field_array = getattr(self.grid, probe.component)
            # Verifica limites
            if (
                0 <= i < field_array.shape[0]
                and 0 <= j < field_array.shape[1]
                and 0 <= k < field_array.shape[2]
            ):
                value = field_array[i, j, k]
                probe.record(self.current_time, value)

    def _record_near_field(self):
        """Registra campos near-field na caixa"""
        if self.nf_box is None:
            return

        self.sync_fields_to_host()

        self.nf_box.times.append(self.current_time)

        # Extrai campos tangenciais em cada face
        # (implementação simplificada - armazena apenas cortes centrais/z_min para demo)
        i1, i2 = self.nf_box.i_range
        j1, j2 = self.nf_box.j_range
        k1, k2 = self.nf_box.k_range

        # Face z_min (k=k1)
        self.nf_box.E_data["z_min"].append(np.copy(self.grid.Ez[i1:i2, j1:j2, k1]))
        self.nf_box.H_data["z_min"].append(np.copy(self.grid.Hz[i1:i2, j1:j2, k1]))

    def _update_stats(self):
        """Atualiza estatísticas"""
        self.sync_fields_to_host()
        self.stats["max_E"] = max(
            self.stats["max_E"],
            np.max(np.abs(self.grid.Ex)),
            np.max(np.abs(self.grid.Ey)),
            np.max(np.abs(self.grid.Ez)),
        )
        self.stats["max_H"] = max(
            self.stats["max_H"],
            np.max(np.abs(self.grid.Hx)),
            np.max(np.abs(self.grid.Hy)),
            np.max(np.abs(self.grid.Hz)),
        )

        E_energy, H_energy = self.grid.get_energy()
        self.stats["total_energy"].append((self.current_time, E_energy + H_energy))

    def step(self):
        """Executa um passo temporal FDTD"""
        # 1. Atualiza H (meio passo para frente)
        self._update_H()

        # 2. Atualiza E (um passo completo)
        self._update_E()

        # 3. Aplica fontes
        self._apply_sources()

        # 4. Incrementa tempo
        self.current_time += self.grid.config.dt
        self.time_step += 1

        # 5. Registra dados
        self._record_probes()
        self._record_near_field()

        if self._cuda_backend is not None and not self.defer_host_sync:
            self.sync_fields_to_host()

    def run(self, num_steps: int = None, total_time: float = None, record_interval: int = 10):
        """
        Executa simulação FDTD.

        Args:
            num_steps: Número de passos temporais
            total_time: Tempo total de simulação [s] (alternativa a num_steps)
            record_interval: Intervalo para gravar estatísticas
        """
        if num_steps is None and total_time is not None:
            num_steps = int(total_time / self.grid.config.dt)
        elif num_steps is None:
            raise ValueError("Especifique num_steps ou total_time")

        start_time = time.time()

        for step in range(num_steps):
            self.step()

            # Atualiza estatísticas periodicamente
            if step % record_interval == 0:
                self._update_stats()

            # Callback de progresso
            if self._progress_callback and step % 100 == 0:
                elapsed = time.time() - start_time
                self._progress_callback(step, num_steps, elapsed)

        self.stats["computation_time"] = time.time() - start_time
        self.sync_fields_to_host()
        self.stats["backend"] = self.backend_name
        if self.backend_warning:
            self.stats["backend_warning"] = self.backend_warning

    def reset(self):
        """Reseta o solver para estado inicial"""
        self.grid.reset_fields()
        if self._cuda_backend is not None:
            self._cuda_backend.sync_from_host(["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"])
            self._host_fields_current = True
        self.current_time = 0.0
        self.time_step = 0

        for probe in self.probes:
            probe.clear()

        self.stats = {
            "max_E": 0.0,
            "max_H": 0.0,
            "total_energy": [],
            "computation_time": 0.0,
            "backend": self.backend_name,
        }
        if self.backend_warning:
            self.stats["backend_warning"] = self.backend_warning

    def calculate_far_field(
        self,
        theta_range: Tuple[float, float] = (0, np.pi),
        phi_range: Tuple[float, float] = (0, 2 * np.pi),
        num_theta: int = 91,
        num_phi: int = 181,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Calcula campo far-field usando NearToFarField"""
        if self.nf_box is None:
            # Retorna arrays vazios/zeros
            theta = np.linspace(theta_range[0], theta_range[1], num_theta)
            phi = np.linspace(phi_range[0], phi_range[1], num_phi)
            return theta, phi, np.zeros((num_theta, num_phi)), np.zeros((num_theta, num_phi))

        # Determina frequência da fonte principal (assumindo single source)
        freq = 1e9  # Default
        if self.sources and hasattr(self.sources[0], "frequency"):
            freq = self.sources[0].frequency
        elif self.sources and hasattr(self.sources[0], "center_freq"):
            freq = self.sources[0].center_freq

        ntff = NearToFarField(self.nf_box, self.grid.config, freq)
        return ntff.calculate_far_field(theta_range, phi_range, num_theta, num_phi)
