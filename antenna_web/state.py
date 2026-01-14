import threading
from typing import Dict

# Armazenamento de simulações em andamento
simulations: Dict[str, dict] = {}
simulation_lock = threading.Lock()

# Armazenamento de otimizações
optimizations: Dict[str, dict] = {}
optimization_lock = threading.Lock()
