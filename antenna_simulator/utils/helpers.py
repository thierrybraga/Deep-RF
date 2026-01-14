"""
IloveAntenas Utils - Funções Utilitárias
======================================
Funções auxiliares para conversão, cálculos e I/O.
"""

import numpy as np
from typing import Tuple, List, Dict, Any, Optional
import json
from pathlib import Path
import struct


# =============================================================================
# Constantes de Conversão
# =============================================================================

def db_to_linear(db: float) -> float:
    """Converte dB para linear (potência)"""
    return 10 ** (db / 10)


def linear_to_db(linear: float) -> float:
    """Converte linear para dB (potência)"""
    return 10 * np.log10(linear + 1e-30)


def dbm_to_watts(dbm: float) -> float:
    """Converte dBm para Watts"""
    return 10 ** ((dbm - 30) / 10)


def watts_to_dbm(watts: float) -> float:
    """Converte Watts para dBm"""
    return 10 * np.log10(watts + 1e-30) + 30


def deg_to_rad(deg: float) -> float:
    """Converte graus para radianos"""
    return np.radians(deg)


def rad_to_deg(rad: float) -> float:
    """Converte radianos para graus"""
    return np.degrees(rad)


def feet_to_meters(feet: float) -> float:
    return feet * 0.3048


def inches_to_meters(inches: float) -> float:
    return inches * 0.0254


def meters_to_feet(meters: float) -> float:
    return meters / 0.3048


def meters_to_inches(meters: float) -> float:
    return meters / 0.0254


def awg_to_diameter_m(awg: int) -> float:
    diameter_mm = 0.127 * (92 ** ((36 - awg) / 39.0))
    return diameter_mm / 1000.0


def awg_to_radius_m(awg: int) -> float:
    return awg_to_diameter_m(awg) / 2.0


def meters_to_awg(diameter_m: float) -> int:
    diameter_mm = diameter_m * 1000.0
    if diameter_mm <= 0:
        return 0
    best_awg = 0
    best_err = float("inf")
    for awg in range(0, 41):
        d_mm = 0.127 * (92 ** ((36 - awg) / 39.0))
        err = abs(d_mm - diameter_mm)
        if err < best_err:
            best_err = err
            best_awg = awg
    return best_awg


def elevation_azimuth_to_theta_phi(elevation_deg: float, azimuth_deg: float) -> Tuple[float, float]:
    theta = 90.0 - elevation_deg
    phi = azimuth_deg
    return theta, phi


def theta_phi_to_elevation_azimuth(theta_deg: float, phi_deg: float) -> Tuple[float, float]:
    elevation = 90.0 - theta_deg
    azimuth = phi_deg
    return elevation, azimuth

# =============================================================================
# Cálculos de Antena
# =============================================================================

def calculate_vswr(gamma: complex) -> float:
    """
    Calcula VSWR a partir do coeficiente de reflexão.
    
    Args:
        gamma: Coeficiente de reflexão (complexo)
        
    Returns:
        VSWR (>= 1)
    """
    rho = abs(gamma)
    if rho >= 1:
        return float('inf')
    return (1 + rho) / (1 - rho)


def calculate_return_loss(gamma: complex) -> float:
    """
    Calcula Return Loss em dB.
    
    Args:
        gamma: Coeficiente de reflexão
        
    Returns:
        Return Loss (dB, positivo)
    """
    rho = abs(gamma)
    if rho == 0:
        return float('inf')
    return -20 * np.log10(rho)


def calculate_reflection_coefficient(z_load: complex, z_ref: float = 50.0) -> complex:
    """
    Calcula coeficiente de reflexão.
    
    Args:
        z_load: Impedância da carga
        z_ref: Impedância de referência (tipicamente 50Ω)
        
    Returns:
        Coeficiente de reflexão Γ
    """
    return (z_load - z_ref) / (z_load + z_ref)


