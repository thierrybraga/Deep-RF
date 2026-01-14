"""
IloveAntenas GUI - Interface Gráfica para Simulação de Antenas
=============================================================
Interface gráfica completa usando PyQt6 para design e simulação de antenas.

Funcionalidades:
- Editor de geometria 3D interativo
- Configuração de simulação FDTD
- Visualização de campos em tempo real
- Diagramas de radiação 2D/3D
- Exportação de resultados
"""

import sys
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import json

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QSplitter, QTabWidget, QToolBar, QStatusBar, QMenuBar, QMenu,
        QDockWidget, QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
        QPushButton, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
        QCheckBox, QGroupBox, QFormLayout, QProgressBar, QSlider,
        QFileDialog, QMessageBox, QDialog, QDialogButtonBox,
        QListWidget, QListWidgetItem, QScrollArea, QFrame
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
    from PyQt6.QtGui import QAction, QIcon, QKeySequence, QColor, QPainter
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False
    print("PyQt6 não disponível. Instale com: pip install PyQt6")

try:
    import matplotlib
    matplotlib.use('QtAgg' if HAS_PYQT6 else 'TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
    from matplotlib.figure import Figure
    from mpl_toolkits.mplot3d import Axes3D
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class AntennaType(Enum):
    """Tipos de antena disponíveis"""
    DIPOLE = auto()
    MONOPOLE = auto()
    YAGI = auto()
    PATCH = auto()
    HELIX = auto()
    CUSTOM = auto()


@dataclass
class SimulationConfig:
    """Configuração da simulação"""
    frequency: float = 300e6  # Hz
    cells_per_wavelength: int = 20
    pml_layers: int = 8
    num_timesteps: int = 1000
    source_type: str = "gaussian"
    courant_number: float = 0.99


@dataclass
class AntennaConfig:
    """Configuração da antena"""
    antenna_type: AntennaType = AntennaType.DIPOLE
    length: float = 0.5  # metros
    radius: float = 0.001  # metros
    material: str = "COPPER"
    extra_params: Dict[str, Any] = field(default_factory=dict)


class SimulationWorker(QObject):
    """Worker thread para simulação FDTD"""
    progress = pyqtSignal(int)
    step_complete = pyqtSignal(int, dict)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, grid, solver, num_steps: int):
        super().__init__()
        self.grid = grid
        self.solver = solver
        self.num_steps = num_steps
        self._is_running = True
    
    def run(self):
        """Executa a simulação"""
        try:
            for step in range(self.num_steps):
                if not self._is_running:
                    break
                
                # Atualiza campos
                self.solver.step()
                
                # Emite progresso
                progress = int((step + 1) / self.num_steps * 100)
                self.progress.emit(progress)
                
                # Emite dados a cada N passos para visualização
                if step % 10 == 0:
                    field_data = {
                        'step': step,
                        'Ex': self.grid.Ex.copy(),
                        'Ey': self.grid.Ey.copy(),
                        'Ez': self.grid.Ez.copy()
                    }
                    self.step_complete.emit(step, field_data)
            
            # Resultados finais
            results = {
                'total_steps': step + 1,
                'grid': self.grid,
                'solver': self.solver
            }
            self.finished.emit(results)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def stop(self):
        """Para a simulação"""
        self._is_running = False


