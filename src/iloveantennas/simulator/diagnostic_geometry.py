import os
import sys

import numpy as np

from iloveantennas.simulator.core.geometry.factory import AntennaFactory
from iloveantennas.simulator.core.geometry.primitives import Vector3D
from iloveantennas.simulator.core.grid import create_grid_for_antenna
from iloveantennas.simulator.fem.mesh_generator import MeshGenerator


def print_vec(v):
    return f"({v.x:.4f}, {v.y:.4f}, {v.z:.4f})"


def run_diagnostic():
    print("=== ANTENNA GEOMETRY DIAGNOSTIC ===")

    # Test cases
    cases = [
        ("Dipole", lambda: AntennaFactory.create_dipole(length=0.1, frequency=1e9)),
        ("Monopole", lambda: AntennaFactory.create_monopole(length=0.075, ground_size=0.2)),
        ("Patch", lambda: AntennaFactory.create_patch(frequency=2.4e9)),
        (
            "Off-Center Dipole",
            lambda: AntennaFactory.create_dipole(length=0.1, center=Vector3D(0.05, 0.05, 0)),
        ),
        ("Yagi", lambda: AntennaFactory.create_yagi(num_directors=3, frequency=500e6)),
        ("Helix", lambda: AntennaFactory.create_helix(frequency=1e9, num_turns=5)),
    ]

    for name, factory_func in cases:
        print(f"\n--- Testing: {name} ---")
        try:
            antenna = factory_func()
        except TypeError:
            if name == "Dipole":
                antenna = AntennaFactory.create_dipole(length=0.1)
            elif name == "Off-Center Dipole":
                antenna = AntennaFactory.create_dipole(length=0.1, center=Vector3D(0.05, 0.05, 0))
            elif name == "Yagi":
                antenna = AntennaFactory.create_yagi(num_directors=3, frequency=500e6)
            elif name == "Helix":
                antenna = AntennaFactory.create_helix(frequency=1e9, num_turns=5)
            else:
                antenna = factory_func()

        bbox = antenna.get_bounding_box()
        # feed_point is already a Vector3D
        feed_pos = antenna.feed_point if antenna.feed_point else Vector3D(0, 0, 0)

        print(f"Antenna BBox: Min={print_vec(bbox.min_point)}, Max={print_vec(bbox.max_point)}")
        print(f"Feed Point: {print_vec(feed_pos)}")

        # Check FDTD Grid mapping
        freq = 1e9
        try:
            grid = create_grid_for_antenna(
                antenna, freq_max=freq, cells_per_lambda=10, pml_layers=4
            )

            # FDTD Origin (World coordinate of grid index 0,0,0)
            # grid._geometry_origin is actually the world coord of (0,0,0) ?
            # Let's check grid_to_world(0,0,0)
            origin_world = grid.grid_to_world(0, 0, 0)
            center_world = grid.grid_to_world(
                grid.config.nx // 2, grid.config.ny // 2, grid.config.nz // 2
            )

            print(f"FDTD Grid: {grid.config.nx}x{grid.config.ny}x{grid.config.nz}")
            print(f"FDTD Origin (0,0,0): {print_vec(origin_world)}")
            print(f"FDTD Center: {print_vec(center_world)}")

            # Map feed point to grid
            fi, fj, fk = grid.world_to_grid(feed_pos)
            feed_recovered = grid.grid_to_world(fi, fj, fk)
            dist_error = (feed_recovered - feed_pos).magnitude
            print(f"FDTD Feed Index: ({fi}, {fj}, {fk})")
            print(
                f"FDTD Feed Recovered: {print_vec(feed_recovered)} (Error: {dist_error*1000:.2f} mm)"
            )

        except Exception as e:
            print(f"FDTD Error: {e}")

        # Check FEM Mesh Generation (Conceptually)
        try:
            mg = MeshGenerator(antenna, freq)
            # Check domain calculation logic from code
            margin = mg.wavelength / 2.0
            domain_min = bbox.min_point - Vector3D(margin, margin, margin)
            domain_max = bbox.max_point + Vector3D(margin, margin, margin)

            mesh_center = (domain_min + domain_max) / 2

            print(f"FEM Domain Min: {print_vec(domain_min)}")
            print(f"FEM Domain Max: {print_vec(domain_max)}")
            print(f"FEM Geometric Center: {print_vec(mesh_center)}")

            # Check deviation of feed from center
            dev = (feed_pos - mesh_center).magnitude
            print(f"Feed deviation from FEM center: {dev*1000:.2f} mm")

            if dev > 1e-4:
                print("WARNING: FEM Solver using center-source would be WRONG!")

        except Exception as e:
            print(f"FEM Error: {e}")


if __name__ == "__main__":
    run_diagnostic()
