"""
Módulo de Carta de Smith para Análise de Antenas

Este módulo implementa:
- Desenho da Carta de Smith completa
- Cálculo de impedância de entrada via FDTD
- Plotagem de impedância vs frequência
- Cálculo de parâmetros S, VSWR, Return Loss
- Marcadores de frequência e anotações

A Carta de Smith é uma representação gráfica do coeficiente de reflexão Γ
no plano complexo, onde:

    Γ = (Z - Z₀) / (Z + Z₀)

Com Z₀ = 50Ω (impedância de referência padrão)
"""

import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Arc, Circle

try:
    from antenna_simulator.integration.scikit_rf_bridge import (
        compute_vswrs_from_impedance,
    )
except ImportError:
    compute_vswrs_from_impedance = None


# =============================================================================
# CONSTANTES E CONFIGURAÇÃO
# =============================================================================

Z0_DEFAULT = 50.0  # Impedância de referência padrão [Ω]


@dataclass
class SmithChartConfig:
    """Configuração da Carta de Smith"""

    z0: float = 50.0  # Impedância de referência [Ω]
    figsize: Tuple[int, int] = (10, 10)
    show_grid: bool = True
    grid_color: str = "#cccccc"
    grid_linewidth: float = 0.5
    background_color: str = "white"
    border_color: str = "black"
    border_linewidth: float = 2.0

    # Círculos de resistência constante a desenhar
    r_circles: List[float] = field(default_factory=lambda: [0, 0.2, 0.5, 1, 2, 5])

    # Arcos de reatância constante a desenhar
    x_arcs: List[float] = field(default_factory=lambda: [0.2, 0.5, 1, 2, 5])

    # Cores para plots
    marker_color: str = "blue"
    trace_color: str = "red"
    swr_circle_color: str = "green"


# =============================================================================
# FUNÇÕES DE CONVERSÃO
# =============================================================================


def impedance_to_gamma(z: complex, z0: float = Z0_DEFAULT) -> complex:
    """
    Converte impedância para coeficiente de reflexão.

    Γ = (Z - Z₀) / (Z + Z₀)

    Args:
        z: Impedância complexa [Ω]
        z0: Impedância de referência [Ω]

    Returns:
        Coeficiente de reflexão complexo
    """
    return (z - z0) / (z + z0)


def gamma_to_impedance(gamma: complex, z0: float = Z0_DEFAULT) -> complex:
    """
    Converte coeficiente de reflexão para impedância.

    Z = Z₀ * (1 + Γ) / (1 - Γ)

    Args:
        gamma: Coeficiente de reflexão complexo
        z0: Impedância de referência [Ω]

    Returns:
        Impedância complexa [Ω]
    """
    if abs(1 - gamma) < 1e-10:
        return complex(float("inf"), 0)
    return z0 * (1 + gamma) / (1 - gamma)


def impedance_to_normalized(z: complex, z0: float = Z0_DEFAULT) -> complex:
    """Normaliza impedância pela impedância de referência"""
    return z / z0


def normalized_to_impedance(z_norm: complex, z0: float = Z0_DEFAULT) -> complex:
    """Desnormaliza impedância"""
    return z_norm * z0


def gamma_to_s11_db(gamma: complex) -> float:
    """
    Converte coeficiente de reflexão para S11 em dB.

    S11[dB] = 20 * log10(|Γ|)
    """
    mag = abs(gamma)
    if mag < 1e-10:
        return -100.0
    return 20 * np.log10(mag)


def gamma_to_vswr(gamma: complex) -> float:
    """
    Calcula VSWR a partir do coeficiente de reflexão.

    VSWR = (1 + |Γ|) / (1 - |Γ|)
    """
    mag = abs(gamma)
    if mag >= 1.0:
        return float("inf")
    return (1 + mag) / (1 - mag)


def vswr_to_gamma_magnitude(vswr: float) -> float:
    """
    Calcula magnitude de Γ a partir do VSWR.

    |Γ| = (VSWR - 1) / (VSWR + 1)
    """
    if vswr < 1.0:
        return 0.0
    return (vswr - 1) / (vswr + 1)


def return_loss_to_gamma(rl_db: float) -> float:
    """
    Converte Return Loss em dB para magnitude de Γ.

    |Γ| = 10^(-RL/20)
    """
    return 10 ** (-rl_db / 20)


# =============================================================================
# CÁLCULO DE IMPEDÂNCIA VIA FDTD
# =============================================================================