class GeometryCanvas(FigureCanvas if HAS_MATPLOTLIB else QWidget):
    """Canvas 3D para visualização de geometria"""
    
    def __init__(self, parent=None):
        if HAS_MATPLOTLIB:
            self.fig = Figure(figsize=(8, 6), dpi=100)
            self.ax = self.fig.add_subplot(111, projection='3d')
            super().__init__(self.fig)
        else:
            super().__init__(parent)
        
        self.antenna_graph = None
        self.setup_axes()
    
    def setup_axes(self):
        """Configura os eixos 3D"""
        if not HAS_MATPLOTLIB:
            return
            
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_zlabel('Z (m)')
        self.ax.set_title('Geometria da Antena')
        self.fig.tight_layout()
    
    def clear(self):
        """Limpa o canvas"""
        if HAS_MATPLOTLIB:
            self.ax.clear()
            self.setup_axes()
            self.draw()
    
    def draw_wire(self, start: Tuple[float, float, float], 
                  end: Tuple[float, float, float],
                  color: str = 'copper', linewidth: float = 2):
        """Desenha um fio"""
        if not HAS_MATPLOTLIB:
            return
            
        xs = [start[0], end[0]]
        ys = [start[1], end[1]]
        zs = [start[2], end[2]]
        
        self.ax.plot(xs, ys, zs, color=color, linewidth=linewidth)
        self.draw()
    
    def draw_antenna(self, antenna_graph):
        """Desenha uma antena completa do grafo"""
        if not HAS_MATPLOTLIB:
            return
            
        self.clear()
        self.antenna_graph = antenna_graph
        
        # Cores por tipo de nó
        node_colors = {
            'feed': 'red',
            'ground': 'green',
            'junction': 'blue',
            'terminal': 'orange'
        }
        
        # Desenha arestas (fios)
        for edge in antenna_graph.edges.values():
            geom = edge.geometry
            if hasattr(geom, 'start') and hasattr(geom, 'end'):
                color = '#B87333'  # Copper color
                self.ax.plot(
                    [geom.start.x, geom.end.x],
                    [geom.start.y, geom.end.y],
                    [geom.start.z, geom.end.z],
                    color=color, linewidth=3
                )
        
        # Desenha nós
        for node in antenna_graph.nodes.values():
            color = node_colors.get(node.node_type, 'gray')
            self.ax.scatter(
                [node.position.x], [node.position.y], [node.position.z],
                color=color, s=100, marker='o'
            )
        
        self.ax.set_title(f'Antena: {antenna_graph.name}')
        self._auto_scale()
        self.draw()
    
    def _auto_scale(self):
        """Ajusta escala automaticamente"""
        if not HAS_MATPLOTLIB or self.antenna_graph is None:
            return
            
        bbox = self.antenna_graph.bounding_box()
        if bbox:
            margin = 0.1 * max(
                bbox.max_point.x - bbox.min_point.x,
                bbox.max_point.y - bbox.min_point.y,
                bbox.max_point.z - bbox.min_point.z
            )
            self.ax.set_xlim(bbox.min_point.x - margin, bbox.max_point.x + margin)
            self.ax.set_ylim(bbox.min_point.y - margin, bbox.max_point.y + margin)
            self.ax.set_zlim(bbox.min_point.z - margin, bbox.max_point.z + margin)


class FieldCanvas(FigureCanvas if HAS_MATPLOTLIB else QWidget):
    """Canvas para visualização de campos EM"""
    
    def __init__(self, parent=None):
        if HAS_MATPLOTLIB:
            self.fig = Figure(figsize=(8, 6), dpi=100)
            self.ax = self.fig.add_subplot(111)
            super().__init__(self.fig)
        else:
            super().__init__(parent)
        
        self.colorbar = None
    
    def plot_field_slice(self, field: np.ndarray, plane: str = 'xy', 
                        slice_index: int = None, title: str = 'Campo'):
        """Plota uma fatia 2D do campo"""
        if not HAS_MATPLOTLIB:
            return
            
        self.ax.clear()
        
        # Seleciona plano
        if plane == 'xy':
            idx = slice_index or field.shape[2] // 2
            data = field[:, :, idx].T
            xlabel, ylabel = 'X', 'Y'
        elif plane == 'xz':
            idx = slice_index or field.shape[1] // 2
            data = field[:, idx, :].T
            xlabel, ylabel = 'X', 'Z'
        else:  # yz
            idx = slice_index or field.shape[0] // 2
            data = field[idx, :, :].T
            xlabel, ylabel = 'Y', 'Z'
        
        # Plot
        vmax = np.max(np.abs(data))
        vmin = -vmax
        
        im = self.ax.imshow(
            data, origin='lower', cmap='RdBu_r',
            vmin=vmin, vmax=vmax, aspect='auto'
        )
        
        # Colorbar
        if self.colorbar:
            self.colorbar.remove()
        self.colorbar = self.fig.colorbar(im, ax=self.ax)
        
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.ax.set_title(f'{title} (plano {plane.upper()}, índice={idx})')
        
        self.fig.tight_layout()
        self.draw()


