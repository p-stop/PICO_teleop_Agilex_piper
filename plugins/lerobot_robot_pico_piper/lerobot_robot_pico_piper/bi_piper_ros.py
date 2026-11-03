"""bi_piper_ros: dual Piper as a LeRobot Robot, on top of the 023 robot_infra stack.

- Drivers and cameras are the same children `collect` starts (checked vendor driver
  wrapper under the system Python, RealSense nodes), in ROS domain from deployment.json.
- Every arm/gripper target goes through robot_infra.live_control.LiveGateway (ownership,
  epochs, joint limits, freshness, single publisher/subscriber checks, measured hold on stop).
- Between lerobot (30 Hz) and the gateway a background thread runs the second-order
  tracker (interpolation (b)) at `tracker_hz`.
- disconnect(): measured hold, children stopped. No automatic disable, home or gripper close.
"""
from dataclasses import asdict
from datetime import datetime, timezone
from functools import cached_property
import json
import logging
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid

from lerobot.robots.robot import Robot
from lerobot.utils.decorators import check_if_not_connected

from .config_bi_piper_ros import BiPiperROSConfig
from .tracker import JointTracker, smoothstep

logger = logging.getLogger(__name__)

SIDES = ("left", "right")
JOINTS = tuple(f"joint{i}" for i in range(1, 7))
CONFLICT_PATTERNS = (
    "piper_ctrl_single_node",
    "robot_infra.adapters.piper_driver",
    "realsense2_camera_node",
    "robot_infra.live_teleop",
    "robot_infra collect",
    "robot_infra device-teleop",
)


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _resolve(deployment_path, value):
    return str((Path(deployment_path).parent / Path(value).expanduser()).resolve())


def motor_keys():
    return [f"{side}_{name}.pos" for side in SIDES for name in (*JOINTS, "gripper")]


