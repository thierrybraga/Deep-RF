import os
import sys

import numpy as np

from iloveantennas.simulator.core.geometry.factory import AntennaFactory
from iloveantennas.simulator.core.geometry.primitives import (
    Helix,
    Horn,
    ParabolicDish,
    Rectangle,
    Vector3D,
    Wire,
)
from iloveantennas.simulator.core.grid import create_grid_for_antenna
from iloveantennas.simulator.fem.mesh_generator import MeshGenerator


def test_diagnose_antennas():
    factories = [
        ("Dipole", lambda: AntennaFactory.create_dipole(0.1)),
        ("Monopole", lambda: AntennaFactory.create_monopole(0.1)),
        ("Yagi", lambda: AntennaFactory.create_yagi(frequency=0.9e9, num_directors=3)),
        ("Patch", lambda: AntennaFactory.create_patch(2.4e9)),
        ("Helix", lambda: AntennaFactory.create_helix(2.4e9)),
        (
            "Horn",
            lambda: AntennaFactory.create_horn(
                10e9, aperture_width=0.05, aperture_height=0.04, length=0.1
            ),
        ),
        ("Dish", lambda: AntennaFactory.create_parabolic(5.0e9, diameter=0.6, focal_length=0.3)),
        ("LPDA", lambda: AntennaFactory.create_log_periodic(500e6, 1000e6)),
        ("Loop", lambda: AntennaFactory.create_loop(0.05)),
        ("Biquad", lambda: AntennaFactory.create_biquad(frequency=2.4e9)),
    ]

    print(f"{'Antenna':<15} | {'Primitives':<30} | {'Feed Point':<30} | {'Mesh Gen Status'}")
    print("-" * 100)

    for name, factory_func in factories:
        try:
            antenna = factory_func()
        except AttributeError:
            print(f"{name:<15} | {'FACTORY METHOD MISSING':<30} | {'-':<30} | FAIL")
            continue
        except Exception as e:
            print(f"{name:<15} | {f'ERROR: {str(e)}':<30} | {'-':<30} | FAIL")
            continue

        # Analisa Primitivas
        primitives = set()
        for geo in antenna.geometries:
            primitives.add(type(geo).__name__)
        for edge in antenna.edges.values():
            if edge.geometry:
                primitives.add(type(edge.geometry).__name__)

        prims_str = ", ".join(list(primitives))

        # Analisa Feed Point
        feed_pos = "None"
        if antenna.feed_point:
            # antenna.feed_point é um Vector3D
            p = antenna.feed_point
            feed_pos = f"({p.x:.3f}, {p.y:.3f}, {p.z:.3f})"

        # Teste de Geração de Malha (Simulado)
        # Verifica se o MeshGenerator saberia lidar com essas primitivas
        mesh_status = "OK"
        supported_prims = ["Wire", "Rectangle"]
        unsupported = [p for p in primitives if p not in supported_prims]

        if unsupported:
            mesh_status = f"UNSUPPORTED: {', '.join(unsupported)}"

        print(f"{name:<15} | {prims_str[:30]:<30} | {feed_pos:<30} | {mesh_status}")


if __name__ == "__main__":
    diagnose_antennas()
