import numpy as np
from core.constants import C0
from visualization.smith_chart import (
    calculate_impedance_analytical,
    calculate_impedance_from_fdtd,
    ImpedanceResult,
    impedance_to_gamma,
    gamma_to_s11_db,
    gamma_to_vswr,
)
from core.grid import create_grid_for_antenna
from solver import FDTDSolver, GaussianSource, FieldProbe
from config import AntennaConfig
from antennas import create_antenna


def estimate_beamwidth(pattern, angles):
    max_val = np.max(pattern)
    half_power = max_val / 2
    
    above_half = pattern >= half_power
    if np.any(above_half):
        indices = np.where(above_half)[0]
        return angles[indices[-1]] - angles[indices[0]]
    return 360


def _calculate_radiation_pattern_analytical(antenna_config: AntennaConfig) -> dict:
    angles = np.linspace(0, 360, 361)
    theta_rad = np.radians(angles)
    
    e_theta = None
    e_phi = None
    
    if antenna_config.type in ['dipole', 'monopole', 'folded_dipole', 'v_dipole']:
        # Padrão de dipolo: sin²(θ)
        # No plano E (θ variando, φ=0)
        pattern_e = np.abs(np.sin(theta_rad)) ** 2
        # No plano H (θ=90°, φ variando) - omnidirecional
        pattern_h = np.ones_like(angles)
        e_theta = pattern_e.astype(complex)
        e_phi = np.zeros_like(pattern_e, dtype=complex)
        
    elif antenna_config.type == 'yagi':
        # Padrão direcional simplificado
        n_elements = antenna_config.num_directors + 2
        # Fator de array aproximado
        pattern_e = np.abs(np.sin(theta_rad)) * np.abs(np.sinc((theta_rad - np.pi/2) * n_elements / np.pi))
        pattern_e = pattern_e / (np.max(pattern_e) + 1e-10)
        pattern_h = pattern_e
        e_theta = pattern_e.astype(complex)
        e_phi = np.zeros_like(pattern_e, dtype=complex)
        
    elif antenna_config.type == 'patch':
        # Padrão de patch - broadside
        pattern_e = np.abs(np.cos(theta_rad - np.pi/2)) ** 2
        pattern_h = np.abs(np.cos(theta_rad - np.pi/2)) ** 2
        e_theta = pattern_e.astype(complex)
        e_phi = np.zeros_like(pattern_e, dtype=complex)
        
    elif antenna_config.type == 'helix':
        # Padrão de hélice axial
        pattern_e = np.abs(np.cos(theta_rad - np.pi/2)) ** 4
        pattern_h = pattern_e
        mag = np.sqrt(pattern_e / 2.0)
        e_theta = mag.astype(complex)
        e_phi = 1j * mag
        
    elif antenna_config.type == 'horn':
        # Padrão de corneta (aprox. cos^q)
        # q depende da área da abertura, aqui aproximado
        q_e = 6  # Moderadamente direcional
        q_h = 4
        pattern_e = np.abs(np.cos(theta_rad - np.pi/2)) ** q_e
        pattern_h = np.abs(np.cos(theta_rad - np.pi/2)) ** q_h
        e_theta = pattern_e.astype(complex)
        e_phi = np.zeros_like(pattern_e, dtype=complex)
        
    elif antenna_config.type == 'dish':
        if antenna_config.dish_diameter and antenna_config.frequency:
            wavelength = C0 / float(antenna_config.frequency)
            beamwidth_deg = 70.0 * wavelength / float(antenna_config.dish_diameter)
            beamwidth_deg = float(np.clip(beamwidth_deg, 1.0, 120.0))
        else:
            beamwidth_deg = 10.0
        k = 180.0 / beamwidth_deg
        arg = (theta_rad - np.pi/2) * k
        pattern_e = np.abs(np.sinc(arg/np.pi)) ** 2
        pattern_h = pattern_e
        e_theta = pattern_e.astype(complex)
        e_phi = np.zeros_like(pattern_e, dtype=complex)
        
    elif antenna_config.type == 'lpda':
        # Padrão LPDA (direcionalidade média, similar a Yagi mas banda larga)
        # Costuma ter f/b ratio menor que yagi
        pattern_e = np.abs(np.cos(theta_rad - np.pi/2)) ** 3
        # Adiciona um lóbulo traseiro pequeno
        back_lobe = 0.2 * np.abs(np.cos(theta_rad + np.pi/2)) ** 2
        pattern_e = pattern_e + back_lobe
        pattern_h = pattern_e
        e_theta = pattern_e.astype(complex)
        e_phi = np.zeros_like(pattern_e, dtype=complex)
        
    elif antenna_config.type == 'loop':
        # Loop pequeno: padrão similar ao dipolo curto mas polarização trocada
        # E-plane (plano do loop): Omnidirecional (círculo)
        # H-plane (eixo do loop): Nulo
        # Mas aqui theta=0 é eixo z (eixo do loop)
        # Então padrão é sin(theta)
        pattern_e = np.abs(np.sin(theta_rad))
        pattern_h = np.ones_like(theta_rad) # Aprox
        e_theta = pattern_e.astype(complex)
        e_phi = np.zeros_like(pattern_e, dtype=complex)

    else:
        pattern_e = np.ones_like(angles)
        pattern_h = np.ones_like(angles)
        e_theta = pattern_e.astype(complex)
        e_phi = np.zeros_like(pattern_e, dtype=complex)
    
    # Normaliza
    pattern_e = pattern_e / (np.max(pattern_e) + 1e-10)
    pattern_h = pattern_h / (np.max(pattern_h) + 1e-10)
    
    if e_theta is None:
        e_theta = pattern_e.astype(complex)
    if e_phi is None:
        e_phi = np.zeros_like(pattern_e, dtype=complex)
    
    e_left = (e_theta + 1j * e_phi) / np.sqrt(2.0)
    e_right = (e_theta - 1j * e_phi) / np.sqrt(2.0)
    pattern_left = np.abs(e_left) ** 2
    pattern_right = np.abs(e_right) ** 2
    pattern_left = pattern_left / (np.max(pattern_left) + 1e-10)
    pattern_right = pattern_right / (np.max(pattern_right) + 1e-10)
    
    front_mask = (angles >= 60) & (angles <= 120)
    back_mask = (angles >= 240) & (angles <= 300)
    if np.any(front_mask):
        front_max = float(np.max(pattern_e[front_mask]))
    else:
        front_max = float(np.max(pattern_e))
    if np.any(back_mask):
        back_max = float(np.max(pattern_e[back_mask]))
    else:
        back_max = front_max
    fb_ratio_db = 10 * np.log10((front_max + 1e-10) / (back_max + 1e-10))
    rear_angle = 270.0
    rear_idx = int(round(rear_angle / 360.0 * (len(angles) - 1)))
    rear_idx = max(0, min(rear_idx, len(angles) - 1))
    rear_val = float(pattern_e[rear_idx])
    fr_ratio_db = 10 * np.log10((front_max + 1e-10) / (rear_val + 1e-10))
    
    # Gera dados 3D simplificados (coarse mesh)
    theta_3d = np.linspace(0, np.pi, 37)  # 5 deg steps
    phi_3d = np.linspace(0, 2*np.pi, 73)
    
    mesh_points = []
    
    THETA, PHI = np.meshgrid(theta_3d, phi_3d, indexing='ij')
    
    if antenna_config.type in ['dipole', 'monopole', 'folded_dipole', 'v_dipole']:
        R = np.abs(np.sin(THETA)) ** 2
    elif antenna_config.type == 'yagi':
        n_elements = antenna_config.num_directors + 2
        R = np.abs(np.sin(THETA)) * np.abs(np.sinc((THETA - np.pi/2) * n_elements / np.pi))
    elif antenna_config.type == 'patch':
        R = np.abs(np.cos(THETA - np.pi/2)) ** 2 * (np.sin(PHI)**2 + 1)/2
    elif antenna_config.type == 'helix':
        R = np.abs(np.cos(THETA - np.pi/2)) ** 4
    elif antenna_config.type == 'horn':
        R = np.abs(np.cos(THETA - np.pi/2)) ** 5 * (np.cos(PHI)**2 * 0.5 + 0.5)
    elif antenna_config.type == 'dish':
        if antenna_config.dish_diameter and antenna_config.frequency:
            wavelength = C0 / float(antenna_config.frequency)
            beamwidth_deg = 70.0 * wavelength / float(antenna_config.dish_diameter)
            beamwidth_deg = float(np.clip(beamwidth_deg, 1.0, 120.0))
        else:
            beamwidth_deg = 10.0
        k_3d = 180.0 / beamwidth_deg
        arg = (THETA - np.pi/2) * k_3d
        R = np.abs(np.sinc(arg/np.pi)) ** 2
    elif antenna_config.type == 'lpda':
        R = np.abs(np.cos(THETA - np.pi/2)) ** 3
        # Lóbulo traseiro simplificado
        R += 0.2 * np.abs(np.cos(THETA + np.pi/2)) ** 2
    elif antenna_config.type == 'loop':
        # Loop (eixo z): padrão toroidal sin(theta)
        R = np.abs(np.sin(THETA))
    else:
        R = np.ones_like(THETA)
        
    # Normaliza R 3D
    R = R / (np.max(R) + 1e-10)
    
    pattern_3d = R.tolist()

    if antenna_config.type == 'dish' and antenna_config.dish_diameter and antenna_config.frequency:
        wavelength_dish = C0 / float(antenna_config.frequency)
        eta = 0.6
        d_over_lambda = float(antenna_config.dish_diameter) / wavelength_dish
        directivity_lin = eta * (np.pi * d_over_lambda) ** 2
        directivity_db = 10 * np.log10(directivity_lin + 1e-10)
    else:
        directivity_db = 10 * np.log10(np.max(pattern_e) ** 2 * 1.5 + 1e-10) + 2.15
    gain_db = directivity_db + 10 * np.log10(0.9)

    return {
        'angles': angles.tolist(),
        'pattern_e': pattern_e.tolist(),
        'pattern_h': pattern_h.tolist(),
        'pattern_3d': pattern_3d,
        'pattern_left': pattern_left.tolist(),
        'pattern_right': pattern_right.tolist(),
        'directivity_db': directivity_db,
        'gain_db': gain_db,
        '3db_beamwidth': estimate_beamwidth(pattern_e, angles),
        'fb_ratio_db': fb_ratio_db,
        'fr_ratio_db': fr_ratio_db
    }

