# Estrutura Geral do Projeto

O projeto usa layout Python moderno com pacote em `src/iloveantennas`. A aplicacao combina um nucleo cientifico de simulacao eletromagnetica com uma interface web FastAPI/Three.js.

## Visao por Camadas

- `src/iloveantennas/simulator/`: nucleo de simulacao, geometria e visualizacao cientifica.
- `src/iloveantennas/web/`: API HTTP, orquestracao de simulacao, templates e assets da interface web.
- `tests/`: testes automatizados do pacote.
- `DOCS_*.md`: documentacao tecnica complementar.
  - `DOCS_ARCHITECTURE.md`: contratos consolidados, melhorias aplicadas e roadmap tecnico.

## Nucleo de Simulacao

- `src/iloveantennas/simulator/core/`
  - `constants.py` e `em_constants.py`: constantes eletromagneticas e auxiliares de comprimento de onda, CFL e impedancia.
  - `grid_config.py`, `grid.py`, `fdtd_grid.py`: configuracao e estruturas da malha FDTD.
  - `materials.py`: biblioteca e modelos de materiais.
  - `geometry/`: primitivas geometricas, topologia de antenas e `AntennaFactory`.
- `src/iloveantennas/simulator/engine/`
  - `GridPolicy`, `GridPlan` e `FramePolicy`: politicas de malha, limites numericos e captura de frames para FDTD/FEM.
  - `normalize_fdtd_backend`: contrato unico para aliases de backend FDTD usados por API e solver.
- `src/iloveantennas/simulator/solver/`
  - `fdtd.py`: loop numerico FDTD.
  - `kernels.py`: atualizacoes otimizadas de campos.
  - `cuda_kernels.py`: backend opcional Numba CUDA para FDTD quando solicitado.
  - `sources.py`, `monitors.py`, `farfield.py`: fontes, probes e pos-processamento campo distante.
- `src/iloveantennas/simulator/propagation/`
  - `models.py`: FSPL, Okumura-Hata, COST-231 Hata e orcamento de enlace.
  - `ray_tracing.py`: tracado de raios 2D com caminho direto e reflexoes de primeira ordem.
- `src/iloveantennas/simulator/runtime/`
  - `gpu.py`: diagnostico de GPU Windows, WSL, Numba/CUDA e backends efetivamente usados.
- `src/iloveantennas/simulator/fem/`
  - Solvers e geracao de malha para fluxo FEM experimental.
- `src/iloveantennas/simulator/visualization/`
  - Graficos Matplotlib, Carta de Smith e visualizacoes cientificas.
- `src/iloveantennas/simulator/gui/`
  - Interface desktop opcional.

## Aplicacao Web

- `src/iloveantennas/web/app.py`
  - Ponto de entrada FastAPI, rotas HTML, endpoints REST e montagem de assets estaticos.
- `src/iloveantennas/web/config.py`
  - Dataclasses `AntennaConfig` e `SimulationConfig`, compartilhadas pela API e pelos fluxos de simulacao.
- `src/iloveantennas/web/schemas.py`
  - Modelos Pydantic da API e conversores para `AntennaConfig`, `SimulationConfig`, propagacao e ray tracing.
- `src/iloveantennas/web/antennas.py`
  - Traduz `AntennaConfig` para geometrias do `AntennaFactory` e serializa dados para o renderer 3D.
- `src/iloveantennas/web/analysis.py`
  - Carta de Smith, padrao de radiacao, S11, VSWR e parametros derivados.
- `src/iloveantennas/web/simulation.py`
  - Orquestra FDTD/FEM em tarefas assíncronas, gera frames de campo e estatisticas.
- `src/iloveantennas/web/optimizer.py` e `optimization.py`
  - Otimizacao de comprimento e controle de progresso.
- `src/iloveantennas/web/matching.py`
  - Calculo de redes de casamento de impedancia.
- `src/iloveantennas/web/resources.py`
  - Tipos de antena e materiais expostos a UI. Materiais sao derivados de `MaterialLibrary`.
- `src/iloveantennas/web/state.py`
  - Estado em memoria de simulacoes e otimizacoes.
- `src/iloveantennas/web/storage.py`
  - Persistencia JSON simples da biblioteca de antenas.

## Frontend Web

- `src/iloveantennas/web/templates/index.html`
  - Tela principal: design, simulacao, analise, biblioteca, modais e viewport 3D.
- `src/iloveantennas/web/templates/analise.html`
  - Tela dedicada a analise detalhada.
- `src/iloveantennas/web/static/css/style.css`
  - Design system central: tokens de cor, tipografia, espacamento, componentes, estados e responsividade.
- `src/iloveantennas/web/static/js/app.core.js`
  - Estado principal da UI e chamadas de criacao/analise de antena.
- `src/iloveantennas/web/static/js/app.events.js`
  - Bind de eventos de interface.
- `src/iloveantennas/web/static/js/app.sim*.js`
  - Fluxos de simulacao, comparacao FDTD/FEM e otimizacao.
- `src/iloveantennas/web/static/js/app.ui.js`
  - Atualizacao de paineis, biblioteca e editor de antenas.
- `src/iloveantennas/web/static/js/engine.theme.js`
  - Fonte unica de gradiente de campo, parametros de animacao, materiais e cores de cena compartilhados por canvas 2D e shader WebGL.
- `src/iloveantennas/web/static/js/renderer.*.js`
  - Renderer Three.js dividido por responsabilidades: core, antena, camera, campo, radiacao e configuracoes.
- `src/iloveantennas/web/static/js/charts.*.js`
  - `ChartManager` e graficos: Carta de Smith, radiacao, S-parametros e modais.
- `src/iloveantennas/web/static/js/rendering/fieldRenderer.js`
  - Renderizacao 2D dos frames de campo e ponte com a visualizacao 3D.

## Padrao de Organizacao

- Estilos de UI devem ficar em `static/css/style.css`; templates e JS nao devem introduzir `style=""` ou cores literais para componentes.
- Cores de graficos devem passar pelo `ChartManager.colors`, que espelha os tokens do CSS.
- Gradientes e animacoes de campo devem passar por `ENGINE_THEME`; a legenda CSS usa `--field-gradient`.
- IDs usados pelo JavaScript ficam nos templates; classes visuais devem ser reutilizaveis e sem dependencias de regra de negocio.
- Novos endpoints devem converter payloads para `AntennaConfig`/`SimulationConfig` antes de chamar o nucleo cientifico.
- O nucleo `simulator` nao deve depender de FastAPI, templates ou estado de sessao web.
