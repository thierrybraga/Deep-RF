## antenna_web — Aplicação Web de Simulação e Visualização

### Visão Geral

`antenna_web` é a interface web do sistema IloveAntenas, construída com FastAPI no backend e Three.js + JS no frontend. Ela permite:
- Escolher e parametrizar diversos tipos de antenas.
- Visualizar a geometria 3D da antena.
- Rodar simulações FDTD (via `antenna_simulator`) e animar o campo eletromagnético.
- Analisar Carta de Smith, S11, VSWR, padrão de radiação e parâmetros derivados.
- Otimizar automaticamente o comprimento da antena para casamento em uma frequência alvo.

---

### Backend (Python)

#### app.py

- Configuração do servidor FastAPI:
  - Monta arquivos estáticos (`/static`).
  - Configura CORS aberto (`allow_origins=["*"]`).
  - Usa Jinja2 para templates HTML (`index.html`, `analise.html`).
- Modelos Pydantic:
  - `AntennaCreateRequest`: parâmetros para criação de antena (tipo, frequência, comprimento, raio, etc.).
  - `SimulationStartRequest`: parâmetros de simulação FDTD (cells_per_wavelength, num_steps, PML, Courant, fonte, amplitude, uso de motor otimizado).
  - `SmithChartRequest`, `RadiationPatternRequest`, `CalculateParametersRequest`, `OptimizeRequest`.
- Endpoints principais:
  - `GET /`: renderiza `index.html`.
  - `GET /analise`: renderiza `analise.html`.
  - `GET /api/materials`: retorna materiais disponíveis.
  - `GET /api/antenna/types`: lista tipos de antena suportados pela UI.
  - `POST /api/antenna/create`:
    - Constrói `AntennaConfig`.
    - Cria antena via `create_antenna`.
    - Converte geometria para formato JSON para o renderer 3D.
  - `POST /api/antenna/analysis`:
    - Faz análise completa: geometria, Carta de Smith, padrão de radiação, parâmetros derivados.
  - `POST /api/simulation/start`:
    - Cria `AntennaConfig` e `SimulationConfig`.
    - Registra simulação em `state.simulations`.
    - Dispara `run_fdtd_simulation` em thread separada.
  - `GET /api/simulation/{sim_id}/status`:
    - Retorna progresso, estatísticas e metadados da simulação (sem os frames).
  - `GET /api/simulation/{sim_id}/frames`:
    - Retorna lista de frames de campo normalizados + `field_shape`.
  - `POST /api/smith-chart`: devolve dados de Carta de Smith.
  - `POST /api/radiation-pattern`: devolve padrão de radiação.
  - `POST /api/calculate`: calcula parâmetros (ganho, largura de feixe, etc.).
  - `POST /api/optimize`: inicia tarefa de otimização de comprimento.
  - `GET /api/optimize/{opt_id}/status`: consulta estado da otimização.

#### config.py

- `AntennaConfig`:
  - Tipo de antena (`dipole`, `monopole`, `yagi`, `patch`, `helix`, `horn`, `dish`, `lpda`, `loop`, `v_dipole`).
  - Frequência.
  - Parâmetros geométricos relevantes (comprimento, raio, número de diretores, geometria de corneta/prato/LPDA/loop).
- `SimulationConfig`:
  - Discretização: `cells_per_wavelength`, `num_steps`, `pml_layers`, `courant`.
  - Fonte: `source_type`, `source_amplitude`.
  - Aceleração: `use_optimized` para habilitar Numba quando disponível.

#### antennas.py

- `create_antenna(config: AntennaConfig)`:
  - Mapeia `AntennaConfig.type` para o método correspondente em `AntennaFactory`.
  - Gera objeto `AntennaGraph` com a geometria completa.
- `get_antenna_geometry_data(antenna)`:
  - Extrai:
    - Lista de primitivas (fios, retângulos, cilindros, etc.) em formato serializável.
    - Bounding box (centro, tamanho).
    - Ponto de alimentação.
  - Formato pronto para consumo pelo `renderer.js`.

#### analysis.py

- `estimate_beamwidth(pattern, angles)`: estima largura de feixe a partir do padrão.
- `calculate_radiation_pattern(antenna_config)`:
  - Usa o núcleo `antenna_simulator` para obter padrão 3D.
  - Processa para formatos 2D (cortes) e 3D (grid θ×φ).
