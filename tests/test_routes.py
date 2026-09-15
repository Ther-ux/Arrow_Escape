from itertools import combinations

import pytest

from data.levels import LEVELS
from ui.rope import distance, resample, smooth_curve
from ui.routes import plan_routes


@pytest.mark.parametrize("level", LEVELS, ids=lambda level: level.name)
def test_planned_resting_curves_have_clear_separate_lanes(level):
    cell = min(76, 440 // max(level.rows, level.cols))
    routes = plan_routes(level.arrows, level.rows, level.cols, cell, (0, 0))
    curves = [smooth_curve(resample(path)) for path in routes.values()]
    for a, b in combinations(curves, 2):
        # A gap well beyond the 9px glow stroke, including highlighted heads.
        assert min(distance(p, q) for p in a for q in b) > 15
    assert routes == plan_routes(level.arrows, level.rows, level.cols, cell, (0, 0))
