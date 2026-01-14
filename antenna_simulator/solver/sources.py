"""
Fontes de excitação para o solver FDTD.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Callable, Dict
from enum import Enum
from abc import ABC, abstractmethod

from core.constants import C0

class SourceType(Enum):
    """Tipos de fonte de excitação"""
    GAUSSIAN = "gaussian"
    SINE = "sine"
    MODULATED_GAUSSIAN = "modulated_gaussian"
    RICKER = "ricker"  # Wavelet mexicano
    CUSTOM = "custom"


@dataclass
class Source(ABC):
    """Classe base abstrata para fontes de excitação"""
    position: Tuple[int, int, int]  # Posição na grade (i, j, k)
    component: str = 'Ez'  # Componente do campo a excitar
    amplitude: float = 1.0
    
    @abstractmethod
    def get_value(self, time: float) -> float:
        """Retorna valor da fonte no tempo especificado"""
        pass
    
    @abstractmethod
    def is_active(self, time: float) -> bool:
        """Verifica se a fonte está ativa no tempo especificado"""
        pass


@dataclass
class GaussianSource(Source):
    """
    Fonte com pulso Gaussiano.
    
    f(t) = A * exp(-(t - t₀)² / (2τ²))
    
    Attributes:
        t0: Tempo central do pulso [s]
        tau: Largura do pulso [s]
    """
    t0: float = 0.0
    tau: float = 1e-9
    
    def __post_init__(self):
        if self.t0 == 0:
            self.t0 = 4 * self.tau  # Garante que o pulso começa suavemente
    
    def get_value(self, time: float) -> float:
        return self.amplitude * np.exp(-((time - self.t0)**2) / (2 * self.tau**2))
    
    def is_active(self, time: float) -> bool:
        return abs(time - self.t0) < 6 * self.tau
    
    @property
    def bandwidth(self) -> float:
        """Largura de banda aproximada (-3dB)"""
        return 0.44 / self.tau
    
    @property
    def center_frequency(self) -> float:
        """Frequência central (DC para Gaussiana pura)"""
        return 0.0


@dataclass
class SineSource(Source):
    """
    Fonte senoidal contínua.
    
    f(t) = A * sin(2πft + φ)
    
    Attributes:
        frequency: Frequência [Hz]
        phase: Fase inicial [rad]
        ramp_time: Tempo de rampa para suavizar o início [s]
    """
    frequency: float = 1e9
    phase: float = 0.0
    ramp_time: float = 0.0
    
    def get_value(self, time: float) -> float:
        # Rampa de amplitude para evitar transientes
        if self.ramp_time > 0 and time < self.ramp_time:
            ramp = np.sin(np.pi * time / (2 * self.ramp_time))**2
        else:
            ramp = 1.0
        
        return self.amplitude * ramp * np.sin(2 * np.pi * self.frequency * time + self.phase)
    
    def is_active(self, time: float) -> bool:
        return True  # Sempre ativa
    
    @property
    def wavelength(self) -> float:
        return C0 / self.frequency
    
    @property
    def period(self) -> float:
        return 1.0 / self.frequency


@dataclass
class ModulatedGaussianSource(Source):
    """
    Pulso Gaussiano modulado (derivada da Gaussiana).
    
    f(t) = A * (t - t₀)/τ² * exp(-(t - t₀)² / (2τ²)) * sin(2πf₀t)
    
    Útil para excitação banda larga centrada em f₀.
    
    Attributes:
        center_freq: Frequência central [Hz]
        bandwidth: Largura de banda [Hz]
        t0: Tempo central [s]
    """
    center_freq: float = 1e9
    bandwidth: float = 0.5e9
    t0: float = 0.0
    
    def __post_init__(self):
        self.tau = 0.44 / self.bandwidth
        if self.t0 == 0:
            self.t0 = 4 * self.tau
    
    def get_value(self, time: float) -> float:
        t_rel = time - self.t0
        envelope = np.exp(-(t_rel**2) / (2 * self.tau**2))
        carrier = np.sin(2 * np.pi * self.center_freq * time)
        return self.amplitude * envelope * carrier
    
    def is_active(self, time: float) -> bool:
        return abs(time - self.t0) < 6 * self.tau


@dataclass
class RickerSource(Source):
    """
    Wavelet de Ricker (chapéu mexicano).
    
    f(t) = A * (1 - 2π²f²(t-t₀)²) * exp(-π²f²(t-t₀)²)
    
    Vantagem: não tem componente DC.
    
    Attributes:
        peak_freq: Frequência de pico [Hz]
        t0: Tempo central [s]
    """
    peak_freq: float = 1e9
    t0: float = 0.0
    
    def __post_init__(self):
        if self.t0 == 0:
            self.t0 = 1.5 / self.peak_freq
    
    def get_value(self, time: float) -> float:
        t_rel = time - self.t0
        arg = (np.pi * self.peak_freq * t_rel)**2
        return self.amplitude * (1 - 2 * arg) * np.exp(-arg)
    
    def is_active(self, time: float) -> bool:
        return abs(time - self.t0) < 3.0 / self.peak_freq
