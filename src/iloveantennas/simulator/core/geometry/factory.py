"""
Módulo de Fábrica de Antenas
Fornece métodos estáticos para criar geometrias de antenas comuns.
"""

import numpy as np

from ..constants import C0, MaterialLibrary
from .primitives import Helix, Horn, ParabolicDish, Rectangle, Vector3D, Wire
from .topology import AntennaGraph


class AntennaFactory:
    """Fábrica para criar tipos comuns de antenas"""

    @staticmethod
    def create_dipole(
        length: float, radius: float = 0.001, center: Vector3D = None, orientation: str = "z"
    ) -> AntennaGraph:
        """
        Cria antena dipolo simples.

        Args:
            length: Comprimento total do dipolo [m]
            radius: Raio do fio [m]
            center: Centro do dipolo
            orientation: Orientação ('x', 'y', ou 'z')
        """
        center = center or Vector3D(0, 0, 0)
        half_len = length / 2

        # Define direção baseada na orientação
        if orientation == "x":
            delta = Vector3D(half_len, 0, 0)
        elif orientation == "y":
            delta = Vector3D(0, half_len, 0)
        else:  # z
            delta = Vector3D(0, 0, half_len)

        antenna = AntennaGraph(name=f"Dipole_{length*1000:.0f}mm")

        # Braço 1 (do centro para +)
        n_center, n_top, e1 = antenna.add_wire(
            center, center + delta, radius, start_type="feed", end_type="terminal"
        )

        # Braço 2 (do centro para -)
        _, n_bottom, e2 = antenna.add_wire(
            center, center - delta, radius, start_type="feed", end_type="terminal"
        )

        antenna.set_feed_point(n_center)

        return antenna

    @staticmethod
    def create_biquad(
        side_length: float = None,
        frequency: float = 2.4e9,
        wire_radius: float = 0.001,
        reflector_distance: float = None,
    ) -> AntennaGraph:
        """
        Cria antena Biquad (formato de 8 deitado).

        Args:
            side_length: Comprimento do lado do quadrado [m]
            frequency: Frequência para cálculo automático [Hz]
            wire_radius: Raio do fio [m]
            reflector_distance: Distância do refletor (None = sem refletor)
        """
        wavelength = C0 / frequency
        if side_length is None:
            side_length = wavelength / 4.0

        antenna = AntennaGraph(name=f"Biquad_{frequency/1e6:.0f}MHz")

        # Geometria Diamond (Losango)
        # Altura e largura do losango
        # Diagonal = side * sqrt(2)
        d = side_length * np.sqrt(2)
        half_d = d / 2

        center = Vector3D(0, 0, 0)

        # Quad Superior (Z+)
        p_top = Vector3D(0, d, 0)
        p_right = Vector3D(0, half_d, half_d)
        p_left = Vector3D(0, half_d, -half_d)

        # Quad Inferior (Z-)
        p_bottom = Vector3D(0, -d, 0)
        p_right_low = Vector3D(0, -half_d, half_d)
        p_left_low = Vector3D(0, -half_d, -half_d)

        # Centro (Feed point)
        # Vamos criar um pequeno gap ou alimentar no nó central

        # Construção dos fios
        # Quad Superior
        antenna.add_wire(center, p_right, wire_radius)
        antenna.add_wire(p_right, p_top, wire_radius)
        antenna.add_wire(p_top, p_left, wire_radius)
        _, n_center_top, _ = antenna.add_wire(p_left, center, wire_radius, end_type="feed")

        # Quad Inferior
        antenna.add_wire(center, p_right_low, wire_radius)
        antenna.add_wire(p_right_low, p_bottom, wire_radius)
        antenna.add_wire(p_bottom, p_left_low, wire_radius)
        _, n_center_bottom, _ = antenna.add_wire(p_left_low, center, wire_radius, end_type="feed")

        # Define feed point no centro (usando um dos nós centrais)
        antenna.set_feed_point(n_center_top)

        # Refletor (Placa)
        if reflector_distance is None:
            reflector_distance = wavelength / 8.0

        ref_w = 2 * d
        ref_h = d

        reflector = Rectangle(
            center=Vector3D(-reflector_distance, 0, 0),
            width=ref_h * 1.5,  # Altura total
            height=ref_w,  # Largura total
            thickness=wire_radius * 2,
            normal=Vector3D(1, 0, 0),
        )
        reflector.material = MaterialLibrary.PEC
        reflector.name = "Reflector"
        antenna.geometries.append(reflector)

        return antenna

    @staticmethod
    def create_discone(
        frequency: float = None,
        disc_radius: float = None,
        cone_radius: float = None,
        cone_height: float = None,
        wire_radius: float = 0.001,
    ) -> AntennaGraph:
        """
        Cria antena Discone (Wireframe approximation).

        Args:
            frequency: Frequência de design (para defaults)
            disc_radius: Raio do disco superior
            cone_radius: Raio da base do cone
            cone_height: Altura do cone
        """
        if frequency:
            wavelength = C0 / frequency
            if disc_radius is None:
                disc_radius = 0.17 * wavelength
            if cone_radius is None:
                cone_radius = 0.25 * wavelength
            if cone_height is None:
                cone_height = 0.25 * wavelength

        antenna = AntennaGraph(name="Discone")

        # Gap de alimentação
        gap = wire_radius * 4

        # Centro do disco e vértice do cone
        disc_z = gap / 2
        cone_tip_z = -gap / 2
        cone_base_z = cone_tip_z - cone_height

        # Disco (Top Hat) - Aproximado por fios radiais e anel
        num_radials = 8
        disc_center = Vector3D(0, 0, disc_z)

        # Feed point (fio vertical curto entre disco e cone)
        n_disc, n_cone, _ = antenna.add_wire(
            disc_center, Vector3D(0, 0, cone_tip_z), wire_radius, start_type="feed", end_type="feed"
        )
        antenna.set_feed_point(n_disc)

        # Fios do Disco
        for i in range(num_radials):
            angle = 2 * np.pi * i / num_radials
            x = disc_radius * np.cos(angle)
            y = disc_radius * np.sin(angle)
            p_rim = Vector3D(x, y, disc_z)

            antenna.add_wire(disc_center, p_rim, wire_radius)

            # Anel externo do disco
            next_angle = 2 * np.pi * (i + 1) / num_radials
            next_x = disc_radius * np.cos(next_angle)
            next_y = disc_radius * np.sin(next_angle)
            p_next = Vector3D(next_x, next_y, disc_z)

            antenna.add_wire(p_rim, p_next, wire_radius)

        # Fios do Cone (Skirt)
        cone_tip = Vector3D(0, 0, cone_tip_z)

        for i in range(num_radials):
            angle = 2 * np.pi * i / num_radials
            x = cone_radius * np.cos(angle)
            y = cone_radius * np.sin(angle)
            p_base = Vector3D(x, y, cone_base_z)

            # Fio da ponta à base
            antenna.add_wire(cone_tip, p_base, wire_radius)

            # Anel da base
            next_angle = 2 * np.pi * (i + 1) / num_radials
            next_x = cone_radius * np.cos(next_angle)
            next_y = cone_radius * np.sin(next_angle)
            p_base_next = Vector3D(next_x, next_y, cone_base_z)

            antenna.add_wire(p_base, p_base_next, wire_radius)

        return antenna

    @staticmethod
    def create_folded_dipole(
        length: float, radius: float = 0.001, spacing: float = None
    ) -> AntennaGraph:
        """
        Cria antena dipolo dobrado (folded dipole).

        Args:
            length: Comprimento total entre as extremidades [m]
            radius: Raio do fio [m]
            spacing: Distância entre os dois condutores paralelos [m]
        """
        if spacing is None:
            spacing = max(length * 0.02, radius * 4)

        half_len = length / 2.0
        half_spacing = spacing / 2.0

        antenna = AntennaGraph(name=f"FoldedDipole_{length*1000:.0f}mm")

        # Fio superior (contém o ponto de alimentação no centro)
        top_left = Vector3D(0, half_spacing, -half_len)
        top_center = Vector3D(0, half_spacing, 0)
        top_right = Vector3D(0, half_spacing, half_len)

        _, n_center, _ = antenna.add_wire(
            top_left, top_center, radius, start_type="terminal", end_type="feed"
        )
        antenna.add_wire(top_center, top_right, radius, start_type="feed", end_type="terminal")

        antenna.set_feed_point(n_center)

        # Fio inferior paralelo
        bottom_left = Vector3D(0, -half_spacing, -half_len)
        bottom_right = Vector3D(0, -half_spacing, half_len)

        antenna.add_wire(
            bottom_left, bottom_right, radius, start_type="terminal", end_type="terminal"
        )

        # Conexões de extremidade (fecham o loop)
        antenna.add_wire(top_left, bottom_left, radius, start_type="junction", end_type="junction")

        antenna.add_wire(
            top_right, bottom_right, radius, start_type="junction", end_type="junction"
        )

        return antenna

    @staticmethod
    def create_v_dipole(
        length: float, radius: float = 0.001, angle_deg: float = 90.0
    ) -> AntennaGraph:
        antenna = AntennaGraph(name=f"VDipole_{length*1000:.0f}mm")

        center = Vector3D(0, 0, 0)
        arm_len = length / 2.0
        half_angle = np.deg2rad(angle_deg / 2.0)

        dir1 = Vector3D(0, np.sin(half_angle), np.cos(half_angle))
        dir2 = Vector3D(0, -np.sin(half_angle), np.cos(half_angle))

        end1 = center + dir1 * arm_len
        end2 = center + dir2 * arm_len

        _, n_center, _ = antenna.add_wire(
            center, end1, radius, start_type="feed", end_type="terminal"
        )

        antenna.add_wire(center, end2, radius, start_type="feed", end_type="terminal")

        antenna.set_feed_point(n_center)

        return antenna

    @staticmethod
    def create_monopole(
        length: float, radius: float = 0.001, ground_size: float = None
    ) -> AntennaGraph:
        """
        Cria antena monopolo com plano de terra.

        Args:
            length: Comprimento do monopolo [m]
            radius: Raio do fio [m]
            ground_size: Tamanho do plano de terra (None = infinito)
        """
        antenna = AntennaGraph(name=f"Monopole_{length*1000:.0f}mm")

        base = Vector3D(0, 0, 0)
        top = Vector3D(0, 0, length)

        # Elemento vertical
        n_base, n_top, _ = antenna.add_wire(
            base, top, radius, start_type="feed", end_type="terminal"
        )

        antenna.set_feed_point(n_base)
        antenna.set_ground(n_base)

        # Adiciona plano de terra como geometria (não no grafo de corrente)
        if ground_size:
            ground = Rectangle(
                center=Vector3D(0, 0, 0),
                width=ground_size,
                height=ground_size,
                thickness=radius * 2,
            )
            ground.material = MaterialLibrary.PEC
            ground.name = "Ground Plane"
            antenna.geometries.append(ground)

        return antenna

    @staticmethod
    def create_yagi(
        num_directors: int = 3,
        driven_length: float = 0.48,  # em λ
        reflector_length: float = 0.5,
        director_length: float = 0.45,
        spacing: float = 0.2,  # em λ
        frequency: float = 300e6,
        wire_radius: float = 0.001,
    ) -> AntennaGraph:
        """
        Cria antena Yagi-Uda.

        Args:
            num_directors: Número de diretores
            driven_length: Comprimento do elemento ativo [λ]
            reflector_length: Comprimento do refletor [λ]
            director_length: Comprimento dos diretores [λ]
            spacing: Espaçamento entre elementos [λ]
            frequency: Frequência de projeto [Hz]
            wire_radius: Raio do fio [m]
        """
        wavelength = C0 / frequency

        antenna = AntennaGraph(name=f"Yagi_{num_directors}dir_{frequency/1e6:.0f}MHz")

        # Posição do refletor (z = 0)
        ref_len = reflector_length * wavelength
        antenna.add_wire(Vector3D(-ref_len / 2, 0, 0), Vector3D(ref_len / 2, 0, 0), wire_radius)

        # Elemento ativo (driven)
        driven_len = driven_length * wavelength
        z_driven = spacing * wavelength
        center_pos = Vector3D(0, 0, z_driven)

        # Braço 1 (Esquerda -> Centro)
        n1, n_center, e1 = antenna.add_wire(
            Vector3D(-driven_len / 2, 0, z_driven),
            center_pos,
            wire_radius,
            start_type="terminal",
            end_type="feed",
        )

        # Braço 2 (Centro -> Direita)
        _, n2, e2 = antenna.add_wire(
            center_pos,
            Vector3D(driven_len / 2, 0, z_driven),
            wire_radius,
            start_type="feed",
            end_type="terminal",
        )

        antenna.set_feed_point(n_center)

        # Diretores
        dir_len = director_length * wavelength
        for i in range(num_directors):
            z_pos = z_driven + (i + 1) * spacing * wavelength
            antenna.add_wire(
                Vector3D(-dir_len / 2, 0, z_pos), Vector3D(dir_len / 2, 0, z_pos), wire_radius
            )
            # Reduz comprimento progressivamente
            dir_len *= 0.95

        return antenna

    @staticmethod
    def create_patch(
        frequency: float,
        substrate_er: float = 4.4,
        substrate_h: float = 1.6e-3,
        feed_offset_factor: float = 0.35,
    ) -> AntennaGraph:
        """
        Cria antena patch microstrip retangular projetada a partir da frequência.

        Usa equações clássicas de patch em microstrip (modo fundamental TM10)
        para calcular largura e comprimento efetivos.

        Args:
            frequency: Frequência central de projeto [Hz]
            substrate_er: Permissividade relativa do substrato
            substrate_h: Altura do substrato [m]
            feed_offset_factor: Fator de deslocamento do ponto de alimentação
                em relação ao comprimento (tipicamente 0.3–0.4)
        """
        # Largura aproximada (equação clássica)
        width = C0 / (2 * frequency) * ((substrate_er + 1) / 2) ** -0.5

        # Permissividade efetiva
        eps_eff = (substrate_er + 1) / 2 + (substrate_er - 1) / 2 * (
            1 + 12 * substrate_h / width
        ) ** -0.5

        # Extensão de comprimento devido ao fringing
        delta_L = (
            substrate_h
            * 0.412
            * (
                (eps_eff + 0.3)
                * (width / substrate_h + 0.264)
                / ((eps_eff - 0.258) * (width / substrate_h + 0.8))
            )
        )

        # Comprimento efetivo
        length_eff = C0 / (2 * frequency * np.sqrt(eps_eff))
        length = length_eff - 2 * delta_L

        antenna = AntennaGraph(name=f"Patch_{width*1000:.0f}x{length*1000:.0f}mm")

        # Patch radiante
        patch = Rectangle(
            center=Vector3D(0, 0, substrate_h),
            width=width,
            height=length,
            thickness=0.035e-3,  # 35μm cobre típico
        )
        patch.material = MaterialLibrary.COPPER
        patch.name = "Patch"
        antenna.geometries.append(patch)

        # Plano de terra
        ground = Rectangle(
            center=Vector3D(0, 0, 0), width=width * 2, height=length * 2, thickness=0.035e-3
        )
        ground.material = MaterialLibrary.PEC
        ground.name = "Ground"
        antenna.geometries.append(ground)

        # Feed via (coaxial simplificado)
        # Coloca o feed deslocado a partir da borda, em x = ±L/2 * (1 - feed_offset_factor)
        feed_x = length * (0.5 - feed_offset_factor)
        feed_wire = Wire(
            start=Vector3D(feed_x, 0, 0), end=Vector3D(feed_x, 0, substrate_h), radius=0.5e-3
        )
        feed_wire.material = MaterialLibrary.COPPER

        n_ground, n_patch, _ = antenna.add_wire(
            feed_wire.start, feed_wire.end, radius=0.5e-3, start_type="ground", end_type="feed"
        )

        antenna.set_feed_point(n_patch)
        antenna.set_ground(n_ground)

        return antenna

    @staticmethod
    def create_helix(
        frequency: float,
        num_turns: float = 5,
        circumference_factor: float = 1.0,
        wire_radius: float = 0.001,
    ) -> AntennaGraph:
        """
        Cria antena helicoidal para polarização circular.

        Args:
            frequency: Frequência de operação [Hz]
            num_turns: Número de espiras
            circumference_factor: Fator de circunferência (1.0 = λ)
            wire_radius: Raio do fio [m]
        """
        wavelength = C0 / frequency

        # Parâmetros ótimos para modo axial
        circumference = circumference_factor * wavelength
        radius = circumference / (2 * np.pi)
        pitch = 0.25 * wavelength  # ~λ/4 entre espiras

        antenna = AntennaGraph(name=f"Helix_{frequency/1e6:.0f}MHz")

        # Hélice
        helix = Helix(
            center=Vector3D(0, 0, 0),
            radius=radius,
            pitch=pitch,
            turns=num_turns,
            wire_radius=wire_radius,
        )
        helix.material = MaterialLibrary.COPPER
        antenna.geometries.append(helix)

        # Cria nós para início e fim da hélice
        helix_points = helix.sample_surface(wavelength / 20)

        feed_node = antenna.add_node(helix_points[0], "feed")
        _end_node = antenna.add_node(helix_points[-1], "terminal")

        antenna.set_feed_point(feed_node)

        return antenna

    @staticmethod
    def create_horn(
        frequency: float,
        aperture_width: float,
        aperture_height: float,
        length: float,
        throat_width: float = None,
        throat_height: float = None,
    ) -> AntennaGraph:
        """
        Cria antena corneta (pyramidal horn).

        Args:
            frequency: Frequência de operação [Hz]
            aperture_width: Largura da abertura [m]
            aperture_height: Altura da abertura [m]
            length: Comprimento axial [m]
            throat_width: Largura da garganta [m]
            throat_height: Altura da garganta [m]
        """
        wavelength = C0 / frequency

        # Padrões se não especificados (guia de onda WR-90 aproximado para X-band)
        if throat_width is None:
            throat_width = 0.5 * wavelength
        if throat_height is None:
            throat_height = 0.25 * wavelength

        antenna = AntennaGraph(name=f"Horn_{frequency/1e6:.0f}MHz")

        horn = Horn(
            center=Vector3D(0, 0, 0),
            aperture_width=aperture_width,
            aperture_height=aperture_height,
            throat_width=throat_width,
            throat_height=throat_height,
            length=length,
        )
        horn.material = MaterialLibrary.COPPER
        antenna.geometries.append(horn)

        # Adiciona probe de alimentação na garganta (simplificado)
        probe_len = throat_height * 0.4
        probe_pos = Vector3D(0, 0, length * 0.1)  # Perto do fundo

        n1, n2, _ = antenna.add_wire(
            probe_pos - Vector3D(0, probe_len / 2, 0),
            probe_pos + Vector3D(0, probe_len / 2, 0),
            radius=0.0005,
            start_type="terminal",
            end_type="feed",
        )
        antenna.set_feed_point(n2)

        return antenna

    @staticmethod
    def create_parabolic(frequency: float, diameter: float, focal_length: float) -> AntennaGraph:
        """
        Cria antena parabólica.

        Args:
            frequency: Frequência de operação [Hz]
            diameter: Diâmetro do prato [m]
            focal_length: Distância focal [m]
        """
        antenna = AntennaGraph(name=f"Dish_{diameter:.1f}m")

        dish = ParabolicDish(center=Vector3D(0, 0, 0), diameter=diameter, focal_length=focal_length)
        dish.material = MaterialLibrary.ALUMINUM
        antenna.geometries.append(dish)

        # Adiciona dipolo alimentador no foco
        wavelength = C0 / frequency
        dipole_len = wavelength / 2
        focus_z = focal_length

        n1, n_center, _ = antenna.add_wire(
            Vector3D(-dipole_len / 2, 0, focus_z),
            Vector3D(dipole_len / 2, 0, focus_z),
            radius=0.001,
            start_type="terminal",
            end_type="feed",
        )
        antenna.set_feed_point(n_center)

        return antenna

    @staticmethod
    def create_log_periodic(
        frequency_min: float,
        frequency_max: float,
        tau: float = 0.86,  # Fator de escala geométrica
        sigma: float = 0.15,  # Fator de espaçamento
        wire_radius: float = 0.001,
    ) -> AntennaGraph:
        """
        Cria antena Log-Periódica de Dipolos (LPDA).

        Args:
            frequency_min: Frequência mínima [Hz]
            frequency_max: Frequência máxima [Hz]
            tau: Razão de escala (L_n+1 / L_n) typically 0.7 to 0.95
            sigma: Fator de espaçamento typically 0.1 to 0.2
            wire_radius: Raio do fio [m]
        """

        # Banda de design com margem
        f_start = frequency_min * 0.9
        f_stop = frequency_max * 1.1

        # Comprimento do maior elemento (baixa freq)
        length_max = (C0 / f_start) / 2
        # Comprimento do menor elemento (alta freq)
        length_min = (C0 / f_stop) / 2

        antenna = AntennaGraph(name=f"LPDA_{frequency_min/1e6:.0f}-{frequency_max/1e6:.0f}MHz")

        # Gera elementos
        lengths = []
        current_length = length_max
        while current_length >= length_min:
            lengths.append(current_length)
            current_length *= tau

        n_elements = len(lengths)

        # Calcula posições
        # d_n = 2 * sigma * L_n
        # x_n+1 = x_n - d_n

        # Posiciona o maior elemento em x=0
        current_x = 0
        element_positions = []

        for i in range(n_elements):
            element_positions.append(current_x)
            if i < n_elements - 1:
                # Distância para o próximo elemento (menor)
                d = 4 * sigma * lengths[i + 1]  # Aproximação comum d_n = x_n - x_n+1
                current_x += d

        # Define offset para centralizar
        center_offset = (element_positions[0] + element_positions[-1]) / 2

        # Adiciona Boom (estrutura de suporte isolante)
        # O boom corre ao longo do eixo X, com largura pequena
        boom_length = (element_positions[-1] - element_positions[0]) + (length_max / 2)
        boom_center_x = (element_positions[0] + element_positions[-1]) / 2 - center_offset

        boom = Rectangle(
            center=Vector3D(boom_center_x, 0, 0),
            width=boom_length,
            height=length_min,  # Largura do boom proporcional ao menor elemento
            thickness=wire_radius * 4,
            normal=Vector3D(0, 0, 1),
        )
        boom.material = MaterialLibrary.TEFLON
        boom.name = "Boom"
        antenna.geometries.append(boom)

        prev_node_top = None
        prev_node_bottom = None

        for i in range(n_elements):
            x_pos = element_positions[i] - center_offset
            length = lengths[i]

            # Elemento dipolo (alinhado em Y, boom em X)
            # Metade superior
            top_start = Vector3D(x_pos, 0.005, 0)  # Pequeno gap no centro para boom
            top_end = Vector3D(x_pos, length / 2, 0)

            # Metade inferior
            bottom_start = Vector3D(x_pos, -0.005, 0)
            bottom_end = Vector3D(x_pos, -length / 2, 0)

            # Cria fios do elemento
            nt1, nt2, _ = antenna.add_wire(top_start, top_end, wire_radius)
            nb1, nb2, _ = antenna.add_wire(bottom_start, bottom_end, wire_radius)

            # Conecta com linha de transmissão cruzada (phase reversal)
            if prev_node_top is not None:
                # Topo anterior conecta com Fundo atual
                antenna.add_wire(
                    antenna.nodes[prev_node_top].position,
                    antenna.nodes[nb1].position,
                    wire_radius,
                    start_type="junction",
                    end_type="junction",
                )
                # Fundo anterior conecta com Topo atual
                antenna.add_wire(
                    antenna.nodes[prev_node_bottom].position,
                    antenna.nodes[nt1].position,
                    wire_radius,
                    start_type="junction",
                    end_type="junction",
                )

            prev_node_top = nt1
            prev_node_bottom = nb1

            # Alimentação no elemento menor (frente)
            if i == n_elements - 1:
                antenna.set_feed_point(nt1)  # Simplificado

        return antenna

    @staticmethod
    def create_loop(
        radius: float, wire_radius: float = 0.001, axis: str = "z", segments: int = 32
    ) -> AntennaGraph:
        """
        Cria antena Loop circular.

        Args:
            radius: Raio do loop [m]
            wire_radius: Raio do fio [m]
            axis: Eixo normal ao loop ('x', 'y', 'z')
            segments: Número de segmentos para aproximação
        """
        antenna = AntennaGraph(name=f"Loop_r{radius*1000:.0f}mm")

        # Gera pontos do círculo
        points = []
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            if axis == "z":
                x = radius * np.cos(angle)
                y = radius * np.sin(angle)
                z = 0
            elif axis == "y":
                x = radius * np.cos(angle)
                y = 0
                z = radius * np.sin(angle)
            else:  # x
                x = 0
                y = radius * np.cos(angle)
                z = radius * np.sin(angle)
            points.append(Vector3D(x, y, z))

        # Adiciona fios conectando os pontos

        for i in range(segments):
            p1 = points[i]
            p2 = points[(i + 1) % segments]

            # Se for o último segmento (fechando o loop), insere o feed point
            if i == segments - 1:
                # Aqui vamos inserir o feed no nó de fechamento
                n1, n2, _ = antenna.add_wire(
                    p1, p2, wire_radius, start_type="junction", end_type="junction"
                )
                antenna.set_feed_point(n1)
            else:
                n1, n2, _ = antenna.add_wire(
                    p1, p2, wire_radius, start_type="junction", end_type="junction"
                )

        return antenna
