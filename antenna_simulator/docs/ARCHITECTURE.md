# IloveAntenas - Simulador de Antenas Baseado em Maxwell

## Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INTERFACE GRÁFICA                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │   Editor    │  │  Controle   │  │ Visualização│  │  Análise   │  │
│  │  Geometria  │  │  Simulação  │  │   Campos    │  │  Resultados│  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘  │
└─────────┼────────────────┼────────────────┼───────────────┼─────────┘
          │                │                │               │
┌─────────▼────────────────▼────────────────▼───────────────▼─────────┐
│                        CAMADA DE CONTROLE                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    SimulationManager                         │    │
│  │  - Orquestra geometria → mesh → solver → pós-processamento  │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
          │                │                │               │
┌─────────▼────────────────▼────────────────▼───────────────▼─────────┐
│                         MÓDULOS CORE                                │
│                                                                     │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────────┐   │
│  │   GEOMETRY    │    │     MESH      │    │      SOLVER       │   │
│  │               │    │               │    │                   │   │
│  │ • Primitivas  │───▶│ • Grid 3D     │───▶│ • FDTD Engine     │   │
│  │ • Operações   │    │ • Yee Cell    │    │ • Equações Maxwell│   │
│  │ • Grafos      │    │ • Materiais   │    │ • ABC/PML         │   │
│  │ • Import/Exp  │    │ • Refinamento │    │ • Excitação       │   │
│  └───────────────┘    └───────────────┘    └───────────────────┘   │
│                                                    │                │
│  ┌───────────────┐    ┌───────────────┐           │                │
│  │   MATERIALS   │    │    SOURCES    │           │                │
│  │               │    │               │           │                │
│  │ • ε, μ, σ     │───▶│ • Gaussiana   │───────────┘                │
│  │ • Dispersivos │    │ • Senoidal    │                            │
│  │ • Anisotrópicos│   │ • Pulso       │                            │
│  └───────────────┘    └───────────────┘                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
          │                              │
┌─────────▼──────────────────────────────▼────────────────────────────┐
│                      PÓS-PROCESSAMENTO                              │
│                                                                     │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────────┐   │
│  │  NEAR FIELD   │    │   FAR FIELD   │    │    PARAMETERS     │   │
│  │               │    │               │    │                   │   │
│  │ • Campo E     │───▶│ • Transf.     │───▶│ • Ganho           │   │
│  │ • Campo H     │    │   Near→Far    │    │ • Diretividade    │   │
│  │ • Poynting    │    │ • Diagrama    │    │ • Impedância      │   │
│  └───────────────┘    └───────────────┘    └───────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Equações de Maxwell - Formulação FDTD

### Equações de Maxwell no Domínio do Tempo

```
∂D/∂t = ∇ × H - J           (Lei de Ampère-Maxwell)
∂B/∂t = -∇ × E              (Lei de Faraday)
∇ · D = ρ                    (Lei de Gauss Elétrica)
∇ · B = 0                    (Lei de Gauss Magnética)
```

### Relações Constitutivas

```
D = ε₀εᵣE                   (Permissividade)
B = μ₀μᵣH                   (Permeabilidade)
J = σE                       (Lei de Ohm)
```

### Discretização FDTD (Yee Cell)

A célula de Yee organiza os campos E e H em posições intercaladas:

```
       Ez(i,j,k+½)
           │
           │  Hy(i+½,j,k+½)
           │ ╱
    ───────┼╱─────────── Ex(i+½,j,k)
          ╱│
         ╱ │
  Hx(i,j+½,k+½)
       │
       │
    Ey(i,j+½,k)
```

### Equações de Atualização FDTD

**Campo Elétrico:**
```
Ex^(n+1)(i+½,j,k) = Ca·Ex^n(i+½,j,k) + Cb·[
    (Hz^(n+½)(i+½,j+½,k) - Hz^(n+½)(i+½,j-½,k))/Δy -
    (Hy^(n+½)(i+½,j,k+½) - Hy^(n+½)(i+½,j,k-½))/Δz
]
```

**Campo Magnético:**
```
Hx^(n+½)(i,j+½,k+½) = Da·Hx^(n-½)(i,j+½,k+½) + Db·[
    (Ey^n(i,j+½,k+1) - Ey^n(i,j+½,k))/Δz -
    (Ez^n(i,j+1,k+½) - Ez^n(i,j,k+½))/Δy
]
```

**Coeficientes:**
```
Ca = (1 - σΔt/2ε) / (1 + σΔt/2ε)
Cb = (Δt/ε) / (1 + σΔt/2ε)
Da = 1 (para materiais não magnéticos)
Db = Δt/μ
```

## Condição de Estabilidade (CFL)

```
Δt ≤ 1 / (c · √(1/Δx² + 1/Δy² + 1/Δz²))
```

## Condições de Contorno

### PML (Perfectly Matched Layer)

Absorve ondas eletromagnéticas sem reflexão:

```
σₓ(x) = σₘₐₓ · (x/d)^m    (perfil polinomial)
```

### ABC (Absorbing Boundary Condition)

Condição de Mur de primeira ordem:

```
E^(n+1)(0) = E^n(1) + (cΔt - Δx)/(cΔt + Δx) · [E^(n+1)(1) - E^n(0)]
```

## Sistema de Grafos para Geometria

A estrutura da antena é representada como um grafo onde:
- **Nós**: Pontos de conexão (junções, terminais)
- **Arestas**: Segmentos condutores
- **Atributos**: Material, seção transversal, orientação

```python
class AntennaGraph:
    nodes: Dict[int, Node3D]      # Posições no espaço
    edges: Dict[int, Edge]        # Conexões
    materials: Dict[int, Material] # Propriedades EM
```

## Tipos de Antena Suportados

1. **Dipolo**: Configuração linear simples
2. **Monopolo**: Com plano de terra
3. **Patch/Microstrip**: Estrutura planar
4. **Yagi-Uda**: Array direcionado
5. **Loop**: Circular ou retangular
6. **Helicoidal**: Estrutura 3D espiral
7. **Horn**: Abertura cônica/piramidal
8. **Array**: Combinação de elementos

## Fluxo de Simulação

```
1. GEOMETRIA → Usuário desenha antena
       ↓
2. VALIDAÇÃO → Verificar conectividade
       ↓
3. MESHING → Criar grid FDTD
       ↓
4. MATERIAIS → Atribuir ε, μ, σ
       ↓
5. EXCITAÇÃO → Definir fonte
       ↓
6. SIMULAÇÃO → Loop temporal FDTD
       ↓
7. NEAR FIELD → Extrair campos
       ↓
8. FAR FIELD → Transformação NF→FF
       ↓
9. ANÁLISE → Ganho, impedância, etc.
```