- `calculate_smith_chart_data(antenna_config)`:
  - Calcula impedância, S11, VSWR e outros parâmetros em faixa de frequência.
  - Retorna dados já prontos para gráficos no frontend.
- `calculate_parameters(frequency, directivity_db, efficiency)`:
  - Deriva área efetiva, ganho, largura de feixe e outras grandezas de interesse.

#### simulation.py

- `run_fdtd_simulation(sim_id, antenna_config, sim_config)`:
  - Marca simulação como `running` em `state.simulations`.
  - Cria antena via `create_antenna`.
  - Calcula λ e tamanho de célula `dx`.
  - Dimensiona o domínio FDTD com base no bounding box da antena + margens em múltiplos de λ.
  - Cria `GridConfig` e `FDTDGrid`, aplica antena e PML.
  - Instancia `FDTDSolver` com ou sem Numba.
  - Configura fonte (`GaussianSource` ou `SineSource`) no centro da grade.
  - Adiciona `FieldProbe` no centro para extrair série temporal.
  - Loop de tempo:
    - Atualiza campos.
    - Atualiza progresso (0–100%).
    - Em intervalos regulares, grava cortes de `Ez` no plano XZ no meio da grade.
  - Para animação:
    - Armazena cortes brutos e seus máximos.
    - Após a simulação, normaliza todos os frames por um único máximo global.
    - Retorna `frames` (lista de dicionários com `step`, `time_ns`, `field`, `max_value`) e `field_shape=[nx, nz]`.
  - Calcula espectro via FFT da série temporal da probe (frequências, magnitudes).
  - Atualiza `state.simulations[sim_id]` para `completed` com todos os resultados.

#### optimizer.py e optimization.py

- `OptimizationResult`:
  - Armazena comprimento otimizado, VSWR final, histórico da busca.
- `AntennaOptimizer`:
  - Implementa algoritmo de busca (por exemplo, busca incremental ou método tipo golden‑section) para ajustar comprimento visando VSWR mínimo.
- `run_optimization_task(opt_id, params)`:
  - Cria `AntennaOptimizer` com parâmetros da requisição.
  - Atualiza `state.optimizations[opt_id]` com progresso, mensagem de status e resultado final.

#### resources.py

- `MATERIALS`: dicionário de materiais disponíveis para seleção no frontend.
- `ANTENNA_TYPES`: lista/dicionário de tipos de antena com rótulos amigáveis e descrição, consumidos pela UI.

#### state.py

- Estruturas globais em memória:
  - `simulations`: mapeia `sim_id` → dados de simulação.
  - `optimizations`: mapeia `opt_id` → estado de otimização.
- Locks (`simulation_lock`, `optimization_lock`) para sincronização entre threads de simulação/otimização e endpoints HTTP.

#### test_antenna_geometry.py

- Conjunto de testes para validar geometrias:
  - `test_dipole`, `test_yagi`, `test_helix`, `test_monopole_ground`, `test_patch_geometry`, `test_horn_geometry`, `test_dish_geometry`, `test_lpda_geometry`, `test_loop_geometry`.
- Verifica:
  - Presença de elementos esperados.
  - Dimensões básicas.
  - Existência de plano de terra no monopolo, etc.

---

### Frontend (static/js, static/css, templates)

#### static/js/app.js

- Classe `IloveAntenas`:
  - Gerencia estado da antena, simulação e resultados (Smith, radiação, parâmetros, simulação FDTD).
  - Inicializa:
    - `AntennaRenderer` (3D).
    - `FieldRenderer` (animação 2D + notificação para 3D).
    - `ChartManager` (gráficos).
  - Bind de eventos:
    - Botões de tipo de antena.
    - Inputs de frequência, comprimento, raio, substrato, etc.
    - Sliders de resolução (`cellsPerWavelength`) e número de passos (`numSteps`).
    - Botão de simulação (chama backend, faz polling de status, baixa frames).
    - Botão de otimização de comprimento.
    - Controles do viewport 3D (reset de câmera, grid, eixos, radiação, auto‑rotate, fullscreen).
    - Controles de tema (claro/escuro).
  - Funções principais:
    - `setAntennaType(type)`: atualiza tipo e mostra/esconde grupos de parâmetros relevantes.
    - `createAntenna()`: envia `POST /api/antenna/create` e atualiza a cena 3D + painel de info.
    - `fetchAnalysis()`: chama `/api/smith-chart`, `/api/radiation-pattern`, `/api/calculate` e alimenta gráficos.
    - `runSimulation()`: dispara `/api/simulation/start`, faz polling de progresso, obtém frames e configura `FieldRenderer` e `AntennaRenderer.setupFieldVisualization`.
    - `optimizeLength()`: dispara `/api/optimize`, acompanha progresso e atualiza comprimento na UI.