def calculate_radiation_pattern(antenna_config: AntennaConfig, mode: str = "analytical") -> dict:
    if mode == "fdtd":
        try:
            antenna = create_antenna(antenna_config)
            freq = float(antenna_config.frequency)
            wavelength = C0 / freq
            grid = create_grid_for_antenna(
                antenna,
                freq_max=freq,
                cells_per_wavelength=15,
                pml_layers=6,
            )
            solver = FDTDSolver(grid, use_numba=True)
            solver.setup_near_field_box(margin=5)
            center = (grid.nx // 2, grid.ny // 2, grid.nz // 2)
            source = GaussianSource(
                position=center,
                component="Ez",
                amplitude=1.0,
                tau=1.0 / (2 * freq),
            )
            solver.add_source(source)
            probe = FieldProbe(position=center, component="Ez")
            solver.add_probe(probe)
            num_steps = 400
            for _ in range(num_steps):
                solver.step()
            theta, phi, e_theta_ff, e_phi_ff = solver.calculate_far_field(
                num_theta=37,
                num_phi=73,
            )
            p = np.abs(e_theta_ff) ** 2 + np.abs(e_phi_ff) ** 2
            p_max = np.max(p) + 1e-12
            p_norm = p / p_max
            theta_e = theta
            phi_h = phi
            idx_phi0 = 0
            pattern_e = p_norm[:, idx_phi0]
            idx_theta90 = int(np.argmin(np.abs(theta - (np.pi / 2))))
            pattern_h = p_norm[idx_theta90, :]
            pattern_e = pattern_e / (np.max(pattern_e) + 1e-10)
            pattern_h = pattern_h / (np.max(pattern_h) + 1e-10)
            angles = np.degrees(theta_e)
            e_theta = e_theta_ff[:, idx_phi0]
            e_phi = e_phi_ff[:, idx_phi0]
            e_left = (e_theta + 1j * e_phi) / np.sqrt(2.0)
            e_right = (e_theta - 1j * e_phi) / np.sqrt(2.0)
            pattern_left = np.abs(e_left) ** 2
            pattern_right = np.abs(e_right) ** 2
            pattern_left = pattern_left / (np.max(pattern_left) + 1e-10)
            pattern_right = pattern_right / (np.max(pattern_right) + 1e-10)
            theta_grid, phi_grid = np.meshgrid(theta, phi, indexing="ij")
            sin_theta = np.sin(theta_grid)
            dtheta = theta[1] - theta[0] if len(theta) > 1 else np.pi
            dphi = phi[1] - phi[0] if len(phi) > 1 else 2 * np.pi
            integral = np.sum(p * sin_theta) * dtheta * dphi + 1e-12
            directivity = 4 * np.pi * p_max / integral
            directivity_db = 10 * np.log10(directivity + 1e-12)
            efficiency = 0.9
            gain_db = directivity_db + 10 * np.log10(efficiency)
            angles_front = angles
            front_mask = (angles_front >= 60) & (angles_front <= 120)
            back_mask = (angles_front >= 240) & (angles_front <= 300)
            if np.any(front_mask):
                front_max = float(np.max(pattern_e[front_mask]))
            else:
                front_max = float(np.max(pattern_e))
            if np.any(back_mask):
                back_max = float(np.max(pattern_e[back_mask]))
            else:
                back_max = front_max
            fb_ratio_db = 10 * np.log10((front_max + 1e-10) / (back_max + 1e-10))
            rear_angle = 270.0
            rear_idx = int(
                round(rear_angle / 360.0 * (len(angles_front) - 1))
            )
            rear_idx = max(0, min(rear_idx, len(angles_front) - 1))
            rear_val = float(pattern_e[rear_idx])
            fr_ratio_db = 10 * np.log10(
                (front_max + 1e-10) / (rear_val + 1e-10)
            )
            pattern_3d = p_norm.tolist()
            return {
                "angles": angles.tolist(),
                "pattern_e": pattern_e.tolist(),
                "pattern_h": pattern_h.tolist(),
                "pattern_3d": pattern_3d,
                "pattern_left": pattern_left.tolist(),
                "pattern_right": pattern_right.tolist(),
                "directivity_db": directivity_db,
                "gain_db": gain_db,
                "3db_beamwidth": estimate_beamwidth(pattern_e, angles),
                "fb_ratio_db": fb_ratio_db,
                "fr_ratio_db": fr_ratio_db,
            }
        except Exception:
            return _calculate_radiation_pattern_analytical(antenna_config)
    return _calculate_radiation_pattern_analytical(antenna_config)


def calculate_smith_chart_data(antenna_config: AntennaConfig, mode: str = "analytical") -> dict:
    wavelength = C0 / antenna_config.frequency
    freq_center = antenna_config.frequency
    freq_min = freq_center * 0.5
    freq_max = freq_center * 1.5
    frequencies = np.linspace(freq_min, freq_max, 101)
    
    # Determina tipo e comprimento base para cálculo analítico
    if antenna_config.type in ["dipole", "folded_dipole"]:
        length = antenna_config.length or wavelength / 2
        antenna_type = "dipole"
    elif antenna_config.type == "monopole":
        length = antenna_config.length or wavelength / 4
        antenna_type = "monopole"
    elif antenna_config.type == "loop":
        length = antenna_config.length or wavelength
        antenna_type = "loop"
    else:
        # Outros tipos (Yagi, V-Dipole, Horn, Helix, etc) agora têm tratamento específico
        # no smith_chart.py ou usam fallback inteligente
        length = antenna_config.length or wavelength / 2
        antenna_type = antenna_config.type

    base_result = calculate_impedance_analytical(
        antenna_type,
        frequencies,
        length=length,
        z0=50.0,
        substrate_er=antenna_config.substrate_er,
        substrate_h=antenna_config.substrate_h,
        f_resonant=freq_center,
    )
    result: ImpedanceResult
    if mode == "fdtd":
        try:
            antenna = create_antenna(antenna_config)
            freq = float(antenna_config.frequency)
            grid = create_grid_for_antenna(
                antenna,
                freq_max=freq,
                cells_per_wavelength=15,
                pml_layers=6,
            )
            solver = FDTDSolver(grid, use_numba=True)
            center = (grid.nx // 2, grid.ny // 2, grid.nz // 2)
            source = GaussianSource(
                position=center,
                component="Ez",
                amplitude=1.0,
                tau=1.0 / (2 * freq),
            )
            solver.add_source(source)
            probe = FieldProbe(position=center, component="Ez")
            solver.add_probe(probe)
            num_steps = 400
            for _ in range(num_steps):
                solver.step()
            result = calculate_impedance_from_fdtd(
                solver,
                frequencies,
                z0=50.0,
            )
        except Exception:
            if antenna_config.type == "folded_dipole":
                impedance = base_result.impedance * 4.0
                gamma = np.array(
                    [impedance_to_gamma(z, base_result.z0) for z in impedance]
                )
                s11_db = np.array([gamma_to_s11_db(g) for g in gamma])
                vswr = np.array([gamma_to_vswr(g) for g in gamma])
                result = ImpedanceResult(
                    frequencies=base_result.frequencies,
                    impedance=impedance,
                    gamma=gamma,
                    s11_db=s11_db,
                    vswr=vswr,
                    z0=base_result.z0,
                )
            else:
                result = base_result
    else:
        if antenna_config.type == "folded_dipole":
            impedance = base_result.impedance * 4.0
            gamma = np.array(
                [impedance_to_gamma(z, base_result.z0) for z in impedance]
            )
            s11_db = np.array([gamma_to_s11_db(g) for g in gamma])
            vswr = np.array([gamma_to_vswr(g) for g in gamma])
            result = ImpedanceResult(
                frequencies=base_result.frequencies,
                impedance=impedance,
                gamma=gamma,
                s11_db=s11_db,
                vswr=vswr,
                z0=base_result.z0,
            )
        else:
            result = base_result
    gamma_real = np.real(result.gamma).tolist()
    gamma_imag = np.imag(result.gamma).tolist()
    gamma_mag = np.abs(result.gamma)
    power_delivered = 1.0 - np.clip(gamma_mag ** 2, 0.0, 0.999999)
    mismatch_loss_db = -10.0 * np.log10(np.clip(power_delivered, 1e-9, 1.0))
    gain_match_db = -mismatch_loss_db
    resonance = result.find_resonance()
    best_match = result.find_best_match()
    bandwidth = result.get_bandwidth(-10.0)
    return {
        "frequencies_mhz": (frequencies / 1e6).tolist(),
        "impedance_real": result.resistance.tolist(),
        "impedance_imag": result.reactance.tolist(),
        "gamma_real": gamma_real,
        "gamma_imag": gamma_imag,
        "gamma_mag": gamma_mag.tolist(),
        "s11_db": result.s11_db.tolist(),
        "vswr": np.clip(result.vswr, 1, 20).tolist(),
        "power_delivered": power_delivered.tolist(),
        "mismatch_loss_db": mismatch_loss_db.tolist(),
        "gain_match_db": gain_match_db.tolist(),
        "z0": result.z0,
        "resonance": {
            "frequency_mhz": resonance["frequency"] / 1e6,
            "impedance": f"{resonance['resistance']:.1f} + j{resonance['reactance']:.1f}",
            "s11_db": resonance["s11_db"],
            "vswr": resonance["vswr"],
        },
        "best_match": {
            "frequency_mhz": best_match["frequency"] / 1e6,
            "impedance": f"{best_match['resistance']:.1f} + j{best_match['reactance']:.1f}",
            "s11_db": best_match["s11_db"],
            "vswr": best_match["vswr"],
        },
        "bandwidth": {
            "min_mhz": bandwidth[0] / 1e6,
            "max_mhz": bandwidth[1] / 1e6,
            "width_mhz": bandwidth[2] / 1e6,
            "percent": 100 * bandwidth[2] / freq_center if bandwidth[2] > 0 else 0,
        },
    }

def calculate_parameters(frequency: float, directivity_db: float | None = None, efficiency: float = 0.9) -> dict:
    wavelength = C0 / frequency
    
    params = {
        'frequency_hz': frequency,
        'frequency_mhz': frequency / 1e6,
        'wavelength_m': wavelength,
        'wavelength_cm': wavelength * 100,
        'half_wavelength_cm': wavelength * 50,
        'quarter_wavelength_cm': wavelength * 25,
        'k': 2 * np.pi / wavelength,
        'omega': 2 * np.pi * frequency
    }
    
    if directivity_db is not None:
        gain_db = directivity_db + 10 * np.log10(efficiency)
        params['directivity_db'] = directivity_db
        params['gain_db'] = gain_db
        params['efficiency'] = efficiency
    
    return params
