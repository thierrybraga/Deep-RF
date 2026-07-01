# IloveAntenas — Simulador e Visualizador de Antenas FDTD

IloveAntenas é um sistema completo para estudo de antenas e campos eletromagnéticos, composto por:

- **Núcleo de simulação** (`src/iloveantennas/simulator/`):
  - Motor FDTD em Python com suporte a múltiplos tipos de antena.
  - Backend FDTD opcional em Numba CUDA quando solicitado e quando o runtime CUDA estiver disponivel.
  - Modelos de materiais, geometrias paramétricas e pós‑processamento (campo distante, Carta de Smith).
  - Politicas de engine para malha/frames, diagnostico GPU/WSL e modelos de propagacao.
  - Ferramentas de visualização científica e uma GUI desktop opcional (PyQt).

- **Interface web** (`src/iloveantennas/web/`):
  - Backend FastAPI expondo criação de antena, simulação FDTD, análise e otimização.
  - Frontend em JavaScript com Three.js para visualização 3D da antena, padrão de radiação e campo EM animado.

Este README descreve:
- Estrutura de pastas.
- Fluxo de dados entre módulos.
- Como instalar e executar cada parte.
- Onde encontrar documentação detalhada de arquivos e funções.

---

## Estrutura do Projeto

- `src/iloveantennas/simulator/` — núcleo FDTD e ferramentas científicas.
  - `core/` — constantes, materiais, grade FDTD e geometria de antenas.
  - `engine/` — politicas de malha FDTD/FEM, limites numericos e captura de frames.
  - `solver/` — solver FDTD, fontes, monitores e conversão near‑to‑far.
  - `propagation/` — FSPL, Okumura-Hata, COST-231, orcamento de enlace e tracado de raios 2D.
  - `runtime/` — diagnostico de GPU Windows, WSL, Numba/CUDA e backends reais.
  - `visualization/` — visualização de geometria, campos, padrões e Carta de Smith (Matplotlib).
  - `utils/` — utilitários (conversões dB, FFT, exportação, estimativas de memória).
  - `gui/` — interface desktop (PyQt) para uso local.
  - `docs/` — documentação interna do núcleo (ver também DOCS_ILOVEANTENAS_SIMULATOR.md).
  - `main.py` — exemplos de uso em linha de comando.

- `src/iloveantennas/web/` — aplicação web para modelagem e estudo de antenas.
  - `app.py` — servidor FastAPI, endpoints REST e templates.
  - `config.py` — configurações de antena e simulação (dataclasses).
  - `antennas.py` — ponte entre `AntennaConfig` e `AntennaFactory`.
  - `analysis.py` — Carta de Smith, padrão de radiação, parâmetros derivados.
  - `simulation.py` — orquestra simulação FDTD em thread separada.
  - Endpoints de propagacao e runtime expostos por `app.py`.
  - `optimizer.py` / `optimization.py` — otimização de comprimento (casamento de impedância).
  - `resources.py` — tipos de antena e materiais expostos à UI.
  - `state.py` — armazenamento em memória de simulações e otimizações.
  - `static/` — CSS/JS (design system, renderer Three.js, animação de campo, gráficos).
  - `templates/` — páginas HTML (`index.html`, `analise.html`).
  - `README.md` — detalhes específicos da aplicação web.

- Arquivos adicionais:
  - `requirements.txt` — dependências Python.
  - `DOCS_STRUCTURE.md` — visão geral da arquitetura e pastas.
  - `DOCS_ILOVEANTENAS_SIMULATOR.md` — detalhes do núcleo FDTD.
  - `DOCS_ILOVEANTENAS_WEB.md` — detalhes da aplicação web.
  - `DOCS_DESIGN_SYSTEM.md` — paleta, tipografia, componentes e regras de manutenção visual.
  - `DOCS_ENGINE.md` — engine, GPU/WSL, propagacao, ray tracing e tema de campo.
  - `DOCS_ARCHITECTURE.md` — contratos consolidados, melhorias aplicadas e roadmap tecnico.

---

## Fluxo Geral do Sistema

1. **Definição da antena**
   - No **backend**:
     - `iloveantennas.web.config.AntennaConfig` descreve tipo e parâmetros (frequência, comprimento, raio, etc.).
     - `iloveantennas.web.antennas.create_antenna` converte `AntennaConfig` em um `AntennaGraph` via `AntennaFactory` em `iloveantennas.simulator.core.geometry.factory`.
   - No **frontend**:
     - `static/js/app.js` controla o estado (tipo de antena, parâmetros) e envia `POST /api/antenna/create`.
     - O backend responde com geometria serializada, bounding box e ponto de alimentação.
     - `static/js/renderer.js` renderiza a antena em 3D.

2. **Simulação FDTD**
   - O usuário configura resolução (`cells_per_wavelength`), passos (`num_steps`), tipo de fonte, PML etc. pela UI.
   - `POST /api/simulation/start`:
     - Constrói `AntennaConfig` e `SimulationConfig`.
     - Registra a simulação em `state.simulations`.
     - Inicia `run_fdtd_simulation` em uma thread.
   - `run_fdtd_simulation`:
     - Cria grade FDTD (`FDTDGrid`) em `iloveantennas.simulator.core`.
     - Configura fonte (`GaussianSource` ou `SineSource`).
     - Roda `FDTDSolver` (com ou sem Numba) pelo número de passos.
     - Grava cortes de campo `Ez` no plano XZ em intervalos regulares, normalizados por um máximo global.
     - Calcula série temporal e espectro (FFT) a partir de um `FieldProbe`.

