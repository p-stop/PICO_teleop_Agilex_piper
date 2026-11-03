"""Fake feedback for offline tests: no ROS, no CAN, no cameras.

Simulated arms follow this teleop's own captured targets with a first-order lag and a
speed limit; camera previews are gray frames pushed through the real CameraIngress.
"""
import math
import threading
import time
from types import SimpleNamespace


class FakeFeedback:
    def __init__(self, session, capture, *, tau_s=0.12, max_speed_rad_s=1.5, rate_hz=180, frame_hz=30):
        self.session, self.capture = session, capture
        self.q = {s: list(arm["home_rad"]) for s, arm in session["arms"].items()}
        self.gripper = {s: 0.03 for s in session["arms"]}
        self.tau, self.vmax, self.rate, self.frame_hz = tau_s, max_speed_rad_s, rate_hz, frame_hz
        self._stop = threading.Event()
        self._threads = []

    def start(self, gateway, ingress=None):
        def arms():
            last = time.monotonic()
            while not self._stop.is_set():
                now = time.monotonic()
                dt, last = now - last, now
                with self.capture.lock:
                    targets, widths = dict(self.capture.q), dict(self.capture.grip)
                k = 1 - math.exp(-dt / self.tau)
                step = self.vmax * dt
                for s in self.q:
                    if s in targets:
                        self.q[s] = [q + max(-step, min(step, (c - q) * k)) for q, c in zip(self.q[s], targets[s])]
                    if s in widths:
                        self.gripper[s] += (widths[s] - self.gripper[s]) * (1 - math.exp(-dt / 0.2))
                    gateway.feedback(s, list(self.q[s]), self.gripper[s], time.monotonic_ns())
                time.sleep(1 / self.rate)

        def cameras():
            frames = {}
            for role, p in ingress.pipeline.items():
                w, h = p["capture"]["rgb"]["width"], p["capture"]["rgb"]["height"]
                frames[role] = (w, h, bytes([96]) * (w * h * 3))
            while not self._stop.is_set():
                stamp = time.time_ns()
                for role, (w, h, data) in frames.items():
                    header = SimpleNamespace(stamp=SimpleNamespace(sec=stamp // 1_000_000_000, nanosec=stamp % 1_000_000_000),
                                             frame_id=role + "_color_optical_frame")
                    msg = SimpleNamespace(header=header, width=w, height=h, step=w * 3, encoding="rgb8",
                                          is_bigendian=0, data=data)
                    ingress.image(msg, role, "rgb")
                time.sleep(1 / self.frame_hz)

        self._threads = [threading.Thread(target=arms, name="fake-vr-arms", daemon=True)]
        if ingress is not None:
            self._threads.append(threading.Thread(target=cameras, name="fake-vr-cameras", daemon=True))
        for t in self._threads:
            t.start()

    def stop(self):
        self._stop.set()
        for t in self._threads:
            t.join(2)