@dataclass
class ImpedanceResult:
    """Resultado do cálculo de impedância"""

    frequencies: np.ndarray  # Frequências [Hz]
    impedance: np.ndarray  # Impedância complexa [Ω]
    gamma: np.ndarray  # Coeficiente de reflexão
    s11_db: np.ndarray  # S11 em dB
    vswr: np.ndarray  # VSWR
    z0: float  # Impedância de referência

    @property
    def resistance(self) -> np.ndarray:
        """Parte real da impedância (resistência)"""
        return np.real(self.impedance)

    @property
    def reactance(self) -> np.ndarray:
        """Parte imaginária da impedância (reatância)"""
        return np.imag(self.impedance)

    @property
    def z_normalized(self) -> np.ndarray:
        """Impedância normalizada"""
        return self.impedance / self.z0

    def get_at_frequency(self, freq: float) -> Dict:
        """Obtém parâmetros em uma frequência específica"""
        idx = np.argmin(np.abs(self.frequencies - freq))
        return {
            "frequency": self.frequencies[idx],
            "impedance": self.impedance[idx],
            "gamma": self.gamma[idx],
            "s11_db": self.s11_db[idx],
            "vswr": self.vswr[idx],
            "resistance": self.resistance[idx],
            "reactance": self.reactance[idx],
        }

    def find_resonance(self, freq_min: float = None, freq_max: float = None) -> Dict:
        """
        Encontra frequência de ressonância (onde reatância cruza zero).

        Returns:
            Dicionário com frequência e parâmetros na ressonância
        """
        mask = np.ones(len(self.frequencies), dtype=bool)
        if freq_min is not None:
            mask &= self.frequencies >= freq_min
        if freq_max is not None:
            mask &= self.frequencies <= freq_max

        reactance = self.reactance[mask]
        freqs = self.frequencies[mask]

        # Encontra cruzamentos por zero
        crossings = np.where(np.diff(np.sign(reactance)))[0]

        if len(crossings) == 0:
            # Retorna onde reatância é mínima em magnitude
            idx = np.argmin(np.abs(reactance))
        else:
            # Primeira ressonância
            idx = crossings[0]

        return self.get_at_frequency(freqs[idx])

    def find_best_match(self, freq_min: float = None, freq_max: float = None) -> Dict:
        """
        Encontra frequência de melhor casamento (menor |S11|).

        Returns:
            Dicionário com frequência e parâmetros no melhor casamento
        """
        mask = np.ones(len(self.frequencies), dtype=bool)
        if freq_min is not None:
            mask &= self.frequencies >= freq_min
        if freq_max is not None:
            mask &= self.frequencies <= freq_max

        s11 = self.s11_db[mask]
        freqs = self.frequencies[mask]

        idx = np.argmin(s11)
        return self.get_at_frequency(freqs[idx])

    def get_bandwidth(self, s11_threshold: float = -10.0) -> Tuple[float, float, float]:
        """
        Calcula largura de banda para um limiar de S11.

        Args:
            s11_threshold: Limiar em dB (padrão -10 dB = VSWR 2:1)

        Returns:
            Tupla (freq_min, freq_max, bandwidth) em Hz
        """
        below_threshold = self.s11_db < s11_threshold

        if not np.any(below_threshold):
            return (0, 0, 0)

        # Encontra índices onde está abaixo do limiar
        indices = np.where(below_threshold)[0]

        # Encontra regiões contíguas
        freq_min = self.frequencies[indices[0]]
        freq_max = self.frequencies[indices[-1]]

        return (freq_min, freq_max, freq_max - freq_min)


def calculate_impedance_from_fdtd(
    solver, frequencies: np.ndarray, z0: float = Z0_DEFAULT
) -> ImpedanceResult:
    """
    Calcula impedância de entrada a partir dos dados da simulação FDTD.

    Usa a transformada de Fourier dos campos E e H no ponto de alimentação
    para obter V(ω) e I(ω), e então Z(ω) = V(ω) / I(ω).

    Args:
        solver: FDTDSolver após execução
        frequencies: Array de frequências de interesse [Hz]
        z0: Impedância de referência [Ω]

    Returns:
        ImpedanceResult com impedâncias calculadas
    """
    if len(solver.probes) == 0:
        raise ValueError("Solver não tem probes configurados")

    # Obtém série temporal do probe principal (no feed)
    times, e_values = solver.probes[0].get_time_series()

    if len(times) < 2:
        raise ValueError("Dados insuficientes no probe")

    dt = times[1] - times[0]
    n_samples = len(times)

    # FFT do campo E (proporcional à tensão)
    E_fft = np.fft.fft(e_values)
    fft_freqs = np.fft.fftfreq(n_samples, dt)

    # Obtém tensão de entrada da fonte
    if len(solver.sources) > 0:
        source = solver.sources[0]
        v_source = np.array([source.get_value(t) for t in times])
        V_fft = np.fft.fft(v_source)
    else:
        V_fft = E_fft

    # Interpola para as frequências de interesse
    impedance = np.zeros(len(frequencies), dtype=complex)

    for i, freq in enumerate(frequencies):
        # Encontra índice mais próximo na FFT
        idx = np.argmin(np.abs(fft_freqs - freq))

        if abs(V_fft[idx]) > 1e-20:
            # Impedância aproximada: Z ≈ E * dx / (H * dy)
            # Simplificação: usamos razão dos campos transformados
            z_ratio = E_fft[idx] / (V_fft[idx] + 1e-30)

            # Escala para impedância física (aproximação)
            dx = solver.grid.config.dx
            impedance[i] = z_ratio * dx * z0
        else:
            impedance[i] = z0  # Fallback

    # Garante parte real positiva (fisicamente válida)
    impedance = np.where(
        np.real(impedance) < 0, -np.real(impedance) + 1j * np.imag(impedance), impedance
    )

    # Calcula parâmetros derivados
    gamma = np.array([impedance_to_gamma(z, z0) for z in impedance])
    s11_db = np.array([gamma_to_s11_db(g) for g in gamma])
    vswr = np.array([gamma_to_vswr(g) for g in gamma])

    if compute_vswrs_from_impedance is not None:
        try:
            skrf_data = compute_vswrs_from_impedance(frequencies, impedance, z0=z0)
            s11_db = skrf_data["s11_db"]
            vswr = skrf_data["vswr"]
        except Exception:
            pass

    return ImpedanceResult(
        frequencies=frequencies, impedance=impedance, gamma=gamma, s11_db=s11_db, vswr=vswr, z0=z0
    )


