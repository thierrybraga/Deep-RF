# IloveAntenas — Simulador e Visualizador de Antenas FDTD

IloveAntenas é um sistema completo para estudo de antenas e campos eletromagnéticos, composto por:

- **Núcleo de simulação** (`antenna_simulator/`):
  - Motor FDTD em Python com suporte a múltiplos tipos de antena.
  - Modelos de materiais, geometrias paramétricas e pós‑processamento (campo distante, Carta de Smith).
  - Ferramentas de visualização científica e uma GUI desktop opcional (PyQt).

- **Interface web** (`antenna_web/`):
  - Backend FastAPI expondo criação de antena, simulação FDTD, análise e otimização.
  - Frontend em JavaScript com Three.js para visualização 3D da antena, padrão de radiação e campo EM animado.

Este README descreve:
- Estrutura de pastas.
- Fluxo de dados entre módulos.
- Como instalar e executar cada parte.
- Onde encontrar documentação detalhada de arquivos e funções.

---

## Estrutura do Projeto

- `antenna_simulator/` — núcleo FDTD e ferramentas científicas.
  - `core/` — constantes, materiais, grade FDTD e geometria de antenas.
  - `solver/` — solver FDTD, fontes, monitores e conversão near‑to‑far.
  - `visualization/` — visualização de geometria, campos, padrões e Carta de Smith (Matplotlib).
  - `utils/` — utilitários (conversões dB, FFT, exportação, estimativas de memória).
  - `gui/` — interface desktop (PyQt) para uso local.
  - `docs/` — documentação interna do núcleo (ver também DOCS_ILOVEANTENAS_SIMULATOR.md).
  - `main.py` — exemplos de uso em linha de comando.

- `antenna_web/` — aplicação web para modelagem e estudo de antenas.
  - `app.py` — servidor FastAPI, endpoints REST e templates.
  - `config.py` — configurações de antena e simulação (dataclasses).
  - `antennas.py` — ponte entre `AntennaConfig` e `AntennaFactory`.
  - `analysis.py` — Carta de Smith, padrão de radiação, parâmetros derivados.
  - `simulation.py` — orquestra simulação FDTD em thread separada.
  - `optimizer.py` / `optimization.py` — otimização de comprimento (casamento de impedância).
  - `resources.py` — tipos de antena e materiais expostos à UI.
  - `state.py` — armazenamento em memória de simulações e otimizações.
  - `static/` — CSS/JS (renderer Three.js, animação de campo, gráficos).
  - `templates/` — páginas HTML (`index.html`, `analise.html`).
  - `README.md` — detalhes específicos da aplicação web.

- Arquivos adicionais:
  - `requirements.txt` — dependências Python.
  - `DOCS_STRUCTURE.md` — visão geral da arquitetura e pastas.
  - `DOCS_ILOVEANTENAS_SIMULATOR.md` — detalhes do núcleo FDTD.
  - `DOCS_ILOVEANTENAS_WEB.md` — detalhes da aplicação web.

---

## Fluxo Geral do Sistema

1. **Definição da antena**
   - No **backend**:
     - `antenna_web.config.AntennaConfig` descreve tipo e parâmetros (frequência, comprimento, raio, etc.).
     - `antenna_web.antennas.create_antenna` converte `AntennaConfig` em um `AntennaGraph` via `AntennaFactory` em `antenna_simulator.core.geometry.factory`.
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
     - Cria grade FDTD (`FDTDGrid`) em `antenna_simulator.core`.
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
   - `analysis.py` faz a ponte com o núcleo `antenna_simulator`.
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

## Executando o Núcleo `antenna_simulator`

### Exemplos em linha de comando

No diretório `antenna_simulator`:

```bash
cd antenna_simulator
python main.py
```

Use os argumentos ou menu interno (quando presente) para:
- Gerar exemplos de dipolo, Yagi, patch, hélice.
- Criar gráficos de Carta de Smith, S11, VSWR, padrões de radiação.

### GUI Desktop (PyQt)

Se as dependências de GUI estiverem instaladas:

```bash
cd antenna_simulator
python -m gui.main_window
```

Isso abre uma janela gráfica onde é possível:
- Selecionar tipo de antena e parâmetros.
- Visualizar geometria e campos.
- Rodar simulações FDTD localmente.

---

## Executando a Interface Web `antenna_web`

No diretório `antenna_web`:

```bash
cd antenna_web
python app.py
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
- `antenna_web/README.md`
- `DOCS_ANTENNA_WEB.md`

---

## Documentação Detalhada

- **Arquitetura e estrutura de pastas**  
  Consulte [DOCS_STRUCTURE.md](file:///c:/Users/thier/Desktop/workspace/DOCS_STRUCTURE.md) para uma visão consolidada dos diretórios e responsabilidades.

- **Núcleo FDTD (`antenna_simulator/`)**  
  Consulte [DOCS_ANTENNA_SIMULATOR.md](file:///c:/Users/thier/Desktop/workspace/DOCS_ANTENNA_SIMULATOR.md) para:
  - Descrição de cada módulo (`core`, `solver`, `visualization`, `utils`, `gui`).
  - Lista das principais classes e funções, com responsabilidade de alto nível.

- **Aplicação Web (`antenna_web/`)**  
  Consulte [DOCS_ANTENNA_WEB.md](file:///c:/Users/thier/Desktop/workspace/DOCS_ANTENNA_WEB.md) para:
  - Descrição dos endpoints FastAPI e modelos Pydantic.
  - Fluxo da simulação e integração com o núcleo FDTD.
  - Papéis dos arquivos JS (app.js, renderer.js, charts.js) e CSS/HTML.

---

## Testes e Validação

- Testes de geometria de antena:
  - Em `antenna_web/test_antenna_geometry.py`, há testes unitários para validar a construção de cada tipo de antena exposta na interface web.
- Verificação básica de sintaxe:
  - Pode ser feita em todo o projeto com:

```bash
cd antenna_web
python -m compileall ..
```

Para adicionar uma suíte de testes mais completa (por exemplo, via `pytest`), a estrutura atual (`test_antenna_geometry.py` e funções puras em `antenna_simulator`) já está preparada para isso.

---

## Onde Começar

- Para **estudo de antenas e campos EM** com visualização moderna:
  - Siga para `antenna_web`, execute `python app.py` e use a interface no navegador.

- Para **desenvolvimento de novos modelos de antena ou algoritmos numéricos**:
  - Explore `antenna_simulator/core/geometry/factory.py` para adicionar novas geometrias.
  - Ajuste ou estenda o solver em `antenna_simulator/solver/fdtd.py` e `kernels.py`.
  - Use `visualization/` para gerar gráficos e animações de alta qualidade para artigos ou relatórios.

