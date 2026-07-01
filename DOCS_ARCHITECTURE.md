# Consolidacao de Arquitetura e Engenharia

Este documento descreve a arquitetura padronizada da aplicacao IloveAntenas depois da consolidacao de biblioteca, calculos, simulacoes e renderizacao.

## Camadas de Responsabilidade

- `src/iloveantennas/simulator/core/`
  - Constantes eletromagneticas, materiais, geometrias e malha FDTD.
  - `MaterialLibrary` e a fonte unica para propriedades fisicas de materiais.
- `src/iloveantennas/simulator/engine/`
  - Politicas numericas compartilhadas: malha, captura de frames e nomes de backend FDTD.
  - `normalize_fdtd_backend()` padroniza aliases como `gpu`, `cuda_gpu`, `numba-cpu` e `numpy-cpu`.
- `src/iloveantennas/simulator/solver/`
  - Loop FDTD e backends `cuda`, `numba-cpu` e `numpy-cpu`.
  - O solver nao decide contratos HTTP; ele recebe configs normalizadas.
- `src/iloveantennas/simulator/propagation/`
  - FSPL, Okumura-Hata, COST-231 Hata, orcamento de enlace e tracado de raios 2D.
- `src/iloveantennas/simulator/runtime/`
  - Diagnostico de GPU Windows, WSL, Numba CUDA e disponibilidade real de aceleracao.
- `src/iloveantennas/web/schemas.py`
  - Contratos Pydantic da API e conversores para dataclasses internas.
  - Mantem `app.py` focado em rotas e orquestracao.
- `src/iloveantennas/web/resources.py`
  - Metadados expostos a UI.
  - Materiais sao gerados a partir de `MaterialLibrary`, evitando duplicacao de cores e propriedades.
- `src/iloveantennas/web/simulation.py`
  - Orquestracao FDTD/FEM, thread de simulacao, frames, espectro e metadados de engine.
- `src/iloveantennas/web/static/js/engine.theme.js`
  - Fonte unica para gradiente de campo, animacao, cores de cena, materiais Three.js, feed e eixos.

## Contratos Padronizados

- Configuracoes de antena entram por schemas HTTP e viram `AntennaConfig`.
- Configuracoes de simulacao entram por schemas HTTP e viram `SimulationConfig`.
- Backends FDTD validos de contrato: `auto`, `cuda`, `numba`, `numpy`.
- O backend efetivo volta nos resultados em `engine.solver_backend`.
- Falhas ou indisponibilidade de CUDA voltam em `engine.backend_warning`.
- Materiais fisicos vivem no core; a API so formata para UI.
- Frames de campo usam `field`, `fieldE`, `fieldH`, `maxVal`, `step` e `time_ns`.
- Gradiente de campo e cores de comparacao FEM/FDTD usam `ENGINE_THEME.generateColormap()`.

## Melhorias Aplicadas

- Extraidos schemas e conversores de `web/app.py` para `web/schemas.py`.
- Material API consolidado a partir de `MaterialLibrary`.
- `Material` recebeu `tan_delta`, `color_hex` e `api_sigma`.
- Normalizacao de backend FDTD movida para `simulator/engine`.
- Solver FDTD e schemas HTTP usam o mesmo normalizador de backend.
- Renderer Three.js usa `ENGINE_THEME.rendering` para cena, grid, eixos, feed e materiais.
- Canvas de comparacao FDTD/FEM usa o mesmo gradiente de campo da engine visual.
- Testes adicionados para catalogo de materiais, schemas e conversores de propagacao.

## Melhorias Recomendadas

- Dividir `web/app.py` em routers: `antenna`, `simulation`, `propagation`, `matching`, `optimization`, `library`.
- Trocar estado global em memoria por um `SimulationRepository` com limpeza de tarefas antigas.
- Criar um `SimulationTaskManager` para ciclo de vida de threads, cancelamento e timeout.
- Separar FEM experimental de fallback sintetico com flag explicita de capacidade.
- Adicionar validacoes Pydantic de faixa fisica para frequencia, distancia, alturas, PML e passos.
- Criar testes de contrato para todos endpoints com `TestClient`.
- Executar suite CUDA em ambiente WSL com GPU real para validar kernels alem do fallback.
- Adicionar snapshots visuais automatizados para canvas desktop/mobile.
- Consolidar aliases legados de CSS gradualmente, mantendo compatibilidade ate a UI estabilizar.
