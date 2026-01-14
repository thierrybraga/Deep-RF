#!/usr/bin/env python3
"""
IloveAntenas - Simulador de Antenas baseado em FDTD

Este é o ponto de entrada principal da aplicação.
Pode ser executado em modo CLI ou GUI.

Uso:
    python main.py              # Inicia GUI
    python main.py --cli        # Modo linha de comando
    python main.py --example    # Executa exemplo de simulação
    python main.py --help       # Mostra ajuda

Autor: IloveAntenas Team
Licença: MIT
"""

import sys
import os
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Backend não interativo
import matplotlib.pyplot as plt

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.constants import C0, MaterialLibrary
from core.geometry import AntennaFactory, Vector3D
from core.grid import FDTDGrid, GridConfig, create_grid_for_antenna
from solver import (
    FDTDSolver, GaussianSource, SineSource, ModulatedGaussianSource,
    RickerSource, FieldProbe, NearToFarField
)
from visualization.smith_chart import (
    SmithChart, SmithChartConfig, ImpedanceResult,
    calculate_impedance_analytical, calculate_impedance_from_fdtd,
    plot_s11_vs_frequency, plot_impedance_vs_frequency, plot_vswr_vs_frequency,
    impedance_to_gamma, gamma_to_s11_db, gamma_to_vswr
)


def print_banner():
    """Exibe banner do programa"""
    banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║     █████╗ ███╗   ██╗████████╗███████╗███╗   ██╗███╗   ██╗ █████╗    ║