#### static/js/renderer.js

- Configuração global `RENDER_CONFIG`:
  - Qualidade (pixel ratio, sombras, antialias).
  - Câmera (FOV, near/far, posição padrão).
  - Campo (`field.scale` usado na construção do plano de campo; mantido em 1.0 para coerência com domínio FDTD).

- Classe `AntennaRenderer`:
  - Responsável por:
    - Criar cena Three.js (luzes, grid, eixos, chão, materiais).
    - Renderizar geometrias da antena a partir dos dados do backend.
    - Ajustar câmera (`fitCameraToObject`, `setCameraView`).
    - Renderizar padrão de radiação 3D em malha esférica.
    - Renderizar plano de campo 3D usando shader customizado com textura de dados.
  - Métodos importantes:
    - `renderAntenna(data)`: recebe bounding box, geometrias e ponto de alimentação; aplica escala (`calculateScale`) e adiciona meshes.
    - `createWire`, `createRectangle`, `createCylinder`, `createHelix`, `createHorn`, `createDish`: convertem primitivas do backend em geometrias Three.js.
    - `createFeedPoint`: esfera destacada no ponto de alimentação.
    - `setRadiationData(data)`, `createRadiationMesh()`, `toggleRadiation()`: padrão de radiação 3D colorido por ganho.
    - `setupFieldVisualization(gridInfo, scale)`: cria plano XZ com resolução `(nx, nz)` e textura de dados para o campo; o tamanho físico é consistente com `nx * dx` e a escala da antena.
    - `updateField3D(frame)`: atualiza textura do campo EM a partir de valores normalizados em `[-1, 1]`.
    - Toggles: `toggleGrid`, `toggleAxes`, `toggleField3D`, `toggleAutoRotate`, `setTheme`.

- Classe `FieldRenderer`:
  - Animação 2D do campo (canvas 2D separado):
    - `setFrames(frames, fieldShape)`: armazena frames e dispara render do primeiro.
    - `renderFrame(idx)`: desenha mapa de cores do campo atual e notifica `AntennaRenderer.updateField3D`.
    - `play`, `pause`, `toggle`, `seekTo`, `setSpeed`: controle de animação.

#### static/js/charts.js

- `ChartManager`:
  - Gera e atualiza:
    - Carta de Smith.
    - S11 vs frequência.
    - VSWR vs frequência.
    - Padrões de radiação 2D.
  - Fornece métodos para expandir gráficos em modal (`showExpanded`), resize responsivo e fechamento.

#### static/js/analise.js

- Script específico da página `analise.html`:
  - Carrega dados existentes ou dispara novas análises.
  - Foca em visualização detalhada de resultados (sem viewport 3D completo).

#### static/css/style.css

- Tema escuro moderno:
  - Layout com painel lateral, viewport 3D, área de resultados e painel de animação.
  - Estilização de botões, sliders, cartões de resultado, modais (ajuda, configurações, matching).
  - Cores consistentes com visualização 3D (fundos escuros, acentos em ciano/laranja).

#### templates/index.html

- Página principal:
  - Tabs de navegação: Design, Simulação, Análise.
  - Contém:
    - Área de design de antena (tipos, parâmetros).
    - Viewport 3D (`canvas-3d`) para geometria e campo.
    - Painel de animação (`canvas-field`) com controles (play/pause, slider de tempo).
    - Painéis de resultados (gráficos, textos).
    - Botões para otimização, ajuda, configurações, matching.

#### templates/analise.html

- Focada em análise:
  - Grandes áreas para gráficos.
  - Menos ênfase na edição de geometria.

