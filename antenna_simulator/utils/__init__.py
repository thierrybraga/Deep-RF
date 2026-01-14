"""
IloveAntenas Utils Module
=======================
Funções utilitárias para simulação de antenas.
"""

from .helpers import (
    # Conversões
    db_to_linear, linear_to_db, dbm_to_watts, watts_to_dbm,
    deg_to_rad, rad_to_deg,
    feet_to_meters, inches_to_meters, meters_to_feet, meters_to_inches,
    awg_to_diameter_m, awg_to_radius_m, meters_to_awg,
    elevation_azimuth_to_theta_phi, theta_phi_to_elevation_azimuth,
    # Cálculos de antena
    calculate_vswr, calculate_return_loss, calculate_reflection_coefficient,
    calculate_mismatch_loss, calculate_bandwidth_from_q, calculate_effective_area,
    calculate_friis_path_loss, calculate_link_budget,
    # Processamento de sinal
    fft_freq, apply_window, smooth_data, interpolate_pattern,
    # Exportação
    export_to_csv, export_to_nec2, export_touchstone, save_field_vtk,
    # Importação
    load_touchstone, load_nec2_output,
    # Grade
    calculate_grid_memory, optimal_grid_size,
    # Logging
    SimulationLogger
)

__all__ = [
    'db_to_linear', 'linear_to_db', 'dbm_to_watts', 'watts_to_dbm',
    'deg_to_rad', 'rad_to_deg',
    'feet_to_meters', 'inches_to_meters', 'meters_to_feet', 'meters_to_inches',
    'awg_to_diameter_m', 'awg_to_radius_m', 'meters_to_awg',
    'elevation_azimuth_to_theta_phi', 'theta_phi_to_elevation_azimuth',
    'calculate_vswr', 'calculate_return_loss', 'calculate_reflection_coefficient',
    'calculate_mismatch_loss', 'calculate_bandwidth_from_q', 'calculate_effective_area',
    'calculate_friis_path_loss', 'calculate_link_budget',
    'fft_freq', 'apply_window', 'smooth_data', 'interpolate_pattern',
    'export_to_csv', 'export_to_nec2', 'export_touchstone', 'save_field_vtk',
    'load_touchstone', 'load_nec2_output',
    'calculate_grid_memory', 'optimal_grid_size',
    'SimulationLogger'
]
