"""LiveGateway backend that publishes nothing: the targets the gateway would have sent
to the drivers become the lerobot action (14 values, left then right)."""
from collections import Counter
import threading


class CaptureBackend:
    def __init__(self, sides):
        self.sides = tuple(sides)
        self.lock = threading.Lock()
        self.capability = None
        self.q, self.grip = {}, {}
        self.counts = Counter()
        self.loop_started = False
        self.on_wait = None  # called while waiting for the lerobot loop (keeps the self-check timer fresh)

    def bind(self, capability):
        if self.capability is not None:
            raise RuntimeError("backend already bound")
        self.capability = capability

    def _check(self, capability):
        if capability is not self.capability or capability is None:
            raise PermissionError("gateway capability required")

    def ready(self):
        # The session self-check waits until lerobot's loop runs (the robot connects after us).
        if self.loop_started:
            return True, []
        if self.on_wait is not None:
            self.on_wait()
        return False, ["lerobot_robot_loop"]

    def enable(self, side, capability):
        # Enabling the hardware is the robot's job; here it only opens the session's activation.
        self._check(capability)
        self.counts["enable"] += 1

    def send(self, side, q, gripper, capability):
        self._check(capability)
        with self.lock:
            self.q[side] = tuple(float(v) for v in q)
            if gripper is not None:
                self.grip[side] = float(gripper)
            self.counts["send"] += 1

    def send_gripper(self, side, width, capability):
        self._check(capability)
        with self.lock:
            self.grip[side] = float(width)
            self.counts["send_gripper"] += 1

    def latest(self, measured):
        """Captured targets; a side never commanded yet holds its measured value (latched)."""
        with self.lock:
            for side in self.sides:
                q, width = measured[side]
                self.q.setdefault(side, tuple(q))
                self.grip.setdefault(side, float(width))
            return dict(self.q), dict(self.grip)
