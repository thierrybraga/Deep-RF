import numpy as np
from scipy.sparse import linalg as splinalg
from skfem import *
from skfem.helpers import dot, grad
from skfem.models.poisson import laplace, mass


class FEMSolver2D:
    """
    Solver FEM 2D simplificado para equação de Helmholtz escalar (Ez).
    Resolve: ∇²E + k²E = f
    """

    def __init__(self, frequency, mesh_file=None, width=1.0, height=1.0, resolution=0.05):
        self.frequency = frequency
        self.omega = 2 * np.pi * frequency
        self.c = 299792458.0
        self.k = self.omega / self.c

        if mesh_file:
            # Carrega malha do Gmsh
            self.mesh = MeshTri.load(mesh_file)
        else:
            # Malha retangular simples (fallback)
            self.mesh = MeshTri.init_tensor(
                np.linspace(-width / 2, width / 2, int(width / resolution)),
                np.linspace(-height / 2, height / 2, int(height / resolution)),
            )

        self.basis = Basis(self.mesh, ElementTriP1())

    def solve(self):
        """
        Resolve a equação de Helmholtz.
        """
        # Forma fraca: (∇u, ∇v) - k²(u, v) - jk_abc(u, v)_boundary = (f, v)

        A = asm(laplace, self.basis)
        M = asm(mass, self.basis)

        # ABC (Absorbing Boundary Condition) de 1ª ordem
        # Termo de borda: - integral (jk u v) dS
        # Precisamos identificar a borda Farfield

        # Tenta encontrar boundary 'Farfield' (tag 1 do gerador)
        # Em skfem, boundaries são acessadas por nome ou tag
        # MeshGenerator usa physical groups. MeshTri.load deve carregar.

        # boundaries = self.basis.get_dofs(facets=True) # Removido pois causou erro

        # Matriz de massa de borda para ABC
        M_boundary = 0

        # Verifica se temos boundaries nomeadas (do Gmsh)
        has_farfield = False

        # Tenta identificar bordas por tags do gmsh
        # O skfem mapeia physical groups para boundaries em self.mesh.boundaries
        # self.mesh.boundaries é um dict {name: indices}

        # Se 'Farfield' existe nas boundaries
        if self.mesh.boundaries and "Farfield" in self.mesh.boundaries:
            basis_b = FacetBasis(self.mesh, ElementTriP1(), facets=self.mesh.boundaries["Farfield"])
            M_boundary = asm(mass, basis_b)
            has_farfield = True

        # Matriz do sistema
        # (-A + k²M + j k M_boundary) u = -f
        # ou (A - k²M - j k M_boundary) u = -f  (depende da convenção de sinal)
        # Helmholtz: ∇²u + k²u = f
        # Weak: - (∇u, ∇v) + k²(u, v) + boundary_terms = (f, v)
        # Boundary term (Sommerfeld): ∇u.n = -j k u
        # int (∇u.n) v = int (-j k u) v = -j k (u, v)_b
        # Eq: - (∇u, ∇v) + k²(u, v) - j k (u, v)_b = (f, v)
        # => - A + k² M - j k M_b = RHS
        # => (A - k² M + j k M_b) u = -RHS

        k2 = self.k**2

        L = A - k2 * M
        if has_farfield:
            L = L + 1j * self.k * M_boundary
        else:
            # Se não tem Farfield explícito, usa damping no volume (perda)
            k2_complex = (self.k * (1 - 0.05j)) ** 2
            L = A - k2_complex * M

        # Fonte
        @LinearForm
        def load(v, w):
            # Fonte gaussiana no centro
            x, y = w.x
            r2 = x**2 + y**2
            return np.exp(-r2 / 0.005) * v  # Mais concentrada

        b = asm(load, self.basis)

        # Condições de Contorno PEC (Dirichlet = 0)
        # Se 'PEC' existe nas boundaries
        D = None
        if self.mesh.boundaries and "PEC" in self.mesh.boundaries:
            D = self.basis.get_dofs("PEC")

        # Resolve
        if D is not None:
            # Usa condense para aplicar Dirichlet
            L_c, b_c, x, I = condense(L, -b, D=D, expand=True)
            # Resolve sistema reduzido
            x[I] = splinalg.spsolve(L_c, b_c)
        else:
            # Se não tem PEC, resolve sistema puro (pode ser singular se k for autovalor e sem perda)
            x = splinalg.spsolve(L, -b)

        return x

    def get_field_on_grid(self, nx=100, ny=100):
        """
        Interpola a solução FEM para um grid regular (para visualização).
        """
        # Cria grid regular
        xs = np.linspace(np.min(self.mesh.p[0]), np.max(self.mesh.p[0]), nx)
        ys = np.linspace(np.min(self.mesh.p[1]), np.max(self.mesh.p[1]), ny)
        grid_x, grid_y = np.meshgrid(xs, ys)

        # Avalia solução nos pontos do grid
        # probes espera array (dim, n_points)
        pts = np.vstack((grid_x.flatten(), grid_y.flatten()))

        # Recalcula solução (idealmente cachear)
        # Se x já foi calculado, devíamos reusar. Mas aqui chamamos self.solve().
        # self.solve() é rápido para 2D pequeno.

        field_flat = self.basis.probes(pts) @ self.solve()

        # Reshape para (ny, nx)
        field = field_flat.reshape((ny, nx))

        # Retorna magnitude real (ou complexa se quisermos fase)
        # Frontend espera (nx, ny) ou (x, y) indexing?
        # Normalmente frontend espera lista de linhas (y) ou colunas (x).
        # Em simulation.py para FDTD: mag[x, z].
        # Aqui geramos (ny, nx). Se quisermos (nx, ny), transpomos.
        return np.real(field).T
