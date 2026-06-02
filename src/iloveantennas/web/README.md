# IloveAntenas Web - Simulador de Antenas FDTD

Aplicação web completa para simulação e análise de antenas usando o método FDTD (Finite-Difference Time-Domain).

## 🚀 Características

### Renderização 3D (Three.js)
- Visualização 3D interativa de antenas
- Materiais PBR (Physically Based Rendering) para metais
- Iluminação realista com sombras
- Controles de câmera (rotação, zoom, pan)
- Grade e eixos de referência

### Tipos de Antena Suportados
- **Dipolo** - Antena básica λ/2
- **Monopolo** - Sobre plano de terra (λ/4)
- **Yagi-Uda** - Array direcional com múltiplos elementos
- **Patch Microstrip** - Antena planar para aplicações compactas
- **Helicoidal** - Polarização circular

### Análise de Impedância
- **Carta de Smith** - Visualização de impedância complexa
- **S11 (Return Loss)** - Coeficiente de reflexão em dB
- **VSWR** - Razão de onda estacionária
- **Largura de Banda** - Cálculo automático (-10 dB)

### Simulação FDTD
- Simulação eletromagnética completa
- Animação do campo elétrico
- Configuração de resolução e passos temporais
- Fontes Gaussiana e Senoidal

### Interface
- Design moderno e responsivo
- Tema claro/escuro
- Painéis redimensionáveis
- Gráficos interativos (Chart.js)

## 📦 Instalação

### Requisitos
- Python 3.8+
- pip

### Passos

1. **Extraia os dois arquivos ZIP:**
   ```bash
   unzip antenna_simulator.zip
   unzip antenna_web.zip
   ```

2. **Instale as dependências:**
   ```bash
   pip install flask flask-cors numpy matplotlib
   ```

3. **Execute a aplicação:**
   ```bash
   cd antenna_web
   python app.py
   ```

4. **Acesse no navegador:**
   ```
   http://localhost:5000
   ```

## 🎮 Como Usar

### Design de Antena
1. Selecione o tipo de antena no painel esquerdo
2. Ajuste a frequência (MHz)
3. Configure parâmetros específicos (comprimento, raio, etc.)
4. A antena é renderizada automaticamente em 3D

### Análise
- **Carta de Smith**: Mostra impedância vs frequência
- **Diagrama de Radiação**: Padrão polar E e H
- **S11**: Return loss em dB
- **VSWR**: Razão de onda estacionária

### Simulação FDTD
1. Configure a resolução (células/λ)
2. Defina o número de passos temporais
3. Selecione o tipo de fonte
4. Clique em "Iniciar Simulação"
5. Observe a animação do campo eletromagnético

### Controles 3D
- **Rotacionar**: Clique + arrastar
- **Zoom**: Scroll do mouse
- **Pan**: Clique direito + arrastar
- **Reset**: Botão de sincronização

## 📁 Estrutura do Projeto

```
antenna_web/
├── app.py                 # Servidor Flask + API
├── templates/
│   └── index.html         # Interface principal
└── static/
    ├── css/
    │   └── style.css      # Estilos (CSS Variables, Dark Mode)
    └── js/
        ├── renderer.js    # Engine 3D (Three.js)
        ├── charts.js      # Gráficos (Chart.js)
        └── app.js         # Lógica da aplicação

antenna_simulator/         # Backend de simulação
├── core/                  # Constantes, geometria, grid
├── solver/                # FDTD solver
└── visualization/         # Smith Chart, plots
```

## 🔧 API Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/antenna/types` | GET | Lista tipos de antena |
| `/api/antenna/create` | POST | Cria geometria da antena |
| `/api/smith-chart` | POST | Calcula dados da Carta de Smith |
| `/api/radiation-pattern` | POST | Calcula padrão de radiação |
| `/api/simulation/start` | POST | Inicia simulação FDTD |
| `/api/simulation/{id}/status` | GET | Status da simulação |
| `/api/simulation/{id}/frames` | GET | Frames da animação |

## 🎨 Tecnologias

- **Backend**: Flask, NumPy, Matplotlib
- **Frontend**: HTML5, CSS3, JavaScript ES6+
- **3D**: Three.js (WebGL)
- **Gráficos**: Chart.js
- **Design**: CSS Variables, Flexbox, Grid

## 📐 Fórmulas Principais

- **Comprimento de onda**: λ = c/f
- **Impedância complexa**: Z = R + jX
- **Coef. de reflexão**: Γ = (Z-Z₀)/(Z+Z₀)
- **VSWR**: VSWR = (1+|Γ|)/(1-|Γ|)
- **S11**: S11[dB] = 20·log₁₀(|Γ|)

## 📝 Licença

MIT License

## 👤 Autor

IloveAntenas Team
