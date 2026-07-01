from iloveantennas.simulator.core.materials import MaterialLibrary
from iloveantennas.web.resources import MATERIALS
from iloveantennas.web.schemas import (
    PropagationRequest,
    RayTraceRequest,
    Segment2DRequest,
    SimulationStartRequest,
    antenna_config_from_payload,
    propagation_environment_from_payload,
    ray_trace_inputs_from_payload,
    simulation_config_from_payload,
)


def _material(group: str, name: str) -> dict:
    return next(item for item in MATERIALS[group] if item["name"] == name)


def test_web_material_catalog_comes_from_core_library():
    copper = _material("conductors", "COPPER")
    fr4 = _material("dielectrics", "FR4")

    assert copper["sigma"] == MaterialLibrary.COPPER.api_sigma
    assert copper["color"] == MaterialLibrary.COPPER.color_hex
    assert fr4["epsilon_r"] == MaterialLibrary.FR4.epsilon_r
    assert fr4["tan_delta"] == MaterialLibrary.FR4.tan_delta
    assert fr4["color"] == MaterialLibrary.FR4.color_hex


def test_simulation_payload_prefers_explicit_antenna_type():
    payload = SimulationStartRequest(
        type="dipole",
        antenna_type="patch",
        frequency=2.4e9,
        solver_backend="cuda_gpu",
        cells_per_wavelength=12,
    )

    antenna_config = antenna_config_from_payload(payload, type_field="antenna_type")
    simulation_config = simulation_config_from_payload(payload)

    assert antenna_config.type == "patch"
    assert antenna_config.frequency == 2.4e9
    assert simulation_config.solver_backend == "cuda"
    assert simulation_config.cells_per_wavelength == 12


def test_propagation_helpers_build_engine_dataclasses():
    env = propagation_environment_from_payload(
        PropagationRequest(
            frequency=900e6,
            distance_km=2.0,
            tx_height_m=30.0,
            rx_height_m=1.5,
        )
    )
    tx, rx, obstacles = ray_trace_inputs_from_payload(
        RayTraceRequest(
            tx={"x": 0.0, "y": 0.0},
            rx={"x": 10.0, "y": 0.0},
            obstacles=[
                Segment2DRequest(
                    start={"x": 0.0, "y": 5.0},
                    end={"x": 10.0, "y": 5.0},
                )
            ],
        )
    )

    assert env.frequency_hz == 900e6
    assert tx.x == 0.0
    assert rx.x == 10.0
    assert len(obstacles) == 1
    assert obstacles[0].reflection_loss_db == 6.0
