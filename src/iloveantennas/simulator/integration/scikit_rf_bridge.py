import numpy as np

try:
    import skrf as rf
except ImportError:  # pragma: no cover - handled graciosamente em runtime
    rf = None


def impedance_result_to_network(
    frequencies_hz: np.ndarray,
    impedance_ohm: np.ndarray,
    z0: float = 50.0,
):
    """
    Converte um vetor de impedâncias Z(f) em um objeto Network do scikit-rf.
    """
    if rf is None:
        raise RuntimeError("scikit-rf não está disponível (módulo 'skrf' não pôde ser importado).")

    frequencies_hz = np.asarray(frequencies_hz, dtype=float)
    impedance_ohm = np.asarray(impedance_ohm, dtype=complex)

    if frequencies_hz.shape[0] != impedance_ohm.shape[0]:
        raise ValueError("frequencies_hz e impedance_ohm devem ter o mesmo tamanho.")

    f_ghz = frequencies_hz / 1e9

    gamma = (impedance_ohm - z0) / (impedance_ohm + z0 + 1e-30)

    s = gamma.reshape(-1, 1, 1)

    freq = rf.Frequency.from_f(f_ghz, unit="ghz")

    ntwk = rf.Network(frequency=freq, s=s, z0=[z0])
    return ntwk


def compute_vswrs_from_impedance(
    frequencies_hz: np.ndarray,
    impedance_ohm: np.ndarray,
    z0: float = 50.0,
):
    """
    Usa scikit-rf para calcular VSWR e S11(dB) com rotinas consolidadas.
    """
    ntwk = impedance_result_to_network(frequencies_hz, impedance_ohm, z0=z0)

    s11 = ntwk.s[:, 0, 0]

    mag = np.abs(s11)
    vswr = (1 + mag) / np.maximum(1 - mag, 1e-12)

    s11_db = 20.0 * np.log10(np.maximum(mag, 1e-12))

    return {
        "frequencies": frequencies_hz,
        "s11": s11,
        "s11_db": s11_db,
        "vswr": vswr,
        "z0": float(z0),
    }
