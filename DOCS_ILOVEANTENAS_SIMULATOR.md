## antenna_simulator — Núcleo de Simulação FDTD

### Visão Geral

O diretório `antenna_simulator` contém o motor de simulação numérica de antenas baseado em FDTD, além de utilitários de geometria, materiais e visualização científica.

---

### core/

#### core/constants.py
- Define constantes físicas fundamentais:
  - Velocidade da luz no vácuo (c0).
  - Permeabilidade e permissividade do vácuo (μ0, ε0).
  - Impedância característica do espaço livre (Z0).
- Usado por todo o núcleo de simulação para manter consistência dimensional.

#### core/em_constants.py
- Funções utilitárias para cálculos eletromagnéticos:
  - `wavelength_in_medium(freq, epsilon_r, mu_r)`: comprimento de onda em meio com εr/μr.
  - `frequency_to_wavelength(freq)`, `wavelength_to_frequency(wavelength)`.
  - `cells_per_wavelength(freq, dx, epsilon_r)`: quantas células por λ.
  - `optimal_cell_size(freq_max, cells_per_lambda)`: calcula dx ideal.
  - `cfl_time_step(dx, dy, dz, courant)`: passo de tempo obedecendo condição CFL.

#### core/grid_config.py
- Classe `GridConfig`:
  - Parâmetros discretos: `nx, ny, nz`, `dx`, `dt`.
  - Configuração de PML (número de camadas).
  - Fator de Courant.
  - Centraliza a configuração da malha usada por `FDTDGrid` e `FDTDSolver`.

#### core/materials.py
- Enumerações:
  - `MaterialType`: tipos básicos (condutor, dielétrico, PML, etc.).
  - `BoundaryType`: tipos de fronteira (aberta, PEC, PMC, PML).
- Classes:
  - `Material`: modelo base de material com ε, μ, σ.
  - `DispersiveMaterial`: extensão para materiais com dispersão em frequência.
  - `AnisotropicMaterial`: materiais com propriedades dependentes da direção.
  - `PMLMaterial`: parâmetros específicos de camada absorvente.
  - `MaterialLibrary`: coleção de materiais típicos (ar, FR4, cobre, etc.).

#### core/geometry/primitives.py
- Classes geométricas:
  - `Vector3D`: vetor 3D com operações básicas (soma, produto escalar, norma).
  - `BoundingBox`: caixa delimitadora com centro, tamanhos e operações de expansão/fusão.
  - `GeometryPrimitive`: classe base abstrata para primitivas.
  - `Wire`: segmento condutor, usado em dipolos, Yagi, LPDA e loops.
  - `Rectangle`: superfícies (por exemplo, plano de terra de monopolo, patches).
  - `Cylinder`: cilindros sólidos (ex.: monopolos cilíndricos).
  - `Helix`: geometria paramétrica de antena helicoidal.
  - `Horn`: corneta (throat/aperture, comprimento, etc.).
  - `ParabolicDish`: parabólica com curva geradora rotacionada.

#### core/geometry/topology.py
- Representação topológica da antena:
  - `AntennaNode`: nó do grafo (ponto no espaço).
  - `AntennaEdge`: ligação entre nós, indicando elementos condutores.
  - `AntennaGraph`:
    - Armazena lista de nós/arestas.
    - Mantém referência ao ponto de alimentação.
    - Expõe `get_bounding_box()` e iteração sobre primitivas para aplicar na grade FDTD.

#### core/geometry/factory.py
- Classe `AntennaFactory`:
  - Métodos estáticos para construção de geometrias padrão:
    - Dipolo centro-alimentado.
    - Monopolo sobre plano de terra (Rectangle + wire).
    - Yagi-Uda (refletor, dipolo excitado, diretores).
    - Patch retangular sobre substrato.
    - Antena helicoidal (helix + ground).
    - Corneta reta.
    - Prato parabólico.
    - LPDA (array de dipolos escalonados).
    - Loop.
    - Dipolo em V.
  - Cada método retorna um `AntennaGraph` pronto para ser aplicado em `FDTDGrid`.

#### core/fdtd_grid.py
- Classe `FDTDGrid`:
  - Mantém arrays 3D dos campos E/H.
  - Aplica geometrias da antena na malha (definindo regiões condutoras).
  - Configura camadas PML.
  - Calcula coeficientes de atualização (σ, ε, μ efetivos).
- Função `create_grid_for_antenna(...)`:
  - Recebe uma antena (`AntennaGraph`) e parâmetros de simulação.
  - Dimensiona `GridConfig` adequado à antena (margens, resolução).

---

### solver/

