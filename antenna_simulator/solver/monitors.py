"""
Monitores e probes de campo para o solver FDTD.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Tuple, List, Dict

@dataclass
class FieldProbe:
    """
    Monitor de campo em um ponto específico.
    
    Attributes:
        position: Posição na grade (i, j, k)
        component: Componente a monitorar ('Ex', 'Ey', 'Ez', 'Hx', 'Hy', 'Hz')
        data: Dados coletados [(time, value), ...]
    """
    position: Tuple[int, int, int]
    component: str = 'Ez'
    data: List[Tuple[float, float]] = field(default_factory=list)
    
    def record(self, time: float, value: float):
        self.data.append((time, value))
    
    def get_time_series(self) -> Tuple[np.ndarray, np.ndarray]:
        """Retorna arrays de tempo e valores"""
        if not self.data:
            return np.array([]), np.array([])
        times, values = zip(*self.data)
        return np.array(times), np.array(values)
    
    def clear(self):
        self.data.clear()


@dataclass
class NearFieldBox:
    """
    Caixa para extração de campos near-field (para transformação far-field).
    
    Attributes:
        i_range, j_range, k_range: Intervalos de índices da caixa
        E_data: Campos E tangenciais armazenados
        H_data: Campos H tangenciais armazenados
        times: Tempos de gravação
    """
    i_range: Tuple[int, int]
    j_range: Tuple[int, int]
    k_range: Tuple[int, int]
    
    E_data: Dict[str, List[np.ndarray]] = field(default_factory=dict)
    H_data: Dict[str, List[np.ndarray]] = field(default_factory=dict)
    times: List[float] = field(default_factory=list)
    
    def __post_init__(self):
        # Inicializa dicionários para cada face
        faces = ['x_min', 'x_max', 'y_min', 'y_max', 'z_min', 'z_max']
        for face in faces:
            self.E_data[face] = []
            self.H_data[face] = []
