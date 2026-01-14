"""
Kernels otimizados para o solver FDTD (Numba).
"""

try:
    from numba import jit, prange
except ImportError:
    # Decorator dummy para evitar erros de sintaxe se Numba não existir
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    # Prange vira range normal
    prange = range

@jit(nopython=True, parallel=True, fastmath=True, cache=True)
def update_h_kernel(Hx, Hy, Hz, Ex, Ey, Ez, 
                   Da_x, Db_x, Da_y, Db_y, Da_z, Db_z,
                   dx, dy, dz):
    """Kernel otimizado para atualização do campo H"""
    
    # Extrai dimensões
    nx, ny, nz = Hx.shape
    
    # Hx update
    for i in prange(nx):
        for j in range(ny - 1):
            for k in range(nz - 1):
                curl_e = (Ez[i, j+1, k] - Ez[i, j, k]) / dy - \
                        (Ey[i, j, k+1] - Ey[i, j, k]) / dz
                Hx[i, j, k] = Da_x[i, j, k] * Hx[i, j, k] - Db_x[i, j, k] * curl_e

    # Hy update
    for i in prange(nx - 1):
        for j in range(ny):
            for k in range(nz - 1):
                curl_e = (Ex[i, j, k+1] - Ex[i, j, k]) / dz - \
                        (Ez[i+1, j, k] - Ez[i, j, k]) / dx
                Hy[i, j, k] = Da_y[i, j, k] * Hy[i, j, k] - Db_y[i, j, k] * curl_e

    # Hz update
    for i in prange(nx - 1):
        for j in range(ny - 1):
            for k in range(nz):
                curl_e = (Ey[i+1, j, k] - Ey[i, j, k]) / dx - \
                        (Ex[i, j+1, k] - Ex[i, j, k]) / dy
                Hz[i, j, k] = Da_z[i, j, k] * Hz[i, j, k] - Db_z[i, j, k] * curl_e

@jit(nopython=True, parallel=True, fastmath=True, cache=True)
def update_e_kernel(Ex, Ey, Ez, Hx, Hy, Hz,
                   Ca_x, Cb_x, Ca_y, Cb_y, Ca_z, Cb_z,
                   dx, dy, dz):
    """Kernel otimizado para atualização do campo E"""
    
    # Extrai dimensões (assumindo grade Yee)
    nx, ny, nz = Ex.shape
    
    # Ex update
    for i in prange(nx):
        for j in range(1, ny - 1):
            for k in range(1, nz - 1):
                curl_h = (Hz[i, j, k] - Hz[i, j-1, k]) / dy - \
                        (Hy[i, j, k] - Hy[i, j, k-1]) / dz
                Ex[i, j, k] = Ca_x[i, j, k] * Ex[i, j, k] + Cb_x[i, j, k] * curl_h

    # Ey update
    for i in prange(1, nx - 1):
        for j in range(ny):
            for k in range(1, nz - 1):
                curl_h = (Hx[i, j, k] - Hx[i, j, k-1]) / dz - \
                        (Hz[i, j, k] - Hz[i-1, j, k]) / dx
                Ey[i, j, k] = Ca_y[i, j, k] * Ey[i, j, k] + Cb_y[i, j, k] * curl_h

    # Ez update
    for i in prange(1, nx - 1):
        for j in range(1, ny - 1):
            for k in range(nz):
                curl_h = (Hy[i, j, k] - Hy[i-1, j, k]) / dx - \
                        (Hx[i, j, k] - Hx[i, j-1, k]) / dy
                Ez[i, j, k] = Ca_z[i, j, k] * Ez[i, j, k] + Cb_z[i, j, k] * curl_h
