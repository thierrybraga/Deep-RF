#!/usr/bin/env python3

import os
import sys
import time
import uuid
import threading
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_dir = os.path.dirname(current_dir)
simulator_path = os.path.join(workspace_dir, 'antenna_simulator')
sys.path.insert(0, simulator_path)

from core.constants import C0
from config import AntennaConfig, SimulationConfig
from state import simulations, simulation_lock, optimizations, optimization_lock
from antennas import create_antenna, get_antenna_geometry_data
from simulation import run_fdtd_simulation, run_fem_simulation
from analysis import calculate_smith_chart_data, calculate_radiation_pattern, calculate_parameters
from optimization import run_optimization_task
from resources import MATERIALS, ANTENNA_TYPES
from matching import calculate_matching, NetworkType, MatchingResult
from storage import storage


class UserAntennaModel(BaseModel):
    id: Optional[str] = None
    name: str
    brand: str = "Custom"
    technology: str = "General"
    config: dict


class AntennaCreateRequest(BaseModel):
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


class SimulationStartRequest(BaseModel):
    antenna_type: str = "dipole"
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
    cells_per_wavelength: int = 15
    num_steps: int = 200
    pml_layers: int = 8
    courant: float = 0.99
    source_type: str = "gaussian"
    source_amplitude: float = 1.0
    use_optimized: bool = True
    method: str = "fdtd"


class SmithChartRequest(BaseModel):
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
    mode: str = "analytical"


class RadiationPatternRequest(BaseModel):
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
    mode: str = "analytical"


class CalculateParametersRequest(BaseModel):
    frequency: float = 300e6
    directivity_db: float | None = None


class OptimizeRequest(BaseModel):
    antenna_type: str = "dipole"
    target_freq: float = 300e6
    start_length: Optional[float] = None
    radius: float = 0.001


class MatchingRequest(BaseModel):
    z_load_re: float
    z_load_im: float
    z0: float = 50.0
    frequency: float
    network_type: NetworkType = "L"
    q: float | None = None


app = FastAPI(title="IloveAntenas Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(current_dir, "static")),
    name="static",
)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/analise", response_class=HTMLResponse)
async def analise(request: Request):
    return templates.TemplateResponse("analise.html", {"request": request})


@app.get("/service-worker.js")
async def service_worker():
    path = os.path.join(current_dir, "static", "js", "service-worker.js")
    return FileResponse(path, media_type="application/javascript")


@app.get("/robots.txt")
async def robots_txt():
    path = os.path.join(current_dir, "static", "robots.txt")
    return FileResponse(path, media_type="text/plain")


@app.get("/sitemap.xml")
async def sitemap_xml():
    path = os.path.join(current_dir, "static", "sitemap.xml")
    return FileResponse(path, media_type="application/xml")


@app.get("/api/materials")
def get_materials():
    return MATERIALS


@app.get("/api/antenna/types")
def get_antenna_types():
    return ANTENNA_TYPES


@app.get("/api/antennas")
def list_antennas():
    return storage.get_all()


@app.post("/api/antennas")
def create_antenna_db(antenna: UserAntennaModel):
    return storage.create(antenna.dict())


@app.put("/api/antennas/{antenna_id}")
def update_antenna_db(antenna_id: str, antenna: UserAntennaModel):
    result = storage.update(antenna_id, antenna.dict())
    if result:
        return result
    return {"error": "Antenna not found"}, 404


@app.delete("/api/antennas/{antenna_id}")
def delete_antenna_db(antenna_id: str):
    success = storage.delete(antenna_id)
    return {"success": success}