#### solver/fdtd.py
- Classe `FDTDSolver`:
  - Recebe `FDTDGrid` e parâmetros numéricos.
  - Integra campos no tempo usando kernels otimizados.
  - Gerencia lista de fontes (`Source`) e monitores (`FieldProbe`, `NearFieldBox`).
  - Mantém estatísticas de simulação (tempo de computação, máximos de campo).

#### solver/kernels.py
- Funções numéricas de baixo nível:
  - `update_h_kernel(...)`: atualiza Hx, Hy, Hz com base em derivadas espaciais de E.
  - `update_e_kernel(...)`: atualiza Ex, Ey, Ez com base em derivadas espaciais de H.
- Implementações pensadas para aceleração via Numba, com loops vetorizados.

#### solver/sources.py
- Enumeração `SourceType`.
- Classe abstrata `Source` com interface comum.
- Fontes concretas:
  - `GaussianSource`: pulso gaussiano no tempo.
  - `SineSource`: onda senoidal contínua.
  - `ModulatedGaussianSource`: portadora senoidal modulada por gaussiana.
  - `RickerSource`: wavelet de Ricker (comum em geofísica, útil para pulsos wideband).

#### solver/monitors.py
- `FieldProbe`:
  - Registra valor de um componente de campo em um ponto ao longo do tempo.
  - Usado para extrair S11, FFT e resposta temporal.
- `NearFieldBox`:
  - Caixa volumétrica que armazena campos numa região para posterior conversão near‑to‑far.

#### solver/farfield.py
- `NearToFarField`:
  - Recebe campos em uma superfície fechada.
  - Calcula campos distantes Eθ/Eφ em malha angular (θ, φ).
- Funções auxiliares:
  - `calculate_directivity`, `calculate_gain`, `dB`, `dBi`.

---

### visualization/

#### visualization/plots.py
- `GeometryVisualizer`: plota antenas a partir de `AntennaGraph` em 3D.
- `FieldVisualizer`: plota cortes de campo (Ex/Ey/Ez) ao longo da malha.
- `RadiationPatternPlot`: gráficos polares/cartesianos de padrões de radiação 2D.
- `FieldAnimator`: gera animações de campo ao longo do tempo (matplotlib / vídeo).
- Funções de conveniência para S‑parâmetros, impedância e outros gráficos.

#### visualization/smith_chart.py
- `SmithChartConfig`: configurações de Carta de Smith (cores, estilo).
- Conversões:
  - Impedância ↔ coeficiente de reflexão (γ).
  - Normalização / desnormalização de impedância.
  - γ ↔ S11 em dB, VSWR, perda de retorno, etc.
- `ImpedanceResult`: estrutura de dados com impedância ao longo da frequência.
- Funções de plot:
  - `plot_s11_vs_frequency`, `plot_impedance_vs_frequency`, `plot_vswr_vs_frequency`.

---

### utils/helpers.py

- Conversões:
  - dB ↔ linear, dBm ↔ watts.
  - VSWR, perda de retorno, coeficiente de reflexão.
- Cálculos de sistema:
  - Área efetiva, path loss de Friis, orçamento de enlace.
- Sinais:
  - FFT e geração de eixos de frequência.
  - Aplicação de janelas (Hann, Hamming etc.).
  - Suavização de dados.
- Exportação:
  - CSV, NEC2, arquivos Touchstone.
  - Campos em VTK (para ParaView/VisIt).
- Estimativas de recursos:
  - Memória da grade FDTD, tamanhos recomendados.

---

### gui/main_window.py

- Define a interface gráfica desktop (PyQt):
  - `AntennaType`, `SimulationConfig`, `AntennaConfig` (lado GUI).
  - `SimulationWorker`: thread para rodar simulações sem travar a UI.
  - `GeometryCanvas`, `FieldCanvas`, `RadiationCanvas`: integra Matplotlib na GUI.
  - `AntennaPropertiesPanel`, `SimulationPanel`, `ResultsPanel`, `MainWindow`.
- Permite:
  - Selecionar tipo de antena, parâmetros geométricos e de simulação.
  - Visualizar geometria, campos e padrões de radiação.
  - Rodar e monitorar simulações FDTD nativamente, sem navegador.

---

### main.py

- Ponto de entrada em linha de comando:
  - `run_dipole_example()`, `run_yagi_example()`, `run_patch_example()`, `run_helix_example()`.
  - `run_smith_chart_example()`: gera Carta de Smith e gráficos associados.
  - `list_materials()`: imprime materiais disponíveis.
  - `main()`: menu/argumentos para disparar exemplos.

