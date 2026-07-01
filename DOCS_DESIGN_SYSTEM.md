# Design System IloveAntenas

## Objetivo

Todas as telas web devem compartilhar a mesma linguagem visual: interface tecnica, densa, legivel e previsivel para engenharia de antenas. A primeira fonte de verdade e `src/iloveantennas/web/static/css/style.css`.

## Tokens

- Fundo: `--color-bg`, `--color-bg-elevated`, `--color-surface`, `--color-canvas`.
- Texto: `--color-text`, `--color-text-secondary`, `--color-text-muted`.
- Acao primaria: `--color-primary`, `--color-primary-hover`, `--color-primary-active`.
- Estados: `--color-info`, `--color-success`, `--color-warning`, `--color-danger`.
- Bordas e foco: `--color-border`, `--color-border-strong`, `--focus-ring`.
- Tipografia: `Inter` para UI e `JetBrains Mono` para valores numericos.
- Raios: usar `--radius-sm` e `--radius-md`; cards e paineis ficam em ate 8px.
- Campo eletromagnetico: `--field-gradient-*` e `--field-gradient` espelham os stops usados por `ENGINE_THEME`.

## Componentes Padrao

- Layout: `.header`, `.main-content`, `.sidebar`, `.main-panel`, `.results-panel`.
- Superficies: `.panel`, `.result-card`, `.info-item`, `.chart-container`.
- Formularios: `.form-group`, `.input-with-unit`, `.input-row`, `.form-grid`, `.checkbox-group`.
- Acoes: `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-outline`, `.btn-icon`, `.btn-xs`.
- Feedback: `.toast`, `.progress-bar`, `.progress-fill`, `.status-card`, `.value-flash-success`.
- Modais: `.modal-overlay`, `.modal`, `.modal-header`, `.modal-body`, `.modal-footer`.
- Tabelas: `.table-container`, `.data-table`, `.table-actions`, `.table-empty`, `.table-loading`.

## Regras de Manutencao

- Nao usar `style=""` em templates.
- Nao inserir cores de componentes diretamente no JavaScript; usar classes CSS ou `ChartManager.colors` para canvas/graficos.
- Nao duplicar mapa de cor, velocidade de playback, contornos ou pulso de campo em renderizadores. Usar `src/iloveantennas/web/static/js/engine.theme.js`.
- Nao criar paletas paralelas por tela. `index.html` e `analise.html` devem apontar para a mesma folha e para a mesma importacao de fontes.
- Manter textos e botoes compactos; a aplicacao e uma ferramenta operacional, nao uma landing page.
- Ao criar uma nova tela, reutilizar os componentes existentes antes de criar novas classes.
- Se uma regra nova for recorrente em duas telas, ela pertence ao design system central.