def calculate_mismatch_loss(vswr: float) -> float:
    """
    Calcula perda por descasamento em dB.
    
    Args:
        vswr: VSWR
        
    Returns:
        Perda em dB
    """
    if vswr <= 1:
        return 0.0
    rho = (vswr - 1) / (vswr + 1)
    return -10 * np.log10(1 - rho**2)


def calculate_bandwidth_from_q(f0: float, q: float) -> float:
    """
    Calcula largura de banda a partir do fator Q.
    
    Args:
        f0: Frequência central (Hz)
        q: Fator de qualidade
        
    Returns:
        Largura de banda (Hz)
    """
    return f0 / q


def calculate_effective_area(gain: float, wavelength: float) -> float:
    """
    Calcula área efetiva da antena.
    
    Args:
        gain: Ganho linear
        wavelength: Comprimento de onda (m)
        
    Returns:
        Área efetiva (m²)
    """
    return gain * wavelength**2 / (4 * np.pi)


def calculate_friis_path_loss(d: float, freq: float) -> float:
    """
    Calcula perda de percurso (Friis) em dB.
    
    Args:
        d: Distância (m)
        freq: Frequência (Hz)
        
    Returns:
        Perda de percurso (dB)
    """
    c = 299792458
    wavelength = c / freq
    return 20 * np.log10(4 * np.pi * d / wavelength)


def calculate_link_budget(
    pt_dbm: float,
    gt_dbi: float,
    gr_dbi: float,
    freq: float,
    distance: float,
    losses_db: float = 0
) -> float:
    """
    Calcula potência recebida usando equação de Friis.
    
    Args:
        pt_dbm: Potência transmitida (dBm)
        gt_dbi: Ganho da antena TX (dBi)
        gr_dbi: Ganho da antena RX (dBi)
        freq: Frequência (Hz)
        distance: Distância (m)
        losses_db: Perdas adicionais (dB)
        
    Returns:
        Potência recebida (dBm)
    """
    fspl = calculate_friis_path_loss(distance, freq)
    return pt_dbm + gt_dbi + gr_dbi - fspl - losses_db


# =============================================================================
# Processamento de Sinal
# =============================================================================

