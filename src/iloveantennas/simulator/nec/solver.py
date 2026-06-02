import necpp
import numpy as np

from ..core.geometry.topology import AntennaGraph
from .geometry import NECGeometryConverter


class NECSolver:
    def __init__(self, antenna: AntennaGraph, frequency: float):
        self.antenna = antenna
        self.frequency = frequency
        self.nec = necpp.nec_create()
        self.converter = NECGeometryConverter(frequency)
        self.tag_map = {}

    def setup(self):
        """Configures geometry, ground, frequency and excitation."""
        # Geometry
        self.tag_map = self.converter.apply_to_context(self.nec, self.antenna)

        # Ground Plane
        # By default, we use Free Space (no GN card).
        # TODO: Add support for ground plane configuration via AntennaGraph properties or Solver config
        # necpp.nec_gn_card(self.nec, 1, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # Frequency
        # nec_fr_card(nec, type, N_steps, start_freq, step_size)
        # NEC uses MHz for frequency
        freq_mhz = self.frequency / 1e6
        necpp.nec_fr_card(self.nec, 0, 1, freq_mhz, 0.0)

        # Excitation
        exc_loc = self.converter.find_excitation_segment(self.antenna, self.tag_map)
        if exc_loc:
            tag, seg = exc_loc
            # nec_ex_card(nec, type, tag, seg, admittance, 0, 0, real, imag, mag, phase)
            # Type 0 = Voltage source
            necpp.nec_ex_card(self.nec, 0, tag, seg, 0, 0, 0, 1.0, 0.0, 0.0, 0.0)
        else:
            print("Warning: No excitation point found for NEC simulation")

    def run(self):
        """Runs the simulation and returns impedance."""
        self.setup()

        # Execute
        necpp.nec_xq_card(self.nec, 0)

        return self.get_impedance()

    def run_frequency_sweep(self, start_freq: float, stop_freq: float, num_points: int):
        """Runs a frequency sweep."""
        # Geometry only needs to be set once
        self.tag_map = self.converter.apply_to_context(self.nec, self.antenna)
        # necpp.nec_gn_card(self.nec, 1, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0) # Free space

        # Excitation
        exc_loc = self.converter.find_excitation_segment(self.antenna, self.tag_map)
        if exc_loc:
            tag, seg = exc_loc
            necpp.nec_ex_card(self.nec, 0, tag, seg, 0, 0, 0, 1.0, 0.0, 0.0, 0.0)

        # Frequency Sweep
        start_mhz = start_freq / 1e6
        stop_mhz = stop_freq / 1e6
        step_mhz = (stop_mhz - start_mhz) / (num_points - 1) if num_points > 1 else 0

        necpp.nec_fr_card(self.nec, 0, num_points, start_mhz, step_mhz)

        # Execute
        necpp.nec_xq_card(self.nec, 0)

        results = []
        for i in range(num_points):
            z_real = necpp.nec_impedance_real(self.nec, i)
            z_imag = necpp.nec_impedance_imag(self.nec, i)
            freq = start_freq + i * (step_mhz * 1e6)
            results.append((freq, complex(z_real, z_imag)))

        return results

    def get_impedance(self):
        z_real = necpp.nec_impedance_real(self.nec, 0)
        z_imag = necpp.nec_impedance_imag(self.nec, 0)
        return complex(z_real, z_imag)

    def cleanup(self):
        necpp.nec_delete(self.nec)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
