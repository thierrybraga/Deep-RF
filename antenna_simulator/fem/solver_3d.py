import numpy as np
from skfem import *
from skfem.helpers import curl, dot, cross
import meshio

try:
    # Quando usado a partir do pacote antenna_simulator
    from antenna_simulator.core.geometry.primitives import Vector3D
except ImportError:
    # Quando importado via antenna_web (sys.path diferente)
    try:
        from core.geometry.primitives import Vector3D
    except ImportError:
        from ..core.geometry.primitives import Vector3D

# Definindo formas bilineares para Maxwell
@BilinearForm
def curl_curl(E, v, w):
    return dot(curl(E), curl(v))

@BilinearForm
def mass_matrix(E, v, w):
    return dot(E, v)

class FEMSolver3D:
    """
    Solver FEM 3D para equações de Maxwell (Time-Harmonic).
    Resolve: ∇ × (1/μ ∇ × E) - ω²ε E = -jωJ
    """
    def __init__(self, mesh_file: str, frequency: float, feed_point: Vector3D = None):
        self.mesh = MeshTet.load(mesh_file)
        self.frequency = frequency
        self.feed_point = feed_point
        self.omega = 2 * np.pi * frequency
        self.c0 = 299792458.0
        self.mu0 = 4 * np.pi * 1e-7
        self.eps0 = 8.854187817e-12
        self.k0 = self.omega / self.c0
        
        # Elementos de borda (Nédélec) de primeira ordem
        self.element = ElementTetN0()
        self.basis = Basis(self.mesh, self.element)
        
    def solve(self):
        """
        Monta e resolve o sistema linear.
        """
        # Constantes
        # k0² = ω²με
        k0_sq = self.k0 ** 2
        
        # Forma fraca para E:
        # ∫ (∇×E)·(∇×v) dV - k₀² ∫ E·v dV = Boundary Terms + Source
        
        # Stiffness matrix (Curl-Curl)
        # vector_laplace em skfem é ∇u : ∇v para vetores, não é curl-curl.
        # Precisamos definir a forma bilinear customizada para Curl-Curl.
        
        @BilinearForm
        def curl_curl(E, v, w):
            return dot(curl(E), curl(v))
        
        @BilinearForm
        def mass_matrix(E, v, w):
            return dot(E, v)
        
        A = asm(curl_curl, self.basis)
        M = asm(mass_matrix, self.basis)
        
        # Matriz do sistema: A - k₀² M
        # Adicionando perdas complexas para simular radiação (ABC simples ou perda no meio)
        # Em domínio aberto sem PML real, precisamos de perda no material ou impedância na borda.
        # Vamos usar k complexo globalmente por enquanto como "meio com perdas" para absorver.
        # Melhor seria ABC na superfície externa: ∫ (n×∇×E)·v dS ...
        
        k_complex = self.k0 * (1 - 0.1j) # Perda fictícia para evitar ressonância infinita e simular radiação
        L = A - (k_complex**2) * M
        
        # Fonte
        # Precisamos identificar onde aplicar a fonte.
        # Em FDTD, aplicamos no gap do dipolo.
        # Aqui, precisamos encontrar a aresta correspondente ao gap.
        # Como não temos tags fáceis de arestas específicas do gap vindas do Gmsh (difícil mapear),
        # vamos usar uma fonte de corrente distribuída (J) no centro do domínio.
        
        if self.feed_point:
             center = np.array([self.feed_point.x, self.feed_point.y, self.feed_point.z])
        else:
             center = np.mean(self.mesh.p, axis=1) # Centro aproximado
        
        # v é vetor (v_x, v_y, v_z)
        # return -1j * self.omega * self.mu0 * Jz * v[2] 
        # Simplificando constantes para 1.0 por enquanto, ajustaremos magnitude depois
        
        # Ajusta sigma baseado no comprimento de onda
        wavelength = 299792458.0 / self.frequency
        sigma = wavelength / 10.0 # Fonte com tamanho ~λ/10
        
        @LinearForm
        def source_term(v, w):
            # Fonte de corrente J na direção Z, localizada no centro (ou feed_point)
            # J = J0 * delta(r) z_hat
            # Termo de fonte: -jωμ ∫ J·v dV
            # Aproximação gaussiana espacial
            x, y, z = w.x
            r2 = (x - center[0])**2 + (y - center[1])**2 + (z - center[2])**2
            Jz = np.exp(-r2 / sigma**2)
            
            return 1.0 * Jz * v[2]
            
        b = asm(source_term, self.basis)
        self.b_vec = b # Guarda para cálculo de potência
        
        # Condições de Contorno
        # PEC nos fios: E_tan = 0.
        # O Gmsh marcou "PEC_Wire" como curvas físicas?
        # Nédélec DOFs estão nas arestas. 
        # Precisamos encontrar DOFs nas arestas físicas marcadas como PEC.
        
        # Em skfem, boundary_dofs encontra dofs nas facetas de contorno do domínio.
        # Fios internos (Embed Curve) são mais complicados.
        # Se o fio é uma aresta da malha, podemos zerar seus DOFs.
        
        # Simplificação: Vamos resolver sem PEC explícito nos fios primeiro (fios "transparentes" com fonte),
        # ou confiar que a fonte domina.
        # Para dipolo real, precisamos zerar E tangencial no fio.
        
        # Vamos tentar encontrar DOFs próximos ao eixo Z (onde estaria o dipolo)
        # e zerar, exceto no gap.
        
        dofs = self.basis.get_dofs() # Todas as bordas externas
        # D = dofs['PEC_Wire'] if we had it mapped correctly via facets.
        
        # Solve
        self.x = solve(L, b)
        
        return self.x

    def calculate_impedance(self):
        """
        Calcula impedância de entrada aproximada.
        Z = V / I
        I = 1.0 (magnitude da fonte J)
        V = Integral de E.dl ao longo do gap.
        """
        if not hasattr(self, 'x'):
            self.solve()
            
        # Integra E_z no centro
        center = np.mean(self.mesh.p, axis=1)
        # Pequeno segmento no centro (gap)
        gap_length = 0.01 
        p1 = center - np.array([0, 0, gap_length/2])
        p2 = center + np.array([0, 0, gap_length/2])
        
        # Avalia E no centro
        # Probes espera arrays de pontos
        pts = np.array([center]).T
        E_at_center = (self.basis.probes(pts) @ self.x).flatten() # (3,)
        
        Ez = E_at_center[2]
        
        # V = - integral E.dl (aproximado por E_z * gap)
        # Na verdade, a fonte impôs J, então V é a reação do campo.
        # P = -1/2 * integral(E . J*) dV
        # Z = 2 * P / |I|^2
        
        # Potência complexa entregue pela fonte:
        # P_in = -0.5 * integral(E . J_src*) dV
        
        # Como J_src é gaussiana no centro, podemos integrar numericamente
        # ou usar a forma bilinear 'b' já montada?
        # b_i = integral(J . w_i)
        # P_in = -0.5 * sum(x_i * b_i*) ? Não exatamente, pois b é linear form.
        # P_in = -0.5 * (b . x) se b representasse J.
        # Na formulação: A x = b => b vem da fonte J.
        # b_i = <J, w_i>. x = sum x_j w_j.
        # <E, J> = <sum x_j w_j, J> = sum x_j <w_j, J> = sum x_j b_j = x . b
        
        # Então Potência = -0.5 * dot(x, b.conj()) ? 
        # Depende da convenção de sinal.
        # Maxwell: curl curl E - k^2 E = -j w mu J
        # Weak: <curl E, curl v> - k^2 <E, v> = -j w mu <J, v>
        # A x - k^2 M x = b_vec
        # onde b_vec_i = -j w mu <J, w_i>
        
        # Power supplied by source: P = 0.5 * integral(J* . E) dV
        # = 0.5 * integral(J* . sum x_i w_i)
        # = 0.5 * sum x_i <J*, w_i>
        # Temos b_i = -j w mu <J, w_i>.
        # Logo <J, w_i> = b_i / (-j w mu) = j b_i / (w mu)
        # <J*, w_i> = conj(j b_i / (w mu)) = -j conj(b_i) / (w mu)
        
        # P = 0.5 * sum x_i * (-j * conj(b_i) / (w mu))
        # P = -0.5j / (w mu) * dot(x, conj(b))
        
        # Z = 2 * P / |I0|^2. Assumindo I0 = 1 (magnitude integrada de J)
        
        term = np.dot(self.x, np.conjugate(self.b_vec))
        P = -0.5j / (self.omega * self.mu0) * term
        
        # Se I0 foi normalizado para 1 na definição de J
        # Na verdade Jz = exp(...) * C. Integral de Jz dx dy = I(z).
        # I0 no centro = integral exp(-r2/sigma^2) 2 pi r dr = ...
        # Integral gaussiana 2D: integral e^-(x^2+y^2)/s^2 dx dy = pi * s^2
        # Então I_total = pi * sigma^2 * AmplitudeJ
        # No código usamos AmplitudeJ = 1.0.
        # Então I0 = np.pi * (0.05)**2
        
        sigma = 0.05
        I0 = np.pi * (sigma**2)
        
        Z = 2 * P / (I0**2)
        return Z

    def get_fields_on_grid(self, nx=30, ny=30, nz=30):
        """
        Interpola solução para grid regular.
        """
        if not hasattr(self, 'x'):
            self.solve()

        bbox_min = np.min(self.mesh.p, axis=1)
        bbox_max = np.max(self.mesh.p, axis=1)
        
        xs = np.linspace(bbox_min[0], bbox_max[0], nx)
        ys = np.linspace(bbox_min[1], bbox_max[1], ny)
        zs = np.linspace(bbox_min[2], bbox_max[2], nz)
        
        grid_x, grid_y, grid_z = np.meshgrid(xs, ys, zs, indexing='ij')
        
        # Prepare points for probes: (3, N)
        pts = np.vstack([grid_x.ravel(), grid_y.ravel(), grid_z.ravel()])
        
        # Interpolate: (3, N)
        # Note: basis.probes returns matrix (3*N, N_dofs) for vector elements? 
        # Or (N_pts, N_dofs) per component?
        # Skfem docs: for vector elements, probes returns a matrix that multiplies coeffs to get vector values at pts.
        # Actually, for ElementTetN0 (vector), basis.probes(pts) returns an object that when multiplied by x gives the field values.
        # The return shape of (basis.probes(pts) @ x) is (dim, n_pts).
        
        interpolated = self.basis.probes(pts) @ self.x
        
        # Reshape to (3, nx, ny, nz)
        field_grid = interpolated.reshape(3, nx, ny, nz)
        
        # Calculate magnitude
        mag = np.sqrt(np.abs(field_grid[0])**2 + np.abs(field_grid[1])**2 + np.abs(field_grid[2])**2)
        
        return mag, field_grid
