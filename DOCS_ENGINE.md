# Engine de Simulacao e Propagacao

Este documento registra os contratos de engenharia da engine depois da consolidacao de estilos, calculos e runtime.

## Camadas

- `src/iloveantennas/simulator/engine/`
  - Politicas numericas reutilizaveis, como limites de malha FDTD/FEM e intervalo de captura de frames.
  - `GridPolicy`, `GridPlan` e `frame_record_interval` removem numeros magicos do orquestrador web.
  - `normalize_fdtd_backend` centraliza aliases aceitos pela API e pelo solver.
- `src/iloveantennas/simulator/runtime/`
  - Diagnostico de GPU Windows, WSL e bibliotecas de aceleracao.
  - O status e exposto em `/api/engine/status`.
- `src/iloveantennas/simulator/solver/cuda_kernels.py`
  - Kernels CUDA opcionais para atualizacao FDTD de `E` e `H`, aplicacao de fonte e leitura pontual de probe.
- `src/iloveantennas/simulator/propagation/`
  - Modelos analiticos de propagacao: espaco livre, Okumura-Hata, COST-231 Hata e orcamento de enlace.
  - Tracado de raios 2D deterministico com caminho direto e reflexoes de primeira ordem.
- `src/iloveantennas/web/simulation.py`
  - Orquestra FDTD/FEM e usa as politicas de engine, mas nao define constantes numericas globais.
- `src/iloveantennas/web/static/js/engine.theme.js`
  - Fonte de verdade para gradiente de campo e tempos/parametros de animacao dos renderizadores.

## GPU, Windows e WSL

O projeto diferencia tres coisas:

- GPU disponivel no Windows: detectada por `nvidia-smi`.
- CUDA acessivel via WSL: diagnosticada por `wsl -l -v` e `wsl nvidia-smi`.
- Solver usando GPU: implementado como backend opcional `cuda` via Numba CUDA. O caminho padrao continua `numba-cpu` quando Numba esta disponivel, ou `numpy-cpu` como fallback.

Essa separacao evita que uma placa CUDA presente seja interpretada como solver GPU ativo sem runtime Python/WSL pronto. A renderizacao WebGL no navegador usa GPU quando o browser disponibiliza esse caminho, mas isso e independente do solver numerico Python.

Para solicitar CUDA em uma simulacao FDTD:

```json
{
  "antenna_type": "dipole",
  "frequency": 300000000,
  "method": "fdtd",
  "solver_backend": "cuda"
}
```

Tambem e possivel forcar por ambiente:

```text
ILOVEANTENNAS_FDTD_BACKEND=cuda
```

Se Numba CUDA nao estiver disponivel, o solver registra `backend_warning` e volta para CPU automaticamente.

Aliases aceitos para backend FDTD:

- `auto`
- `cuda`, `gpu`, `cuda_gpu`
- `numba`, `cpu`, `numba_cpu`
- `numpy`, `numpy_cpu`

## Modelos de Propagacao

- `free_space_path_loss_db(frequency_hz, distance_m)` usa FSPL em dB.
- `okumura_hata_path_loss_db(...)` aplica Okumura-Hata e retorna avisos quando parametros saem da faixa calibrada.
- `cost231_hata_path_loss_db(...)` cobre a extensao urbana em 1500 MHz a 2000 MHz.
- `compare_path_loss(...)` devolve todos os modelos, seleciona um modelo valido e calcula orcamento de enlace.

Endpoints:

- `POST /api/propagation/path-loss`
- `POST /api/propagation/ray-trace`

## Renderizacao e Cores de Campo

O gradiente do campo eletromagnetico e definido uma vez em `engine.theme.js`:

- frio: `#0b1026`
- informacao: `#38bdf8`
- medio: `#22c55e`
- quente: `#f59e0b`
- pico: `#ef4444`

O CSS usa `--field-gradient` para a legenda, o canvas 2D usa `ENGINE_THEME.generateColormap()`, o canvas de comparacao FDTD/FEM usa o mesmo colormap, e o shader WebGL injeta os mesmos stops no fragment shader.

`ENGINE_THEME.rendering` tambem define cores de cena, grid, eixos, feed e materiais Three.js. O catalogo de materiais da API vem de `MaterialLibrary`, mantendo propriedades fisicas e cores em uma fonte unica.
