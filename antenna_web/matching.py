import math
from dataclasses import dataclass
from typing import Literal

from core.constants import C0


NetworkType = Literal["L", "Pi", "T", "Stub"]


@dataclass
class ReactiveComponent:
    role: str
    kind: Literal["L", "C"]
    value: float
    unit: Literal["H", "F"]


@dataclass
class StubResult:
    short_lambda: float | None
    open_lambda: float | None


@dataclass
class MatchingResult:
    network_type: NetworkType
    topology: str
    components: list[ReactiveComponent]
    stub: StubResult | None
    q_used: float | None
    notes: list[str]


def _format_stub_from_shunt_capacitor(z0: float, f: float, c_shunt: float) -> StubResult:
    if c_shunt <= 0:
        return StubResult(short_lambda=None, open_lambda=None)
    w = 2 * math.pi * f
    x_cap = -1.0 / (w * c_shunt)
    b_target = -1.0 / x_cap
    wavelength = C0 / f
    beta = 2.0 * math.pi / wavelength
    zc = z0
    short_lambda = None
    open_lambda = None
    arg_short = zc * b_target
    ang_short = math.atan(arg_short)
    if not math.isnan(ang_short):
        l = ang_short / beta
        if l < 0:
            l += wavelength / 2.0
        short_lambda = l / wavelength
    denom = zc * b_target
    if abs(denom) > 1e-12:
        arg_open = -1.0 / denom
        ang_open = math.atan(arg_open)
        if not math.isnan(ang_open):
            l = ang_open / beta
            if l < 0:
                l += wavelength / 2.0
            open_lambda = l / wavelength
    return StubResult(short_lambda=short_lambda, open_lambda=open_lambda)


def calculate_l_match(z_load: complex, z0: float, f: float) -> MatchingResult:
    r = z_load.real
    x = z_load.imag
    w = 2 * math.pi * f
    series_comp: ReactiveComponent | None = None
    shunt_comp: ReactiveComponent | None = None
    stub = StubResult(short_lambda=None, open_lambda=None)
    topology = ""
    notes: list[str] = []
    if r <= 0:
        notes.append("Resistência de carga não positiva; casamento L não é possível.")
        return MatchingResult(
            network_type="L",
            topology="indefinido",
            components=[],
            stub=stub,
            q_used=None,
            notes=notes,
        )
    if r < z0:
        q = math.sqrt((z0 / r) - 1.0)
        xs = q * r - x
        xp_cap = -z0 / q
        if xs > 0:
            series_comp = ReactiveComponent(
                role="series",
                kind="L",
                value=xs / w,
                unit="H",
            )
        else:
            series_comp = ReactiveComponent(
                role="series",
                kind="C",
                value=-1.0 / (w * xs),
                unit="F",
            )
        c_shunt = -1.0 / (w * xp_cap)
        shunt_comp = ReactiveComponent(
            role="shunt_source",
            kind="C",
            value=c_shunt,
            unit="F",
        )
        stub = _format_stub_from_shunt_capacitor(z0, f, c_shunt)
        topology = "Shunt na fonte, série na carga (step-up)"
    else:
        g_load = r / (r * r + x * x)
        b_load = -x / (r * r + x * x)
        if g_load > 1.0 / z0:
            notes.append("Topologia L escolhida não é adequada para esta impedância.")
            return MatchingResult(
                network_type="L",
                topology="indefinido",
                components=[],
                stub=stub,
                q_used=None,
                notes=notes,
            )
        term = g_load / z0 - g_load * g_load
        if term < 0:
            notes.append("Impedância fora da região de casamento L para esta topologia.")
            return MatchingResult(
                network_type="L",
                topology="indefinido",
                components=[],
                stub=stub,
                q_used=None,
                notes=notes,
            )
        b_total = math.sqrt(term)
        b_shunt_val = b_total - b_load
        x_series_val = z0 * b_total / g_load
        if b_shunt_val > 0:
            shunt_comp = ReactiveComponent(
                role="shunt_load",
                kind="C",
                value=b_shunt_val / w,
                unit="F",
            )
        else:
            shunt_comp = ReactiveComponent(
                role="shunt_load",
                kind="L",
                value=-1.0 / (w * b_shunt_val),
                unit="H",
            )
        if x_series_val > 0:
            series_comp = ReactiveComponent(
                role="series",
                kind="L",
                value=x_series_val / w,
                unit="H",
            )
        else:
            series_comp = ReactiveComponent(
                role="series",
                kind="C",
                value=-1.0 / (w * x_series_val),
                unit="F",
            )
        topology = "Shunt na carga, série na fonte (step-down)"
    components = []
    if series_comp is not None:
        components.append(series_comp)
    if shunt_comp is not None:
        components.append(shunt_comp)
    return MatchingResult(
        network_type="L",
        topology=topology,
        components=components,
        stub=stub,
        q_used=None,
        notes=notes,
    )


