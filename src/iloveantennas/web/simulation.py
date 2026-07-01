import os
import time

import numpy as np
from iloveantennas.simulator.engine import (
    FDTD_GRID_POLICY,
    FEM_GRID_POLICY,
    frame_record_interval,
    plan_grid_from_bbox,
)
from iloveantennas.web.antennas import create_antenna
from iloveantennas.web.config import AntennaConfig, SimulationConfig
from iloveantennas.web.state import simulation_lock, simulations


def run_fdtd_simulation(sim_id: str, antenna_config: AntennaConfig, sim_config: SimulationConfig):
    """Executa simulação FDTD em thread separada"""
    try:
        from iloveantennas.simulator.solver import FDTDSolver, FieldProbe, GaussianSource, SineSource

        from iloveantennas.simulator.core.grid import FDTDGrid, GridConfig

        with simulation_lock:
            simulations[sim_id]["status"] = "running"
            simulations[sim_id]["progress"] = 0

        # Cria antena
        antenna = create_antenna(antenna_config)
        # Configura grade com politica numerica centralizada.
        bb = antenna.get_bounding_box()
        grid_plan = plan_grid_from_bbox(
            bb,
            antenna_config.frequency,
            sim_config.cells_per_wavelength,
            FDTD_GRID_POLICY,
        )

        config = GridConfig(
            dx=grid_plan.dx,
            nx=grid_plan.nx,
            ny=grid_plan.ny,
            nz=grid_plan.nz,
            pml_layers=sim_config.pml_layers,
            courant=sim_config.courant,
        )

        grid = FDTDGrid(config)
        grid.apply_antenna(antenna)
        grid.setup_pml()
        grid.calculate_coefficients()

        solver = FDTDSolver(
            grid,
            use_numba=sim_config.use_optimized,
            backend=sim_config.solver_backend,
            defer_host_sync=True,
        )

        # Fonte
        center = (config.nx // 2, config.ny // 2, config.nz // 2)

        if sim_config.source_type == "gaussian":
            source = GaussianSource(
                position=center, component="Ez", amplitude=sim_config.source_amplitude, tau=2e-9
            )
        else:
            source = SineSource(
                position=center,
                component="Ez",
                amplitude=sim_config.source_amplitude,
                frequency=antenna_config.frequency,
            )

        solver.add_source(source)

        probe = FieldProbe(position=center, component="Ez")
        solver.add_probe(probe)

        raw_frames = []
        global_max = 1e-9

        num_steps = sim_config.num_steps
        record_interval = frame_record_interval(num_steps)

        # Listas para séries temporais
        times = []
        values = []

        for step in range(num_steps):
            solver.step()

            progress = int((step + 1) / num_steps * 100)
            with simulation_lock:
                simulations[sim_id]["progress"] = progress

            if step % record_interval == 0:
                solver.sync_fields_to_host(["Ez"])

                # Plano E (XZ) - Corte Vertical
                field_slice_E = grid.Ez[:, config.ny // 2, :].copy()

                # Plano H (XY) - Corte Horizontal
                # Para dipolo vertical (Z), o plano H é o plano XY cruzando o centro
                field_slice_H = grid.Ez[:, :, config.nz // 2].copy()

                # Atualiza máximo global
                current_max = max(np.max(np.abs(field_slice_E)), np.max(np.abs(field_slice_H)))
                if current_max > global_max:
                    global_max = current_max

                time_ns = float(step * config.dt * 1e9)

                # Armazena dados brutos para normalização posterior
                raw_frames.append(
                    {
                        "step": step,
                        "time_ns": time_ns,
                        "fieldE_raw": field_slice_E,
                        "fieldH_raw": field_slice_H,
                    }
                )

            # Coleta dados da sonda
            t, v = probe.get_time_series()
            if len(t) > len(times):
                times = t
                values = v

        solver.sync_fields_to_host()
        solver._update_stats()

        # Normalização Global e Geração de Frames Finais
        frames = []
        for rf in raw_frames:
            # Normaliza com o máximo global encontrado em toda a simulação
            norm_E = rf["fieldE_raw"] / global_max
            norm_H = rf["fieldH_raw"] / global_max

            frames.append(
                {
                    "step": rf["step"],
                    "time_ns": rf["time_ns"],
                    "field": norm_E.tolist(),  # Mantendo compatibilidade
                    "fieldE": norm_E.tolist(),
                    "fieldH": norm_H.tolist(),
                    "maxVal": float(global_max),
                }
            )

        # FFT (Simples)
        if len(values) > 0:
            fft_vals = np.fft.fft(values)
            freqs = np.fft.fftfreq(len(values), config.dt)
            positive_mask = freqs > 0
            spectrum_freqs = freqs[positive_mask][:100]
            spectrum_vals = np.abs(fft_vals[positive_mask])[:100]
        else:
            spectrum_freqs = []
            spectrum_vals = []

        spectrum_max = float(np.max(spectrum_vals)) if len(spectrum_vals) > 0 else 0.0
        if spectrum_max > 0:
            spectrum_magnitudes = (np.array(spectrum_vals) / (spectrum_max + 1e-10)).tolist()
        else:
            spectrum_magnitudes = []

        # Resultados
        results = {
            "status": "completed",
            "grid": {
                "nx": config.nx,
                "ny": config.ny,
                "nz": config.nz,
                "dx": config.dx,
                "dt": config.dt,
                "maxE": float(solver.stats.get("max_E", 0)),
                "maxH": float(solver.stats.get("max_H", 0)),
                "plan": grid_plan.to_dict(),
            },
            "engine": {
                "method": "fdtd",
                "requested_backend": sim_config.solver_backend,
                "solver_backend": solver.backend_name,
                "backend_warning": solver.backend_warning,
                "record_interval": record_interval,
                "notes": [
                    "GPU status is exposed separately by /api/engine/status.",
                    "CUDA is used only when requested and successfully initialized.",
                ],
            },
            "stats": {
                "computation_time": solver.stats.get("computation_time", 0),
                "max_E": float(solver.stats.get("max_E", 0)),
                "max_H": float(solver.stats.get("max_H", 0)),
                "num_steps": num_steps,
            },
            "time_series": {
                "times": (np.array(times) * 1e9).tolist() if len(times) > 0 else [],
                "values": values.tolist() if len(values) > 0 else [],
            },
            "spectrum": {
                "frequencies": (np.array(spectrum_freqs) / 1e6).tolist(),
                "magnitudes": spectrum_magnitudes,
            },
            "frames": frames,
            "field_shape": [config.nx, config.nz],
        }

        with simulation_lock:
            simulations[sim_id].update(results)
            simulations[sim_id]["progress"] = 100

    except Exception as e:
        import traceback

        traceback.print_exc()
        with simulation_lock:
            simulations[sim_id]["status"] = "error"
            simulations[sim_id]["error"] = str(e)


def run_fem_simulation(sim_id: str, antenna_config: AntennaConfig, sim_config: SimulationConfig):
    """
    Executa simulação FEM.
    Se antena for 3D e tivermos suporte, roda 3D.
    Por enquanto, vamos forçar 3D se o usuário selecionou FEM (já que implementamos suporte básico 3D).
    """
    try:
        from iloveantennas.simulator.fem.mesh_generator import MeshGenerator
        from iloveantennas.simulator.fem.solver_3d import FEMSolver3D

        with simulation_lock:
            simulations[sim_id]["status"] = "running"
            simulations[sim_id]["progress"] = 5

        # Cria antena (grafo)
        antenna = create_antenna(antenna_config)

        bb = antenna.get_bounding_box()
        grid_plan = plan_grid_from_bbox(
            bb,
            antenna_config.frequency,
            sim_config.cells_per_wavelength,
            FEM_GRID_POLICY,
        )
        dx = grid_plan.dx
        nx = grid_plan.nx
        ny = grid_plan.ny
        nz = grid_plan.nz

        use_fallback = False
        mag = None

        # Tenta caminho completo com Gmsh + FEMSolver3D
        try:
            mesh_file = f"temp_{sim_id}.msh"
            generator = MeshGenerator(antenna, antenna_config.frequency)

            with simulation_lock:
                simulations[sim_id]["progress"] = 15

            generator.generate(mesh_file, resolution_factor=8.0)

            with simulation_lock:
                simulations[sim_id]["progress"] = 30

            solver = FEMSolver3D(mesh_file, antenna_config.frequency, feed_point=antenna.feed_point)

            with simulation_lock:
                simulations[sim_id]["progress"] = 50

            mag, fields = solver.get_fields_on_grid(nx, ny, nz)

            try:
                os.remove(mesh_file)
            except:
                pass
        except Exception:
            use_fallback = True

        if use_fallback:
            # Fallback: campo sintético gaussiano 3D para manter fluxo da API
            with simulation_lock:
                simulations[sim_id]["progress"] = 40

            xs = np.linspace(-1.0, 1.0, nx)
            ys = np.linspace(-1.0, 1.0, ny)
            zs = np.linspace(-1.0, 1.0, nz)
            grid_x, grid_y, grid_z = np.meshgrid(xs, ys, zs, indexing="ij")

            r2 = grid_x**2 + grid_y**2 + grid_z**2
            mag = np.exp(-r2 / (0.4**2))

        with simulation_lock:
            simulations[sim_id]["progress"] = 80

        # Seleciona cortes centrais
        slice_E = mag[:, ny // 2, :]
        slice_H = mag[:, :, nz // 2]

        max_val = np.max(mag)
        if max_val > 0:
            slice_E /= max_val
            slice_H /= max_val

        # Gera frames animados falsos (fase)
        frames = []
        num_frames = 20
        for i in range(num_frames):
            phase = 2 * np.pi * i / num_frames
            osc = np.cos(phase)
            data_E = (slice_E * osc).tolist()
            data_H = (slice_H * osc).tolist()
            if antenna_config.frequency:
                time_ns = float(i / num_frames / antenna_config.frequency * 1e9)
            else:
                time_ns = float(i)
            frames.append(
                {
                    "step": i,
                    "time_ns": time_ns,
                    "field": data_E,
                    "fieldE": data_E,
                    "fieldH": data_H,
                    "maxVal": float(max_val),
                }
            )

        # Impedância (Placeholder por enquanto, ou calculado se solver tiver suporte)
        # Se solver tiver método calculate_impedance...
        z_real = 73.0  # Exemplo dipolo
        z_imag = 0.0
        Z = complex(z_real, z_imag)

        results = {
            "status": "completed",
            "grid": {
                "nx": nx,
                "ny": ny,
                "nz": nz,
                "dx": dx,
                "dt": 0,
                "maxE": float(max_val),
                "maxH": 0.0,
                "plan": grid_plan.to_dict(),
            },
            "engine": {
                "method": "fem",
                "solver_backend": "gmsh/scipy-cpu" if not use_fallback else "synthetic-cpu",
                "fallback": use_fallback,
                "notes": [
                    "FEM uses the Gmsh/scipy path when meshing succeeds.",
                    "Fallback frames are synthetic and preserve the visualization flow.",
                ],
            },
            "stats": {
                "computation_time": 0,
                "max_E": float(max_val),
                "max_H": 0.0,
                "num_steps": num_frames,
                "impedance": {
                    "real": float(np.real(Z)),
                    "imag": float(np.imag(Z)),
                    "magnitude": float(np.abs(Z)),
                },
            },
            "time_series": {"times": [], "values": []},
            "spectrum": {"frequencies": [], "magnitudes": []},
            "frames": frames,
            "field_shape": [nx, nz],
        }

        with simulation_lock:
            simulations[sim_id].update(results)
            simulations[sim_id]["progress"] = 100

    except Exception as e:
        import traceback

        traceback.print_exc()
        with simulation_lock:
            simulations[sim_id]["status"] = "error"
            simulations[sim_id]["error"] = str(e)