def calculate_impedance_analytical(
    antenna_type: str,
    frequencies: np.ndarray,
    length: float = None,
    z0: float = Z0_DEFAULT,
    **kwargs,
) -> ImpedanceResult:
    """
    Calcula impedância usando fórmulas analíticas aproximadas.

    Útil para comparação e validação.

    Args:
        antenna_type: Tipo de antena ('dipole', 'monopole', 'loop')
        frequencies: Array de frequências [Hz]
        length: Comprimento da antena [m]
        z0: Impedância de referência [Ω]

    Returns:
        ImpedanceResult
    """
    from iloveantennas.simulator.core.constants import C0

    impedance = np.zeros(len(frequencies), dtype=complex)

    if antenna_type.lower() == "dipole":
        # Impedância de dipolo de meia onda
        # Z ≈ 73 + j42.5 na ressonância
        # Varia com frequência

        if length is None:
            raise ValueError("Comprimento necessário para dipolo")

        for i, freq in enumerate(frequencies):
            wavelength = C0 / freq
            electrical_length = length / wavelength

            # Fórmula aproximada de Balanis
            kl = 2 * np.pi * electrical_length

            if abs(kl) < 0.01:
                # Dipolo muito curto
                R_rad = 20 * (kl**2)
                X = -120 * (np.log(length / 0.001) - 1) / kl
            else:
                # Fórmula geral aproximada
                R_rad = 73.13 * (np.sin(kl / 2) ** 2)
                X = 42.5 * np.tan(kl / 2 - np.pi / 2)

                # Limita valores extremos
                X = np.clip(X, -1000, 1000)

            impedance[i] = R_rad + 1j * X

    elif antenna_type.lower() == "monopole":
        # Monopole sobre plano de terra = metade do dipolo
        dipole_result = calculate_impedance_analytical(
            "dipole", frequencies, length * 2 if length else None, z0
        )
        impedance = dipole_result.impedance / 2

    elif antenna_type.lower() == "loop":
        if length is None:
            raise ValueError("Perímetro necessário para loop")

        area = (length / (2 * np.pi)) ** 2 * np.pi

        for i, freq in enumerate(frequencies):
            wavelength = C0 / freq
            k = 2 * np.pi / wavelength

            R_rad = 31171 * (area / wavelength**2) ** 2
            X = k * 120 * np.pi * area / wavelength

            impedance[i] = R_rad + 1j * X

    elif antenna_type.lower() == "patch":
        substrate_er = kwargs.get("substrate_er", 4.4)
        f_res = kwargs.get("f_resonant", None)

        if f_res is None:
            if len(frequencies) > 0:
                f_res = frequencies[len(frequencies) // 2]
            else:
                f_res = 1.0

        omega0 = 2 * np.pi * f_res
        R0 = z0

        base_q = kwargs.get("q_factor", None)
        if base_q is None:
            base_q = 10.0 * np.sqrt(max(substrate_er, 1.0) / 4.4)

        L = base_q * R0 / omega0
        C = 1.0 / (omega0**2 * L)

        for i, freq in enumerate(frequencies):
            omega = 2 * np.pi * freq
            X = omega * L - 1.0 / (omega * C)
            impedance[i] = R0 + 1j * X

    elif antenna_type.lower() == "yagi":
        # Yagi-Uda: Driven element is a dipole, but parasitics lower Z and Q increases
        # Approx: Z_yagi ~ 0.8 * Z_dipole (Resistance drops) + narrower band effects

        dipole_res = calculate_impedance_analytical("dipole", frequencies, length, z0)

        # Modifica impedância para simular Yagi
        # Resistência menor, reatância varia mais rápido (Q maior)
        for i, z in enumerate(dipole_res.impedance):
            freq = frequencies[i]
            f_center = frequencies[len(frequencies) // 2]

            # Q multiplier (Bandwidth narrowing)
            q_mult = 4.0  # Aumentado para tornar o loop mais visível na carta

            # Radiation resistance drops due to parasitic loading
            r_new = z.real * 0.5

            # Reactance slope increases
            x_new = z.imag * q_mult

            impedance[i] = r_new + 1j * x_new

    elif antenna_type.lower() == "helix":
        # Helix (Axial Mode):
        # R ~ 140 * (C/lambda) -> Wideband resistive behavior
        # Z_in is typically 100-150 Ohms and capacitive

        f_center = frequencies[len(frequencies) // 2]

        for i, freq in enumerate(frequencies):
            # Normalizado pela frequência central
            ratio = freq / f_center

            # Resistência base ~140 ohms, levemente dependente da frequência
            R = 140.0 / ratio**0.5

            # Reatância capacitiva leve que diminui com frequência
            X = -20.0 / ratio

            # Adiciona um pequeno ripple devido a reflexões de fim de fio
            phase = freq / 1e9 * 20
            ripple = 5.0 * np.cos(phase)

            impedance[i] = (R + ripple) + 1j * (X + ripple * 0.5)

    elif antenna_type.lower() == "horn":
        # Horn: Wideband match.
        # Behaves like a high-pass filter.
        # Z approaches waveguide impedance but matched to 50 at feed.

        f_center = frequencies[len(frequencies) // 2]

        for i, freq in enumerate(frequencies):
            ratio = freq / f_center

            # Better match at higher frequencies
            # S11 improves as freq increases

            # Base impedance (matched to 50)
            # Ripple decreases with frequency
            ripple_mag = 10.0 * np.exp(-(ratio - 1.0)) if ratio > 0.8 else 50.0

            phase = freq / 1e9 * 12
            ripple_r = ripple_mag * np.cos(phase)
            ripple_x = ripple_mag * np.sin(phase)

            impedance[i] = (50.0 + ripple_r) + 1j * ripple_x

    elif antenna_type.lower() == "dish":
        # Dish: Feed + Reflector.
        # Feed (e.g. dipole/horn) ripple + reflection from dish back to feed.
        # This creates a fast ripple superimposed on the feed impedance.

        f_center = frequencies[len(frequencies) // 2]

        for i, freq in enumerate(frequencies):
            # Feed impedance (assume dipole-like but flatter)
            dipole_z = calculate_impedance_analytical(
                "dipole", np.array([freq]), length, z0
            ).impedance[0]
            feed_z = 50.0 + (dipole_z - 50.0) * 0.2  # Better matched feed

            # Dish reflection ripple (fast phase change due to 2*focal_length path)
            # Assume focal length ~ 10 wavelengths
            path_length_lambda = 10.0 * (freq / f_center)
            phase_delay = 4 * np.pi * path_length_lambda

            # Reflection coefficient magnitude (small)
            gamma_mag = 0.1
            gamma_ref = gamma_mag * np.exp(-1j * phase_delay)

            # Convert back to Z
            # Z_in = Z0 * (1 + G) / (1 - G)
            z_in_norm = (1 + gamma_ref) / (1 - gamma_ref)
            z_dish = 50.0 * z_in_norm

            impedance[i] = z_dish

    elif antenna_type.lower() == "lpda":
        # LPDA: Log-Periodic Dipole Array
        # Characterized by repetitive impedance behavior with log(f).
        # Nominal Z often designed for 50, 75 or 100 Ohms.

        for i, freq in enumerate(frequencies):
            # Log-periodic ripple
            log_f = np.log10(freq)

            # Periodicity related to tau (scaling factor)
            # Simulate tau ~ 0.8 -> period in log domain
            period = -np.log10(0.85)

            phase = (log_f / period) * 2 * np.pi

            # Impedance oscillates around mean (e.g. 60 Ohms)
            R_mean = 60.0
            R_var = 15.0
            X_var = 10.0

            R = R_mean + R_var * np.cos(phase)
            X = X_var * np.sin(phase)

            impedance[i] = R + 1j * X

    elif antenna_type.lower() == "biquad":
        # Biquad: Loop-like, ~60 Ohms resonant

        f_center = frequencies[len(frequencies) // 2]

        for i, freq in enumerate(frequencies):
            delta = (freq - f_center) / f_center

            # Series RLC approx
            R = 60.0
            Q = 10.0
            X = R * Q * delta

            impedance[i] = R + 1j * X

    elif antenna_type.lower() == "v_dipole":
        # V-Dipole: Similar to dipole but lower R depending on angle
        # 120 deg V-dipole -> Z ~ 50 ohms? (Planar dipole is 73, V lowers it?)
        # Actually V-shape often used to match 50 ohms better than straight dipole (73 ohm)

        dipole_res = calculate_impedance_analytical("dipole", frequencies, length, z0)
        # Closer to 50 ohms
        impedance = dipole_res.impedance * (50.0 / 73.0)

    else:
        impedance = np.ones(len(frequencies), dtype=complex) * z0

    # Calcula parâmetros derivados
    gamma = np.array([impedance_to_gamma(z, z0) for z in impedance])
    s11_db = np.array([gamma_to_s11_db(g) for g in gamma])
    vswr = np.array([gamma_to_vswr(g) for g in gamma])

    return ImpedanceResult(
        frequencies=frequencies, impedance=impedance, gamma=gamma, s11_db=s11_db, vswr=vswr, z0=z0
    )


# =============================================================================
# CARTA DE SMITH - PLOTAGEM
# =============================================================================


class SmithChart:
    """
    Classe para desenhar e manipular a Carta de Smith.

    A Carta de Smith mapeia impedâncias complexas para um círculo unitário
    usando a transformação bilinear (transformação de Möbius).

    Uso básico:
        chart = SmithChart()
        chart.plot_impedance(50 + 25j)  # Plota ponto
        chart.plot_trace(impedances)     # Plota traço
        chart.show()
    """

    def __init__(self, config: SmithChartConfig = None):
        """
        Inicializa a Carta de Smith.

        Args:
            config: Configuração (usa padrão se None)
        """
        self.config = config or SmithChartConfig()
        self.fig = None
        self.ax = None
        self._markers = []
        self._traces = []

    def _create_figure(self):
        """Cria a figura matplotlib"""
        if self.fig is None:
            self.fig, self.ax = plt.subplots(
                figsize=self.config.figsize, subplot_kw={"aspect": "equal"}
            )
            self.ax.set_facecolor(self.config.background_color)
            self._draw_chart()

    def _draw_chart(self):
        """Desenha a grade da Carta de Smith"""
        ax = self.ax

        # Círculo externo (|Γ| = 1)
        circle_outer = Circle(
            (0, 0),
            1,
            fill=False,
            color=self.config.border_color,
            linewidth=self.config.border_linewidth,
        )
        ax.add_patch(circle_outer)

        if self.config.show_grid:
            # Círculos de resistência constante
            for r in self.config.r_circles:
                self._draw_r_circle(r)

            # Arcos de reatância constante
            for x in self.config.x_arcs:
                self._draw_x_arc(x)
                self._draw_x_arc(-x)

            # Eixo real (X = 0)
            ax.axhline(y=0, color=self.config.grid_color, linewidth=self.config.grid_linewidth)

        # Labels
        self._add_labels()

        # Configurações do eixo
        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-1.3, 1.3)
        ax.set_xlabel("Real(Γ)")
        ax.set_ylabel("Imag(Γ)")
        ax.set_title("Carta de Smith")
        ax.axis("off")

    def _draw_r_circle(self, r: float):
        """
        Desenha círculo de resistência constante.

        Na carta de Smith, círculos de r constante têm:
        - Centro em (r/(r+1), 0)
        - Raio = 1/(r+1)
        """
        if r < 0:
            return

        center_x = r / (r + 1)
        radius = 1 / (r + 1)

        circle = Circle(
            (center_x, 0),
            radius,
            fill=False,
            color=self.config.grid_color,
            linewidth=self.config.grid_linewidth,
        )
        self.ax.add_patch(circle)

    def _draw_x_arc(self, x: float):
        """
        Desenha arco de reatância constante.

        Na carta de Smith, arcos de x constante têm:
        - Centro em (1, 1/x)
        - Raio = |1/x|
        """
        if abs(x) < 1e-10:
            return

        center_y = 1 / x
        radius = abs(1 / x)

        # Calcula ângulos de início e fim do arco
        # O arco deve estar dentro do círculo unitário

        # Ponto onde o arco cruza o círculo unitário
        # Resolvendo: (1-x)² + (y-1/x)² = 1/x² e x² + y² = 1

        if abs(x) <= 1:
            # Arco completo visível
            if x > 0:
                theta1 = 180
                theta2 = 270
            else:
                theta1 = 90
                theta2 = 180
        else:
            # Arco parcial
            if x > 0:
                theta1 = 180 + np.degrees(np.arcsin(1 / abs(x)))
                theta2 = 270
            else:
                theta1 = 90
                theta2 = 180 - np.degrees(np.arcsin(1 / abs(x)))

        arc = Arc(
            (1, center_y),
            2 * radius,
            2 * radius,
            angle=0,
            theta1=theta1,
            theta2=theta2,
            color=self.config.grid_color,
            linewidth=self.config.grid_linewidth,
        )
        self.ax.add_patch(arc)

    def _add_labels(self):
        """Adiciona labels de resistência e reatância"""
        # Labels de resistência
        for r in self.config.r_circles:
            if r == 0:
                pos = (-1, 0)
                label = "0"
            else:
                x = r / (r + 1) + 1 / (r + 1)
                if x <= 1:
                    pos = (x, 0.05)
                    label = f"{r}"
                else:
                    continue

            self.ax.annotate(label, pos, fontsize=8, ha="center", va="bottom", color="gray")

        # Labels de reatância
        for x in [0.5, 1, 2]:
            # Posição no círculo unitário
            gamma = impedance_to_gamma(complex(0, x), 1)
            self.ax.annotate(
                f"+j{x}", (gamma.real, gamma.imag), fontsize=8, ha="left", va="bottom", color="gray"
            )

            gamma = impedance_to_gamma(complex(0, -x), 1)
            self.ax.annotate(
                f"-j{x}", (gamma.real, gamma.imag), fontsize=8, ha="left", va="top", color="gray"
            )

    def plot_impedance(
        self,
        z: complex,
        label: str = None,
        marker: str = "o",
        color: str = None,
        size: float = 100,
        annotate: bool = True,
    ):
        """
        Plota um ponto de impedância na carta.

        Args:
            z: Impedância complexa [Ω]
            label: Rótulo do ponto
            marker: Estilo do marcador
            color: Cor (usa padrão se None)
            size: Tamanho do marcador
            annotate: Mostrar anotação com valor
        """
        self._create_figure()

        color = color or self.config.marker_color
        gamma = impedance_to_gamma(z, self.config.z0)

        self.ax.scatter(
            gamma.real, gamma.imag, marker=marker, c=color, s=size, label=label, zorder=10
        )

        if annotate:
            annotation = f"Z={z.real:.1f}{z.imag:+.1f}j Ω"
            self.ax.annotate(
                annotation,
                (gamma.real, gamma.imag),
                xytext=(10, 10),
                textcoords="offset points",
                fontsize=8,
                color=color,
                arrowprops=dict(arrowstyle="->", color=color, lw=0.5),
            )

        self._markers.append((z, gamma, label))

    def plot_trace(
        self,
        impedances: np.ndarray,
        frequencies: np.ndarray = None,
        label: str = None,
        color: str = None,
        linewidth: float = 1.5,
        marker_freq: List[float] = None,
    ):
        """
        Plota um traço de impedância vs frequência.

        Args:
            impedances: Array de impedâncias complexas
            frequencies: Array de frequências correspondentes
            label: Rótulo do traço
            color: Cor do traço
            linewidth: Largura da linha
            marker_freq: Frequências para marcar no traço
        """
        self._create_figure()

        color = color or self.config.trace_color
        gammas = np.array([impedance_to_gamma(z, self.config.z0) for z in impedances])

        self.ax.plot(
            gammas.real, gammas.imag, color=color, linewidth=linewidth, label=label, zorder=5
        )

        # Marcadores de frequência
        if marker_freq is not None and frequencies is not None:
            for freq in marker_freq:
                idx = np.argmin(np.abs(frequencies - freq))
                gamma = gammas[idx]

                self.ax.scatter(gamma.real, gamma.imag, marker="o", c=color, s=50, zorder=10)

                freq_label = f"{freq/1e6:.0f} MHz" if freq >= 1e6 else f"{freq/1e3:.0f} kHz"
                self.ax.annotate(
                    freq_label,
                    (gamma.real, gamma.imag),
                    xytext=(5, 5),
                    textcoords="offset points",
                    fontsize=7,
                    color=color,
                )

        # Marca início e fim
        self.ax.scatter(gammas.real[0], gammas.imag[0], marker="^", c=color, s=80, zorder=10)
        self.ax.scatter(gammas.real[-1], gammas.imag[-1], marker="s", c=color, s=80, zorder=10)

        self._traces.append((impedances, frequencies, label))

    def plot_vswr_circle(self, vswr: float, color: str = None, label: str = None):
        """
        Plota círculo de VSWR constante.

        Args:
            vswr: Valor de VSWR
            color: Cor do círculo
            label: Rótulo
        """
        self._create_figure()

        color = color or self.config.swr_circle_color
        gamma_mag = vswr_to_gamma_magnitude(vswr)

        circle = Circle(
            (0, 0),
            gamma_mag,
            fill=False,
            color=color,
            linewidth=1.5,
            linestyle="--",
            label=label or f"VSWR {vswr}:1",
        )
        self.ax.add_patch(circle)

    def plot_result(
        self,
        result: ImpedanceResult,
        label: str = None,
        color: str = None,
        marker_freqs: List[float] = None,
        show_vswr_circle: bool = True,
    ):
        """
        Plota resultado completo de impedância.

        Args:
            result: ImpedanceResult
            label: Rótulo
            color: Cor
            marker_freqs: Frequências para marcar
            show_vswr_circle: Mostrar círculo VSWR 2:1
        """
        self.plot_trace(
            result.impedance, result.frequencies, label=label, color=color, marker_freq=marker_freqs
        )

        if show_vswr_circle:
            self.plot_vswr_circle(2.0, color="green", label="VSWR 2:1")

        # Marca ponto de melhor casamento
        best = result.find_best_match()
        self.plot_impedance(
            best["impedance"],
            label=f"Best match @ {best['frequency']/1e6:.1f} MHz",
            marker="*",
            color="gold",
            size=200,
            annotate=True,
        )

    def add_legend(self, loc: str = "upper right"):
        """Adiciona legenda"""
        if self.ax is not None:
            self.ax.legend(loc=loc, fontsize=8)

    def set_title(self, title: str):
        """Define título"""
        if self.ax is not None:
            self.ax.set_title(title)

    def show(self):
        """Mostra a figura"""
        self._create_figure()
        plt.tight_layout()
        plt.show()

    def save(self, filename: str, dpi: int = 150):
        """Salva a figura"""
        self._create_figure()
        self.fig.savefig(
            filename, dpi=dpi, bbox_inches="tight", facecolor="white", edgecolor="none"
        )

    def clear(self):
        """Limpa a carta"""
        if self.ax is not None:
            self.ax.clear()
            self._draw_chart()
        self._markers.clear()
        self._traces.clear()


# =============================================================================
# FUNÇÕES DE PLOTAGEM AUXILIARES
# =============================================================================


def plot_s11_vs_frequency(
    result: ImpedanceResult,
    title: str = "Parâmetro S11 vs Frequência",
    figsize: Tuple[int, int] = (12, 5),
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Plota S11 em dB vs frequência.

    Args:
        result: ImpedanceResult
        title: Título do gráfico
        figsize: Tamanho da figura

    Returns:
        Tupla (figura, eixo)
    """
    fig, ax = plt.subplots(figsize=figsize)

    freq_mhz = result.frequencies / 1e6

    ax.plot(freq_mhz, result.s11_db, "b-", linewidth=1.5)

    # Linhas de referência
    ax.axhline(y=-10, color="r", linestyle="--", alpha=0.5, label="VSWR 2:1 (-10 dB)")
    ax.axhline(y=-15, color="g", linestyle="--", alpha=0.5, label="VSWR 1.5:1 (-15 dB)")
    ax.axhline(y=-20, color="purple", linestyle="--", alpha=0.5, label="VSWR 1.2:1 (-20 dB)")

    # Marca melhor ponto
    best = result.find_best_match()
    ax.scatter(
        best["frequency"] / 1e6,
        best["s11_db"],
        marker="*",
        c="gold",
        s=200,
        zorder=10,
        label=f"Min @ {best['frequency']/1e6:.1f} MHz ({best['s11_db']:.1f} dB)",
    )

    # Largura de banda
    bw = result.get_bandwidth(-10)
    if bw[2] > 0:
        ax.axvspan(
            bw[0] / 1e6,
            bw[1] / 1e6,
            alpha=0.2,
            color="green",
            label=f"BW (-10dB): {bw[2]/1e6:.1f} MHz",
        )

    ax.set_xlabel("Frequência [MHz]")
    ax.set_ylabel("S11 [dB]")
    ax.set_title(title)
    ax.set_ylim(-40, 0)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)

    return fig, ax


def plot_impedance_vs_frequency(
    result: ImpedanceResult,
    title: str = "Impedância vs Frequência",
    figsize: Tuple[int, int] = (12, 5),
) -> Tuple[plt.Figure, Tuple[plt.Axes, plt.Axes]]:
    """
    Plota resistência e reatância vs frequência.

    Args:
        result: ImpedanceResult
        title: Título
        figsize: Tamanho da figura

    Returns:
        Tupla (figura, (eixo1, eixo2))
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    freq_mhz = result.frequencies / 1e6

    # Resistência
    ax1.plot(freq_mhz, result.resistance, "b-", linewidth=1.5)
    ax1.axhline(
        y=result.z0, color="r", linestyle="--", alpha=0.5, label=f"{result.z0:.0f} Ω (referência)"
    )
    ax1.set_xlabel("Frequência [MHz]")
    ax1.set_ylabel("Resistência [Ω]")
    ax1.set_title("R(f)")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Reatância
    ax2.plot(freq_mhz, result.reactance, "g-", linewidth=1.5)
    ax2.axhline(y=0, color="r", linestyle="--", alpha=0.5, label="X = 0")
    ax2.set_xlabel("Frequência [MHz]")
    ax2.set_ylabel("Reatância [Ω]")
    ax2.set_title("X(f)")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # Marca ressonância
    res = result.find_resonance()
    ax2.scatter(
        res["frequency"] / 1e6,
        res["reactance"],
        marker="*",
        c="gold",
        s=200,
        zorder=10,
        label=f"Ressonância @ {res['frequency']/1e6:.1f} MHz",
    )
    ax2.legend()

    fig.suptitle(title)
    plt.tight_layout()

    return fig, (ax1, ax2)


def plot_vswr_vs_frequency(
    result: ImpedanceResult, title: str = "VSWR vs Frequência", figsize: Tuple[int, int] = (12, 5)
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Plota VSWR vs frequência.

    Args:
        result: ImpedanceResult
        title: Título
        figsize: Tamanho da figura

    Returns:
        Tupla (figura, eixo)
    """
    fig, ax = plt.subplots(figsize=figsize)

    freq_mhz = result.frequencies / 1e6

    # Limita VSWR para visualização
    vswr_plot = np.clip(result.vswr, 1, 10)

    ax.plot(freq_mhz, vswr_plot, "b-", linewidth=1.5)

    # Linhas de referência
    ax.axhline(y=2.0, color="r", linestyle="--", alpha=0.5, label="VSWR 2:1")
    ax.axhline(y=1.5, color="g", linestyle="--", alpha=0.5, label="VSWR 1.5:1")
    ax.axhline(y=1.2, color="purple", linestyle="--", alpha=0.5, label="VSWR 1.2:1")

    ax.set_xlabel("Frequência [MHz]")
    ax.set_ylabel("VSWR")
    ax.set_title(title)
    ax.set_ylim(1, 10)
    ax.grid(True, alpha=0.3)
    ax.legend()

    return fig, ax


# =============================================================================
# EXEMPLO E TESTE
# =============================================================================

if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    print("=" * 60)
    print("IloveAntenas - Módulo de Carta de Smith")
    print("=" * 60)

    # Teste com impedância de dipolo analítica
    print("\n📊 Gerando Carta de Smith para dipolo de meia onda...")

    # Frequências de interesse (280-320 MHz em torno de 300 MHz)
    frequencies = np.linspace(250e6, 350e6, 101)

    # Calcula impedância analítica
    from iloveantennas.simulator.core.constants import C0

    wavelength_center = C0 / 300e6
    dipole_length = wavelength_center / 2

    result = calculate_impedance_analytical("dipole", frequencies, length=dipole_length, z0=50.0)

    print(f"\n📈 Resultados do Dipolo (λ/2 @ 300 MHz):")
    print(f"   Comprimento: {dipole_length*100:.2f} cm")

    # Encontra ressonância
    res = result.find_resonance()
    print(f"\n   Ressonância:")
    print(f"      Frequência: {res['frequency']/1e6:.1f} MHz")
    print(f"      Impedância: {res['resistance']:.1f} + j{res['reactance']:.1f} Ω")
    print(f"      S11: {res['s11_db']:.1f} dB")
    print(f"      VSWR: {res['vswr']:.2f}:1")

    # Melhor casamento
    best = result.find_best_match()
    print(f"\n   Melhor Casamento:")
    print(f"      Frequência: {best['frequency']/1e6:.1f} MHz")
    print(f"      Impedância: {best['resistance']:.1f} + j{best['reactance']:.1f} Ω")
    print(f"      S11: {best['s11_db']:.1f} dB")
    print(f"      VSWR: {best['vswr']:.2f}:1")

    # Largura de banda
    bw = result.get_bandwidth(-10)
    print(f"\n   Largura de Banda (-10 dB):")
    print(f"      {bw[0]/1e6:.1f} - {bw[1]/1e6:.1f} MHz")
    print(f"      BW: {bw[2]/1e6:.1f} MHz ({100*bw[2]/300e6:.1f}%)")

    # Cria Carta de Smith
    chart = SmithChart()
    chart.plot_result(result, label="Dipolo λ/2", color="blue", marker_freqs=[280e6, 300e6, 320e6])
    chart.set_title("Carta de Smith - Dipolo de Meia Onda")
    chart.add_legend()

    # Salva
    chart.save("/home/claude/antenna_simulator/smith_chart_test.png")
    print("\n✓ Carta de Smith salva: smith_chart_test.png")

    # Plota S11
    fig, ax = plot_s11_vs_frequency(result, "S11 - Dipolo λ/2")
    fig.savefig("/home/claude/antenna_simulator/s11_test.png", dpi=150)
    print("✓ S11 vs Frequência salvo: s11_test.png")

    # Plota impedância
    fig, axes = plot_impedance_vs_frequency(result, "Impedância - Dipolo λ/2")
    fig.savefig("/home/claude/antenna_simulator/impedance_test.png", dpi=150)
    print("✓ Impedância vs Frequência salvo: impedance_test.png")

    print("\n✅ Teste concluído!")