class RadiationCanvas(FigureCanvas if HAS_MATPLOTLIB else QWidget):
    """Canvas para diagrama de radiação"""
    
    def __init__(self, parent=None, polar: bool = True):
        if HAS_MATPLOTLIB:
            self.fig = Figure(figsize=(8, 6), dpi=100)
            if polar:
                self.ax = self.fig.add_subplot(111, projection='polar')
            else:
                self.ax = self.fig.add_subplot(111)
            super().__init__(self.fig)
        else:
            super().__init__(parent)
        
        self.is_polar = polar
    
    def plot_pattern(self, angles: np.ndarray, pattern: np.ndarray,
                    title: str = 'Diagrama de Radiação', normalize: bool = True):
        """Plota diagrama de radiação"""
        if not HAS_MATPLOTLIB:
            return
            
        self.ax.clear()
        
        # Normaliza para dB
        if normalize:
            pattern_db = 20 * np.log10(pattern / np.max(pattern) + 1e-10)
            pattern_db = np.clip(pattern_db, -40, 0)
        else:
            pattern_db = pattern
        
        if self.is_polar:
            self.ax.plot(np.radians(angles), pattern_db + 40, 'b-', linewidth=2)
            self.ax.fill(np.radians(angles), pattern_db + 40, alpha=0.3)
            self.ax.set_theta_zero_location('N')
            self.ax.set_theta_direction(-1)
            self.ax.set_ylim(0, 40)
            self.ax.set_yticks([0, 10, 20, 30, 40])
            self.ax.set_yticklabels(['-40', '-30', '-20', '-10', '0'])
        else:
            self.ax.plot(angles, pattern_db, 'b-', linewidth=2)
            self.ax.fill_between(angles, -40, pattern_db, alpha=0.3)
            self.ax.set_xlim(angles[0], angles[-1])
            self.ax.set_ylim(-40, 0)
            self.ax.set_xlabel('Ângulo (graus)')
            self.ax.set_ylabel('Ganho (dB)')
            self.ax.grid(True, linestyle='--', alpha=0.7)
        
        self.ax.set_title(title)
        self.fig.tight_layout()
        self.draw()


class AntennaPropertiesPanel(QWidget):
    """Painel de propriedades da antena"""
    
    antenna_changed = pyqtSignal(AntennaConfig)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = AntennaConfig()
        self.setup_ui()
    
    def setup_ui(self):
        """Configura a interface"""
        layout = QVBoxLayout(self)
        
        # Tipo de antena
        type_group = QGroupBox("Tipo de Antena")
        type_layout = QFormLayout()
        
        self.type_combo = QComboBox()
        for atype in AntennaType:
            self.type_combo.addItem(atype.name, atype)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addRow("Tipo:", self.type_combo)
        
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Dimensões
        dim_group = QGroupBox("Dimensões")
        dim_layout = QFormLayout()
        
        self.length_spin = QDoubleSpinBox()
        self.length_spin.setRange(0.001, 100)
        self.length_spin.setDecimals(4)
        self.length_spin.setValue(0.5)
        self.length_spin.setSuffix(" m")
        self.length_spin.valueChanged.connect(self._on_param_changed)
        dim_layout.addRow("Comprimento:", self.length_spin)
        
        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(0.0001, 1)
        self.radius_spin.setDecimals(4)
        self.radius_spin.setValue(0.001)
        self.radius_spin.setSuffix(" m")
        self.radius_spin.valueChanged.connect(self._on_param_changed)
        dim_layout.addRow("Raio:", self.radius_spin)
        
        dim_group.setLayout(dim_layout)
        layout.addWidget(dim_group)
        
        # Material
        mat_group = QGroupBox("Material")
        mat_layout = QFormLayout()
        
        self.material_combo = QComboBox()
        materials = ['COPPER', 'ALUMINUM', 'GOLD', 'SILVER', 'PEC']
        for mat in materials:
            self.material_combo.addItem(mat)
        self.material_combo.currentTextChanged.connect(self._on_param_changed)
        mat_layout.addRow("Material:", self.material_combo)
        
        mat_group.setLayout(mat_layout)
        layout.addWidget(mat_group)
        
        # Parâmetros específicos (Yagi, Patch, etc.)
        self.extra_group = QGroupBox("Parâmetros Específicos")
        self.extra_layout = QFormLayout()
        self.extra_group.setLayout(self.extra_layout)
        self.extra_group.setVisible(False)
        layout.addWidget(self.extra_group)
        
        # Botão criar
        self.create_btn = QPushButton("Criar Antena")
        self.create_btn.clicked.connect(self._emit_config)
        layout.addWidget(self.create_btn)
        
        layout.addStretch()
    
    def _on_type_changed(self, index):
        """Atualiza quando tipo muda"""
        atype = self.type_combo.currentData()
        self.config.antenna_type = atype
        
        # Atualiza parâmetros específicos
        self._update_extra_params(atype)
    
    def _update_extra_params(self, atype: AntennaType):
        """Atualiza parâmetros específicos por tipo"""
        # Limpa layout anterior
        while self.extra_layout.count():
            child = self.extra_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.extra_widgets = {}
        
        if atype == AntennaType.YAGI:
            self.extra_group.setVisible(True)
            
            directors = QSpinBox()
            directors.setRange(1, 20)
            directors.setValue(3)
            self.extra_layout.addRow("Nº Diretores:", directors)
            self.extra_widgets['num_directors'] = directors
            
        elif atype == AntennaType.PATCH:
            self.extra_group.setVisible(True)
            
            width = QDoubleSpinBox()
            width.setRange(0.001, 10)
            width.setValue(0.05)
            width.setSuffix(" m")
            self.extra_layout.addRow("Largura:", width)
            self.extra_widgets['width'] = width
            
            height = QDoubleSpinBox()
            height.setRange(0.0001, 1)
            height.setValue(0.001)
            height.setSuffix(" m")
            self.extra_layout.addRow("Espessura Substrato:", height)
            self.extra_widgets['substrate_height'] = height
            
        elif atype == AntennaType.HELIX:
            self.extra_group.setVisible(True)
            
            turns = QSpinBox()
            turns.setRange(1, 50)
            turns.setValue(10)
            self.extra_layout.addRow("Nº Voltas:", turns)
            self.extra_widgets['num_turns'] = turns
            
            spacing = QDoubleSpinBox()
            spacing.setRange(0.001, 1)
            spacing.setValue(0.05)
            spacing.setSuffix(" m")
            self.extra_layout.addRow("Espaçamento:", spacing)
            self.extra_widgets['spacing'] = spacing
            
        else:
            self.extra_group.setVisible(False)
    
    def _on_param_changed(self):
        """Atualiza configuração quando parâmetro muda"""
        self.config.length = self.length_spin.value()
        self.config.radius = self.radius_spin.value()
        self.config.material = self.material_combo.currentText()
    
    def _emit_config(self):
        """Emite configuração atual"""
        # Coleta parâmetros extras
        self.config.extra_params = {}
        if hasattr(self, 'extra_widgets'):
            for key, widget in self.extra_widgets.items():
                if isinstance(widget, QSpinBox):
                    self.config.extra_params[key] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    self.config.extra_params[key] = widget.value()
        
        self.antenna_changed.emit(self.config)