@app.post("/api/antenna/create")
def create_antenna_endpoint(payload: AntennaCreateRequest):
    try:
        config = AntennaConfig(
            type=payload.type,
            frequency=float(payload.frequency),
            length=float(payload.length) if payload.length is not None else None,
            radius=float(payload.radius),
            num_directors=int(payload.num_directors),
            substrate_er=float(payload.substrate_er),
            substrate_h=float(payload.substrate_h),
            turns=int(payload.turns),
            aperture_width=float(payload.aperture_width) if payload.aperture_width is not None else None,
            aperture_height=float(payload.aperture_height) if payload.aperture_height is not None else None,
            flare_length=float(payload.flare_length) if payload.flare_length is not None else None,
            dish_diameter=float(payload.dish_diameter) if payload.dish_diameter is not None else None,
            focal_length=float(payload.focal_length) if payload.focal_length is not None else None,
            tau=float(payload.tau),
            sigma=float(payload.sigma),
            loop_radius=float(payload.loop_radius) if payload.loop_radius is not None else None,
            side_length=float(payload.side_length) if payload.side_length is not None else None,
            reflector_distance=float(payload.reflector_distance) if payload.reflector_distance is not None else None,
            disc_radius=float(payload.disc_radius) if payload.disc_radius is not None else None,
            cone_radius=float(payload.cone_radius) if payload.cone_radius is not None else None,
            cone_height=float(payload.cone_height) if payload.cone_height is not None else None,
        )

        antenna = create_antenna(config)
        geometry_data = get_antenna_geometry_data(antenna)
        wavelength = C0 / config.frequency
        geometry_data["wavelength"] = wavelength
        geometry_data["frequency"] = config.frequency
        geometry_data["config"] = config.to_dict()

        return {"success": True, "data": geometry_data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/antenna/analysis")
def antenna_full_analysis(payload: AntennaCreateRequest):
    try:
        config = AntennaConfig(
            type=payload.type,
            frequency=float(payload.frequency),
            length=float(payload.length) if payload.length is not None else None,
            radius=float(payload.radius),
            num_directors=int(payload.num_directors),
            substrate_er=float(payload.substrate_er),
            substrate_h=float(payload.substrate_h),
            turns=int(payload.turns),
            aperture_width=float(payload.aperture_width) if payload.aperture_width is not None else None,
            aperture_height=float(payload.aperture_height) if payload.aperture_height is not None else None,
            flare_length=float(payload.flare_length) if payload.flare_length is not None else None,
            dish_diameter=float(payload.dish_diameter) if payload.dish_diameter is not None else None,
            focal_length=float(payload.focal_length) if payload.focal_length is not None else None,
            tau=float(payload.tau),
            sigma=float(payload.sigma),
            loop_radius=float(payload.loop_radius) if payload.loop_radius is not None else None,
            side_length=float(payload.side_length) if payload.side_length is not None else None,
            reflector_distance=float(payload.reflector_distance) if payload.reflector_distance is not None else None,
            disc_radius=float(payload.disc_radius) if payload.disc_radius is not None else None,
            cone_radius=float(payload.cone_radius) if payload.cone_radius is not None else None,
            cone_height=float(payload.cone_height) if payload.cone_height is not None else None,
        )

        antenna = create_antenna(config)
        geometry_data = get_antenna_geometry_data(antenna)
        wavelength = C0 / config.frequency
        geometry_data["wavelength"] = wavelength
        geometry_data["frequency"] = config.frequency
        geometry_data["config"] = config.to_dict()

        smith_data = calculate_smith_chart_data(config)
        radiation_data = calculate_radiation_pattern(config)
        params = calculate_parameters(config.frequency, radiation_data.get("directivity_db"))

        return {
            "success": True,
            "data": {
                "geometry": geometry_data,
                "smith": smith_data,
                "radiation": radiation_data,
                "parameters": params,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/matching")
def matching_endpoint(payload: MatchingRequest):
    try:
        z_load = complex(float(payload.z_load_re), float(payload.z_load_im))
        z0 = float(payload.z0)
        f = float(payload.frequency)
        q = float(payload.q) if payload.q is not None else None
        result: MatchingResult = calculate_matching(z_load, z0, f, payload.network_type, q)

        def format_component(c):
            return {
                "role": c.role,
                "kind": c.kind,
                "value": c.value,
                "unit": c.unit,
            }

        stub_data = None
        if result.stub is not None:
            stub_data = {
                "short_lambda": result.stub.short_lambda,
                "open_lambda": result.stub.open_lambda,
            }

        return {
            "success": True,
            "data": {
                "network_type": result.network_type,
                "topology": result.topology,
                "components": [format_component(c) for c in result.components],
                "stub": stub_data,
                "q_used": result.q_used,
                "notes": result.notes,
            },
        }
    except Exception as e:
        return {"success": True, "error": str(e)}


@app.post("/api/simulation/compare")
def start_comparison(payload: SimulationStartRequest):
    try:
        # Config common
        antenna_config = AntennaConfig(
            type=payload.antenna_type,
            frequency=float(payload.frequency),
            length=float(payload.length) if payload.length is not None else None,
            radius=float(payload.radius),
            num_directors=int(payload.num_directors),
            substrate_er=float(payload.substrate_er),
            substrate_h=float(payload.substrate_h),
            turns=int(payload.turns),
            aperture_width=float(payload.aperture_width) if payload.aperture_width is not None else None,
            aperture_height=float(payload.aperture_height) if payload.aperture_height is not None else None,
            flare_length=float(payload.flare_length) if payload.flare_length is not None else None,
            dish_diameter=float(payload.dish_diameter) if payload.dish_diameter is not None else None,
            focal_length=float(payload.focal_length) if payload.focal_length is not None else None,
            tau=float(payload.tau),
            sigma=float(payload.sigma),
            loop_radius=float(payload.loop_radius) if payload.loop_radius is not None else None,
        )

        # FDTD Config
        sim_config_fdtd = SimulationConfig(
            cells_per_wavelength=int(payload.cells_per_wavelength),
            num_steps=int(payload.num_steps),
            pml_layers=int(payload.pml_layers),
            courant=float(payload.courant),
            source_type=payload.source_type,
            source_amplitude=float(payload.source_amplitude),
            use_optimized=bool(payload.use_optimized),
            method="fdtd"
        )
        
        # FEM Config
        sim_config_fem = SimulationConfig(
            cells_per_wavelength=int(payload.cells_per_wavelength),
            num_steps=1, # FEM is freq domain
            pml_layers=int(payload.pml_layers),
            courant=float(payload.courant),
            source_type=payload.source_type,
            source_amplitude=float(payload.source_amplitude),
            use_optimized=bool(payload.use_optimized),
            method="fem"
        )

        id_fdtd = str(uuid.uuid4())[:8]
        id_fem = str(uuid.uuid4())[:8]
        comp_id = str(uuid.uuid4())[:8]

        with simulation_lock:
            # FDTD Entry
            simulations[id_fdtd] = {
                "id": id_fdtd,
                "status": "starting",
                "progress": 0,
                "created_at": time.time(),
                "antenna_config": antenna_config.to_dict(),
                "sim_config": sim_config_fdtd.to_dict(),
                "parent_comparison": comp_id
            }
            # FEM Entry
            simulations[id_fem] = {
                "id": id_fem,
                "status": "starting",
                "progress": 0,
                "created_at": time.time(),
                "antenna_config": antenna_config.to_dict(),
                "sim_config": sim_config_fem.to_dict(),
                "parent_comparison": comp_id
            }

        t_fdtd = threading.Thread(target=run_fdtd_simulation, args=(id_fdtd, antenna_config, sim_config_fdtd))
        t_fem = threading.Thread(target=run_fem_simulation, args=(id_fem, antenna_config, sim_config_fem))
        
        t_fdtd.daemon = True
        t_fem.daemon = True
        
        t_fdtd.start()
        t_fem.start()

        return {
            "success": True, 
            "comparison_id": comp_id,
            "fdtd_id": id_fdtd,
            "fem_id": id_fem
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/simulation/start")
def start_simulation(payload: SimulationStartRequest):
    try:
        antenna_config = AntennaConfig(
            type=payload.antenna_type,
            frequency=float(payload.frequency),
            length=float(payload.length) if payload.length is not None else None,
            radius=float(payload.radius),
            num_directors=int(payload.num_directors),
            substrate_er=float(payload.substrate_er),
            substrate_h=float(payload.substrate_h),
            turns=int(payload.turns),
            aperture_width=float(payload.aperture_width) if payload.aperture_width is not None else None,
            aperture_height=float(payload.aperture_height) if payload.aperture_height is not None else None,
            flare_length=float(payload.flare_length) if payload.flare_length is not None else None,
            dish_diameter=float(payload.dish_diameter) if payload.dish_diameter is not None else None,
            focal_length=float(payload.focal_length) if payload.focal_length is not None else None,
            tau=float(payload.tau),
            sigma=float(payload.sigma),
            loop_radius=float(payload.loop_radius) if payload.loop_radius is not None else None,
        )

        sim_config = SimulationConfig(
            cells_per_wavelength=int(payload.cells_per_wavelength),
            num_steps=int(payload.num_steps),
            pml_layers=int(payload.pml_layers),
            courant=float(payload.courant),
            source_type=payload.source_type,
            source_amplitude=float(payload.source_amplitude),
            use_optimized=bool(payload.use_optimized),
            method=payload.method
        )

        sim_id = str(uuid.uuid4())[:8]

        with simulation_lock:
            simulations[sim_id] = {
                "id": sim_id,
                "status": "starting",
                "progress": 0,
                "created_at": time.time(),
                "antenna_config": antenna_config.to_dict(),
                "sim_config": sim_config.to_dict(),
            }

        target_func = run_fem_simulation if payload.method == "fem" else run_fdtd_simulation

        thread = threading.Thread(
            target=target_func,
            args=(sim_id, antenna_config, sim_config),
        )
        thread.daemon = True
        thread.start()

        return {"success": True, "simulation_id": sim_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/simulation/{sim_id}/status")
def get_simulation_status(sim_id: str):
    with simulation_lock:
        if sim_id not in simulations:
            return {"success": False, "error": "Simulação não encontrada"}
        sim = simulations[sim_id].copy()

    if "frames" in sim:
        sim["num_frames"] = len(sim["frames"])
        del sim["frames"]

    return {"success": True, "data": sim}


@app.get("/api/simulation/{sim_id}/frames")
def get_simulation_frames(sim_id: str):
    with simulation_lock:
        if sim_id not in simulations:
            return {"success": False, "error": "Simulação não encontrada"}

        sim = simulations[sim_id]

        if sim.get("status") != "completed":
            return {"success": False, "error": "Simulação ainda não concluída"}

        return {
            "success": True,
            "frames": sim.get("frames", []),
            "field_shape": sim.get("field_shape", [0, 0]),
        }


@app.post("/api/smith-chart")
def get_smith_chart(payload: SmithChartRequest):
    try:
        config = AntennaConfig(
            type=payload.type,
            frequency=float(payload.frequency),
            length=float(payload.length) if payload.length is not None else None,
            radius=float(payload.radius),
            num_directors=int(payload.num_directors),
            substrate_er=float(payload.substrate_er),
            substrate_h=float(payload.substrate_h),
            turns=int(payload.turns),
            aperture_width=float(payload.aperture_width) if payload.aperture_width is not None else None,
            aperture_height=float(payload.aperture_height) if payload.aperture_height is not None else None,
            flare_length=float(payload.flare_length) if payload.flare_length is not None else None,
            dish_diameter=float(payload.dish_diameter) if payload.dish_diameter is not None else None,
            focal_length=float(payload.focal_length) if payload.focal_length is not None else None,
            tau=float(payload.tau),
            sigma=float(payload.sigma),
            loop_radius=float(payload.loop_radius) if payload.loop_radius is not None else None,
            side_length=float(payload.side_length) if payload.side_length is not None else None,
            reflector_distance=float(payload.reflector_distance) if payload.reflector_distance is not None else None,
            disc_radius=float(payload.disc_radius) if payload.disc_radius is not None else None,
            cone_radius=float(payload.cone_radius) if payload.cone_radius is not None else None,
            cone_height=float(payload.cone_height) if payload.cone_height is not None else None,
        )

        smith_data = calculate_smith_chart_data(config, mode=payload.mode)

        return {"success": True, "data": smith_data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/radiation-pattern")
def get_radiation_pattern(payload: RadiationPatternRequest):
    try:
        config = AntennaConfig(
            type=payload.type,
            frequency=float(payload.frequency),
            length=float(payload.length) if payload.length is not None else None,
            radius=float(payload.radius),
            num_directors=int(payload.num_directors),
            substrate_er=float(payload.substrate_er),
            substrate_h=float(payload.substrate_h),
            turns=int(payload.turns),
            aperture_width=float(payload.aperture_width) if payload.aperture_width is not None else None,
            aperture_height=float(payload.aperture_height) if payload.aperture_height is not None else None,
            flare_length=float(payload.flare_length) if payload.flare_length is not None else None,
            dish_diameter=float(payload.dish_diameter) if payload.dish_diameter is not None else None,
            focal_length=float(payload.focal_length) if payload.focal_length is not None else None,
            tau=float(payload.tau),
            sigma=float(payload.sigma),
            loop_radius=float(payload.loop_radius) if payload.loop_radius is not None else None,
            side_length=float(payload.side_length) if payload.side_length is not None else None,
            reflector_distance=float(payload.reflector_distance) if payload.reflector_distance is not None else None,
            disc_radius=float(payload.disc_radius) if payload.disc_radius is not None else None,
            cone_radius=float(payload.cone_radius) if payload.cone_radius is not None else None,
            cone_height=float(payload.cone_height) if payload.cone_height is not None else None,
        )

        pattern_data = calculate_radiation_pattern(config, mode=payload.mode)

        return {"success": True, "data": pattern_data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/calculate")
def calculate_parameters_endpoint(payload: CalculateParametersRequest):
    try:
        frequency = float(payload.frequency)
        directivity_db = float(payload.directivity_db) if payload.directivity_db is not None else None
        params = calculate_parameters(frequency, directivity_db)
        return {"success": True, "data": params}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/optimize")
def start_optimization_endpoint(payload: OptimizeRequest):
    opt_id = str(uuid.uuid4())

    with optimization_lock:
        optimizations[opt_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Inicializando...",
            "result": None,
        }

    thread = threading.Thread(
        target=run_optimization_task,
        args=(opt_id, payload.dict()),
    )
    thread.daemon = True
    thread.start()

    return {"id": opt_id}


@app.get("/api/optimize/{opt_id}/status")
def get_optimization_status_endpoint(opt_id: str):
    with optimization_lock:
        if opt_id not in optimizations:
            return {"error": "Optimization not found"}

        data = optimizations[opt_id].copy()
        if "optimizer" in data:
            del data["optimizer"]
        return data


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("  IloveAntenas Web - Simulador de Antenas FDTD")
    print("=" * 60)
    print("  Servidor: http://localhost:5000")
    print("=" * 60 + "\n")

    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)