3. **Visualização e animação do campo**
   - O frontend:
     - Consulta progresso em `GET /api/simulation/{sim_id}/status`.
     - Ao término, busca frames em `GET /api/simulation/{sim_id}/frames`.
   - `FieldRenderer` (`static/js/renderer.js`):
     - Anima os frames em um canvas 2D.
     - A cada frame, notifica `AntennaRenderer.updateField3D` para atualizar a textura de campo em um plano 3D.
   - `AntennaRenderer`:
     - Gera um plano XZ com resolução `(nx, nz)` coerente com a malha FDTD.
     - Usa shader customizado para mapear valores de campo em cores/alpha.

4. **Análise de antena**
   - Endpoints:
     - `/api/smith-chart` → dados para Carta de Smith.
     - `/api/radiation-pattern` → padrão de radiação 2D/3D.
     - `/api/calculate` → parâmetros derivados (ganho, largura de feixe, área efetiva etc.).
   - `analysis.py` faz a ponte com o núcleo `iloveantennas.simulator`.
   - `static/js/charts.js` e `ChartManager` cuidam dos gráficos.

5. **Otimização de comprimento**
   - `/api/optimize` inicia tarefa assíncrona em `optimization.py`.
   - `AntennaOptimizer` ajusta o comprimento buscando um VSWR desejado em uma frequência alvo.
   - O frontend acompanha progresso e aplica o resultado na UI (`optimizeLength` em `app.js`).

---

## Instalação

### Requisitos

- Python 3.11+ recomendado.
- Navegador moderno com suporte a WebGL (para a interface web).

### Passos

1. Criar e ativar um ambiente virtual (opcional, mas recomendado).
2. Instalar dependências:

```bash
pip install -r requirements.txt
```

---

## Executando o Núcleo `iloveantennas.simulator`

### Exemplos em linha de comando

Na raiz do projeto:

```bash
python -m iloveantennas.simulator.main
```

Use os argumentos ou menu interno (quando presente) para:
- Gerar exemplos de dipolo, Yagi, patch, hélice.
- Criar gráficos de Carta de Smith, S11, VSWR, padrões de radiação.

### GUI Desktop (PyQt)

Se as dependências de GUI estiverem instaladas:

```bash
python -m iloveantennas.simulator.gui.main_window
```

Isso abre uma janela gráfica onde é possível:
- Selecionar tipo de antena e parâmetros.
- Visualizar geometria e campos.
- Rodar simulações FDTD localmente.

---

## Executando a Interface Web `iloveantennas.web`

Na raiz do projeto:

```bash
python -m uvicorn iloveantennas.web.app:app --host 127.0.0.1 --port 5000 --reload
```

Por padrão, o servidor sobe em:

- http://localhost:5000

Funcionalidades principais:
- Modelagem de antenas com parâmetros interativos.
- Visualização 3D da antena em Three.js.
- Simulação FDTD com animação de campo EM (2D e 3D).
- Carta de Smith, S11, VSWR, padrão de radiação.
- Otimização de comprimento da antena para casamento.

Para mais detalhes específicos da aplicação web, veja:
- `src/iloveantennas/web/README.md`
- `DOCS_ILOVEANTENAS_WEB.md`

---

## Documentação Detalhada

- **Arquitetura e estrutura de pastas**  
  Consulte `DOCS_STRUCTURE.md` para uma visão consolidada dos diretórios e responsabilidades.

- **Engine, runtime e propagacao**  
  Consulte `DOCS_ENGINE.md` para politicas de malha, GPU/WSL, modelos de propagacao, tracado de raios e gradiente de campo.

- **Núcleo FDTD (`src/iloveantennas/simulator/`)**  
  Consulte `DOCS_ILOVEANTENAS_SIMULATOR.md` para:
  - Descrição de cada módulo (`core`, `solver`, `visualization`, `utils`, `gui`).
  - Lista das principais classes e funções, com responsabilidade de alto nível.

- **Aplicação Web (`src/iloveantennas/web/`)**  
  Consulte `DOCS_ILOVEANTENAS_WEB.md` para:
  - Descrição dos endpoints FastAPI e modelos Pydantic.
  - Fluxo da simulação e integração com o núcleo FDTD.
  - Papéis dos arquivos JS (app.js, renderer.js, charts.js) e CSS/HTML.

---

## Testes e Validação

- Testes de geometria de antena:
  - Em `tests/`, há testes unitários e diagnósticos para validar a construção das geometrias expostas pela aplicação.
- Verificação básica de sintaxe:
  - Pode ser feita em todo o projeto com:

```bash
python -m compileall src tests
```

Para adicionar uma suíte de testes mais completa (por exemplo, via `pytest`), a estrutura atual em `tests/` e as funções puras em `iloveantennas.simulator` já estão preparadas para isso.

---

## Onde Começar

- Para **estudo de antenas e campos EM** com visualização moderna:
  - Execute `python -m uvicorn iloveantennas.web.app:app --host 127.0.0.1 --port 5000 --reload` e use a interface no navegador.

- Para **desenvolvimento de novos modelos de antena ou algoritmos numéricos**:
  - Explore `src/iloveantennas/simulator/core/geometry/factory.py` para adicionar novas geometrias.
  - Ajuste ou estenda o solver em `src/iloveantennas/simulator/solver/fdtd.py` e `kernels.py`.
  - Use `visualization/` para gerar gráficos e animações de alta qualidade para artigos ou relatórios.