class SimulationPanel(QWidget):
    """Painel de configuração da simulação"""
    
    run_simulation = pyqtSignal(SimulationConfig)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = SimulationConfig()
        self.setup_ui()
    
    def setup_ui(self):
        """Configura a interface"""
        layout = QVBoxLayout(self)
        
        # Frequência
        freq_group = QGroupBox("Frequência")
        freq_layout = QFormLayout()
        
        self.freq_spin = QDoubleSpinBox()
        self.freq_spin.setRange(1, 100000)
        self.freq_spin.setValue(300)
        self.freq_spin.setSuffix(" MHz")
        self.freq_spin.valueChanged.connect(self._update_wavelength)
        freq_layout.addRow("Frequência:", self.freq_spin)
        
        self.wavelength_label = QLabel("λ = 1.000 m")
        freq_layout.addRow("Comprimento de Onda:", self.wavelength_label)
        
        freq_group.setLayout(freq_layout)
        layout.addWidget(freq_group)
        
        # Grid
        grid_group = QGroupBox("Grade FDTD")
        grid_layout = QFormLayout()
        
        self.cells_spin = QSpinBox()
        self.cells_spin.setRange(5, 50)
        self.cells_spin.setValue(20)
        self.cells_spin.setSuffix(" células/λ")
        grid_layout.addRow("Resolução:", self.cells_spin)
        
        self.pml_spin = QSpinBox()
        self.pml_spin.setRange(4, 20)
        self.pml_spin.setValue(8)
        self.pml_spin.setSuffix(" camadas")
        grid_layout.addRow("PML:", self.pml_spin)
        
        grid_group.setLayout(grid_layout)
        layout.addWidget(grid_group)
        
        # Simulação
        sim_group = QGroupBox("Simulação")
        sim_layout = QFormLayout()
        
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(100, 100000)
        self.steps_spin.setValue(1000)
        self.steps_spin.setSingleStep(100)
        sim_layout.addRow("Passos:", self.steps_spin)
        
        self.source_combo = QComboBox()
        self.source_combo.addItems(['Gaussiana', 'Senoidal', 'Modulada', 'Ricker'])
        sim_layout.addRow("Fonte:", self.source_combo)
        
        self.courant_spin = QDoubleSpinBox()
        self.courant_spin.setRange(0.1, 1.0)
        self.courant_spin.setValue(0.99)
        self.courant_spin.setDecimals(2)
        sim_layout.addRow("Nº Courant:", self.courant_spin)
        
        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)
        
        # Progresso
        progress_group = QGroupBox("Progresso")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Pronto")
        progress_layout.addWidget(self.status_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Botões
        btn_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("▶ Executar")
        self.run_btn.clicked.connect(self._run_simulation)
        btn_layout.addWidget(self.run_btn)
        
        self.stop_btn = QPushButton("⬛ Parar")
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        self._update_wavelength()
    
    def _update_wavelength(self):
        """Atualiza display de comprimento de onda"""
        freq_hz = self.freq_spin.value() * 1e6
        c = 299792458  # m/s
        wavelength = c / freq_hz
        self.wavelength_label.setText(f"λ = {wavelength:.3f} m")
    
    def _run_simulation(self):
        """Emite sinal para rodar simulação"""
        source_map = {
            'Gaussiana': 'gaussian',
            'Senoidal': 'sine',
            'Modulada': 'modulated',
            'Ricker': 'ricker'
        }
        
        self.config = SimulationConfig(
            frequency=self.freq_spin.value() * 1e6,
            cells_per_wavelength=self.cells_spin.value(),
            pml_layers=self.pml_spin.value(),
            num_timesteps=self.steps_spin.value(),
            source_type=source_map.get(self.source_combo.currentText(), 'gaussian'),
            courant_number=self.courant_spin.value()
        )
        
        self.run_simulation.emit(self.config)
    
    def set_progress(self, value: int):
        """Atualiza barra de progresso"""
        self.progress_bar.setValue(value)
    
    def set_status(self, text: str):
        """Atualiza status"""
        self.status_label.setText(text)
    
    def set_running(self, running: bool):
        """Atualiza estado de execução"""
        self.run_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)


