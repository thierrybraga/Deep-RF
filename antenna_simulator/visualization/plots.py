"""
Módulo de Visualização para Simulação de Antenas

Este módulo implementa:
- Visualização de geometria 3D
- Plots de campos E e H
- Diagramas de radiação (polar e 3D)
- Animações de propagação
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import Axes3D, art3d
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import matplotlib.animation as animation
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass

# Configuração padrão de estilo
plt.style.use('default')
plt.rcParams['figure.figsize'] = (10, 8)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.grid'] = True


# =============================================================================
# VISUALIZAÇÃO DE GEOMETRIA
# =============================================================================

class GeometryVisualizer:
    """Visualizador 3D de geometria de antenas"""
    
    def __init__(self, figsize: Tuple[int, int] = (12, 10)):
        self.fig = plt.figure(figsize=figsize)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self._setup_axes()
    
    def _setup_axes(self):
        """Configura eixos"""
        self.ax.set_xlabel('X [m]')
        self.ax.set_ylabel('Y [m]')
        self.ax.set_zlabel('Z [m]')
        self.ax.set_title('Geometria da Antena')
    
    def draw_wire(
        self,
        start: Tuple[float, float, float],
        end: Tuple[float, float, float],
        radius: float = 0.001,
        color: str = 'copper',
        label: str = None
    ):
        """Desenha um fio como linha 3D"""
        x = [start[0], end[0]]
        y = [start[1], end[1]]
        z = [start[2], end[2]]
        
        # Largura proporcional ao raio (visual)
        linewidth = max(1, radius * 1000)
        
        self.ax.plot(x, y, z, color=color, linewidth=linewidth, label=label)
    
    def draw_rectangle(
        self,
        center: Tuple[float, float, float],
        width: float,
        height: float,
        normal: str = 'z',
        color: str = 'orange',
        alpha: float = 0.7,
        label: str = None
    ):
        """Desenha um retângulo (patch)"""
        cx, cy, cz = center
        hw, hh = width/2, height/2
        
        if normal == 'z':
            vertices = [
                [cx - hw, cy - hh, cz],
                [cx + hw, cy - hh, cz],
                [cx + hw, cy + hh, cz],
                [cx - hw, cy + hh, cz]
            ]
        elif normal == 'x':
            vertices = [
                [cx, cy - hw, cz - hh],
                [cx, cy + hw, cz - hh],
                [cx, cy + hw, cz + hh],
                [cx, cy - hw, cz + hh]
            ]
        else:  # y
            vertices = [
                [cx - hw, cy, cz - hh],
                [cx + hw, cy, cz - hh],
                [cx + hw, cy, cz + hh],
                [cx - hw, cy, cz + hh]
            ]
        
        poly = Poly3DCollection([vertices], alpha=alpha, facecolor=color, 
                                 edgecolor='black', linewidth=1)
        self.ax.add_collection3d(poly)
        
        if label:
            self.ax.text(cx, cy, cz, label, fontsize=8)
    
    def draw_cylinder(
        self,
        center: Tuple[float, float, float],
        radius: float,
        height: float,
        axis: str = 'z',
        color: str = 'gray',
        alpha: float = 0.5,
        resolution: int = 20
    ):
        """Desenha um cilindro"""
        cx, cy, cz = center
        
        theta = np.linspace(0, 2*np.pi, resolution)
        z_line = np.linspace(-height/2, height/2, 2)
        THETA, Z = np.meshgrid(theta, z_line)
        
        if axis == 'z':
            X = cx + radius * np.cos(THETA)
            Y = cy + radius * np.sin(THETA)
            Z = cz + Z
        elif axis == 'x':
            Y = cy + radius * np.cos(THETA)
            Z = cz + radius * np.sin(THETA)
            X = cx + Z
        else:  # y
            X = cx + radius * np.cos(THETA)
            Z = cz + radius * np.sin(THETA)
            Y = cy + Z
        
        self.ax.plot_surface(X, Y, Z, color=color, alpha=alpha)
    
    def draw_helix(
        self,
        center: Tuple[float, float, float],
        radius: float,
        pitch: float,
        turns: float,
        wire_radius: float = 0.001,
        color: str = 'red',
        resolution: int = 100
    ):
        """Desenha uma hélice"""
        cx, cy, cz = center
        total_angle = 2 * np.pi * turns
        t = np.linspace(0, total_angle, int(resolution * turns))
        
        x = cx + radius * np.cos(t)
        y = cy + radius * np.sin(t)
        z = cz + pitch * t / (2 * np.pi)
        
        linewidth = max(1, wire_radius * 2000)
        self.ax.plot(x, y, z, color=color, linewidth=linewidth)
    
    def draw_antenna_graph(self, antenna, show_nodes: bool = True, show_labels: bool = True):
        """
        Desenha um grafo de antena completo.
        
        Args:
            antenna: AntennaGraph
            show_nodes: Mostrar nós
            show_labels: Mostrar rótulos
        """
        from core.geometry import Wire, Rectangle, Helix, Cylinder
        
        # Desenha geometrias
        for geom in antenna.geometries:
            if isinstance(geom, Wire):
                self.draw_wire(
                    geom.start.to_tuple(),
                    geom.end.to_tuple(),
                    geom.radius,
                    color='peru'
                )
            elif isinstance(geom, Rectangle):
                self.draw_rectangle(
                    geom.center.to_tuple(),
                    geom.width,
                    geom.height,
                    color='orange'
                )
            elif isinstance(geom, Helix):
                self.draw_helix(
                    geom.center.to_tuple(),
                    geom.radius,
                    geom.pitch,
                    geom.turns,
                    geom.wire_radius
                )
            elif isinstance(geom, Cylinder):
                self.draw_cylinder(
                    geom.center.to_tuple(),
                    geom.radius,
                    geom.height
                )
        
        # Desenha nós
        if show_nodes:
            for node_id, node in antenna.nodes.items():
                pos = node.position
                
                # Cores por tipo
                colors = {
                    'feed': 'red',
                    'ground': 'green',
                    'junction': 'blue',
                    'terminal': 'gray'
                }
                color = colors.get(node.node_type, 'black')
                marker_size = 100 if node.node_type == 'feed' else 50
                
                self.ax.scatter(
                    pos.x, pos.y, pos.z,
                    c=color, s=marker_size, marker='o'
                )
                
                if show_labels:
                    label = f"{node_id}" if node.node_type == 'junction' else node.node_type
                    self.ax.text(pos.x, pos.y, pos.z, f"  {label}", fontsize=8)
        
        # Ajusta limites
        bb = antenna.get_bounding_box()
        margin = max(bb.size.x, bb.size.y, bb.size.z) * 0.2
        
        self.ax.set_xlim(bb.min_point.x - margin, bb.max_point.x + margin)
        self.ax.set_ylim(bb.min_point.y - margin, bb.max_point.y + margin)
        self.ax.set_zlim(bb.min_point.z - margin, bb.max_point.z + margin)
        
        # Equaliza aspecto
        self._set_equal_aspect()
    
    def _set_equal_aspect(self):
        """Define aspecto igual para os três eixos"""
        limits = np.array([
            self.ax.get_xlim3d(),
            self.ax.get_ylim3d(),
            self.ax.get_zlim3d()
        ])
        
        center = np.mean(limits, axis=1)
        max_range = np.max(limits[:, 1] - limits[:, 0]) / 2
        
        self.ax.set_xlim3d([center[0] - max_range, center[0] + max_range])
        self.ax.set_ylim3d([center[1] - max_range, center[1] + max_range])
        self.ax.set_zlim3d([center[2] - max_range, center[2] + max_range])
    
    def show(self):
        """Mostra a figura"""
        plt.show()
    
    def save(self, filename: str, dpi: int = 150):
        """Salva a figura"""
        self.fig.savefig(filename, dpi=dpi, bbox_inches='tight')


# =============================================================================
# VISUALIZAÇÃO DE CAMPOS
# =============================================================================

class FieldVisualizer:
    """Visualizador de campos eletromagnéticos"""
    
    def __init__(self):
        self.fig = None
        self.ax = None
    
    def plot_field_slice(
        self,
        field_data: np.ndarray,
        dx: float,
        dy: float,
        title: str = "Campo",
        cmap: str = 'RdBu_r',
        vmin: float = None,
        vmax: float = None,
        show_colorbar: bool = True
    ):
        """
        Plota uma fatia 2D de campo.
        
        Args:
            field_data: Array 2D com valores do campo
            dx, dy: Tamanho das células [m]
            title: Título do gráfico
            cmap: Colormap
            vmin, vmax: Limites da escala de cores
        """
        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        
        ny, nx = field_data.shape
        extent = [0, nx * dx * 1000, 0, ny * dy * 1000]  # em mm
        
        if vmin is None or vmax is None:
            max_val = np.max(np.abs(field_data))
            vmin = -max_val
            vmax = max_val
        
        im = self.ax.imshow(
            field_data.T,
            origin='lower',
            extent=extent,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            aspect='auto'
        )
        
        self.ax.set_xlabel('X [mm]')
        self.ax.set_ylabel('Y [mm]')
        self.ax.set_title(title)
        
        if show_colorbar:
            cbar = plt.colorbar(im, ax=self.ax)
            cbar.set_label('Amplitude [V/m]')
        
        return self.fig, self.ax
    
    def plot_field_magnitude(
        self,
        Ex: np.ndarray,
        Ey: np.ndarray,
        Ez: np.ndarray,
        dx: float,
        plane: str = 'xy',
        index: int = None,
        title: str = "Magnitude |E|"
    ):
        """
        Plota magnitude do campo elétrico.
        
        Args:
            Ex, Ey, Ez: Componentes do campo
            dx: Tamanho da célula [m]
            plane: Plano de corte ('xy', 'xz', 'yz')
            index: Índice do corte (None = centro)
        """
        # Calcula magnitude
        E_mag = np.sqrt(Ex**2 + Ey**2 + Ez**2)
        
        # Extrai fatia
        if plane == 'xy':
            if index is None:
                index = E_mag.shape[2] // 2
            slice_data = E_mag[:, :, index]
            xlabel, ylabel = 'X [mm]', 'Y [mm]'
        elif plane == 'xz':
            if index is None:
                index = E_mag.shape[1] // 2
            slice_data = E_mag[:, index, :]
            xlabel, ylabel = 'X [mm]', 'Z [mm]'
        else:  # yz
            if index is None:
                index = E_mag.shape[0] // 2
            slice_data = E_mag[index, :, :]
            xlabel, ylabel = 'Y [mm]', 'Z [mm]'
        
        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        
        extent = [0, slice_data.shape[0] * dx * 1000, 
                  0, slice_data.shape[1] * dx * 1000]
        
        im = self.ax.imshow(
            slice_data.T,
            origin='lower',
            extent=extent,
            cmap='hot',
            aspect='auto'
        )
        
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.ax.set_title(f"{title} - Plano {plane.upper()} (índice {index})")
        
        cbar = plt.colorbar(im, ax=self.ax)
        cbar.set_label('|E| [V/m]')
        
        return self.fig, self.ax
    
    def plot_vector_field(
        self,
        Ex: np.ndarray,
        Ey: np.ndarray,
        dx: float,
        dy: float,
        skip: int = 2,
        title: str = "Campo Vetorial"
    ):
        """
        Plota campo vetorial 2D com setas.
        
        Args:
            Ex, Ey: Componentes do campo na fatia
            dx, dy: Tamanho das células [m]
            skip: Pular células para clareza visual
            title: Título
        """
        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        
        ny, nx = Ex.shape
        x = np.arange(0, nx * dx * 1000, dx * 1000)
        y = np.arange(0, ny * dy * 1000, dy * 1000)
        X, Y = np.meshgrid(x, y)
        
        # Magnitude para cor
        magnitude = np.sqrt(Ex**2 + Ey**2)
        
        # Plot com setas
        self.ax.quiver(
            X[::skip, ::skip],
            Y[::skip, ::skip],
            Ex[::skip, ::skip],
            Ey[::skip, ::skip],
            magnitude[::skip, ::skip],
            cmap='viridis',
            scale=np.max(magnitude) * 20
        )
        
        self.ax.set_xlabel('X [mm]')
        self.ax.set_ylabel('Y [mm]')
        self.ax.set_title(title)
        self.ax.set_aspect('equal')
        
        return self.fig, self.ax
    
    def plot_time_series(
        self,
        times: np.ndarray,
        values: np.ndarray,
        title: str = "Campo vs Tempo",
        ylabel: str = "Amplitude [V/m]"
    ):
        """Plota série temporal de campo"""
        self.fig, self.ax = plt.subplots(figsize=(12, 5))
        
        # Converte tempo para ns
        times_ns = times * 1e9
        
        self.ax.plot(times_ns, values, 'b-', linewidth=0.8)
        self.ax.set_xlabel('Tempo [ns]')
        self.ax.set_ylabel(ylabel)
        self.ax.set_title(title)
        self.ax.grid(True, alpha=0.3)
        
        return self.fig, self.ax
    
    def plot_spectrum(
        self,
        times: np.ndarray,
        values: np.ndarray,
        title: str = "Espectro de Frequência"
    ):
        """Plota espectro de frequência via FFT"""
        self.fig, self.ax = plt.subplots(figsize=(12, 5))
        
        dt = times[1] - times[0]
        n = len(values)
        
        # FFT
        fft_values = np.fft.fft(values)
        freqs = np.fft.fftfreq(n, dt)
        
        # Apenas frequências positivas
        pos_mask = freqs > 0
        freqs_ghz = freqs[pos_mask] / 1e9
        magnitude_db = 20 * np.log10(np.abs(fft_values[pos_mask]) + 1e-10)
        
        self.ax.plot(freqs_ghz, magnitude_db, 'b-', linewidth=0.8)
        self.ax.set_xlabel('Frequência [GHz]')
        self.ax.set_ylabel('Magnitude [dB]')
        self.ax.set_title(title)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlim(0, freqs_ghz[-1])
        
        return self.fig, self.ax
    
    def show(self):
        plt.show()
    
    def save(self, filename: str, dpi: int = 150):
        if self.fig:
            self.fig.savefig(filename, dpi=dpi, bbox_inches='tight')


# =============================================================================
# DIAGRAMA DE RADIAÇÃO
# =============================================================================

class RadiationPatternPlot:
    """Visualizador de diagramas de radiação"""
    
    def __init__(self):
        self.fig = None
        self.ax = None
    
    def plot_polar(
        self,
        angles: np.ndarray,
        pattern_db: np.ndarray,
        title: str = "Diagrama de Radiação",
        min_db: float = -40,
        label: str = None,
        color: str = 'b',
        linewidth: float = 1.5
    ):
        """
        Plota diagrama de radiação em coordenadas polares.
        
        Args:
            angles: Ângulos [rad]
            pattern_db: Padrão normalizado [dB]
            title: Título
            min_db: Valor mínimo em dB (para escala)
            label: Legenda
            color: Cor da linha
        """
        if self.fig is None:
            self.fig, self.ax = plt.subplots(
                figsize=(10, 10),
                subplot_kw={'projection': 'polar'}
            )
        
        # Limita valores
        pattern_clipped = np.clip(pattern_db, min_db, 0)
        
        # Normaliza para escala visual (0 a 1)
        pattern_norm = (pattern_clipped - min_db) / (-min_db)
        
        self.ax.plot(angles, pattern_norm, color=color, linewidth=linewidth, label=label)
        
        # Configura eixos
        self.ax.set_theta_zero_location('N')  # 0° no topo
        self.ax.set_theta_direction(-1)  # Sentido horário
        
        # Níveis de grade em dB
        levels = [0, -10, -20, -30, -40]
        level_norm = [(l - min_db) / (-min_db) for l in levels]
        self.ax.set_rticks(level_norm)
        self.ax.set_yticklabels([f'{l} dB' for l in levels])
        
        self.ax.set_title(title, pad=20)
        
        if label:
            self.ax.legend(loc='upper right')
        
        return self.fig, self.ax
    
    def plot_2d(
        self,
        angles_deg: np.ndarray,
        pattern_db: np.ndarray,
        title: str = "Diagrama de Radiação",
        xlabel: str = "Ângulo [°]",
        min_db: float = -40
    ):
        """
        Plota diagrama de radiação em gráfico cartesiano.
        
        Args:
            angles_deg: Ângulos [graus]
            pattern_db: Padrão normalizado [dB]
        """
        self.fig, self.ax = plt.subplots(figsize=(12, 6))
        
        self.ax.plot(angles_deg, pattern_db, 'b-', linewidth=1.5)
        self.ax.fill_between(angles_deg, min_db, pattern_db, alpha=0.3)
        
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel('Ganho Relativo [dB]')
        self.ax.set_title(title)
        self.ax.set_xlim(angles_deg[0], angles_deg[-1])
        self.ax.set_ylim(min_db, 5)
        self.ax.grid(True, alpha=0.3)
        
        # Linha de -3dB
        self.ax.axhline(y=-3, color='r', linestyle='--', alpha=0.5, label='-3 dB')
        self.ax.legend()
        
        return self.fig, self.ax
    
    def plot_3d(
        self,
        theta: np.ndarray,
        phi: np.ndarray,
        pattern: np.ndarray,
        title: str = "Diagrama de Radiação 3D"
    ):
        """
        Plota diagrama de radiação em 3D.
        
        Args:
            theta: Ângulos θ [rad]
            phi: Ângulos φ [rad]
            pattern: Padrão 2D (theta, phi)
        """
        self.fig = plt.figure(figsize=(12, 10))
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        THETA, PHI = np.meshgrid(theta, phi, indexing='ij')
        
        # Normaliza e converte para escala linear
        pattern_norm = pattern / np.max(pattern + 1e-10)
        
        # Converte para coordenadas cartesianas
        X = pattern_norm * np.sin(THETA) * np.cos(PHI)
        Y = pattern_norm * np.sin(THETA) * np.sin(PHI)
        Z = pattern_norm * np.cos(THETA)
        
        # Cores baseadas na magnitude
        colors = cm.jet(pattern_norm)
        
        self.ax.plot_surface(
            X, Y, Z,
            facecolors=colors,
            alpha=0.8,
            rstride=1,
            cstride=1,
            antialiased=True
        )
        
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        self.ax.set_title(title)
        
        # Aspecto igual
        max_range = np.max(pattern_norm)
        self.ax.set_xlim(-max_range, max_range)
        self.ax.set_ylim(-max_range, max_range)
        self.ax.set_zlim(-max_range, max_range)
        
        return self.fig, self.ax
    
    def show(self):
        plt.show()
    
    def save(self, filename: str, dpi: int = 150):
        if self.fig:
            self.fig.savefig(filename, dpi=dpi, bbox_inches='tight')


# =============================================================================
# ANIMAÇÕES
# =============================================================================

class FieldAnimator:
    """Criador de animações de propagação de campos"""
    
    def __init__(self, grid, solver):
        """
        Args:
            grid: FDTDGrid
            solver: FDTDSolver
        """
        self.grid = grid
        self.solver = solver
        self.frames = []
    
    def record_frame(self, plane: str = 'xy', component: str = 'Ez'):
        """Grava um frame da simulação"""
        if plane == 'xy':
            index = self.grid.config.nz // 2
            data = self.grid.get_slice('z', index, component)
        elif plane == 'xz':
            index = self.grid.config.ny // 2
            data = self.grid.get_slice('y', index, component)
        else:  # yz
            index = self.grid.config.nx // 2
            data = self.grid.get_slice('x', index, component)
        
        self.frames.append(np.copy(data))
    
    def create_animation(
        self,
        interval: int = 50,
        title: str = "Propagação do Campo"
    ):
        """
        Cria animação a partir dos frames gravados.
        
        Args:
            interval: Intervalo entre frames [ms]
            title: Título
            
        Returns:
            Objeto de animação matplotlib
        """
        if not self.frames:
            raise ValueError("Nenhum frame gravado")
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Encontra limites globais
        all_max = max(np.max(np.abs(f)) for f in self.frames)
        
        # Primeiro frame
        dx = self.grid.config.dx * 1000
        extent = [0, self.frames[0].shape[0] * dx, 
                  0, self.frames[0].shape[1] * dx]
        
        im = ax.imshow(
            self.frames[0].T,
            origin='lower',
            extent=extent,
            cmap='RdBu_r',
            vmin=-all_max,
            vmax=all_max,
            aspect='auto'
        )
        
        ax.set_xlabel('X [mm]')
        ax.set_ylabel('Y [mm]')
        ax.set_title(title)
        plt.colorbar(im, ax=ax, label='Amplitude [V/m]')
        
        def update(frame_num):
            im.set_data(self.frames[frame_num].T)
            ax.set_title(f"{title} - Frame {frame_num}/{len(self.frames)}")
            return [im]
        
        anim = animation.FuncAnimation(
            fig,
            update,
            frames=len(self.frames),
            interval=interval,
            blit=True
        )
        
        return anim
    
    def save_animation(self, filename: str, fps: int = 20):
        """Salva animação como arquivo"""
        anim = self.create_animation(interval=1000//fps)
        
        if filename.endswith('.gif'):
            writer = animation.PillowWriter(fps=fps)
        else:
            writer = animation.FFMpegWriter(fps=fps)
        
        anim.save(filename, writer=writer)
    
    def clear_frames(self):
        """Limpa frames gravados"""
        self.frames.clear()


# =============================================================================
# FUNÇÕES UTILITÁRIAS
# =============================================================================

def plot_s_parameters(
    frequencies: np.ndarray,
    s11_db: np.ndarray,
    title: str = "Parâmetros S",
    figsize: Tuple[int, int] = (12, 5)
):
    """
    Plota parâmetros S (tipicamente S11/Return Loss).
    
    Args:
        frequencies: Frequências [Hz]
        s11_db: S11 em dB
        title: Título
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    freq_ghz = frequencies / 1e9
    
    ax.plot(freq_ghz, s11_db, 'b-', linewidth=1.5)
    ax.axhline(y=-10, color='r', linestyle='--', alpha=0.5, label='VSWR 2:1')
    ax.axhline(y=-15, color='g', linestyle='--', alpha=0.5, label='VSWR 1.5:1')
    
    ax.set_xlabel('Frequência [GHz]')
    ax.set_ylabel('S11 [dB]')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_ylim(-40, 0)
    
    return fig, ax


