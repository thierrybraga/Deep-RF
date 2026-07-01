# IloveAntenas Web

Aplicacao web FastAPI para modelagem, simulacao e analise de antenas. O frontend usa HTML, CSS centralizado, JavaScript modular, Three.js e Chart.js.

## Execucao

Na raiz do projeto:

```bash
python -m uvicorn iloveantennas.web.app:app --host 127.0.0.1 --port 5000 --reload
```

Acesse:

```text
http://127.0.0.1:5000
```

## Estrutura

```text
src/iloveantennas/web/
├── app.py                  # FastAPI, endpoints e templates
├── config.py               # AntennaConfig e SimulationConfig
├── schemas.py              # Schemas HTTP e conversores para dataclasses internas
├── antennas.py             # Ponte entre API e AntennaFactory
├── analysis.py             # Smith, S11, VSWR, radiacao e parametros
├── simulation.py           # Orquestracao FDTD/FEM
├── optimizer.py            # Otimizador de comprimento
├── optimization.py         # Tarefa async de otimizacao
├── matching.py             # Redes de casamento
├── resources.py            # Tipos de antena e materiais derivados do core
├── state.py                # Estado em memoria
├── storage.py              # Biblioteca JSON de antenas
├── templates/
│   ├── index.html          # Tela principal
│   └── analise.html        # Tela de analise completa
└── static/
    ├── css/style.css       # Design system central
    └── js/                 # App, engine theme, renderer, charts e field renderer
```

## Frontend

- `static/css/style.css` concentra paleta, tipografia, espacamento, componentes e responsividade.
- `static/js/engine.theme.js` concentra gradiente de campo, contornos, temporizacao, materiais Three.js e cores de cena.
- `templates/index.html` e `templates/analise.html` devem permanecer sem `style=""`.
- Cores de graficos em canvas devem vir de `ChartManager.colors`, que espelha os tokens do CSS.
- `renderer.*.js` cuida do Three.js; `charts.*.js` cuida dos graficos; `app.*.js` cuida de estado, eventos, simulacao e biblioteca.

## Endpoints Principais

| Endpoint | Metodo | Descricao |
| --- | --- | --- |
| `/` | GET | Renderiza a tela principal |
| `/analise` | GET | Renderiza a tela de analise |
| `/api/antenna/types` | GET | Lista tipos de antena |
| `/api/materials` | GET | Lista materiais |
| `/api/engine/status` | GET | Diagnostica GPU Windows, WSL e backends da engine |
| `/api/antennas` | GET/POST | Biblioteca de antenas |
| `/api/antennas/{id}` | PUT/DELETE | Atualiza ou remove antena da biblioteca |
| `/api/antenna/create` | POST | Cria geometria serializada para o renderer |
| `/api/antenna/analysis` | POST | Retorna geometria, Smith, radiacao e parametros |
| `/api/smith-chart` | POST | Calcula dados de Carta de Smith |
| `/api/radiation-pattern` | POST | Calcula padrao de radiacao |
| `/api/matching` | POST | Calcula rede de casamento |
| `/api/propagation/path-loss` | POST | Calcula FSPL, Okumura-Hata, COST-231 e orcamento de enlace |
| `/api/propagation/ray-trace` | POST | Calcula caminhos geometricos 2D direto/refletidos |
| `/api/simulation/start` | POST | Inicia simulacao FDTD ou FEM |
| `/api/simulation/compare` | POST | Compara FDTD e FEM |
| `/api/simulation/{id}/status` | GET | Consulta progresso |
| `/api/simulation/{id}/frames` | GET | Retorna frames de campo |
| `/api/optimize` | POST | Inicia otimizacao de comprimento |
| `/api/optimize/{id}/status` | GET | Consulta otimizacao |

`POST /api/simulation/start` aceita `solver_backend` com `"auto"`, `"cuda"`, `"numba"` ou `"numpy"`. Aliases como `"gpu"`, `"cuda_gpu"`, `"cpu"`, `"numba_cpu"` e `"numpy_cpu"` sao normalizados em `simulator.engine`. Use `"cuda"` para solicitar os kernels FDTD em Numba CUDA; se o runtime CUDA nao estiver disponivel, a resposta de status inclui `engine.backend_warning` e o solver volta para CPU.

## Design

Veja `DOCS_DESIGN_SYSTEM.md` na raiz do projeto para paleta, tokens, componentes e regras de manutencao visual.
