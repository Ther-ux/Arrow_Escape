import math

import pytest

from ui.rope import Rope, distance, nearest_on_path, resample, smooth_curve


def test_head_is_pinned_and_tail_is_not_translated_as_a_rigid_body():
    rope = Rope([(0, 0), (-80, 0), (-80, 80)])
    original = list(rope.positions)
    rope.advance(1 / 60, lambda t: (600 * t, 0))
    assert rope.positions[0] == pytest.approx((10, 0))
    assert distance(rope.positions[-1], original[-1]) < 3
    assert distance(rope.positions[1], original[1]) > distance(rope.positions[-1], original[-1])


def test_turning_head_produces_a_bent_following_tail():
    rope = Rope([(0, 0), (-160, 0)])

    def head(t):
        return (min(t, 0.5) * 160, max(0, t - 0.5) * 160)

    rope.advance(0.9, head)
    assert rope.positions[0] == pytest.approx((80, 64))
    # At least one internal node deviates from the straight head–tail chord.
    start, end = rope.positions[0], rope.positions[-1]
    deviation = [abs((end[0] - start[0]) * (p[1] - start[1])
                     - (end[1] - start[1]) * (p[0] - start[0])) / distance(start, end)
                 for p in rope.positions[1:-1]]
    assert max(deviation) > 10


def test_distance_constraints_limit_stretch_and_damping_settles_recoil():
    rope = Rope([(0, 0), (-80, 0), (-80, 80)])
    head = lambda t: (min(t, 0.5) * 240, 0)
    rope.advance(0.5, head)
    errors = [abs(distance(a, b) / rest - 1)
              for a, b, rest in zip(rope.positions, rope.positions[1:], rope.lengths)]
    assert max(errors) < 0.08
    after_stop = list(rope.positions)
    rope.advance(0.1, head)
    assert distance(after_stop[-1], rope.positions[-1]) > 0.1
    rope.advance(3.0, head)
    previous = list(rope.positions)
    rope.advance(0.1, head)
    assert max(distance(a, b) for a, b in zip(previous, rope.positions)) < 1


def test_fixed_substeps_are_consistent_at_30_and_144_fps():
    slow = Rope([(0, 0), (-90, 0), (-90, 50)])
    fast = Rope([(0, 0), (-90, 0), (-90, 50)])
    head = lambda t: (100 * t, 30 * math.sin(t * 5))
    for _ in range(30):
        slow.advance(1 / 30, head)
    for _ in range(144):
        fast.advance(1 / 144, head)
    for a, b in zip(slow.positions, fast.positions):
        assert a == pytest.approx(b, abs=1e-7)


def test_controlled_follow_stays_in_history_corridor_without_whipping():
    rope = Rope([(0, 0), (-100, 0), (-100, 100)])
    for _ in range(60):
        rope.advance(1 / 60, lambda t: (180 * t, 40 * math.sin(t * 3)))
        assert max(distance(p, nearest_on_path(p, rope.trail))
                   for p in rope.positions[1:]) <= 4.000001


def test_resampling_and_curve_preserve_endpoints_and_smooth_tangent():
    nodes = resample([(0, 0), (50, 0), (50, 50)])
    assert nodes[0] == (0, 0) and nodes[-1] == (50, 50)
    curve = smooth_curve(nodes, samples=100)
    assert curve[0] == nodes[0] and curve[-1] == nodes[-1]
    # C1 continuity at the bend: adjacent sample tangents are nearly parallel.
    index = 5 * 100
    incoming = (curve[index][0] - curve[index - 1][0], curve[index][1] - curve[index - 1][1])
    outgoing = (curve[index + 1][0] - curve[index][0], curve[index + 1][1] - curve[index][1])
    cosine = sum(a * b for a, b in zip(incoming, outgoing)) / (math.hypot(*incoming) * math.hypot(*outgoing))
    assert cosine > 0.999


@pytest.mark.parametrize("dt", [-1, float("inf"), float("nan")])
def test_invalid_time_is_rejected(dt):
    with pytest.raises(ValueError):
        Rope([(0, 0), (-50, 0)]).advance(dt, lambda t: (t, 0))
