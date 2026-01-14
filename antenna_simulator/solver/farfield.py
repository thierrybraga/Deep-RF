"""
Transformação Near-to-Far Field e funções de análise de antena.
"""

import numpy as np
from typing import Tuple
from core.constants import C0
from core.grid import GridConfig
from .monitors import NearFieldBox

class NearToFarField:
    """
    Transformação de campos near-field para far-field.
    
    Usa o princípio de equivalência de Huygens para calcular
    o diagrama de radiação a partir dos campos na caixa near-field.
    """
    
    def __init__(
        self,
        nf_box: NearFieldBox,
        grid_config: GridConfig,
        frequency: float
    ):
        """
        Args:
            nf_box: Caixa de near-field com dados gravados
            grid_config: Configuração da grade
            frequency: Frequência de interesse [Hz]
        """
        self.nf_box = nf_box
        self.config = grid_config
        self.frequency = frequency
        self.wavelength = C0 / frequency
        self.k = 2 * np.pi / self.wavelength  # Número de onda
    
    def calculate_far_field(
        self,
        theta_range: Tuple[float, float] = (0, np.pi),
        phi_range: Tuple[float, float] = (0, 2*np.pi),
        num_theta: int = 91,
        num_phi: int = 181
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calcula campo far-field em coordenadas esféricas.
        
        Args:
            theta_range: Intervalo de θ [rad]
            phi_range: Intervalo de φ [rad]
            num_theta: Número de pontos em θ
            num_phi: Número de pontos em φ
            
        Returns:
            Tupla (theta, phi, E_theta, E_phi) com arrays 2D
        """
        theta = np.linspace(theta_range[0], theta_range[1], num_theta)
        phi = np.linspace(phi_range[0], phi_range[1], num_phi)
        
        THETA, PHI = np.meshgrid(theta, phi, indexing='ij')
        
        # Direções de observação
        sin_theta = np.sin(THETA)
        cos_theta = np.cos(THETA)
        sin_phi = np.sin(PHI)
        cos_phi = np.cos(PHI)
        
        # Vetores unitários esféricos
        r_hat = np.stack([
            sin_theta * cos_phi,
            sin_theta * sin_phi,
            cos_theta
        ], axis=-1)
        
        # (theta_hat e phi_hat podem ser úteis para cálculos mais complexos de polarização)
        
        # Inicializa campos far-field
        E_theta = np.zeros((num_theta, num_phi), dtype=complex)
        E_phi = np.zeros((num_theta, num_phi), dtype=complex)
        
        # Integração sobre superfície near-field (simplificada)
        # Aqui usamos apenas a face z_min como exemplo
        if len(self.nf_box.E_data['z_min']) == 0:
            return theta, phi, np.abs(E_theta), np.abs(E_phi)
        
        # Pega último snapshot ou faz FFT para frequência específica
        E_surface = self.nf_box.E_data['z_min'][-1]
        
        # Posição do centro da face
        i1, i2 = self.nf_box.i_range
        j1, j2 = self.nf_box.j_range
        k1, _ = self.nf_box.k_range
        
        dx, dy = self.config.dx, self.config.dy
        
        # Integração numérica simplificada
        for i in range(E_surface.shape[0]):
            for j in range(E_surface.shape[1]):
                # Posição do ponto fonte
                x_src = (i1 + i) * dx
                y_src = (j1 + j) * dy
                z_src = k1 * self.config.dz
                
                r_src = np.array([x_src, y_src, z_src])
                
                # Fase devido à posição
                phase = -1j * self.k * np.sum(r_hat * r_src, axis=-1)
                
                # Contribuição para o campo (simplificado)
                contrib = E_surface[i, j] * np.exp(phase) * dx * dy
                
                # Projeções
                E_theta += contrib * cos_theta
                E_phi += contrib * (-sin_phi)
        
        # Normaliza pelo fator de propagação far-field
        factor = 1j * self.k * np.exp(-1j * self.k) / (4 * np.pi)
        E_theta *= factor
        E_phi *= factor
        
        return theta, phi, np.abs(E_theta), np.abs(E_phi)


def calculate_directivity(E_theta: np.ndarray, E_phi: np.ndarray) -> float:
    """Calcula diretividade máxima em dB"""
    U = np.abs(E_theta)**2 + np.abs(E_phi)**2
    max_U = np.max(U)
    avg_U = np.mean(U)
    return 10 * np.log10(max_U / (avg_U + 1e-30))


def calculate_gain(directivity_db: float, efficiency: float = 1.0) -> float:
    """Calcula ganho em dBi"""
    return directivity_db + 10 * np.log10(efficiency)


def dB(value: float) -> float:
    """Converte valor linear para dB"""
    return 10 * np.log10(value + 1e-30)


def dBi(gain: float) -> float:
    """Converte ganho linear para dBi"""
    return dB(gain)
