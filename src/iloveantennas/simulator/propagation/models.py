from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class PropagationEnvironment:
    frequency_hz: float
    distance_km: float
    tx_height_m: float
    rx_height_m: float
    city_size: str = "small_medium"
    area: str = "urban"
    system_loss_db: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PathLossResult:
    model: str
    path_loss_db: float
    valid: bool
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class LinkBudgetResult:
    path_loss: PathLossResult
    tx_power_dbm: float
    tx_gain_dbi: float
    rx_gain_dbi: float
    system_loss_db: float
    received_power_dbm: float
    margin_db: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _require_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def _log10(value: float) -> float:
    _require_positive("log input", value)
    return math.log10(value)


def free_space_path_loss_db(frequency_hz: float, distance_m: float) -> float:
    """Free-space path loss in dB for frequency in Hz and distance in meters."""

    _require_positive("frequency_hz", frequency_hz)
    _require_positive("distance_m", distance_m)
    frequency_mhz = frequency_hz / 1e6
    distance_km = distance_m / 1000.0
    return 32.44 + 20.0 * _log10(frequency_mhz) + 20.0 * _log10(distance_km)


def mobile_antenna_correction_db(
    frequency_mhz: float,
    rx_height_m: float,
    city_size: str = "small_medium",
) -> float:
    city = city_size.lower().replace("-", "_")
    if city in {"large", "metropolitan"}:
        if frequency_mhz <= 300.0:
            return 8.29 * (_log10(1.54 * rx_height_m) ** 2) - 1.1
        return 3.2 * (_log10(11.75 * rx_height_m) ** 2) - 4.97

    log_f = _log10(frequency_mhz)
    return (1.1 * log_f - 0.7) * rx_height_m - (1.56 * log_f - 0.8)


def okumura_hata_path_loss_db(
    frequency_hz: float,
    distance_km: float,
    tx_height_m: float,
    rx_height_m: float,
    city_size: str = "small_medium",
    area: str = "urban",
) -> PathLossResult:
    """Okumura-Hata path loss for macro-cell ranges."""

    _require_positive("frequency_hz", frequency_hz)
    _require_positive("distance_km", distance_km)
    _require_positive("tx_height_m", tx_height_m)
    _require_positive("rx_height_m", rx_height_m)

    frequency_mhz = frequency_hz / 1e6
    warnings = _okumura_hata_warnings(frequency_mhz, distance_km, tx_height_m, rx_height_m)

    log_f = _log10(frequency_mhz)
    log_hb = _log10(tx_height_m)
    log_d = _log10(distance_km)
    correction = mobile_antenna_correction_db(frequency_mhz, rx_height_m, city_size)

    urban = (
        69.55
        + 26.16 * log_f
        - 13.82 * log_hb
        - correction
        + (44.9 - 6.55 * log_hb) * log_d
    )

    area_key = area.lower().replace("-", "_")
    if area_key == "suburban":
        loss = urban - 2.0 * (_log10(frequency_mhz / 28.0) ** 2) - 5.4
    elif area_key in {"open", "rural"}:
        loss = urban - 4.78 * (log_f**2) + 18.33 * log_f - 40.94
    else:
        loss = urban

    return PathLossResult(
        model="okumura_hata",
        path_loss_db=loss,
        valid=not warnings,
        warnings=warnings,
    )


def cost231_hata_path_loss_db(
    frequency_hz: float,
    distance_km: float,
    tx_height_m: float,
    rx_height_m: float,
    city_size: str = "small_medium",
    metropolitan: bool = False,
) -> PathLossResult:
    _require_positive("frequency_hz", frequency_hz)
    _require_positive("distance_km", distance_km)
    _require_positive("tx_height_m", tx_height_m)
    _require_positive("rx_height_m", rx_height_m)

    frequency_mhz = frequency_hz / 1e6
    warnings = _cost231_warnings(frequency_mhz, distance_km, tx_height_m, rx_height_m)
    correction = mobile_antenna_correction_db(frequency_mhz, rx_height_m, city_size)
    city_constant = 3.0 if metropolitan else 0.0

    loss = (
        46.3
        + 33.9 * _log10(frequency_mhz)
        - 13.82 * _log10(tx_height_m)
        - correction
        + (44.9 - 6.55 * _log10(tx_height_m)) * _log10(distance_km)
        + city_constant
    )
    return PathLossResult(
        model="cost231_hata",
        path_loss_db=loss,
        valid=not warnings,
        warnings=warnings,
    )


