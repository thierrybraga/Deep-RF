import math

from iloveantennas.simulator.propagation import (
    Point2D,
    Segment2D,
    free_space_path_loss_db,
    okumura_hata_path_loss_db,
    trace_2d_rays,
)


def test_free_space_path_loss_reference_value():
    loss = free_space_path_loss_db(900e6, 1000.0)

    assert math.isclose(loss, 91.52, abs_tol=0.05)


def test_okumura_hata_urban_reference_range():
    result = okumura_hata_path_loss_db(
        frequency_hz=900e6,
        distance_km=2.0,
        tx_height_m=30.0,
        rx_height_m=1.5,
        city_size="small_medium",
        area="urban",
    )

    assert result.valid
    assert 125.0 <= result.path_loss_db <= 140.0


def test_ray_tracing_returns_direct_and_reflected_paths():
    paths = trace_2d_rays(
        tx=Point2D(2.0, 0.0),
        rx=Point2D(8.0, 0.0),
        obstacles=[Segment2D(Point2D(0.0, 5.0), Point2D(10.0, 5.0))],
        frequency_hz=900e6,
        max_reflections=1,
    )

    assert len(paths) == 2
    assert paths[0].reflection_count == 0
    assert paths[1].reflection_count == 1
    assert paths[1].path_loss_db > paths[0].path_loss_db
