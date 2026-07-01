import threading

from iloveantennas.web.optimizer import AntennaOptimizer
from iloveantennas.web.state import optimization_lock, optimizations


def run_optimization_task(opt_id: str, params: dict):
    """Executa tarefa de otimização"""
    optimizer = AntennaOptimizer()

    def callback(info):
        with optimization_lock:
            if opt_id in optimizations:
                optimizations[opt_id].update(info)

    with optimization_lock:
        if opt_id in optimizations:
            optimizations[opt_id]["optimizer"] = optimizer

    try:
        target_freq = params.get("target_freq", params.get("frequency", 300e6))
        start_length = params.get("start_length", params.get("length"))
        result = optimizer.optimize_length(
            antenna_type=params.get("antenna_type", params.get("type", "dipole")),
            target_freq=float(target_freq),
            start_length=float(start_length) if start_length else None,
            radius=float(params.get("radius", 0.001)),
            target_vswr=float(params.get("target_vswr", 1.5)),
            max_iter=int(params.get("max_iter", 5)),
            callback=callback,
        )

        with optimization_lock:
            if opt_id in optimizations:
                optimizations[opt_id]["status"] = "completed"
                optimizations[opt_id]["result"] = {
                    "success": result.success,
                    "final_length": result.final_length,
                    "final_vswr": result.final_vswr,
                    "final_resonance": result.final_resonance,
                    "history": result.history,
                    "message": result.message,
                }
    except Exception as e:
        with optimization_lock:
            if opt_id in optimizations:
                optimizations[opt_id]["status"] = "error"
                optimizations[opt_id]["error"] = str(e)