class ResultsPanel(QWidget):
    """Painel de resultados"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Configura a interface"""
        layout = QVBoxLayout(self)
        
        # Parâmetros calculados
        params_group = QGroupBox("Parâmetros da Antena")
        params_layout = QFormLayout()
        
        self.directivity_label = QLabel("--")
        params_layout.addRow("Diretividade:", self.directivity_label)
        
        self.gain_label = QLabel("--")
        params_layout.addRow("Ganho:", self.gain_label)
        
        self.impedance_label = QLabel("--")
        params_layout.addRow("Impedância:", self.impedance_label)
        
        self.vswr_label = QLabel("--")
        params_layout.addRow("VSWR:", self.vswr_label)
        
        self.bandwidth_label = QLabel("--")
        params_layout.addRow("Bandwidth:", self.bandwidth_label)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Exportação
        export_group = QGroupBox("Exportar")
        export_layout = QVBoxLayout()
        
        self.export_csv_btn = QPushButton("Exportar CSV")
        export_layout.addWidget(self.export_csv_btn)
        
        self.export_img_btn = QPushButton("Exportar Imagem")
        export_layout.addWidget(self.export_img_btn)
        
        self.export_nec_btn = QPushButton("Exportar NEC2")
        export_layout.addWidget(self.export_nec_btn)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        layout.addStretch()
    
    def update_results(self, results: Dict[str, Any]):
        """Atualiza resultados exibidos"""
        if 'directivity' in results:
            d = results['directivity']
            self.directivity_label.setText(f"{d:.2f} ({10*np.log10(d):.1f} dBi)")
        
        if 'gain' in results:
            g = results['gain']
            self.gain_label.setText(f"{g:.2f} ({10*np.log10(g):.1f} dBi)")
        
        if 'impedance' in results:
            z = results['impedance']
            self.impedance_label.setText(f"{z.real:.1f} + j{z.imag:.1f} Ω")
        
        if 'vswr' in results:
            self.vswr_label.setText(f"{results['vswr']:.2f}")
        
        if 'bandwidth' in results:
            bw = results['bandwidth']
            self.bandwidth_label.setText(f"{bw/1e6:.1f} MHz")