def friis_received_power_dbm(
    tx_power_dbm: float,
    tx_gain_dbi: float,
    rx_gain_dbi: float,
    path_loss_db: float,
    system_loss_db: float = 0.0,
) -> float:
    return tx_power_dbm + tx_gain_dbi + rx_gain_dbi - path_loss_db - system_loss_db


def link_budget(
    path_loss: PathLossResult,
    tx_power_dbm: float,
    tx_gain_dbi: float = 0.0,
    rx_gain_dbi: float = 0.0,
    system_loss_db: float = 0.0,
    receiver_sensitivity_dbm: float | None = None,
) -> LinkBudgetResult:
    received = friis_received_power_dbm(
        tx_power_dbm,
        tx_gain_dbi,
        rx_gain_dbi,
        path_loss.path_loss_db,
        system_loss_db,
    )
    margin = None
    if receiver_sensitivity_dbm is not None:
        margin = received - receiver_sensitivity_dbm

    return LinkBudgetResult(
        path_loss=path_loss,
        tx_power_dbm=tx_power_dbm,
        tx_gain_dbi=tx_gain_dbi,
        rx_gain_dbi=rx_gain_dbi,
        system_loss_db=system_loss_db,
        received_power_dbm=received,
        margin_db=margin,
    )


def compare_path_loss(
    environment: PropagationEnvironment,
    tx_power_dbm: float = 30.0,
    tx_gain_dbi: float = 0.0,
    rx_gain_dbi: float = 0.0,
    receiver_sensitivity_dbm: float | None = None,
) -> dict:
    fspl = PathLossResult(
        model="free_space",
        path_loss_db=free_space_path_loss_db(
            environment.frequency_hz,
            environment.distance_km * 1000.0,
        ),
        valid=True,
    )
    okumura = okumura_hata_path_loss_db(
        environment.frequency_hz,
        environment.distance_km,
        environment.tx_height_m,
        environment.rx_height_m,
        environment.city_size,
        environment.area,
    )
    cost231 = cost231_hata_path_loss_db(
        environment.frequency_hz,
        environment.distance_km,
        environment.tx_height_m,
        environment.rx_height_m,
        environment.city_size,
        metropolitan=environment.area.lower() in {"metropolitan", "dense_urban"},
    )

    selected = okumura if okumura.valid else cost231 if cost231.valid else fspl

    return {
        "environment": environment.to_dict(),
        "models": {
            "free_space": fspl.to_dict(),
            "okumura_hata": okumura.to_dict(),
            "cost231_hata": cost231.to_dict(),
        },
        "selected_model": selected.model,
        "link_budget": link_budget(
            selected,
            tx_power_dbm=tx_power_dbm,
            tx_gain_dbi=tx_gain_dbi,
            rx_gain_dbi=rx_gain_dbi,
            system_loss_db=environment.system_loss_db,
            receiver_sensitivity_dbm=receiver_sensitivity_dbm,
        ).to_dict(),
    }


def _okumura_hata_warnings(
    frequency_mhz: float,
    distance_km: float,
    tx_height_m: float,
    rx_height_m: float,
) -> list[str]:
    warnings = []
    if not 150.0 <= frequency_mhz <= 1500.0:
        warnings.append("Okumura-Hata is calibrated for 150 MHz to 1500 MHz.")
    if not 1.0 <= distance_km <= 20.0:
        warnings.append("Okumura-Hata is calibrated for 1 km to 20 km paths.")
    if not 30.0 <= tx_height_m <= 200.0:
        warnings.append("Okumura-Hata base antenna height range is 30 m to 200 m.")
    if not 1.0 <= rx_height_m <= 10.0:
        warnings.append("Okumura-Hata mobile antenna height range is 1 m to 10 m.")
    return warnings


def _cost231_warnings(
    frequency_mhz: float,
    distance_km: float,
    tx_height_m: float,
    rx_height_m: float,
) -> list[str]:
    warnings = []
    if not 1500.0 <= frequency_mhz <= 2000.0:
        warnings.append("COST-231 Hata is calibrated for 1500 MHz to 2000 MHz.")
    if not 1.0 <= distance_km <= 20.0:
        warnings.append("COST-231 Hata is calibrated for 1 km to 20 km paths.")
    if not 30.0 <= tx_height_m <= 200.0:
        warnings.append("COST-231 Hata base antenna height range is 30 m to 200 m.")
    if not 1.0 <= rx_height_m <= 10.0:
        warnings.append("COST-231 Hata mobile antenna height range is 1 m to 10 m.")
    return warnings
