#!/usr/bin/env python3

import os
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

current_dir = os.path.dirname(os.path.abspath(__file__))

from iloveantennas.simulator.core.constants import C0
from iloveantennas.simulator.propagation import (
    compare_path_loss,
    trace_2d_rays,
)
from iloveantennas.simulator.runtime import get_runtime_status
from iloveantennas.web.analysis import (
    calculate_parameters,
    calculate_radiation_pattern,
    calculate_smith_chart_data,
)
from iloveantennas.web.antennas import create_antenna, get_antenna_geometry_data
from iloveantennas.web.matching import MatchingResult, calculate_matching
from iloveantennas.web.optimization import run_optimization_task
from iloveantennas.web.resources import ANTENNA_TYPES, MATERIALS
from iloveantennas.web.schemas import (
    AntennaCreateRequest,
    CalculateParametersRequest,
    MatchingRequest,
    OptimizeRequest,
    PropagationRequest,
    RadiationPatternRequest,
    RayTraceRequest,
    SimulationStartRequest,
    SmithChartRequest,
    UserAntennaModel,
    antenna_config_from_payload,
    model_dump,
    propagation_environment_from_payload,
    ray_trace_inputs_from_payload,
    simulation_config_from_payload,
)
from iloveantennas.web.simulation import run_fdtd_simulation, run_fem_simulation
from iloveantennas.web.state import optimization_lock, optimizations, simulation_lock, simulations
from iloveantennas.web.storage import storage


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
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.get("/analise", response_class=HTMLResponse)
async def analise(request: Request):
    return templates.TemplateResponse(request, "analise.html", {"request": request})


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


@app.get("/api/engine/status")
def get_engine_status():
    return {"success": True, "data": get_runtime_status()}


@app.get("/api/antenna/types")
def get_antenna_types():
    return ANTENNA_TYPES


@app.get("/api/antennas")
def list_antennas():
    return storage.get_all()


@app.post("/api/antennas")
def create_antenna_db(antenna: UserAntennaModel):
    return storage.create(model_dump(antenna))


@app.put("/api/antennas/{antenna_id}")
def update_antenna_db(antenna_id: str, antenna: UserAntennaModel):
    result = storage.update(antenna_id, model_dump(antenna))
    if result:
        return result
    raise HTTPException(status_code=404, detail="Antenna not found")


@app.delete("/api/antennas/{antenna_id}")
def delete_antenna_db(antenna_id: str):
    success = storage.delete(antenna_id)
    return {"success": success}


@app.post("/api/antenna/create")
def create_antenna_endpoint(payload: AntennaCreateRequest):
    try:
        config = antenna_config_from_payload(payload)

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
        config = antenna_config_from_payload(payload)

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
        return {"success": False, "error": str(e)}


@app.post("/api/propagation/path-loss")
def propagation_path_loss_endpoint(payload: PropagationRequest):
    try:
        environment = propagation_environment_from_payload(payload)
        data = compare_path_loss(
            environment,
            tx_power_dbm=float(payload.tx_power_dbm),
            tx_gain_dbi=float(payload.tx_gain_dbi),
            rx_gain_dbi=float(payload.rx_gain_dbi),
            receiver_sensitivity_dbm=(
                float(payload.receiver_sensitivity_dbm)
                if payload.receiver_sensitivity_dbm is not None
                else None
            ),
        )
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/propagation/ray-trace")
def propagation_ray_trace_endpoint(payload: RayTraceRequest):
    try:
        tx, rx, obstacles = ray_trace_inputs_from_payload(payload)
        paths = trace_2d_rays(
            tx,
            rx,
            obstacles,
            float(payload.frequency),
            max_reflections=int(payload.max_reflections),
        )
        return {"success": True, "data": {"paths": [path.to_dict() for path in paths]}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/simulation/compare")
def start_comparison(payload: SimulationStartRequest):
    try:
        antenna_config = antenna_config_from_payload(payload, type_field="antenna_type")
        sim_config_fdtd = simulation_config_from_payload(payload, method="fdtd")
        sim_config_fem = simulation_config_from_payload(payload, method="fem", num_steps=1)

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
                "parent_comparison": comp_id,
            }
            # FEM Entry
            simulations[id_fem] = {
                "id": id_fem,
                "status": "starting",
                "progress": 0,
                "created_at": time.time(),
                "antenna_config": antenna_config.to_dict(),
                "sim_config": sim_config_fem.to_dict(),
                "parent_comparison": comp_id,
            }

        t_fdtd = threading.Thread(
            target=run_fdtd_simulation, args=(id_fdtd, antenna_config, sim_config_fdtd)
        )
        t_fem = threading.Thread(
            target=run_fem_simulation, args=(id_fem, antenna_config, sim_config_fem)
        )

        t_fdtd.daemon = True
        t_fem.daemon = True

        t_fdtd.start()
        t_fem.start()

        return {"success": True, "comparison_id": comp_id, "fdtd_id": id_fdtd, "fem_id": id_fem}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/simulation/start")
def start_simulation(payload: SimulationStartRequest):
    try:
        antenna_config = antenna_config_from_payload(payload, type_field="antenna_type")
        sim_config = simulation_config_from_payload(payload)

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
        config = antenna_config_from_payload(payload)

        smith_data = calculate_smith_chart_data(config, mode=payload.mode)

        return {"success": True, "data": smith_data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/radiation-pattern")
def get_radiation_pattern(payload: RadiationPatternRequest):
    try:
        config = antenna_config_from_payload(payload)

        pattern_data = calculate_radiation_pattern(config, mode=payload.mode)

        return {"success": True, "data": pattern_data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/calculate")
def calculate_parameters_endpoint(payload: CalculateParametersRequest):
    try:
        frequency = float(payload.frequency)
        directivity_db = (
            float(payload.directivity_db) if payload.directivity_db is not None else None
        )
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
        args=(opt_id, model_dump(payload)),
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

    uvicorn.run("iloveantennas.web.app:app", host="0.0.0.0", port=5000, reload=True)