def _virtual_resistor_and_q(z0: float, z_load: complex, q_target: float | None) -> tuple[float, float, float]:
    rs = z0
    rl = max(z_load.real, 1e-6)
    r_low = min(rs, rl)
    r_high = max(rs, rl)
    min_q = math.sqrt(max(r_high / r_low - 1.0, 0.0))
    if q_target is None or q_target < min_q:
        q_used = min_q
    else:
        q_used = q_target
    if q_used <= 0:
        q_used = min_q if min_q > 0 else 1.0
    r_int = r_high / (q_used * q_used + 1.0)
    return r_int, q_used, min_q


def _l_section_from_resistors(r_series_side: float, r_shunt_side: float, q_section: float, f: float) -> tuple[float, float]:
    w = 2 * math.pi * f
    if r_shunt_side <= 0 or q_section <= 0:
        return 0.0, 0.0
    b_shunt = q_section / r_shunt_side
    x_series = q_section * r_shunt_side / (1.0 + q_section * q_section)
    c_shunt = b_shunt / w
    l_series = x_series / w
    return l_series, c_shunt


def synthesize_pi_network(z0: float, z_load: complex, f: float, q_target: float | None) -> MatchingResult:
    notes: list[str] = []
    if z_load.real <= 0:
        notes.append("Resistência de carga não positiva; rede Pi não é aplicável.")
        return MatchingResult(
            network_type="Pi",
            topology="indefinido",
            components=[],
            stub=None,
            q_used=None,
            notes=notes,
        )
    r_int, q_used, min_q = _virtual_resistor_and_q(z0, z_load, q_target)
    if q_target is not None and q_target < min_q:
        notes.append(f"Q alvo menor que o mínimo; usando Q={q_used:.3f}.")
    rs = z0
    rl = z_load.real
    r_high = max(rs, rl)
    r_low = min(rs, rl)
    q_high = q_used
    q_low = r_low / r_int - 1.0 if r_int > 0 else 0.0
    if q_low <= 0:
        q_low = q_high
        notes.append("Q da seção de baixa resistência ajustado para Q da seção de alta resistência.")
    l_series_high, c_shunt_high = _l_section_from_resistors(r_int, r_high, q_high, f)
    l_series_low, c_shunt_low = _l_section_from_resistors(r_int, r_low, q_low, f)
    w = 2 * math.pi * f
    x_series_total = w * (l_series_high + l_series_low)
    l_series_total = x_series_total / w
    components: list[ReactiveComponent] = []
    if rs == r_high:
        components.append(
            ReactiveComponent(
                role="shunt_source",
                kind="C",
                value=c_shunt_high,
                unit="F",
            )
        )
        components.append(
            ReactiveComponent(
                role="series_center",
                kind="L",
                value=l_series_total,
                unit="H",
            )
        )
        components.append(
            ReactiveComponent(
                role="shunt_load",
                kind="C",
                value=c_shunt_low,
                unit="F",
            )
        )
    else:
        components.append(
            ReactiveComponent(
                role="shunt_source",
                kind="C",
                value=c_shunt_low,
                unit="F",
            )
        )
        components.append(
            ReactiveComponent(
                role="series_center",
                kind="L",
                value=l_series_total,
                unit="H",
            )
        )
        components.append(
            ReactiveComponent(
                role="shunt_load",
                kind="C",
                value=c_shunt_high,
                unit="F",
            )
        )
    topology = "Pi de baixa passagem com resistor virtual"
    return MatchingResult(
        network_type="Pi",
        topology=topology,
        components=components,
        stub=None,
        q_used=q_used,
        notes=notes,
    )


