import math

from lerobot_robot_pico_piper.tracker import JointTracker, smoothstep


def run(trk, steps, dt):
    qs = []
    for _ in range(steps):
        qs.append(trk.step(dt))
    return qs


def test_step_respects_velocity_and_acceleration_limits():
    dt = 1 / 60
    trk = JointTracker(6, time_constant_s=0.08, max_velocity_rad_s=0.8, max_acceleration_rad_s2=4.0)
    trk.reset([0.0] * 6)
    trk.set_target([1.0, -1.0, 0.5, 0, 0, 0])
    qs = run(trk, 400, dt)
    v = [(b[i] - a[i]) / dt for a, b in zip(qs, qs[1:]) for i in range(6)]
    assert max(abs(x) for x in v) <= 0.8 + 1e-9
    vel = [[(b[i] - a[i]) / dt for i in range(6)] for a, b in zip(qs, qs[1:])]
    acc = [(b[i] - a[i]) / dt for a, b in zip(vel, vel[1:]) for i in range(6)]
    assert max(abs(x) for x in acc) <= 4.0 + 1e-6
    assert abs(qs[-1][0] - 1.0) < 1e-3 and abs(qs[-1][1] + 1.0) < 1e-3


def test_jitter_is_attenuated():
    dt = 1 / 60
    trk = JointTracker(1)
    trk.reset([0.0])
    out = []
    for k in range(600):
        trk.set_target([0.03 * (1 if (k // 2) % 2 else -1)])  # 15 Hz +-30 mrad chatter
        out.append(trk.step(dt)[0])
    tail = out[300:]
    assert max(tail) - min(tail) < 0.02


def test_smoothstep_endpoints():
    assert smoothstep((0, 1), (1, 3), 0) == (0, 1)
    assert smoothstep((0, 1), (1, 3), 1) == (1, 3)
    assert smoothstep((0, 1), (1, 3), 2) == (1, 3)


def test_rejects_nonfinite():
    trk = JointTracker(2)
    trk.reset([0, 0])
    try:
        trk.set_target([math.nan, 0])
    except ValueError:
        return
    raise AssertionError("nan accepted")