def fft_freq(data: np.ndarray, dt: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calcula FFT e retorna frequências.
    
    Args:
        data: Sinal no tempo
        dt: Intervalo de tempo
        
    Returns:
        (frequências, magnitudes)
    """
    n = len(data)
    freqs = np.fft.fftfreq(n, dt)
    spectrum = np.fft.fft(data)
    
    # Pega apenas frequências positivas
    pos_mask = freqs >= 0
    return freqs[pos_mask], np.abs(spectrum[pos_mask])


def apply_window(data: np.ndarray, window: str = 'hann') -> np.ndarray:
    """
    Aplica janela ao sinal.
    
    Args:
        data: Sinal de entrada
        window: Tipo de janela ('hann', 'hamming', 'blackman', 'kaiser')
        
    Returns:
        Sinal com janela aplicada
    """
    n = len(data)
    
    if window == 'hann':
        w = np.hanning(n)
    elif window == 'hamming':
        w = np.hamming(n)
    elif window == 'blackman':
        w = np.blackman(n)
    elif window == 'kaiser':
        w = np.kaiser(n, 14)
    else:
        w = np.ones(n)
    
    return data * w


def smooth_data(data: np.ndarray, window_size: int = 5) -> np.ndarray:
    """
    Suaviza dados com média móvel.
    
    Args:
        data: Dados de entrada
        window_size: Tamanho da janela
        
    Returns:
        Dados suavizados
    """
    kernel = np.ones(window_size) / window_size
    return np.convolve(data, kernel, mode='same')


def interpolate_pattern(
    angles: np.ndarray,
    pattern: np.ndarray,
    new_angles: np.ndarray
) -> np.ndarray:
    """
    Interpola diagrama de radiação para novos ângulos.
    
    Args:
        angles: Ângulos originais (graus)
        pattern: Padrão original
        new_angles: Novos ângulos
        
    Returns:
        Padrão interpolado
    """
    return np.interp(new_angles, angles, pattern)


# =============================================================================
# Exportação de Arquivos
# =============================================================================

def export_to_csv(
    filename: str,
    data: Dict[str, np.ndarray],
    header: str = None
) -> None:
    """
    Exporta dados para CSV.
    
    Args:
        filename: Nome do arquivo
        data: Dicionário com colunas
        header: Cabeçalho opcional
    """
    # Prepara colunas
    columns = list(data.keys())
    values = np.column_stack([data[k] for k in columns])
    
    with open(filename, 'w') as f:
        if header:
            f.write(f"# {header}\n")
        f.write(','.join(columns) + '\n')
        
        for row in values:
            f.write(','.join(f'{v:.6e}' for v in row) + '\n')


def export_to_nec2(
    filename: str,
    wires: List[Dict],
    frequency: float,
    comments: str = None
) -> None:
    """
    Exporta geometria para formato NEC2.
    
    Args:
        filename: Nome do arquivo
        wires: Lista de fios [{start, end, radius, segments}]
        frequency: Frequência (MHz)
        comments: Comentários opcionais
    """
    lines = []
    
    # Comentários
    lines.append("CM IloveAntenas Export to NEC2")
    if comments:
        lines.append(f"CM {comments}")
    lines.append("CE")
    
    # Fios
    for i, wire in enumerate(wires, 1):
        x1, y1, z1 = wire['start']
        x2, y2, z2 = wire['end']
        r = wire.get('radius', 0.001)
        segs = wire.get('segments', 11)
        
        lines.append(
            f"GW {i:3d} {segs:3d} "
            f"{x1:10.5f} {y1:10.5f} {z1:10.5f} "
            f"{x2:10.5f} {y2:10.5f} {z2:10.5f} "
            f"{r:10.6f}"
        )
    
    # Fim da geometria
    lines.append("GE 0")
    
    # Excitação no centro do primeiro fio
    lines.append("EX 0 1 6 0 1.0 0.0")
    
    # Frequência
    lines.append(f"FR 0 1 0 0 {frequency:.3f} 0")
    
    # Solicitações de padrão de radiação
    lines.append("RP 0 181 1 1000 -90.0 0.0 1.0 1.0")
    lines.append("RP 0 1 360 1000 90.0 0.0 1.0 1.0")
    
    # Fim
    lines.append("EN")
    
    with open(filename, 'w') as f:
        f.write('\n'.join(lines))


def export_touchstone(
    filename: str,
    frequencies: np.ndarray,
    s_params: np.ndarray,
    z_ref: float = 50.0,
    format: str = 'MA'
) -> None:
    """
    Exporta parâmetros S para formato Touchstone (.s1p ou .s2p).
    
    Args:
        filename: Nome do arquivo
        frequencies: Frequências (Hz)
        s_params: Parâmetros S (complexos)
        z_ref: Impedância de referência
        format: 'MA' (mag/angle), 'DB' (dB/angle), 'RI' (real/imag)
    """
    num_ports = 1 if s_params.ndim == 1 else s_params.shape[1]
    ext = f".s{num_ports}p"
    
    if not filename.endswith(ext):
        filename += ext
    
    with open(filename, 'w') as f:
        f.write(f"! IloveAntenas Touchstone Export\n")
        f.write(f"# HZ S {format} R {z_ref}\n")
        
        for i, freq in enumerate(frequencies):
            if s_params.ndim == 1:
                s = s_params[i]
            else:
                s = s_params[i, 0, 0]
            
            if format == 'MA':
                mag = abs(s)
                ang = np.angle(s, deg=True)
                f.write(f"{freq:.6e} {mag:.6e} {ang:.2f}\n")
            elif format == 'DB':
                db = 20 * np.log10(abs(s) + 1e-30)
                ang = np.angle(s, deg=True)
                f.write(f"{freq:.6e} {db:.6e} {ang:.2f}\n")
            else:  # RI
                f.write(f"{freq:.6e} {s.real:.6e} {s.imag:.6e}\n")


def save_field_vtk(
    filename: str,
    grid_shape: Tuple[int, int, int],
    dx: float,
    fields: Dict[str, np.ndarray]
) -> None:
    """
    Salva campos em formato VTK para visualização em ParaView.
    
    Args:
        filename: Nome do arquivo
        grid_shape: (nx, ny, nz)
        dx: Espaçamento da grade
        fields: Dicionário com campos {'Ex': array, ...}
    """
    nx, ny, nz = grid_shape
    
    with open(filename, 'w') as f:
        # Cabeçalho VTK
        f.write("# vtk DataFile Version 3.0\n")
        f.write("IloveAntenas Field Data\n")
        f.write("ASCII\n")
        f.write("DATASET STRUCTURED_POINTS\n")
        f.write(f"DIMENSIONS {nx} {ny} {nz}\n")
        f.write(f"ORIGIN 0 0 0\n")
        f.write(f"SPACING {dx} {dx} {dx}\n")
        f.write(f"POINT_DATA {nx*ny*nz}\n")
        
        # Campos
        for name, field in fields.items():
            f.write(f"SCALARS {name} float 1\n")
            f.write("LOOKUP_TABLE default\n")
            
            for k in range(nz):
                for j in range(ny):
                    for i in range(nx):
                        f.write(f"{field[i,j,k]:.6e}\n")


# =============================================================================
# Importação de Arquivos
# =============================================================================

def load_touchstone(filename: str) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Carrega arquivo Touchstone.
    
    Args:
        filename: Nome do arquivo
        
    Returns:
        (frequências, s_params, z_ref)
    """
    frequencies = []
    s_params = []
    z_ref = 50.0
    format_type = 'MA'
    freq_unit = 1.0
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Ignora comentários
            if line.startswith('!') or not line:
                continue
            
            # Linha de opções
            if line.startswith('#'):
                parts = line.upper().split()
                for i, p in enumerate(parts):
                    if p == 'HZ':
                        freq_unit = 1.0
                    elif p == 'KHZ':
                        freq_unit = 1e3
                    elif p == 'MHZ':
                        freq_unit = 1e6
                    elif p == 'GHZ':
                        freq_unit = 1e9
                    elif p in ('MA', 'DB', 'RI'):
                        format_type = p
                    elif p == 'R':
                        z_ref = float(parts[i+1])
                continue
            
            # Dados
            parts = line.split()
            if len(parts) >= 3:
                freq = float(parts[0]) * freq_unit
                
                if format_type == 'MA':
                    mag = float(parts[1])
                    ang = np.radians(float(parts[2]))
                    s = mag * np.exp(1j * ang)
                elif format_type == 'DB':
                    db = float(parts[1])
                    ang = np.radians(float(parts[2]))
                    mag = 10 ** (db / 20)
                    s = mag * np.exp(1j * ang)
                else:  # RI
                    real = float(parts[1])
                    imag = float(parts[2])
                    s = complex(real, imag)
                
                frequencies.append(freq)
                s_params.append(s)
    
    return np.array(frequencies), np.array(s_params), z_ref


def load_nec2_output(filename: str) -> Dict[str, Any]:
    """
    Carrega resultados de simulação NEC2.
    
    Args:
        filename: Nome do arquivo de saída NEC2
        
    Returns:
        Dicionário com resultados
    """
    results = {
        'impedance': [],
        'gain': [],
        'pattern': {'theta': [], 'phi': [], 'gain': []}
    }
    
    # Parser simplificado - NEC2 output é complexo
    # Implementação completa requereria análise mais detalhada
    
    return results


# =============================================================================
# Utilidades de Grade
# =============================================================================

def calculate_grid_memory(nx: int, ny: int, nz: int, num_arrays: int = 24) -> float:
    """
    Estima uso de memória para grade FDTD.
    
    Args:
        nx, ny, nz: Dimensões da grade
        num_arrays: Número de arrays (E, H, coeficientes)
        
    Returns:
        Memória em MB
    """
    cells = nx * ny * nz
    bytes_per_cell = 8  # float64
    total_bytes = cells * bytes_per_cell * num_arrays
    return total_bytes / (1024 * 1024)


def optimal_grid_size(
    bbox_size: Tuple[float, float, float],
    wavelength: float,
    cells_per_wavelength: int = 20,
    pml_layers: int = 8
) -> Tuple[int, int, int]:
    """
    Calcula tamanho ótimo da grade.
    
    Args:
        bbox_size: Tamanho da bounding box (x, y, z) em metros
        wavelength: Comprimento de onda em metros
        cells_per_wavelength: Resolução desejada
        pml_layers: Camadas de PML
        
    Returns:
        (nx, ny, nz)
    """
    dx = wavelength / cells_per_wavelength
    
    # Células para geometria
    nx = int(np.ceil(bbox_size[0] / dx))
    ny = int(np.ceil(bbox_size[1] / dx))
    nz = int(np.ceil(bbox_size[2] / dx))
    
    # Adiciona margem e PML
    margin = cells_per_wavelength  # Uma wavelength de margem
    nx += 2 * (margin + pml_layers)
    ny += 2 * (margin + pml_layers)
    nz += 2 * (margin + pml_layers)
    
    # Arredonda para múltiplos de 4 (otimização)
    nx = ((nx + 3) // 4) * 4
    ny = ((ny + 3) // 4) * 4
    nz = ((nz + 3) // 4) * 4
    
    return nx, ny, nz


# =============================================================================
# Logging e Debug
# =============================================================================

class SimulationLogger:
    """Logger para simulações"""
    
    def __init__(self, filename: str = None, verbose: bool = True):
        self.filename = filename
        self.verbose = verbose
        self.log_entries = []
    
    def log(self, message: str, level: str = 'INFO'):
        """Registra mensagem"""
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        entry = f"[{timestamp}] [{level}] {message}"
        
        self.log_entries.append(entry)
        
        if self.verbose:
            print(entry)
        
        if self.filename:
            with open(self.filename, 'a') as f:
                f.write(entry + '\n')
    
    def info(self, message: str):
        self.log(message, 'INFO')
    
    def warning(self, message: str):
        self.log(message, 'WARNING')
    
    def error(self, message: str):
        self.log(message, 'ERROR')
    
    def debug(self, message: str):
        self.log(message, 'DEBUG')


__all__ = [
    # Conversões
    'db_to_linear', 'linear_to_db', 'dbm_to_watts', 'watts_to_dbm',
    'deg_to_rad', 'rad_to_deg',
    'feet_to_meters', 'inches_to_meters', 'meters_to_feet', 'meters_to_inches',
    'awg_to_diameter_m', 'awg_to_radius_m', 'meters_to_awg',
    'elevation_azimuth_to_theta_phi', 'theta_phi_to_elevation_azimuth',
    # Cálculos
    'calculate_vswr', 'calculate_return_loss', 'calculate_reflection_coefficient',
    'calculate_mismatch_loss', 'calculate_bandwidth_from_q', 'calculate_effective_area',
    'calculate_friis_path_loss', 'calculate_link_budget',
    # Processamento
    'fft_freq', 'apply_window', 'smooth_data', 'interpolate_pattern',
    # Exportação
    'export_to_csv', 'export_to_nec2', 'export_touchstone', 'save_field_vtk',
    # Importação
    'load_touchstone', 'load_nec2_output',
    # Grade
    'calculate_grid_memory', 'optimal_grid_size',
    # Logging
    'SimulationLogger'
]