def plot_impedance(
    frequencies: np.ndarray,
    z_real: np.ndarray,
    z_imag: np.ndarray,
    title: str = "Impedância de Entrada",
    figsize: Tuple[int, int] = (12, 5)
):
    """
    Plota impedância complexa vs frequência.
    
    Args:
        frequencies: Frequências [Hz]
        z_real: Parte real da impedância [Ω]
        z_imag: Parte imaginária [Ω]
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    
    freq_ghz = frequencies / 1e9
    
    ax1.plot(freq_ghz, z_real, 'b-', linewidth=1.5)
    ax1.axhline(y=50, color='r', linestyle='--', alpha=0.5, label='50Ω')
    ax1.set_xlabel('Frequência [GHz]')
    ax1.set_ylabel('Re(Z) [Ω]')
    ax1.set_title('Resistência')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    ax2.plot(freq_ghz, z_imag, 'g-', linewidth=1.5)
    ax2.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    ax2.set_xlabel('Frequência [GHz]')
    ax2.set_ylabel('Im(Z) [Ω]')
    ax2.set_title('Reatância')
    ax2.grid(True, alpha=0.3)
    
    fig.suptitle(title)
    plt.tight_layout()
    
    return fig, (ax1, ax2)


if __name__ == "__main__":
    print("=" * 60)
    print("IloveAntenas - Módulo de Visualização")
    print("=" * 60)
    
    # Teste: diagrama de radiação de exemplo
    angles = np.linspace(0, 2*np.pi, 361)
    
    # Padrão de dipolo aproximado
    pattern = np.sin(angles)**2
    pattern_db = 10 * np.log10(pattern + 1e-10)
    pattern_db = pattern_db - np.max(pattern_db)  # Normaliza
    
    plotter = RadiationPatternPlot()
    plotter.plot_polar(angles, pattern_db, title="Padrão de Dipolo (Plano E)")
    plotter.show()