def synthesize_t_network(z0: float, z_load: complex, f: float, q_target: float | None) -> MatchingResult:
    notes: list[str] = []
    if z_load.real <= 0:
        notes.append("Resistência de carga não positiva; rede T não é aplicável.")
        return MatchingResult(
            network_type="T",
            topology="indefinido",
            components=[],
            stub=None,
            q_used=None,
            notes=notes,
        )
    r_int, q_used, min_q = _virtual_resistor_and_q(z0, z_load, q_target)
    if q_target is not None and q_target < min_q:
        notes.append(f"Q alvo menor que o mínimo; usando Q={q_used:.3f}.")
    rs = z0
    rl = z_load.real
    r_high = max(rs, rl)
    r_low = min(rs, rl)
    q_high = q_used
    q_low = r_low / r_int - 1.0 if r_int > 0 else 0.0
    if q_low <= 0:
        q_low = q_high
        notes.append("Q da seção de baixa resistência ajustado para Q da seção de alta resistência.")
    w = 2 * math.pi * f
    l_series_high, c_shunt_high = _l_section_from_resistors(r_int, r_high, q_high, f)
    l_series_low, c_shunt_low = _l_section_from_resistors(r_int, r_low, q_low, f)
    b_center = 0.0
    if c_shunt_high > 0:
        b_center += w * c_shunt_high
    if c_shunt_low > 0:
        b_center += w * c_shunt_low
    c_center = b_center / w if b_center > 0 else 0.0
    components: list[ReactiveComponent] = []
    if rs == r_high:
        components.append(
            ReactiveComponent(
                role="series_source",
                kind="L",
                value=l_series_high,
                unit="H",
            )
        )
        components.append(
            ReactiveComponent(
                role="shunt_center",
                kind="C",
                value=c_center,
                unit="F",
            )
        )
        components.append(
            ReactiveComponent(
                role="series_load",
                kind="L",
                value=l_series_low,
                unit="H",
            )
        )
    else:
        components.append(
            ReactiveComponent(
                role="series_source",
                kind="L",
                value=l_series_low,
                unit="H",
            )
        )
        components.append(
            ReactiveComponent(
                role="shunt_center",
                kind="C",
                value=c_center,
                unit="F",
            )
        )
        components.append(
            ReactiveComponent(
                role="series_load",
                kind="L",
                value=l_series_high,
                unit="H",
            )
        )
    topology = "T de baixa passagem com resistor virtual"
    return MatchingResult(
        network_type="T",
        topology=topology,
        components=components,
        stub=None,
        q_used=q_used,
        notes=notes,
    )


def calculate_matching(z_load: complex, z0: float, f: float, network_type: NetworkType, q: float | None) -> MatchingResult:
    if network_type == "L":
        return calculate_l_match(z_load, z0, f)
    if network_type == "Pi":
        return synthesize_pi_network(z0, z_load, f, q)
    if network_type == "T":
        return synthesize_t_network(z0, z_load, f, q)
    if network_type == "Stub":
        base = calculate_l_match(z_load, z0, f)
        return MatchingResult(
            network_type="Stub",
            topology=base.topology,
            components=base.components,
            stub=base.stub,
            q_used=base.q_used,
            notes=base.notes,
        )
    return calculate_l_match(z_load, z0, f)