class MainWindow(QMainWindow):
    """Janela principal do IloveAntenas"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IloveAntenas - Simulador de Antenas")
        self.setMinimumSize(1400, 900)
        
        self.antenna = None
        self.grid = None
        self.solver = None
        self.simulation_thread = None
        
        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_statusbar()
    
    def setup_ui(self):
        """Configura a interface principal"""
        # Widget central
        central = QWidget()
        self.setCentralWidget(central)
        
        # Layout principal
        main_layout = QHBoxLayout(central)
        
        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Painel esquerdo (propriedades)
        left_panel = QTabWidget()
        left_panel.setMaximumWidth(350)
        
        self.antenna_panel = AntennaPropertiesPanel()
        self.antenna_panel.antenna_changed.connect(self._on_antenna_changed)
        left_panel.addTab(self.antenna_panel, "Antena")
        
        self.sim_panel = SimulationPanel()
        self.sim_panel.run_simulation.connect(self._on_run_simulation)
        left_panel.addTab(self.sim_panel, "Simulação")
        
        self.results_panel = ResultsPanel()
        left_panel.addTab(self.results_panel, "Resultados")
        
        splitter.addWidget(left_panel)
        
        # Área central (visualização)
        center_tabs = QTabWidget()
        
        # Tab Geometria
        geom_widget = QWidget()
        geom_layout = QVBoxLayout(geom_widget)
        self.geom_canvas = GeometryCanvas()
        if HAS_MATPLOTLIB:
            geom_toolbar = NavigationToolbar(self.geom_canvas, self)
            geom_layout.addWidget(geom_toolbar)
        geom_layout.addWidget(self.geom_canvas)
        center_tabs.addTab(geom_widget, "Geometria 3D")
        
        # Tab Campos
        field_widget = QWidget()
        field_layout = QVBoxLayout(field_widget)
        self.field_canvas = FieldCanvas()
        if HAS_MATPLOTLIB:
            field_toolbar = NavigationToolbar(self.field_canvas, self)
            field_layout.addWidget(field_toolbar)
        field_layout.addWidget(self.field_canvas)
        
        # Controles de visualização de campo
        field_controls = QHBoxLayout()
        field_controls.addWidget(QLabel("Plano:"))
        self.plane_combo = QComboBox()
        self.plane_combo.addItems(['XY', 'XZ', 'YZ'])
        field_controls.addWidget(self.plane_combo)
        field_controls.addWidget(QLabel("Índice:"))
        self.slice_slider = QSlider(Qt.Orientation.Horizontal)
        self.slice_slider.setRange(0, 100)
        self.slice_slider.setValue(50)
        field_controls.addWidget(self.slice_slider)
        field_controls.addStretch()
        field_layout.addLayout(field_controls)
        
        center_tabs.addTab(field_widget, "Campos EM")
        
        # Tab Radiação
        rad_widget = QWidget()
        rad_layout = QVBoxLayout(rad_widget)
        self.rad_canvas = RadiationCanvas(polar=True)
        if HAS_MATPLOTLIB:
            rad_toolbar = NavigationToolbar(self.rad_canvas, self)
            rad_layout.addWidget(rad_toolbar)
        rad_layout.addWidget(self.rad_canvas)
        
        # Controles de diagrama
        rad_controls = QHBoxLayout()
        rad_controls.addWidget(QLabel("Corte:"))
        self.cut_combo = QComboBox()
        self.cut_combo.addItems(['Plano E', 'Plano H', '3D'])
        rad_controls.addWidget(self.cut_combo)
        self.normalize_check = QCheckBox("Normalizar")
        self.normalize_check.setChecked(True)
        rad_controls.addWidget(self.normalize_check)
        rad_controls.addStretch()
        rad_layout.addLayout(rad_controls)
        
        center_tabs.addTab(rad_widget, "Diagrama de Radiação")
        
        splitter.addWidget(center_tabs)
        
        # Proporções do splitter
        splitter.setSizes([300, 1100])
    
    def setup_menus(self):
        """Configura menus"""
        menubar = self.menuBar()
        
        # Menu Arquivo
        file_menu = menubar.addMenu("&Arquivo")
        
        new_action = QAction("&Novo Projeto", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Abrir...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Salvar", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Sai&r", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Menu Editar
        edit_menu = menubar.addMenu("&Editar")
        
        undo_action = QAction("&Desfazer", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_action)
        
        # Menu Antena
        antenna_menu = menubar.addMenu("&Antena")
        
        dipole_action = QAction("Dipolo λ/2", self)
        dipole_action.triggered.connect(lambda: self._create_preset('dipole'))
        antenna_menu.addAction(dipole_action)
        
        monopole_action = QAction("Monopolo λ/4", self)
        monopole_action.triggered.connect(lambda: self._create_preset('monopole'))
        antenna_menu.addAction(monopole_action)
        
        yagi_action = QAction("Yagi-Uda", self)
        yagi_action.triggered.connect(lambda: self._create_preset('yagi'))
        antenna_menu.addAction(yagi_action)
        
        patch_action = QAction("Patch Microstrip", self)
        patch_action.triggered.connect(lambda: self._create_preset('patch'))
        antenna_menu.addAction(patch_action)
        
        # Menu Simulação
        sim_menu = menubar.addMenu("&Simulação")
        
        run_action = QAction("&Executar", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self.sim_panel._run_simulation)
        sim_menu.addAction(run_action)
        
        # Menu Ajuda
        help_menu = menubar.addMenu("A&juda")
        
        about_action = QAction("&Sobre", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def setup_toolbar(self):
        """Configura barra de ferramentas"""
        toolbar = QToolBar("Principal")
        self.addToolBar(toolbar)
        
        # Botões
        toolbar.addAction("📁 Novo")
        toolbar.addAction("📂 Abrir")
        toolbar.addAction("💾 Salvar")
        toolbar.addSeparator()
        toolbar.addAction("▶ Executar")
        toolbar.addAction("⏹ Parar")
        toolbar.addSeparator()
        toolbar.addAction("🔍 Zoom+")
        toolbar.addAction("🔍 Zoom-")
    
    def setup_statusbar(self):
        """Configura barra de status"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Pronto")
    
    def _new_project(self):
        """Novo projeto"""
        self.antenna = None
        self.grid = None
        self.solver = None
        self.geom_canvas.clear()
        self.statusbar.showMessage("Novo projeto criado")
    
    def _open_project(self):
        """Abre projeto existente"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Abrir Projeto", "", "Projetos IloveAntenas (*.asim);;JSON (*.json)"
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                self.statusbar.showMessage(f"Projeto carregado: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao abrir: {e}")
    
    def _save_project(self):
        """Salva projeto"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Salvar Projeto", "", "Projetos IloveAntenas (*.asim);;JSON (*.json)"
        )
        if filename:
            try:
                data = {
                    'antenna': self.antenna.to_dict() if self.antenna else None,
                    'simulation': {
                        'frequency': self.sim_panel.freq_spin.value() * 1e6,
                        'steps': self.sim_panel.steps_spin.value()
                    }
                }
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                self.statusbar.showMessage(f"Projeto salvo: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao salvar: {e}")
    
    def _create_preset(self, preset_type: str):
        """Cria antena pré-definida"""
        try:
            # Importa factory
            from core.geometry import AntennaFactory
            from core.constants import C0
            
            freq = self.sim_panel.freq_spin.value() * 1e6
            wavelength = C0 / freq
            
            if preset_type == 'dipole':
                self.antenna = AntennaFactory.create_dipole(length=wavelength/2)
            elif preset_type == 'monopole':
                self.antenna = AntennaFactory.create_monopole(length=wavelength/4)
            elif preset_type == 'yagi':
                self.antenna = AntennaFactory.create_yagi(wavelength=wavelength, num_directors=3)
            elif preset_type == 'patch':
                self.antenna = AntennaFactory.create_patch(length=wavelength/2, width=wavelength/2)
            
            self.geom_canvas.draw_antenna(self.antenna)
            self.statusbar.showMessage(f"Antena {preset_type} criada para f={freq/1e6:.1f} MHz")
            
        except ImportError as e:
            QMessageBox.warning(self, "Aviso", f"Módulo não encontrado: {e}")
    
    def _on_antenna_changed(self, config: AntennaConfig):
        """Callback quando antena é alterada"""
        try:
            from core.geometry import AntennaFactory
            from core.constants import C0
            
            freq = self.sim_panel.freq_spin.value() * 1e6
            wavelength = C0 / freq
            
            if config.antenna_type == AntennaType.DIPOLE:
                self.antenna = AntennaFactory.create_dipole(
                    length=config.length,
                    radius=config.radius
                )
            elif config.antenna_type == AntennaType.MONOPOLE:
                self.antenna = AntennaFactory.create_monopole(
                    length=config.length,
                    radius=config.radius
                )
            elif config.antenna_type == AntennaType.YAGI:
                num_dirs = config.extra_params.get('num_directors', 3)
                self.antenna = AntennaFactory.create_yagi(
                    wavelength=wavelength,
                    num_directors=num_dirs
                )
            elif config.antenna_type == AntennaType.HELIX:
                num_turns = config.extra_params.get('num_turns', 10)
                spacing = config.extra_params.get('spacing', 0.05)
                self.antenna = AntennaFactory.create_helix(
                    radius=config.length/10,
                    pitch=spacing,
                    num_turns=num_turns
                )
            
            if self.antenna:
                self.geom_canvas.draw_antenna(self.antenna)
                self.statusbar.showMessage(f"Antena atualizada: {config.antenna_type.name}")
                
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao criar antena: {e}")
    
    def _on_run_simulation(self, config: SimulationConfig):
        """Callback para executar simulação"""
        if not self.antenna:
            QMessageBox.warning(self, "Aviso", "Crie uma antena primeiro!")
            return
        
        try:
            from core.grid import create_grid_for_antenna
            from solver import FDTDSolver, GaussianSource, SineSource
            
            self.statusbar.showMessage("Criando grade FDTD...")
            self.sim_panel.set_status("Criando grade...")
            
            # Cria grade
            self.grid = create_grid_for_antenna(
                self.antenna,
                freq_max=config.frequency,
                cells_per_wavelength=config.cells_per_wavelength,
                pml_layers=config.pml_layers
            )
            
            # Cria solver
            self.solver = FDTDSolver(self.grid)
            
            # Adiciona fonte
            feed_pos = self.antenna.get_feed_position()
            if feed_pos:
                grid_pos = self.grid.world_to_grid(feed_pos.x, feed_pos.y, feed_pos.z)
                
                if config.source_type == 'gaussian':
                    source = GaussianSource(
                        position=grid_pos,
                        amplitude=1.0,
                        tau=1.0 / config.frequency
                    )
                else:
                    source = SineSource(
                        position=grid_pos,
                        amplitude=1.0,
                        frequency=config.frequency
                    )
                
                self.solver.add_source(source)
            
            self.statusbar.showMessage("Executando simulação FDTD...")
            self.sim_panel.set_status("Simulando...")
            self.sim_panel.set_running(True)
            
            # Executa (em thread para não travar UI)
            self._run_simulation_steps(config.num_timesteps)
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro na simulação: {e}")
            self.sim_panel.set_running(False)
    
    def _run_simulation_steps(self, num_steps: int):
        """Executa passos da simulação"""
        # Nota: Em produção, usar QThread para não travar UI
        for step in range(num_steps):
            self.solver.step()
            
            if step % 50 == 0:
                progress = int((step + 1) / num_steps * 100)
                self.sim_panel.set_progress(progress)
                self.sim_panel.set_status(f"Passo {step}/{num_steps}")
                QApplication.processEvents()  # Atualiza UI
        
        self.sim_panel.set_progress(100)
        self.sim_panel.set_status("Concluído!")
        self.sim_panel.set_running(False)
        self.statusbar.showMessage("Simulação concluída!")
        
        # Atualiza visualização de campos
        self._update_field_display()
    
    def _update_field_display(self):
        """Atualiza visualização de campos"""
        if self.grid is None:
            return
        
        # Calcula magnitude do campo E
        E_mag = np.sqrt(
            self.grid.Ex**2 + 
            self.grid.Ey**2 + 
            self.grid.Ez**2
        )
        
        plane = self.plane_combo.currentText().lower()
        self.field_canvas.plot_field_slice(
            E_mag, plane=plane,
            title='|E| - Magnitude do Campo Elétrico'
        )
    
    def _show_about(self):
        """Mostra diálogo sobre"""
        QMessageBox.about(
            self,
            "Sobre IloveAntenas",
            "<h2>IloveAntenas v1.0</h2>"
            "<p>Simulador de Antenas baseado em FDTD</p>"
            "<p>Desenvolvido para simulação eletromagnética "
            "usando as equações de Maxwell.</p>"
            "<p><b>Funcionalidades:</b></p>"
            "<ul>"
            "<li>Design de geometria de antenas</li>"
            "<li>Simulação FDTD completa</li>"
            "<li>Visualização de campos EM</li>"
            "<li>Diagramas de radiação</li>"
            "</ul>"
            "<p>© 2026 - Licença MIT</p>"
        )


def main():
    """Função principal"""
    if not HAS_PYQT6:
        print("Erro: PyQt6 não está instalado.")
        print("Instale com: pip install PyQt6")
        return 1
    
    if not HAS_MATPLOTLIB:
        print("Aviso: Matplotlib não está instalado.")
        print("Visualização será limitada.")
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Estilo escuro opcional
    # app.setStyleSheet(DARK_STYLE)
    
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
