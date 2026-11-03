"""Fake backend for offline tests: no ROS, no CAN, no cameras.

Arms follow the last published joint target with a first-order lag and a speed
limit (roughly what the Piper MOVE J loop does at low speed); frames are black.
"""
import math
import threading
import time


class FakeBackend:
    def __init__(self, stack):
        self.stack, self.capability = stack, None

    def bind(self, capability):
        if self.capability is not None:
            raise RuntimeError("backend already bound")
        self.capability = capability

    def _check(self, capability):
        if capability is not self.capability or capability is None:
            raise PermissionError("gateway capability required")

    def ready(self):
        return True, []

    def enable(self, side, capability):
        self._check(capability)
        self.stack.enabled[side] = True

    def send(self, side, q, gripper, capability):
        self._check(capability)
        with self.stack.lock:
            self.stack.command[side] = list(q)
            self.stack.sends[side] += 1

    def send_gripper(self, side, width, capability):
        self._check(capability)
        with self.stack.lock:
            self.stack.grip_command[side] = width


class FakeStack:
    def __init__(self, session, model, shapes, *, initial=None, tau_s=0.12, max_speed_rad_s=1.5, rate_hz=180):
        self.session, self.model, self.shapes = session, model, shapes
        self.lock = threading.Lock()
        sides = list(session["arms"])
        start = initial or {s: [0.05, 0.1, -0.1, 0.0, 0.05, 0.0] for s in sides}
        self.q = {s: list(start[s]) for s in sides}
        self.gripper = {s: 0.03 for s in sides}
        self.command = {s: None for s in sides}
        self.grip_command = {s: None for s in sides}
        self.enabled = {s: False for s in sides}
        self.sends = {s: 0 for s in sides}
        self.tau, self.vmax, self.rate = tau_s, max_speed_rad_s, rate_hz
        self.backend = FakeBackend(self)
        self._stop = threading.Event()
        self._thread = None

    def start(self, gateway, frames, frame_lock):
        import numpy as np
        black = {r: np.zeros(shape, dtype=np.uint8) for r, shape in self.shapes.items()}

        def run():
            last = time.monotonic()
            next_frame = 0.0
            while not self._stop.is_set():
                now = time.monotonic()
                dt, last = now - last, now
                with self.lock:
                    for s in self.q:
                        if self.enabled[s] and self.command[s] is not None:
                            k = 1 - math.exp(-dt / self.tau)
                            step = self.vmax * dt
                            self.q[s] = [q + max(-step, min(step, (c - q) * k)) for q, c in zip(self.q[s], self.command[s])]
                        if self.grip_command[s] is not None:
                            self.gripper[s] += (self.grip_command[s] - self.gripper[s]) * (1 - math.exp(-dt / 0.2))
                    snapshot = {s: (list(v), self.gripper[s]) for s, v in self.q.items()}
                for s, (q, g) in snapshot.items():
                    gateway.feedback(s, q, g, time.monotonic_ns())
                if now >= next_frame:
                    with frame_lock:
                        for r, img in black.items():
                            frames[r] = (img, now)
                    next_frame = now + 1 / 30
                time.sleep(1 / self.rate)

        self._thread = threading.Thread(target=run, name="fake-piper", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(2)