║    ██╔══██╗████╗  ██║╚══██╔══╝██╔════╝████╗  ██║████╗  ██║██╔══██╗   ║
║    ███████║██╔██╗ ██║   ██║   █████╗  ██╔██╗ ██║██╔██╗ ██║███████║   ║
║    ██╔══██║██║╚██╗██║   ██║   ██╔══╝  ██║╚██╗██║██║╚██╗██║██╔══██║   ║
║    ██║  ██║██║ ╚████║   ██║   ███████╗██║ ╚████║██║ ╚████║██║  ██║   ║
║    ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═══╝╚═╝  ╚═╝   ║
║                                                                      ║
║             ███████╗██╗███╗   ███╗                                   ║
║             ██╔════╝██║████╗ ████║                                   ║
║             ███████╗██║██╔████╔██║                                   ║
║             ╚════██║██║██║╚██╔╝██║                                   ║
║             ███████║██║██║ ╚═╝ ██║                                   ║
║             ╚══════╝╚═╝╚═╝     ╚═╝                                   ║
║                                                                      ║
║           Simulador de Antenas baseado em FDTD                       ║
║           Equações de Maxwell no Domínio do Tempo                    ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def run_dipole_example():
    """
    Executa exemplo de simulação de um dipolo de meia onda.
    
    Este exemplo demonstra:
    1. Criação de geometria de antena (dipolo λ/2)
    2. Configuração da grade FDTD
    3. Excitação com pulso Gaussiano
    4. Execução da simulação
    5. Visualização de resultados
    """
    print("\n" + "="*60)
    print("EXEMPLO: Simulação de Dipolo de Meia Onda")
    print("="*60)
    
    # Parâmetros
    freq_center = 300e6  # 300 MHz
    wavelength = C0 / freq_center
    
    print(f"\n📡 Parâmetros da Antena:")
    print(f"   Frequência central: {freq_center/1e6:.0f} MHz")
    print(f"   Comprimento de onda: {wavelength*100:.2f} cm")
    print(f"   Comprimento do dipolo: {wavelength/2*100:.2f} cm (λ/2)")
    
    # 1. Criar geometria do dipolo
    print("\n🔧 Criando geometria do dipolo...")
    dipole = AntennaFactory.create_dipole(
        length=wavelength / 2,  # λ/2
        radius=0.001,           # 1 mm
    )
    
    # Mostrar estrutura
    print(f"   Nós: {len(dipole.nodes)}")
    print(f"   Arestas: {len(dipole.edges)}")
    print(f"   Geometrias: {len(dipole.geometries)}")
    
    # Validar antena
    messages = dipole.validate()
    is_valid = len(messages) == 0
    print(f"   Válida: {'✓' if is_valid else '✗'}")
    if not is_valid:
        for msg in messages:
            print(f"      ⚠ {msg}")
    
    # 2. Criar grade FDTD
    print("\n📐 Configurando grade FDTD...")
    
    # Configuração otimizada para a frequência
    cells_per_lambda = 15  # Reduzido para execução mais rápida
    
    config = GridConfig(
        dx=wavelength / cells_per_lambda,
        nx=40, ny=40, nz=60,  # Grade menor para demonstração
        pml_layers=8,
        courant=0.99
    )
    
    print(f"   Células: {config.nx}×{config.ny}×{config.nz}")
    print(f"   Tamanho da célula: {config.dx*1000:.2f} mm")
    print(f"   Domínio: {config.domain_size[0]*100:.1f}×{config.domain_size[1]*100:.1f}×{config.domain_size[2]*100:.1f} cm")
    print(f"   Passo temporal: {config.dt*1e12:.3f} ps")
    print(f"   Células totais: {config.total_cells:,}")
    
    # Criar grade
    grid = FDTDGrid(config)
    
    print("\n📊 Inicializando materiais e PML...")
    grid.apply_antenna(dipole)
    grid.setup_pml()
    grid.calculate_coefficients()
    
    print(f"   Memória estimada: {grid.memory_usage():.1f} MB")
    
    # 3. Configurar solver
    print("\n⚡ Configurando solver FDTD...")
    solver = FDTDSolver(grid)
    
    # Fonte Gaussiana no centro (ponto de alimentação)
    center = (config.nx // 2, config.ny // 2, config.nz // 2)
    
    # Pulso com largura de banda adequada
    tau = 2e-9  # 2 ns
    source = GaussianSource(
        position=center,
        component='Ez',
        amplitude=1.0,
        tau=tau
    )
    solver.add_source(source)
    print(f"   Fonte: Gaussiana em {center}")
    print(f"   Largura do pulso: {tau*1e9:.1f} ns")
    print(f"   Largura de banda: {source.bandwidth/1e6:.0f} MHz")
    
    # Probes para monitoramento
    probe_positions = [
        (center[0], center[1], center[2]),           # No feed
        (center[0], center[1], center[2] + 10),      # Acima
        (center[0] + 10, center[1], center[2]),      # Lateral
    ]
    
    for i, pos in enumerate(probe_positions):
        probe = FieldProbe(position=pos, component='Ez')
        solver.add_probe(probe)
    print(f"   Probes: {len(solver.probes)} monitores de campo")
    
    # Configurar near-field box
    solver.setup_near_field_box(margin=3)
    print("   Near-field box: configurada")
    
    # 4. Executar simulação
    num_steps = 300  # Reduzido para demonstração
    
    print(f"\n🚀 Executando simulação FDTD...")
    print(f"   Passos: {num_steps}")
    print(f"   Tempo simulado: {num_steps * config.dt * 1e9:.2f} ns")
    
    # Callback de progresso
    def progress_callback(step, total, elapsed):
        pct = step / total * 100
        bar_len = 40
        filled = int(bar_len * step / total)
        bar = '█' * filled + '░' * (bar_len - filled)
        print(f"\r   [{bar}] {pct:.1f}% ({elapsed:.1f}s)", end='', flush=True)
    
    solver.set_progress_callback(progress_callback)
    
    # Executa!
    solver.run(num_steps=num_steps, record_interval=10)
    print()  # Nova linha após barra de progresso
    
    # 5. Resultados
    print("\n📈 Resultados da simulação:")
    print(f"   Tempo de computação: {solver.stats['computation_time']:.2f} s")
    print(f"   |E|_max: {solver.stats['max_E']:.3e} V/m")
    print(f"   |H|_max: {solver.stats['max_H']:.3e} A/m")
    
    # Dados do probe principal
    times, values = solver.probes[0].get_time_series()
    if len(values) > 0:
        print(f"   Valor máximo no feed: {np.max(np.abs(values)):.3e} V/m")
        print(f"   Amostras coletadas: {len(times)}")
    
    # Energia
    if solver.stats['total_energy']:
        _, energies = zip(*solver.stats['total_energy'])
        print(f"   Energia máxima: {max(energies):.3e} J")
    
    print("\n✅ Simulação concluída com sucesso!")
    
    # Tentar visualização se matplotlib disponível
    try:
        print("\n📊 Gerando visualizações...")
        from visualization.plots import FieldVisualizer, RadiationPatternPlot
        
        # Plot da série temporal
        viz = FieldVisualizer()
        if len(times) > 0:
            fig, ax = viz.plot_time_series(
                times, values,
                title="Campo Ez no ponto de alimentação"
            )
            viz.save("/home/claude/antenna_simulator/output_time_series.png")
            print("   ✓ Série temporal salva: output_time_series.png")
        
        # Plot do campo
        field_slice = grid.get_slice('y', config.ny // 2, 'Ez')
        fig, ax = viz.plot_field_slice(
            field_slice,
            config.dx, config.dz,
            title="Campo Ez - Plano XZ"
        )
        viz.save("/home/claude/antenna_simulator/output_field.png")
        print("   ✓ Campo salvo: output_field.png")
        
        # Diagrama de radiação (simplificado)
        if solver.nf_box and len(solver.nf_box.E_data['z_min']) > 0:
            nf2ff = NearToFarField(solver.nf_box, config, freq_center)
            angles, pattern = nf2ff.calculate_radiation_pattern(plane='E')
            
            rad_plot = RadiationPatternPlot()
            rad_plot.plot_polar(angles, pattern, title="Diagrama de Radiação - Plano E")
            rad_plot.save("/home/claude/antenna_simulator/output_radiation.png")
            print("   ✓ Diagrama de radiação salvo: output_radiation.png")
        
        print("\n📁 Arquivos salvos em: /home/claude/antenna_simulator/")
        
    except ImportError as e:
        print(f"\n⚠ Visualização não disponível: {e}")
    except Exception as e:
        print(f"\n⚠ Erro na visualização: {e}")
    
    return solver, grid, dipole


def run_yagi_example():
    """Exemplo de simulação de antena Yagi-Uda"""
    print("\n" + "="*60)
    print("EXEMPLO: Simulação de Antena Yagi-Uda")
    print("="*60)
    
    freq = 144e6  # 144 MHz (VHF)
    wavelength = C0 / freq
    
    print(f"\n📡 Parâmetros:")
    print(f"   Frequência: {freq/1e6:.0f} MHz")
    print(f"   Comprimento de onda: {wavelength:.2f} m")
    
    # Criar Yagi com 3 elementos
    print("\n🔧 Criando antena Yagi-Uda...")
    yagi = AntennaFactory.create_yagi(
        frequency=freq,
        num_directors=3,
        boom_radius=0.01
    )
    
    print(f"   Elementos: 1 refletor + 1 ativo + 3 diretores")
    print(f"   Nós: {len(yagi.nodes)}")
    print(f"   Geometrias: {len(yagi.geometries)}")
    
    # Validar
    messages = yagi.validate()
    is_valid = len(messages) == 0
    print(f"   Válida: {'✓' if is_valid else '✗'}")
    
    bb = yagi.get_bounding_box()
    print(f"   Dimensões: {bb.size.x:.2f}×{bb.size.y:.2f}×{bb.size.z:.2f} m")
    
    return yagi


def run_patch_example():
    """Exemplo de antena patch microstrip"""
    print("\n" + "="*60)
    print("EXEMPLO: Antena Patch Microstrip")
    print("="*60)
    
    freq = 2.4e9  # 2.4 GHz WiFi
    wavelength = C0 / freq
    
    print(f"\n📡 Parâmetros:")
    print(f"   Frequência: {freq/1e9:.1f} GHz")
    print(f"   Comprimento de onda: {wavelength*1000:.2f} mm")
    
    # Criar patch
    print("\n🔧 Criando antena patch...")
    patch = AntennaFactory.create_patch(
        frequency=freq,
        substrate_er=4.4,  # FR4
        substrate_h=1.6e-3  # 1.6 mm
    )
    
    print(f"   Substrato: FR4 (εᵣ=4.4)")
    print(f"   Espessura: 1.6 mm")
    print(f"   Nós: {len(patch.nodes)}")
    print(f"   Geometrias: {len(patch.geometries)}")
    
    bb = patch.get_bounding_box()
    print(f"   Dimensões do patch: {bb.size.x*1000:.2f}×{bb.size.y*1000:.2f} mm")
    
    return patch


def run_helix_example():
    """Exemplo de antena helicoidal"""
    print("\n" + "="*60)
    print("EXEMPLO: Antena Helicoidal")
    print("="*60)
    
    freq = 435e6  # UHF
    wavelength = C0 / freq
    
    print(f"\n📡 Parâmetros:")
    print(f"   Frequência: {freq/1e6:.0f} MHz")
    print(f"   Comprimento de onda: {wavelength:.2f} m")
    
    # Criar hélice
    print("\n🔧 Criando antena helicoidal...")
    helix = AntennaFactory.create_helix(
        frequency=freq,
        turns=5,
        mode='axial'
    )
    
    print(f"   Modo: Axial (polarização circular)")
    print(f"   Voltas: 5")
    print(f"   Nós: {len(helix.nodes)}")
    print(f"   Geometrias: {len(helix.geometries)}")
    
    return helix


def run_smith_chart_example():
    """
    Exemplo de geração de Carta de Smith para análise de impedância.
    
    Demonstra:
    1. Cálculo de impedância analítica
    2. Plotagem na Carta de Smith
    3. Análise de S11, VSWR e largura de banda
    """
    print("\n" + "="*60)
    print("EXEMPLO: Carta de Smith - Análise de Impedância")
    print("="*60)
    
    # Parâmetros
    freq_center = 300e6  # 300 MHz
    wavelength = C0 / freq_center
    z0 = 50.0  # Impedância de referência
    
    print(f"\n📡 Parâmetros da Análise:")
    print(f"   Frequência central: {freq_center/1e6:.0f} MHz")
    print(f"   Comprimento de onda: {wavelength*100:.2f} cm")
    print(f"   Impedância de referência: {z0:.0f} Ω")
    
    # Frequências de análise
    freq_min = 200e6
    freq_max = 400e6
    n_points = 201
    frequencies = np.linspace(freq_min, freq_max, n_points)
    
    print(f"\n📊 Faixa de frequências:")
    print(f"   {freq_min/1e6:.0f} - {freq_max/1e6:.0f} MHz ({n_points} pontos)")
    
    # 1. Dipolo de meia onda
    print("\n🔧 Calculando impedância do dipolo λ/2...")
    dipole_length = wavelength / 2
    
    result_dipole = calculate_impedance_analytical(
        'dipole',
        frequencies,
        length=dipole_length,
        z0=z0
    )
    
    # Encontra ressonância
    res = result_dipole.find_resonance()
    print(f"\n   📍 Ressonância:")
    print(f"      Frequência: {res['frequency']/1e6:.1f} MHz")
    print(f"      Impedância: {res['resistance']:.1f} + j{res['reactance']:.1f} Ω")
    print(f"      S11: {res['s11_db']:.1f} dB")
    print(f"      VSWR: {res['vswr']:.2f}:1")
    
    # Melhor casamento
    best = result_dipole.find_best_match()
    print(f"\n   📍 Melhor casamento:")
    print(f"      Frequência: {best['frequency']/1e6:.1f} MHz")
    print(f"      Impedância: {best['resistance']:.1f} + j{best['reactance']:.1f} Ω")
    print(f"      S11: {best['s11_db']:.1f} dB")
    print(f"      VSWR: {best['vswr']:.2f}:1")
    
    # Largura de banda
    bw = result_dipole.get_bandwidth(-10.0)
    print(f"\n   📍 Largura de banda (-10 dB):")
    if bw[2] > 0:
        print(f"      Faixa: {bw[0]/1e6:.1f} - {bw[1]/1e6:.1f} MHz")
        print(f"      BW: {bw[2]/1e6:.1f} MHz ({100*bw[2]/freq_center:.1f}%)")
    else:
        print(f"      Não encontrada dentro da faixa")
    
    # 2. Monopolo (comparação)
    print("\n🔧 Calculando impedância do monopolo λ/4...")
    monopole_length = wavelength / 4
    
    result_monopole = calculate_impedance_analytical(
        'monopole',
        frequencies,
        length=monopole_length,
        z0=z0
    )
    
    res_mono = result_monopole.find_resonance()
    print(f"   Ressonância: {res_mono['frequency']/1e6:.1f} MHz")
    print(f"   Impedância: {res_mono['resistance']:.1f} + j{res_mono['reactance']:.1f} Ω")
    
    # 3. Gerar visualizações
    print("\n📊 Gerando visualizações...")
    
    # Carta de Smith
    chart = SmithChart(SmithChartConfig(z0=z0))
    
    # Plota dipolo
    chart.plot_trace(
        result_dipole.impedance,
        result_dipole.frequencies,
        label='Dipolo λ/2',
        color='blue',
        marker_freq=[250e6, 300e6, 350e6]
    )
    
    # Plota monopolo
    chart.plot_trace(
        result_monopole.impedance,
        result_monopole.frequencies,
        label='Monopolo λ/4',
        color='red',
        marker_freq=[300e6]
    )
    
    # Círculo VSWR 2:1
    chart.plot_vswr_circle(2.0, color='green', label='VSWR 2:1')
    
    # Marca ponto de referência (50 Ω)
    chart.plot_impedance(
        complex(50, 0),
        label='Z₀ = 50 Ω',
        marker='*',
        color='gold',
        size=200
    )
    
    chart.set_title('Carta de Smith - Dipolo vs Monopolo')
    chart.add_legend(loc='lower left')
    chart.save('/home/claude/antenna_simulator/output_smith_chart.png')
    print("   ✓ Carta de Smith salva: output_smith_chart.png")
    
    # S11 vs Frequência
    fig, ax = plot_s11_vs_frequency(
        result_dipole,
        title="S11 - Dipolo de Meia Onda"
    )
    fig.savefig('/home/claude/antenna_simulator/output_s11.png', dpi=150)
    plt.close(fig)
    print("   ✓ S11 vs Frequência salvo: output_s11.png")
    
    # Impedância vs Frequência
    fig, axes = plot_impedance_vs_frequency(
        result_dipole,
        title="Impedância - Dipolo λ/2"
    )
    fig.savefig('/home/claude/antenna_simulator/output_impedance.png', dpi=150)
    plt.close(fig)
    print("   ✓ Impedância vs Frequência salvo: output_impedance.png")
    
    # VSWR vs Frequência
    fig, ax = plot_vswr_vs_frequency(
        result_dipole,
        title="VSWR - Dipolo de Meia Onda"
    )
    fig.savefig('/home/claude/antenna_simulator/output_vswr.png', dpi=150)
    plt.close(fig)
    print("   ✓ VSWR vs Frequência salvo: output_vswr.png")
    
    # Resumo final
    print("\n" + "="*60)
    print("RESUMO DA ANÁLISE")
    print("="*60)
    
    print(f"""
┌────────────────────────────────────────────────────────────┐
│  DIPOLO DE MEIA ONDA (λ/2)                                 │
├────────────────────────────────────────────────────────────┤
│  Comprimento: {dipole_length*100:.2f} cm                              │
│  Frequência central: {freq_center/1e6:.0f} MHz                        │
│                                                            │
│  Na ressonância ({res['frequency']/1e6:.0f} MHz):                         │
│    R = {res['resistance']:.1f} Ω                                        │
│    X = {res['reactance']:+.1f} Ω                                        │
│    VSWR = {res['vswr']:.2f}:1                                       │
│    S11 = {res['s11_db']:.1f} dB                                       │
│                                                            │
│  Largura de banda (-10 dB): {bw[2]/1e6:.1f} MHz                    │
│  BW relativa: {100*bw[2]/freq_center:.1f}%                                     │
└────────────────────────────────────────────────────────────┘

Arquivos gerados:
  • output_smith_chart.png  - Carta de Smith
  • output_s11.png          - S11 vs Frequência
  • output_impedance.png    - R e X vs Frequência
  • output_vswr.png         - VSWR vs Frequência
""")
    
    print("\n✅ Análise de Carta de Smith concluída!")
    
    return result_dipole


def list_materials():
    """Lista materiais disponíveis"""
    print("\n" + "="*60)
    print("MATERIAIS DISPONÍVEIS")
    print("="*60)
    
    print("\n📦 Condutores:")
    conductors = ['COPPER', 'ALUMINUM', 'GOLD', 'SILVER', 'PEC']
    for name in conductors:
        mat = getattr(MaterialLibrary, name)
        print(f"   {name}: σ = {mat.sigma:.2e} S/m")
    
    print("\n📦 Dielétricos:")
    dielectrics = ['FR4', 'ROGERS_4003C', 'TEFLON', 'SILICON', 'AIR']
    for name in dielectrics:
        mat = getattr(MaterialLibrary, name)
        print(f"   {name}: εᵣ = {mat.epsilon_r:.2f}, tan(δ) = {mat.tan_delta:.4f}")
    
    print("\n📦 Outros:")
    others = ['WATER', 'DRY_SOIL', 'WET_SOIL']
    for name in others:
        mat = getattr(MaterialLibrary, name)
        print(f"   {name}: εᵣ = {mat.epsilon_r:.1f}, σ = {mat.sigma:.4f} S/m")


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description='IloveAntenas - Simulador de Antenas baseado em FDTD',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python main.py --example dipole    Simula dipolo de meia onda
  python main.py --example yagi      Cria antena Yagi-Uda
  python main.py --example patch     Cria antena patch microstrip
  python main.py --example helix     Cria antena helicoidal
  python main.py --example smith     Gera Carta de Smith
  python main.py --materials         Lista materiais disponíveis
        """
    )
    
    parser.add_argument(
        '--gui', action='store_true',
        help='Inicia interface gráfica (padrão)'
    )
    parser.add_argument(
        '--cli', action='store_true',
        help='Modo linha de comando interativo'
    )
    parser.add_argument(
        '--example', type=str,
        choices=['dipole', 'yagi', 'patch', 'helix', 'smith', 'all'],
        help='Executa exemplo de simulação'
    )
    parser.add_argument(
        '--materials', action='store_true',
        help='Lista materiais disponíveis'
    )
    parser.add_argument(
        '--version', action='store_true',
        help='Mostra versão do programa'
    )
    
    args = parser.parse_args()
    
    # Banner
    print_banner()
    
    # Versão
    if args.version:
        print("IloveAntenas v1.0.0")
        print("Método: FDTD (Finite-Difference Time-Domain)")
        print("Baseado nas Equações de Maxwell")
        return 0
    
    # Materiais
    if args.materials:
        list_materials()
        return 0
    
    # Exemplos
    if args.example:
        if args.example == 'dipole':
            run_dipole_example()
        elif args.example == 'yagi':
            run_yagi_example()
        elif args.example == 'patch':
            run_patch_example()
        elif args.example == 'helix':
            run_helix_example()
        elif args.example == 'smith':
            run_smith_chart_example()
        elif args.example == 'all':
            run_dipole_example()
            run_yagi_example()
            run_patch_example()
            run_helix_example()
            run_smith_chart_example()
        return 0
    
    # CLI interativo
    if args.cli:
        print("\n📟 Modo CLI interativo")
        print("Digite 'help' para ver comandos disponíveis")
        print("Digite 'exit' para sair\n")
        
        while True:
            try:
                cmd = input("IloveAntenas> ").strip().lower()
                
                if cmd in ['exit', 'quit', 'q']:
                    print("Até logo!")
                    break
                elif cmd == 'help':
                    print("Comandos disponíveis:")
                    print("  dipole   - Simula dipolo")
                    print("  yagi     - Cria Yagi-Uda")
                    print("  patch    - Cria patch")
                    print("  helix    - Cria helicoidal")
                    print("  smith    - Gera Carta de Smith")
                    print("  materials- Lista materiais")
                    print("  exit     - Sair")
                elif cmd == 'dipole':
                    run_dipole_example()
                elif cmd == 'yagi':
                    run_yagi_example()
                elif cmd == 'patch':
                    run_patch_example()
                elif cmd == 'helix':
                    run_helix_example()
                elif cmd == 'smith':
                    run_smith_chart_example()
                elif cmd == 'materials':
                    list_materials()
                else:
                    print(f"Comando não reconhecido: {cmd}")
                    
            except KeyboardInterrupt:
                print("\n\nInterrompido pelo usuário.")
                break
            except EOFError:
                print()
                break
        
        return 0
    
    # GUI (padrão)
    print("\n🖥️  Iniciando interface gráfica...")
    try:
        from gui.main_window import main as gui_main
        return gui_main()
    except ImportError as e:
        print(f"\n⚠ Erro ao importar GUI: {e}")
        print("\nExecute com --example dipole para testar o simulador:")
        print("  python main.py --example dipole")
        return 1
    except Exception as e:
        print(f"\n❌ Erro ao iniciar GUI: {e}")
        print("\nExecute com --cli para modo interativo:")
        print("  python main.py --cli")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