class BiPiperROS(Robot):
    config_class = BiPiperROSConfig
    name = "bi_piper_ros"

    def __init__(self, config: BiPiperROSConfig):
        super().__init__(config)
        self.config = config
        if config.backend not in ("ros", "fake"):
            raise ValueError("backend must be 'ros' or 'fake'")
        self.deployment = _load_json(config.deployment)
        self.camera_spec = _load_json(_resolve(config.deployment, self.deployment["camera_config"]))
        roles = [c["role"] for c in self.camera_spec["cameras"]] if config.cameras_enabled else []
        self._shapes = {}
        for cam in self.camera_spec["cameras"]:
            if cam["role"] in roles:
                rgb = cam["capture"]["rgb"]
                self._shapes[cam["role"]] = (int(rgb["height"]), int(rgb["width"]), 3)
        # Only for code that sizes image writers from `robot.cameras`.
        self.cameras = {role: None for role in roles}
        self._connected = False
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._frames = {}
        self._frame_lock = threading.Lock()
        self._processes, self._logs, self._manifest = [], [], []
        self._errors = []
        self.gateway = self.journal = self.node = self.run_dir = None
        self._context = self._executor = self._spin_thread = self._tracker_thread = None
        self._fake = None

    # ------------------------------------------------------------------ features
    @cached_property
    def observation_features(self) -> dict:
        return {**{k: float for k in motor_keys()}, **{role: shape for role, shape in self._shapes.items()}}

    @cached_property
    def action_features(self) -> dict:
        return {k: float for k in motor_keys()}

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_calibrated(self) -> bool:
        return True

    def calibrate(self) -> None:
        pass

    def configure(self) -> None:
        pass

    # ------------------------------------------------------------------ connect
    def connect(self, calibrate: bool = True) -> None:
        if self._connected:
            raise RuntimeError(f"{self} already connected")
        c = self.config
        if c.robot_infra_src not in sys.path:
            sys.path.insert(0, c.robot_infra_src)
        from robot_infra.camera_config import bind_cameras
        from robot_infra.adapters.realsense_ros import validate_config
        from robot_infra.diagnostics import EventJournal, diagnostic_config
        from robot_infra.live_control import LiveGateway
        from robot_infra.live_teleop import create_model, validate_profile

        session = validate_profile(_load_json(_resolve(c.deployment, self.deployment["config"])))
        validate_config(self.camera_spec)
        session = bind_cameras(session, self.camera_spec)
        if set(session["arms"]) != set(SIDES):
            raise ValueError("profile must define left and right arms")
        model = create_model(session)
        if list(model.names) != list(JOINTS):
            raise ValueError("profile joint names must be joint1..joint6")
        self.session, self.model = session, model
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.run_dir = Path(c.output_root) / f"{stamp}_lerobot_{uuid.uuid4().hex[:8]}"
        self.run_dir.mkdir(parents=True, exist_ok=False)
        try:
            from robot_infra.provenance import runtime_identity
            session["runtime_identity"] = runtime_identity()
        except Exception as exc:  # provenance is evidence, not a precondition
            session["runtime_identity"] = {"error": str(exc)}
        self.effective = self.run_dir / "effective-config.json"
        self.effective.write_text(json.dumps(session, indent=2), encoding="utf-8")
        (self.run_dir / "plugin-config.json").write_text(
            json.dumps({k: str(v) if isinstance(v, Path) else v for k, v in asdict(c).items()}, indent=2), encoding="utf-8")
        self.journal = EventJournal(self.run_dir / "episode", **diagnostic_config(session.get("diagnostics")))
        self.owner = "lerobot-" + uuid.uuid4().hex[:12]
        self.trackers = {s: JointTracker(6, time_constant_s=c.tracker_time_constant_s,
                                         max_velocity_rad_s=c.tracker_max_velocity_rad_s,
                                         max_acceleration_rad_s2=c.tracker_max_acceleration_rad_s2) for s in SIDES}
        self._mode, self._fault = "idle", None
        self._seq, self._last_action_s, self._action_count = 0, 0.0, 0
        self._last_cmd = {}
        self._grip_target, self._grip_sent = {}, {}
        self._stats = {"submitted": 0, "rejected": {}, "rearms": 0, "approaches": 0}
        try:
            if c.backend == "ros":
                if c.launch_stack:
                    self._check_conflicts()
                    self._check_can()
                    self._launch_children()
                self._start_ros(LiveGateway)
            else:
                self._start_fake(LiveGateway)
            self.emit("manifest", {"config": session, "model_sha256": model.sha256, "mode": "lerobot_bi_piper_ros",
                                   "plugin": {k: str(v) for k, v in asdict(c).items()}, "owner": self.owner})
            self._selftest()
            self._tracker_thread = threading.Thread(target=self._loop, name="bi-piper-tracker", daemon=True)
            self._tracker_thread.start()
            self._connected = True
            if not c.dry_run:
                self._arm()
                if c.home_on_connect:
                    home = {s: tuple(self.session["arms"][s]["home_rad"]) for s in SIDES}
                    self._move_blocking(home, "home", duration=self.session["session"]["home_duration_s"],
                                        settle=self.session["session"]["home_tolerance_rad"],
                                        timeout=self.session["session"]["home_timeout_s"])
            else:
                with self._lock:
                    for s in SIDES:
                        self.trackers[s].reset(self._measured(s))
                        self._last_cmd[s] = tuple(self.trackers[s].q)
                    self._mode = "hold"
                logger.warning("bi_piper_ros dry_run: nothing will be enabled or published")
        except BaseException:
            self._connected = False
            self._teardown("connect_failed")
            raise
        logger.info("bi_piper_ros connected; run dir %s", self.run_dir)

    def _check_conflicts(self):
        mine = {os.getpid()}
        found = []
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit() or int(entry.name) in mine:
                continue
            try:
                cmd = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            except OSError:
                continue
            if any(p in cmd for p in CONFLICT_PATTERNS):
                found.append(f"{entry.name}: {cmd[:160]}")
        if found:
            raise RuntimeError("another robot stack is running (CAN/cameras would be shared):\n" + "\n".join(found))

    def _check_can(self):
        for side, arm in self.session["arms"].items():
            iface = Path("/sys/class/net") / arm["can_interface"]
            if not iface.is_dir() or not int((iface / "flags").read_text().strip(), 16) & 1:
                raise RuntimeError(f"CAN interface missing or DOWN: {arm['can_interface']} ({side})")

    def _launch_children(self):
        from robot_infra.session_launcher import arm_arguments
        from robot_infra.adapters.realsense_ros import driver_arguments
        env = os.environ.copy()
        env["ROS_DOMAIN_ID"] = str(self.deployment["ros_domain_id"])
        env.pop("VIRTUAL_ENV", None)
        paths = [_resolve(self.config.deployment, p) for p in self.deployment["python_paths"]]
        env["PYTHONPATH"] = os.pathsep.join(paths + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        for side, arm in self.session["arms"].items():
            args = arm_arguments("driver", side, arm, gripper_enabled=self.session.get("gripper_control", False))
            args = ["/usr/bin/python3", "-m", "robot_infra.adapters.piper_driver", "--config", str(self.effective),
                    *args[1:], "--log-level", "warn"]
            self._start_child(side + "_driver", args, env)
        if self.config.cameras_enabled:
            driver = self.deployment["camera_driver"]
            for cam in self.camera_spec["cameras"]:
                self._start_child(cam["role"], driver_arguments(driver, cam), env)

    def _start_child(self, role, command, env):
        log = (self.run_dir / (role + ".log")).open("x")
        self._logs.append(log)
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        self._processes.append((role, child))
        self._manifest.append({"role": role, "pid": child.pid, "args": command})
        (self.run_dir / "processes.json").write_text(json.dumps(
            {"ros_domain_id": self.deployment["ros_domain_id"], "children": self._manifest}, indent=2), encoding="utf-8")

    def _start_ros(self, LiveGateway):
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
        from rclpy.signals import SignalHandlerOptions
        from sensor_msgs.msg import Image, JointState
        from piper_msgs.msg import PiperStatusMsg
        from robot_infra.adapters.piper_ros import PiperROSBackend

        self._context = rclpy.Context()
        rclpy.init(context=self._context, domain_id=int(self.deployment["ros_domain_id"]),
                   signal_handler_options=SignalHandlerOptions.NO)
        self.node = rclpy.create_node("pico_lerobot_bi_piper", context=self._context)
        self.gateway = LiveGateway(self.session, self.model, PiperROSBackend(self.node, self.session, self.model.names), self.emit)
        g = self.gateway
        self.status_messages = {}
        for side, arm in self.session["arms"].items():
            def joints(m, s=side):
                try:
                    indexed = dict(zip(m.name, m.position))
                    g.feedback(s, [indexed[n] for n in self.model.names], indexed["gripper"],
                               m.header.stamp.sec * 1_000_000_000 + m.header.stamp.nanosec)
                except Exception as exc:
                    self._note_error(f"feedback {s}: {exc}")

            def status(m, s=side):
                self.status_messages[s] = {k: getattr(m, k) for k in ("ctrl_mode", "arm_status", "err_code")}
                if m.err_code or m.arm_status:
                    with g.lock:
                        if g.enabled or not g.faulted:
                            g.stop("driver_error_" + s, fault=True)
            self.node.create_subscription(JointState, arm["feedback_topic"], joints, 1)
            self.node.create_subscription(PiperStatusMsg, arm["status_topic"], status, 1)
        image_qos = QoSProfile(depth=2, history=HistoryPolicy.KEEP_LAST, reliability=ReliabilityPolicy.RELIABLE,
                               durability=DurabilityPolicy.VOLATILE)
        for role in self._shapes:
            topic = self.session["camera_topics"][role]
            self.node.create_subscription(Image, topic, lambda m, r=role: self._on_image(r, m), image_qos)
        self._executor = SingleThreadedExecutor(context=self._context)
        self._executor.add_node(self.node)

        def spin():
            while not self._stop.is_set() and self._context.ok():
                try:
                    self._executor.spin_once(timeout_sec=0.05)
                except Exception as exc:
                    if not self._stop.is_set():
                        self._note_error(f"ros spin: {exc}")
                        with g.lock:
                            g.stop("ros_spin_failure", fault=True)
                        return
        self._spin_thread = threading.Thread(target=spin, name="bi-piper-ros-spin", daemon=True)
        self._spin_thread.start()

    def _on_image(self, role, m):
        import numpy as np
        h, w, _ = self._shapes[role]
        if m.height != h or m.width != w or m.encoding not in ("rgb8", "bgr8"):
            self._note_error(f"camera {role}: unexpected {m.width}x{m.height} {m.encoding}")
            return
        rows = np.frombuffer(m.data, dtype=np.uint8).reshape(h, m.step)[:, : w * 3]
        img = rows.reshape(h, w, 3)
        img = img[:, :, ::-1].copy() if m.encoding == "bgr8" else img.copy()
        with self._frame_lock:
            self._frames[role] = (img, time.monotonic())

    def _start_fake(self, LiveGateway):
        from .fake import FakeStack
        self._fake = FakeStack(self.session, self.model, self._shapes)
        self.gateway = LiveGateway(self.session, self.model, self._fake.backend, self.emit)
        self.status_messages = {}
        self._fake.start(self.gateway, self._frames, self._frame_lock)

    def _note_error(self, text):
        self._errors = (self._errors + [text])[-20:]
        logger.warning(text)

    def emit(self, kind, payload):
        journal = self.journal
        return journal.emit(kind, payload) if journal is not None else None

    def _measured(self, side):
        with self.gateway.lock:
            return self.gateway.hold_target(self.gateway.states[side]["q"])

    def _selftest(self):
        c = self.config
        deadline = time.monotonic() + c.selftest_timeout_s
        last_report = 0.0
        while True:
            missing = []
            for role, child in self._processes:
                if child.poll() is not None:
                    raise RuntimeError(f"child {role} exited with {child.returncode}; see {self.run_dir / (role + '.log')}")
            with self.gateway.lock:
                if not self.gateway._fresh():
                    missing.append("arm_feedback")
                if self.gateway.faulted:
                    raise RuntimeError("gateway fault during self-check: " + str(self.gateway.last_reason))
            ok, errors = self.gateway.backend.ready()
            if not ok:
                missing += errors
            now = time.monotonic()
            with self._frame_lock:
                for role in self._shapes:
                    if now - self._frames.get(role, (None, 0.0))[1] > 1.5:
                        missing.append("camera:" + role)
            if not missing:
                self.emit("session_state", {"state": "STANDBY", "reason": "lerobot_selftest_passed", "trials": 0})
                return
            if now - last_report > 3:
                logger.info("bi_piper_ros self-check waiting for: %s", ", ".join(missing))
                last_report = now
            if now > deadline:
                raise TimeoutError("self-check timed out; missing: " + ", ".join(missing))
            time.sleep(0.1)

    # ------------------------------------------------------------------ control
    def _arm(self):
        g = self.gateway
        with self._lock:
            with g.lock:
                if g.faulted:
                    raise RuntimeError("gateway fault latched: " + str(g.last_reason) + "; reconnect after checking the arms")
                g.arm(self.owner, enable_hardware=False)
                for s in SIDES:
                    g.activate(s)
                for s in SIDES:
                    self.trackers[s].reset(g.hold_target(g.states[s]["q"]))
                    self._last_cmd[s] = tuple(self.trackers[s].q)
            self._grip_sent.clear()
            self._mode = "hold"
            self._last_tick = time.monotonic()

    def _lost_control(self, reason):
        if self._mode != "idle":
            logger.warning("bi_piper_ros lost control (%s): measured hold by gateway", reason)
            self.emit("session_state", {"state": "PAUSED", "reason": str(reason), "trials": 0})
        self._mode = "idle"
        if self.gateway.faulted:
            self._fault = str(reason)

    def _loop(self):
        period = 1.0 / self.config.tracker_hz
        next_t = time.monotonic()
        self._last_tick = next_t
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as exc:
                self._note_error(f"tracker: {exc!r}")
                with self._lock:
                    with self.gateway.lock:
                        self.gateway.stop("tracker_failure", fault=True)
                    self._lost_control("tracker_failure")
            next_t += period
            delay = next_t - time.monotonic()
            if delay < -5 * period:
                next_t = time.monotonic()
            elif delay > 0:
                time.sleep(delay)

    def _tick(self):
        c, g = self.config, self.gateway
        with self._lock:
            now = time.monotonic()
            dt, self._last_tick = now - self._last_tick, now
            if not c.dry_run:
                g.watchdog()
                if self._mode != "idle" and not (g.enabled and g.owner == self.owner):
                    self._lost_control(g.last_reason)
            mode = self._mode
            if mode == "idle":
                return
            if mode == "move":
                s = (now - self._traj_t0) / self._traj_T
                q = {side: smoothstep(self._traj_from[side], self._traj_to[side], s) for side in SIDES}
                for side in SIDES:
                    self.trackers[side].reset(q[side])
            else:
                q = {side: self.trackers[side].step(dt) for side in SIDES}
            renew = mode in ("move", "hold") or now - self._last_action_s < c.action_timeout_s
            jaws = {}
            if mode == "follow":
                for side, width in self._grip_target.items():
                    last = self._grip_sent.get(side)
                    if last is None or abs(last[0] - width) > c.gripper_resend_threshold_m or now - last[1] > c.gripper_refresh_s:
                        jaws[side] = width
            self._publish(q, jaws, renew, now)

    def _publish(self, q, jaws, renew, now):
        g = self.gateway
        self._last_cmd = {s: tuple(v) for s, v in q.items()}
        if self.config.dry_run:
            self.emit("dry_run_command", {"q": {s: list(v) for s, v in q.items()}, "gripper_m": jaws, "mode": self._mode})
            for side, width in jaws.items():
                self._grip_sent[side] = (width, now)
            return
        with g.lock:
            if renew:
                try:
                    g.renew(self.owner, g.epoch)
                except PermissionError:
                    pass  # expired: the watchdog will hold on the next tick
            self._seq += 1
            command = g.command({s: q[s] for s in SIDES}, self._seq, jaws)
            try:
                result = g.submit(command, active_sides=set(SIDES), jaw_sides=set(jaws))
            except PermissionError:  # stopped concurrently (e.g. driver status callback)
                self._lost_control(g.last_reason)
                return
        if result["accepted"]:
            self._stats["submitted"] += 1
            for side, width in jaws.items():
                self._grip_sent[side] = (width, now)
        else:
            reason = result["reason"]
            self._stats["rejected"][reason] = self._stats["rejected"].get(reason, 0) + 1

    def _move_blocking(self, target, kind, *, duration=None, settle=None, timeout=None):
        """Smooth (smoothstep) move of both arms from the current command to `target`."""
        c = self.config
        with self._lock:
            start = {s: tuple(self.trackers[s].q) for s in SIDES}
            dist = max(abs(a - b) for s in SIDES for a, b in zip(start[s], target[s]))
            T = duration if duration is not None else max(1.0, 1.5 * dist / c.approach_peak_velocity_rad_s)
            self._traj_from, self._traj_to, self._traj_t0, self._traj_T = start, {s: tuple(target[s]) for s in SIDES}, time.monotonic(), T
            self._mode = "move"
            self._stats["approaches"] += 1
            self.emit("session_state", {"state": "HOMING" if kind == "home" else "APPROACH",
                                        "reason": f"lerobot_{kind}", "trials": 0, "distance_rad": dist, "duration_s": T})
        logger.info("bi_piper_ros %s: max joint distance %.3f rad over %.1f s", kind, dist, T)
        settle = c.approach_settle_tolerance_rad if settle is None else settle
        deadline = time.monotonic() + (T + c.approach_timeout_s if timeout is None else max(timeout, T + 2))
        settled_since = None
        while True:
            time.sleep(0.02)
            with self._lock:
                if self._mode != "move":
                    raise RuntimeError(f"{kind} interrupted: {self._fault or self.gateway.last_reason}")
            now = time.monotonic()
            if now < self._traj_t0 + T:
                continue
            if c.dry_run:
                break
            with self.gateway.lock:
                err = max(abs(a - b) for s in SIDES for a, b in zip(self.gateway.states[s]["q"], target[s]))
            if err <= settle:
                settled_since = settled_since or now
                if now - settled_since >= 0.3:
                    break
            else:
                settled_since = None
            if now > deadline:
                raise TimeoutError(f"{kind}: feedback did not reach target (max error {err:.3f} rad)")
        with self._lock:
            for s in SIDES:
                self.trackers[s].reset(target[s])
            self._mode = "hold"
            self.emit("session_state", {"state": "READY", "reason": f"lerobot_{kind}_done", "trials": 0})

    # ------------------------------------------------------------------ lerobot API
    @check_if_not_connected
    def get_observation(self) -> dict:
        now = time.monotonic()
        obs = {}
        with self.gateway.lock:
            for side in SIDES:
                state = self.gateway.states.get(side)
                if state is None or now - state["received_s"] > 0.5:
                    raise RuntimeError(f"stale arm feedback: {side}")
                for name, value in zip(JOINTS, state["q"]):
                    obs[f"{side}_{name}.pos"] = float(value)
                obs[f"{side}_gripper.pos"] = float(state["gripper"])
        with self._frame_lock:
            for role in self._shapes:
                frame = self._frames.get(role)
                if frame is None or now - frame[1] > self.config.max_image_age_s:
                    raise RuntimeError(f"stale camera frame: {role}")
                obs[role] = frame[0]
        return obs

    @check_if_not_connected
    def send_action(self, action: dict) -> dict:
        c = self.config
        limits = self.model.limits
        q, grip = {}, {}
        for side in SIDES:
            values = []
            for name, (lo, hi) in zip(JOINTS, limits):
                v = float(action[f"{side}_{name}.pos"])
                if not math.isfinite(v):
                    raise ValueError(f"non-finite action {side}_{name}")
                values.append(min(hi, max(lo, v)))
            q[side] = tuple(values)
            glo, ghi = self.session["arms"][side]["gripper"]["limits_m"]
            w = float(action[f"{side}_gripper.pos"])
            if not math.isfinite(w):
                raise ValueError(f"non-finite action {side}_gripper")
            grip[side] = min(ghi, max(glo, w))
        with self._lock:
            if self._fault:
                raise RuntimeError("gateway fault latched: " + self._fault)
            self._action_count += 1
            self._last_action_s = time.monotonic()
            self.emit("lerobot_action", {"index": self._action_count, "q": {s: list(v) for s, v in q.items()},
                                         "gripper_m": grip})
            if self._mode == "idle" and not c.dry_run:
                self._stats["rearms"] += 1
                logger.warning("bi_piper_ros: re-arming after %s", self.gateway.last_reason)
                self._arm()
            mode = self._mode
            far = max(abs(a - b) for s in SIDES for a, b in zip(self.trackers[s].q, q[s]))
            if self._action_count == 1:
                measured = {s: self._measured(s) for s in SIDES}
                d0 = max(abs(a - b) for s in SIDES for a, b in zip(measured[s], q[s]))
                self.emit("first_action", {"distance_to_measured_rad": d0, "distance_to_command_rad": far})
                logger.info("bi_piper_ros first action: %.3f rad from measured pose", d0)
        if mode != "follow" and far > c.first_action_tolerance_rad:
            self._move_blocking(q, "approach")
            self._last_action_s = time.monotonic()
        with self._lock:
            if self._mode == "hold":
                self._mode = "follow"
                self.emit("session_state", {"state": "TELEOP", "reason": "lerobot_follow", "trials": 0})
            elif self._mode != "follow":
                raise RuntimeError(f"robot not following (mode {self._mode}): {self.gateway.last_reason}")
            for side in SIDES:
                self.trackers[side].set_target(q[side])
            self._grip_target = dict(grip)
            sent = {}
            for side in SIDES:
                for name, value in zip(JOINTS, self._last_cmd[side]):
                    sent[f"{side}_{name}.pos"] = float(value)
                sent[f"{side}_gripper.pos"] = float(grip[side])
        return sent

    def disconnect(self) -> None:
        if not self._connected and self.journal is None:
            return
        self._connected = False
        self._teardown("lerobot_disconnect")

    def _teardown(self, reason):
        self._stop.set()
        if self._tracker_thread is not None:
            self._tracker_thread.join(2)
        g = self.gateway
        if g is not None:
            try:
                with g.lock:
                    if g.enabled:
                        g.stop(reason)  # measured hold; no disable, home or gripper close
                time.sleep(0.2)  # let the hold message leave before the node goes away
            except Exception as exc:
                self._note_error(f"stop: {exc}")
        try:
            if self.journal is not None:
                self.emit("session_state", {"state": "CLOSED", "reason": reason, "trials": 0})
                self.emit("finalize", {"outcome": "lerobot_disconnect", "errors": self._errors, "stats": getattr(self, "_stats", {})})
        except Exception:
            pass
        if self._fake is not None:
            self._fake.stop()
        if self._spin_thread is not None:
            self._spin_thread.join(2)
        try:
            if self.node is not None:
                self.node.destroy_node()
            if self._context is not None and self._context.ok():
                self._context.shutdown()
        except Exception as exc:
            self._note_error(f"ros shutdown: {exc}")
        for role, child in reversed(self._processes):
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGINT)
                    child.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        for log in self._logs:
            log.close()
        if self.run_dir is not None:
            (self.run_dir / "stack-ended.json").write_text(json.dumps({
                "exit_codes": {role: child.poll() for role, child in self._processes},
                "stop_semantics": "gateway measured hold; no automatic home, disable or gripper-close",
                "stats": getattr(self, "_stats", {}), "errors": self._errors}, indent=2), encoding="utf-8")
        if self.journal is not None:
            self.journal.close()
            self.journal = None
