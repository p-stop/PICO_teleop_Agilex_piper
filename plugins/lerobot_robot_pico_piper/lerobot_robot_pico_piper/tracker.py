"""Second-order joint tracker (interpolation design (b)).

Per cycle: v_des = clip((q_tgt - q_cmd) / T, +-v_max); v += clip(v_des - v, +-a_max*dt); q_cmd += v*dt.
Pure Python so it can be unit-tested and reused by the offline dry run.
"""
import math


class JointTracker:
    def __init__(self, n, *, time_constant_s=0.08, max_velocity_rad_s=0.8, max_acceleration_rad_s2=4.0):
        if not (time_constant_s > 0 and max_velocity_rad_s > 0 and max_acceleration_rad_s2 > 0):
            raise ValueError('tracker parameters must be positive')
        self.n, self.T, self.vmax, self.amax = n, float(time_constant_s), float(max_velocity_rad_s), float(max_acceleration_rad_s2)
        self.q = None
        self.v = [0.0] * n
        self.target = None

    def reset(self, q):
        if len(q) != self.n or not all(math.isfinite(x) for x in q):
            raise ValueError('invalid tracker state')
        self.q = [float(x) for x in q]
        self.v = [0.0] * self.n
        self.target = list(self.q)

    def set_target(self, q):
        if self.q is None:
            raise RuntimeError('tracker not initialised')
        if len(q) != self.n or not all(math.isfinite(x) for x in q):
            raise ValueError('invalid tracker target')
        self.target = [float(x) for x in q]

    def step(self, dt):
        if self.q is None:
            raise RuntimeError('tracker not initialised')
        dt = max(0.0, min(float(dt), 0.05))
        dv = self.amax * dt
        for i in range(self.n):
            v_des = max(-self.vmax, min(self.vmax, (self.target[i] - self.q[i]) / self.T))
            self.v[i] += max(-dv, min(dv, v_des - self.v[i]))
            self.q[i] += self.v[i] * dt
        return tuple(self.q)

    def error(self):
        return max(abs(a - b) for a, b in zip(self.target, self.q)) if self.q is not None else float('inf')

    def speed(self):
        return max(abs(v) for v in self.v)


def smoothstep(a, b, s):
    s = max(0.0, min(1.0, s))
    w = s * s * (3 - 2 * s)
    return tuple(x + (y - x) * w for x, y in zip(a, b))
