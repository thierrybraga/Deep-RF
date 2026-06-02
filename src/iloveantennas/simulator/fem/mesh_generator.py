import gmsh
import numpy as np

try:
    from antenna_simulator.core.geometry.primitives import (
        Cylinder,
        Helix,
        Horn,
        ParabolicDish,
        Rectangle,
        Wire,
    )
    from antenna_simulator.core.geometry.topology import AntennaGraph
except ImportError:
    # Fallback para execução local ou testes
    try:
        from iloveantennas.simulator.core.geometry.primitives import (
            Cylinder,
            Helix,
            Horn,
            ParabolicDish,
            Rectangle,
            Wire,
        )
        from iloveantennas.simulator.core.geometry.topology import AntennaGraph
    except ImportError:
        # Tenta relativo
        from ..core.geometry.primitives import Cylinder, Helix, Horn, ParabolicDish, Rectangle, Wire
        from ..core.geometry.topology import AntennaGraph


class MeshGenerator:
    """
    Gera malha 3D usando Gmsh a partir de um AntennaGraph.
    """

    def __init__(self, antenna: AntennaGraph, frequency: float):
        self.antenna = antenna
        self.frequency = frequency
        self.wavelength = 299792458.0 / frequency
        self.model = None
        self.mesh_tags = {}

    def generate_2d(self, filename: str = None, plane: str = "xz", resolution_factor: float = 10.0):
        """
        Gera malha 2D (slice) usando Gmsh.
        Ideal para simulações rápidas ou simétricas.
        """
        gmsh.initialize()
        gmsh.clear()

        # Usaremos OpenCASCADE (occ) para facilitar booleanas 2D
        # Atenção: O código 3D acima usa 'geo'. Eles são kernels diferentes.
        # Aqui estamos reiniciando, então tudo bem.

        gmsh.model.add(f"{self.antenna.name}_2d")

        lc = self.wavelength / resolution_factor

        # Bounding box 3D
        bbox = self.antenna.get_bounding_box()
        margin = self.wavelength / 1.0

        # Define dimensões do domínio 2D baseado no plano
        if plane == "xz":
            u_min, u_max = bbox.min_point.x - margin, bbox.max_point.x + margin
            v_min, v_max = bbox.min_point.z - margin, bbox.max_point.z + margin
            u_idx, v_idx = 0, 2
        elif plane == "yz":
            u_min, u_max = bbox.min_point.y - margin, bbox.max_point.y + margin
            v_min, v_max = bbox.min_point.z - margin, bbox.max_point.z + margin
            u_idx, v_idx = 1, 2
        else:  # xy
            u_min, u_max = bbox.min_point.x - margin, bbox.max_point.x + margin
            v_min, v_max = bbox.min_point.y - margin, bbox.max_point.y + margin
            u_idx, v_idx = 0, 1

        # Cria retângulo do domínio (Ar)
        # addRectangle(x, y, z, dx, dy) -> Tag
        # Note: OCC rectangles are created on XY plane by default usually, but we can transform.
        # Simplificação: Criar sempre no XY do OCC e interpretar como U,V.

        domain_tag = gmsh.model.occ.addRectangle(u_min, v_min, 0, u_max - u_min, v_max - v_min)

        # Cria geometria da antena (Cortes)
        antenna_tags = []

        for edge_id, edge in self.antenna.edges.items():
            geo = edge.geometry
            if isinstance(geo, Wire):
                # Projeta Wire no plano
                # Um Wire é um cilindro.
                # Se o wire está no plano (ou paralelo), vira um retângulo.
                # Se é perpendicular, vira um círculo.

                # Vamos simplificar assumindo Wires alinhados com eixos principais
                p1 = geo.start
                p2 = geo.end
                radius = geo.radius

                # Coordenadas no plano UV
                coords1 = [p1.x, p1.y, p1.z]
                coords2 = [p2.x, p2.y, p2.z]

                u1, v1 = coords1[u_idx], coords1[v_idx]
                u2, v2 = coords2[u_idx], coords2[v_idx]

                # Verifica se está no plano (coordenada normal próxima de 0 se plano central)
                # Assumindo corte em 0.

                # Se é um fio vertical (Z) e plano é XZ:
                # Vira um retângulo de largura 2*r e altura L.

                # Vetor diretor
                du = u2 - u1
                dv = v2 - v1
                length = np.sqrt(du**2 + dv**2)

                if length > 1e-6:
                    # É uma linha no plano
                    # Cria retângulo rotacionado representando a espessura do fio
                    # Ângulo
                    angle = np.arctan2(dv, du)

                    # Centro
                    uc = (u1 + u2) / 2
                    vc = (v1 + v2) / 2

                    # Cria retângulo no centro (0,0) depois move e rotaciona
                    # Width = length, Height = 2*radius
                    t = gmsh.model.occ.addRectangle(-length / 2, -radius, 0, length, 2 * radius)

                    # Rotação
                    if abs(angle) > 1e-6:
                        gmsh.model.occ.rotate([(2, t)], 0, 0, 0, 0, 0, 1, angle)

                    # Translação
                    gmsh.model.occ.translate([(2, t)], uc, vc, 0)

                    antenna_tags.append(t)

                else:
                    # É um ponto no plano (fio perpendicular)
                    # Cria círculo
                    t = gmsh.model.occ.addDisk(u1, v1, 0, radius, radius)
                    antenna_tags.append(t)

        # Operação Booleana: Domínio - Antena
        # Cut (dim 2, tag)
        if antenna_tags:
            # Cut retorna (list of (dim, tag), list of list of maps)
            # domain_tag é (2, domain_tag)
            cut_result = gmsh.model.occ.cut([(2, domain_tag)], [(2, t) for t in antenna_tags])
            final_surfaces = [tag for dim, tag in cut_result[0] if dim == 2]
        else:
            final_surfaces = [domain_tag]

        gmsh.model.occ.synchronize()

        # Grupos Físicos
        # O resultado do cut são superfícies de AR.
        # As bordas internas (buracos) são PEC.
        # As bordas externas são Farfield.

        # Identificar bordas
        # Bounding box do domínio original
        # Se uma curva está na borda do bbox, é Farfield. Caso contrário, é PEC.

        all_curves = gmsh.model.getEntities(dim=1)
        pec_curves = []
        farfield_curves = []

        eps = 1e-5
        for dim, tag in all_curves:
            # Bbox da curva
            bbox_c = gmsh.model.getBoundingBox(dim, tag)
            # xmin, ymin, zmin, xmax, ymax, zmax
            cx_min, cy_min, _, cx_max, cy_max, _ = bbox_c

            is_boundary = (
                abs(cx_min - u_min) < eps
                or abs(cx_max - u_max) < eps
                or abs(cy_min - v_min) < eps
                or abs(cy_max - v_max) < eps
            )

            if is_boundary:
                farfield_curves.append(tag)
            else:
                pec_curves.append(tag)

        gmsh.model.addPhysicalGroup(1, farfield_curves, tag=1, name="Farfield")
        gmsh.model.addPhysicalGroup(1, pec_curves, tag=2, name="PEC")
        gmsh.model.addPhysicalGroup(2, final_surfaces, tag=3, name="Air")

        # Geração de Malha
        gmsh.model.mesh.setSize(gmsh.model.getEntities(0), lc)

        # Refinamento perto do PEC
        # Field distance... (Opcional, mas bom para precisão)

        gmsh.model.mesh.generate(2)

        if filename:
            gmsh.write(filename)

        gmsh.finalize()

    def generate(self, filename: str = None, resolution_factor: float = 10.0):
        """
        Gera a malha e opcionalmente salva em arquivo (.msh).

        Args:
            filename: Caminho para salvar o arquivo de malha. Se None, apenas gera na memória.
            resolution_factor: Pontos por comprimento de onda (lambda/N).
        """
        gmsh.initialize()
        gmsh.model.add(self.antenna.name)

        # Tamanho de elemento alvo
        lc = self.wavelength / resolution_factor

        # Bounding box global para o domínio de ar
        bbox = self.antenna.get_bounding_box()
        margin = self.wavelength / 2.0  # Margem de meio lambda

        domain_min = bbox.min_point - margin
        domain_max = bbox.max_point + margin

        # 1. Cria domínio de ar (Caixa)
        # Pontos da caixa
        p1 = gmsh.model.geo.addPoint(domain_min.x, domain_min.y, domain_min.z, lc)
        p2 = gmsh.model.geo.addPoint(domain_max.x, domain_min.y, domain_min.z, lc)
        p3 = gmsh.model.geo.addPoint(domain_max.x, domain_max.y, domain_min.z, lc)
        p4 = gmsh.model.geo.addPoint(domain_min.x, domain_max.y, domain_min.z, lc)

        p5 = gmsh.model.geo.addPoint(domain_min.x, domain_min.y, domain_max.z, lc)
        p6 = gmsh.model.geo.addPoint(domain_max.x, domain_min.y, domain_max.z, lc)
        p7 = gmsh.model.geo.addPoint(domain_max.x, domain_max.y, domain_max.z, lc)
        p8 = gmsh.model.geo.addPoint(domain_min.x, domain_max.y, domain_max.z, lc)

        # Linhas da caixa
        l1 = gmsh.model.geo.addLine(p1, p2)
        l2 = gmsh.model.geo.addLine(p2, p3)
        l3 = gmsh.model.geo.addLine(p3, p4)
        l4 = gmsh.model.geo.addLine(p4, p1)

        l5 = gmsh.model.geo.addLine(p5, p6)
        l6 = gmsh.model.geo.addLine(p6, p7)
        l7 = gmsh.model.geo.addLine(p7, p8)
        l8 = gmsh.model.geo.addLine(p8, p5)

        l9 = gmsh.model.geo.addLine(p1, p5)
        l10 = gmsh.model.geo.addLine(p2, p6)
        l11 = gmsh.model.geo.addLine(p3, p7)
        l12 = gmsh.model.geo.addLine(p4, p8)

        # Loops e Superfícies da caixa
        cl1 = gmsh.model.geo.addCurveLoop([l1, l2, l3, l4])
        s1 = gmsh.model.geo.addPlaneSurface([cl1])  # Z min

        cl2 = gmsh.model.geo.addCurveLoop([l5, l6, l7, l8])
        s2 = gmsh.model.geo.addPlaneSurface([cl2])  # Z max

        cl3 = gmsh.model.geo.addCurveLoop([l1, l10, -l5, -l9])
        s3 = gmsh.model.geo.addPlaneSurface([cl3])  # Y min

        cl4 = gmsh.model.geo.addCurveLoop([l3, l12, -l7, -l11])
        s4 = gmsh.model.geo.addPlaneSurface([cl4])  # Y max

        cl5 = gmsh.model.geo.addCurveLoop([l2, l11, -l6, -l10])
        s5 = gmsh.model.geo.addPlaneSurface([cl5])  # X max

        cl6 = gmsh.model.geo.addCurveLoop([l4, l9, -l8, -l12])
        s6 = gmsh.model.geo.addPlaneSurface([cl6])  # X min

        air_surface_loop = gmsh.model.geo.addSurfaceLoop([s1, s2, s3, s4, s5, s6])
        air_volume = gmsh.model.geo.addVolume([air_surface_loop])

        # 2. Cria geometria da antena dentro do domínio
        # Por enquanto, focamos em Fios (Wires) como Cilindros finos ou Linhas 1D
        # Para FEM 3D com elementos de borda, fios podem ser linhas embutidas na malha.
        # No entanto, scikit-fem lida melhor com tetraedros.
        # Fios 1D em malha 3D requerem cuidado especial.
        # Vamos modelar fios como cilindros físicos para ter volume.

        antenna_volumes = []
        antenna_surfaces = []  # Para patch

        for edge_id, edge in self.antenna.edges.items():
            geo = edge.geometry
            if isinstance(geo, Wire):
                # Cria cilindro para o fio
                # gmsh.model.occ é melhor para primitivas 3D
                pass

        # Como misturar geo e occ é complexo, vamos usar OCC (OpenCascade) para tudo se possível.
        # Reiniciando com OCC kernel

        gmsh.model.remove()
        gmsh.model.add(self.antenna.name)

        # Domínio de ar via OCC
        box_dim = domain_max - domain_min
        air_box = gmsh.model.occ.addBox(
            domain_min.x, domain_min.y, domain_min.z, box_dim.x, box_dim.y, box_dim.z
        )

        antenna_tags = []

        for edge_id, edge in self.antenna.edges.items():
            geo = edge.geometry
            if isinstance(geo, Wire):
                # Cria cilindro
                dx = geo.end.x - geo.start.x
                dy = geo.end.y - geo.start.y
                dz = geo.end.z - geo.start.z

                # Se for muito fino, pode dar problema na malha.
                # Raio mínimo para visualização/malha
                r = max(geo.radius, lc / 20.0)

                cyl = gmsh.model.occ.addCylinder(
                    geo.start.x, geo.start.y, geo.start.z, dx, dy, dz, r
                )
                antenna_tags.append((3, cyl))  # 3 = volume

            elif isinstance(geo, Rectangle):
                # Patch como volume fino (ou superfície se suportado pelo solver)
                # Vamos fazer volume fino
                thick = max(geo.thickness, lc / 20.0)
                # Posição do canto inferior
                corner = geo.center - Vector3D(geo.width / 2, geo.height / 2, thick / 2)

                rect = gmsh.model.occ.addBox(
                    corner.x, corner.y, corner.z, geo.width, geo.height, thick
                )
                antenna_tags.append((3, rect))

        gmsh.model.occ.synchronize()

        # Subtrai antena do ar para ter o volume do ar
        # cut retorna (tags_result, tags_map)
        # air_box é tag (3, air_box)

        if antenna_tags:
            # Corta antena do ar.
            # Mas queremos manter a antena como PEC (boundary) ou material.
            # Se for PEC, apenas o "buraco" no ar é suficiente e aplicamos BC na superfície interna.
            # Se for dielétrico, precisamos manter o volume.

            # Para dipolo PEC: Subtraímos o cilindro e aplicamos BC na superfície do buraco.
            res, _ = gmsh.model.occ.cut(
                [(3, air_box)], antenna_tags, removeObject=True, removeTool=True
            )
            # O volume resultante é o ar com buracos.

            # Precisamos identificar as superfícies do buraco para aplicar PEC.
            # Isso é complexo automaticamente.
            # Alternativa: Manter volumes separados e "fragment" para conformar malha.
            pass

        # Re-abordagem simplificada:
        # Apenas domínio de ar.
        # Fios são 1D Lines embutidos na malha (Embed Curve).
        # Patch são 2D Surfaces embutidas (Embed Surface).
        # Isso evita malha ultra-fina em torno de fios grossos.

        gmsh.model.remove()
        gmsh.model.add(self.antenna.name)

        # Recria Box Geo (não OCC para facilitar tags manuais)
        # Mas Embed precisa que pontos estejam na geometria...
        # Vamos usar OCC e Fragment.

        air = gmsh.model.occ.addBox(
            domain_min.x, domain_min.y, domain_min.z, box_dim.x, box_dim.y, box_dim.z
        )

        embedded_curves = []
        embedded_surfaces = []

        for edge_id, edge in self.antenna.edges.items():
            geo = edge.geometry
            if isinstance(geo, Wire):
                p1 = gmsh.model.occ.addPoint(geo.start.x, geo.start.y, geo.start.z)
                p2 = gmsh.model.occ.addPoint(geo.end.x, geo.end.y, geo.end.z)
                line = gmsh.model.occ.addLine(p1, p2)
                embedded_curves.append((1, line))

            elif isinstance(geo, Rectangle):
                # Retângulo 2D
                # Cantos
                c = geo.center
                hw, hh = geo.width / 2, geo.height / 2
                p1 = gmsh.model.occ.addPoint(c.x - hw, c.y - hh, c.z)
                p2 = gmsh.model.occ.addPoint(c.x + hw, c.y - hh, c.z)
                p3 = gmsh.model.occ.addPoint(c.x + hw, c.y + hh, c.z)
                p4 = gmsh.model.occ.addPoint(c.x - hw, c.y + hh, c.z)

                l1 = gmsh.model.occ.addLine(p1, p2)
                l2 = gmsh.model.occ.addLine(p2, p3)
                l3 = gmsh.model.occ.addLine(p3, p4)
                l4 = gmsh.model.occ.addLine(p4, p1)

                loop = gmsh.model.occ.addCurveLoop([l1, l2, l3, l4])
                surf = gmsh.model.occ.addPlaneSurface([loop])
                embedded_surfaces.append((2, surf))

        gmsh.model.occ.synchronize()

        # Fragmenta o ar com as curvas/superfícies para garantir nós coincidentes
        # Fragment(object, tool)
        # Object: Ar
        # Tool: Antenas

        tools = embedded_curves + embedded_surfaces
        if tools:
            # fragment retorna (objectDimTags, toolDimTags)
            # Precisamos pegar o volume de volta
            ov, tv = gmsh.model.occ.fragment([(3, air)], tools)
            gmsh.model.occ.synchronize()

        # Define Physical Groups
        # Volume do ar
        vols = gmsh.model.getEntities(3)
        gmsh.model.addPhysicalGroup(3, [v[1] for v in vols], name="Air")

        # Superfícies da Antena (PEC)
        # As curvas/superfícies "tools" agora fazem parte da fronteira ou interior
        # Precisamos identificar quais tags correspondem à antena para BC.
        # Isso é chato pós-fragment.
        # Mas podemos pegar por Bounding Box ou "Parent".

        # Por simplicidade para o MVP:
        # Assumimos que curvas internas são PEC.
        # Bordas externas da caixa são ABC.

        # Pega todas as curvas
        all_curves = gmsh.model.getEntities(1)
        pec_curves = []
        for c in all_curves:
            # Verifica se está "dentro" do domínio (com margem)
            # Se não está na borda da caixa, é antena
            bbox_c = gmsh.model.getBoundingBox(1, c[1])  # minx, miny, minz, maxx, ...
            cx = (bbox_c[0] + bbox_c[3]) / 2
            cy = (bbox_c[1] + bbox_c[4]) / 2
            cz = (bbox_c[2] + bbox_c[5]) / 2

            # Se está longe da borda
            tol = margin * 0.1
            if (
                cx > domain_min.x + tol
                and cx < domain_max.x - tol
                and cy > domain_min.y + tol
                and cy < domain_max.y - tol
                and cz > domain_min.z + tol
                and cz < domain_max.z - tol
            ):
                pec_curves.append(c[1])

        if pec_curves:
            gmsh.model.addPhysicalGroup(1, pec_curves, name="PEC_Wire")

        # Pega superfícies internas (Patch)
        all_surfs = gmsh.model.getEntities(2)
        pec_surfs = []
        abc_surfs = []

        for s in all_surfs:
            bbox_s = gmsh.model.getBoundingBox(2, s[1])
            cx = (bbox_s[0] + bbox_s[3]) / 2

            # Check if boundary or internal
            # Na verdade, a caixa externa tem 6 superfícies.
            # O fragment pode ter dividido elas, mas geralmente mantém.
            # Vamos classificar por proximidade com as bordas do domínio.

            is_boundary = False
            # Verifica proximidade com domain_min/max
            # ... simplificação

            # Se está dentro, é PEC
            if bbox_s[0] > domain_min.x + tol and bbox_s[3] < domain_max.x - tol:
                pec_surfs.append(s[1])
            else:
                abc_surfs.append(s[1])

        if pec_surfs:
            gmsh.model.addPhysicalGroup(2, pec_surfs, name="PEC_Surface")

        if abc_surfs:
            gmsh.model.addPhysicalGroup(2, abc_surfs, name="ABC_Boundary")

        # Mesh generation
        gmsh.model.mesh.generate(3)

        if filename:
            gmsh.write(filename)

        gmsh.finalize()
