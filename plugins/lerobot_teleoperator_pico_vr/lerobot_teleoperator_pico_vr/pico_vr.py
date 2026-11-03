"""pico_vr: the PICO headset as a LeRobot teleoperator, on top of the 023 robot_infra teleop.

The 023 collect pipeline runs in-process, unchanged: LiveApp + TeleopSession (One-Euro grip
filter with anchor deadbands, clutch anchors from the FK of the measured joints,
latest-target Pinocchio IK subprocesses, convergence gate, interpolation (a), IK
consistency gate (c), independent_trigger grippers, command shaping) and the A/X workflow,
served by the same HTTPS page and WebRTC data channel (port/certificate from the profile).

The only change: the LiveGateway backend publishes nothing. Whatever it would have sent
to the drivers (teleop targets, home trajectory, measured holds, gripper widths) is
captured and returned by get_action(). The robot (bi_piper_ros) executes it through its
own gateway and tracker (b). Feedback and camera previews are extra ROS subscribers on the
topics of the robot's stack. The session never enables or moves anything by itself.
"""
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
import ssl
import sys
import threading
import time
import uuid

from lerobot.teleoperators.teleoperator import Teleoperator

from .capture import CaptureBackend
from .config_pico_vr import PicoVRConfig

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


def motor_keys():
    """Same keys and order as bi_piper_ros (left 6 joints + gripper, then right)."""
    return [f"{side}_{name}.pos" for side in SIDES for name in (*JOINTS, "gripper")]


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _resolve(deployment_path, value):
    return str((Path(deployment_path).parent / Path(value).expanduser()).resolve())


@contextmanager
def _no_main_reimport():
    """Spawned IK workers would re-run the lerobot script (torch & co.) as __mp_main__.
    They only need robot_infra, so hide the main script path while they start."""
    main = sys.modules.get("__main__")
    path = getattr(main, "__file__", None)
    hide = main is not None and path is not None and getattr(main, "__spec__", None) is None
    if hide:
        del main.__file__
    try:
        yield
    finally:
        if hide:
            main.__file__ = path


class PicoVR(Teleoperator):
    config_class = PicoVRConfig
    name = "pico_vr"

    def __init__(self, config: PicoVRConfig):
        super().__init__(config)
        self.config = config
        if config.backend not in ("ros", "fake"):
            raise ValueError("backend must be 'ros' or 'fake'")
        if config.input_delay_s is not None and not 0 <= config.input_delay_s <= 0.5:
            raise ValueError("input_delay_s must be within 0..0.5 s")
        self._connected = False
        self._stop = threading.Event()
        self.app = self.journal = self.run_dir = self.capture = None
        self._server = self._server_thread = self._control = None
        self._context = self._executor = self._node = self._spin_thread = None
        self._fake = None
        self._errors = []
        self._actions = 0
        self._loop_started = False
        self._last_call = None
        self._max_call_gap = 0.0
        self.url = None

    # ------------------------------------------------------------------ features
    @property
    def action_features(self) -> dict:
        return {k: float for k in motor_keys()}

    @property
    def feedback_features(self) -> dict:
        return {}

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

    def send_feedback(self, feedback: dict) -> None:
        # Anchors use the FK of the measured joints from our own feedback subscription.
        pass

    # ------------------------------------------------------------------ connect
    def connect(self, calibrate: bool = True) -> None:
        if self._connected:
            raise RuntimeError(f"{self} already connected")
        c = self.config
        if c.robot_infra_src not in sys.path:
            sys.path.insert(0, c.robot_infra_src)
        from robot_infra.adapters.realsense_ros import validate_config
        from robot_infra.camera_config import bind_cameras
        from robot_infra.diagnostics import EventJournal, diagnostic_config
        from robot_infra.live_teleop import LiveApp, create_model, validate_profile

        deployment = _load_json(c.deployment)
        session = validate_profile(_load_json(_resolve(c.deployment, deployment["config"])))
        cameras = _load_json(_resolve(c.deployment, deployment["camera_config"]))
        validate_config(cameras)
        session = bind_cameras(session, cameras)
        if set(session["arms"]) != set(SIDES):
            raise ValueError("profile must define left and right arms")
        # Teleop only: lerobot records; the VR page needs RGB previews, no depth.
        session["recording_enabled"] = False
        session.pop("collection_request", None)
        if c.input_delay_s is not None:
            session.setdefault("teleop_filter", {})["input_delay_s"] = float(c.input_delay_s)
        if c.cameras_enabled:
            session["camera_pipeline"] = {r: {**p, "capture": {**p["capture"], "depth": None}, "record": {}}
                                          for r, p in session["camera_pipeline"].items()}
        else:
            session["camera_topics"], session["camera_pipeline"] = {}, {}
        model = create_model(session)
        if list(model.names) != list(JOINTS):
            raise ValueError("profile joint names must be joint1..joint6")
        self.session, self.model, self.deployment = session, model, deployment
        host = c.host if c.host is not None else deployment.get("host", "127.0.0.1")
        port = c.port if c.port is not None else int(deployment.get("port", 8445))
        advertise = c.advertise_host or deployment.get("advertise_host") or host
        if c.check_conflicts and c.backend == "ros":
            self._check_conflicts()

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.run_dir = Path(c.output_root) / f"{stamp}_pico_vr_{uuid.uuid4().hex[:8]}"
        self.run_dir.mkdir(parents=True, exist_ok=False)
        try:
            from robot_infra.provenance import runtime_identity
            session["runtime_identity"] = runtime_identity()
        except Exception as exc:  # provenance is evidence, not a precondition
            session["runtime_identity"] = {"error": str(exc)}
        (self.run_dir / "effective-config.json").write_text(json.dumps(session, indent=2), encoding="utf-8")
        (self.run_dir / "plugin-config.json").write_text(
            json.dumps({k: str(v) if isinstance(v, Path) else v for k, v in asdict(c).items()}, indent=2), encoding="utf-8")
        self.journal = EventJournal(self.run_dir / "episode", **diagnostic_config(session.get("diagnostics")))
        self.capture = CaptureBackend(SIDES)
        try:
            with _no_main_reimport():
                self.app = LiveApp(session, model, self.capture, self.journal)
            s = self.app.session
            self.capture.on_wait = lambda: setattr(s, "started", s.clock())
            self.app.emit("manifest", {"config": session, "model_sha256": model.sha256, "mode": "lerobot_pico_vr",
                                       "plugin": {k: str(v) for k, v in asdict(c).items()},
                                       "execution": "captured gateway targets returned as lerobot actions; nothing published"})
            ingress = self._start_cameras()
            if c.backend == "ros":
                self._start_ros(ingress)
            else:
                from .fake import FakeFeedback
                self._fake = FakeFeedback(session, self.capture)
                self._fake.start(self.app.gateway, ingress if c.cameras_enabled else None)
            self._start_server(host, port)
        except BaseException:
            self._teardown("connect_failed")
            raise
        self.url = f"https://{advertise}:{self._server.server_address[1]}/"
        self._connected = True
        logger.info("pico_vr ready: open %s in the PICO browser; run dir %s", self.url, self.run_dir)
        print(json.dumps({"event": "pico_vr_ready", "url": self.url, "run_dir": str(self.run_dir),
                          "workflow": "A home -> A start -> squeeze to follow -> A end"}), flush=True)

    def _check_conflicts(self):
        found = []
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit() or int(entry.name) == os.getpid():
                continue
            try:
                cmd = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            except OSError:
                continue
            if any(p in cmd for p in CONFLICT_PATTERNS):
                found.append(f"{entry.name}: {cmd[:160]}")
        if found:
            raise RuntimeError("another robot stack is running (CAN/cameras/VR port would be shared):\n" + "\n".join(found))

    def _start_cameras(self):
        """Same preview path as live_teleop.main: CameraIngress -> on-demand PreviewWorker -> /camera/<role>.jpg."""
        from collections import deque
        from robot_infra.camera_ingress import CameraIngress
        from robot_infra.image_codec import preview_jpeg
        from robot_infra.preview import PreviewWorker
        app = self.app
        pipeline = self.session["camera_pipeline"]

        def publish_preview(role, meta, jpeg, seq):
            with app.video_lock:
                app.images[role] = {"jpeg": jpeg, "received_s": meta["host_monotonic_ns"] / 1e9, "seq": seq,
                                    "capture_sequence": meta["capture_sequence"]}
                app.preview_ticks.setdefault(role, deque(maxlen=90)).append(time.monotonic())
        app.preview = PreviewWorker(pipeline, preview_jpeg, publish_preview, app.performance,
                                    config=self.session.get("preview_runtime"), archive_root=self.journal.root,
                                    emit=self.journal.emit)
        ingress = CameraIngress(pipeline, app.performance, recorder=None, preview=app.preview)
        app.video_lock = ingress.lock
        for key in ("stream_last", "observed_profiles", "capture_sequences", "camera_ticks", "camera_info"):
            setattr(app, key, getattr(ingress, key))
        return ingress

    def _start_ros(self, ingress):
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.signals import SignalHandlerOptions
        from sensor_msgs.msg import JointState
        from piper_msgs.msg import PiperStatusMsg
        from robot_infra.camera_ingress import subscribe_cameras

        app, model = self.app, self.model
        self._context = rclpy.Context()
        rclpy.init(context=self._context, domain_id=int(self.deployment["ros_domain_id"]),
                   signal_handler_options=SignalHandlerOptions.NO)
        node = self._node = rclpy.create_node("pico_lerobot_vr_teleop", context=self._context)
        for side, arm in self.session["arms"].items():
            def joints(m, s=side):
                try:
                    indexed = dict(zip(m.name, m.position))
                    app.gateway.feedback(s, [indexed[n] for n in model.names], indexed["gripper"],
                                         m.header.stamp.sec * 1_000_000_000 + m.header.stamp.nanosec)
                except Exception as exc:
                    self._note_error(f"feedback {s}: {exc}")

            def status(m, s=side):
                app.status_messages[s] = {k: getattr(m, k) for k in ("ctrl_mode", "arm_status", "err_code")}
                if m.err_code or m.arm_status:
                    with app.gateway.lock:
                        if app.gateway.enabled or not app.gateway.faulted:
                            app.gateway.stop("driver_error_" + s, fault=True)
            node.create_subscription(JointState, arm["feedback_topic"], joints, 1)
            node.create_subscription(PiperStatusMsg, arm["status_topic"], status, 1)
        if self.config.cameras_enabled:
            subscribe_cameras(node, self.session, ingress, app.emit, app.errors)
        self._executor = SingleThreadedExecutor(context=self._context)
        self._executor.add_node(node)

        def spin():
            while not self._stop.is_set() and self._context.ok():
                try:
                    self._executor.spin_once(timeout_sec=0.05)
                except Exception as exc:
                    if not self._stop.is_set():
                        self._note_error(f"ros spin: {exc}")
                        with app.gateway.lock:
                            app.gateway.stop("ros_spin_failure", fault=True)
                        return
        self._spin_thread = threading.Thread(target=spin, name="pico-vr-ros-spin", daemon=True)
        self._spin_thread.start()

    def _start_server(self, host, port):
        from robot_infra.live_teleop import make_server
        app = self.app
        server = make_server((host, port), app)
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(_resolve(self.config.deployment, self.deployment["cert"]),
                                    _resolve(self.config.deployment, self.deployment["key"]))
            server.socket = context.wrap_socket(server.socket, server_side=True)
        except BaseException:
            server.server_close()
            raise
        self._server_thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2},
                                               name="pico-vr-https", daemon=True)
        self._server_thread.start()
        self._server = server  # only a running server is shut down in teardown
        transport = self.session.get("webxr_transport", {})
        if transport.get("input") == "websocket":
            from robot_infra.control_socket import ControlSocketServer
            self._control = ControlSocketServer(app, host, transport["port"], context, server.server_address[1])
            app.input_service_ready = True
        elif transport.get("input") == "webrtc":
            from robot_infra.control_webrtc import WebRTCInputServer
            self._control = WebRTCInputServer(app)
            app.webrtc = self._control
            app.input_service_ready = True

    def _note_error(self, text):
        self._errors = (self._errors + [text])[-20:]
        logger.warning(text)

    # ------------------------------------------------------------------ lerobot API
    def _measured(self):
        g = self.app.gateway
        with g.lock:
            return {s: (g.hold_target(g.states[s]["q"]), g.states[s]["gripper"]) for s in SIDES}

    def _first_call(self):
        g = self.app.gateway
        deadline = time.monotonic() + self.config.first_feedback_timeout_s
        while True:
            with g.lock:
                if g._fresh():
                    break
            if time.monotonic() > deadline:
                raise RuntimeError("pico_vr: no fresh arm feedback; is the robot stack running?")
            time.sleep(0.05)
        session = self.app.session
        with session.lock:
            if session.state == "SELF_CHECK":
                session.started = session.clock()  # self-check timeout counts from here
        self.capture.loop_started = True
        self._loop_started = True

    def get_action(self) -> dict:
        if not self._connected:
            raise RuntimeError(f"{self} is not connected")
        if not self._loop_started:
            self._first_call()
        now = time.monotonic()
        if self._last_call is not None:
            self._max_call_gap = max(self._max_call_gap, now - self._last_call)
        self._last_call = now
        q, grip = self.capture.latest(self._measured())
        action = {}
        for side in SIDES:
            lo, hi = self.session["arms"][side]["gripper"]["limits_m"]
            for name, value in zip(JOINTS, q[side]):
                action[f"{side}_{name}.pos"] = float(value)
            width = grip[side]
            action[f"{side}_gripper.pos"] = float(min(hi, max(lo, width))) if math.isfinite(width) else float(lo)
        self._actions += 1
        self.app.emit("lerobot_teleop_action", {"index": self._actions,
                                                "q": {s: list(q[s]) for s in SIDES}, "gripper_m": dict(grip)})
        return action

    def status(self):
        """Session state for scripts/tests (same structure as the page's /api/status session)."""
        return self.app.session.snapshot() if self.app and self.app.session else None

    # ------------------------------------------------------------------ disconnect
    def disconnect(self) -> None:
        if not self._connected and self.journal is None:
            return
        self._connected = False
        self._teardown("lerobot_disconnect")

    def _teardown(self, reason):
        app = self.app
        try:
            if self._control is not None:
                self._control.close()
        except Exception as exc:
            self._note_error(f"control close: {exc}")
        if app is not None:
            try:
                app.close()  # session close -> gateway stop (captured measured hold), IK workers, preview
            except Exception as exc:
                self._note_error(f"app close: {exc}")
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        self._stop.set()
        if app is not None:
            app.keep_running = False
            app.watchdog_thread.join(2)
        if self._fake is not None:
            self._fake.stop()
        if self._spin_thread is not None:
            self._spin_thread.join(2)
        try:
            if self._executor is not None:
                self._executor.shutdown(timeout_sec=1)
            if self._node is not None:
                self._node.destroy_node()
            if self._context is not None and self._context.ok():
                self._context.shutdown()
        except Exception as exc:
            self._note_error(f"ros shutdown: {exc}")
        stats = {"actions": self._actions, "max_get_action_gap_s": self._max_call_gap,
                 "captured": dict(self.capture.counts) if self.capture else {}, "errors": self._errors,
                 "final_state": app.session.snapshot()["state"] if app and app.session else None}
        if self.journal is not None:
            try:
                if app is not None:
                    (self.journal.root / "performance.json").write_text(json.dumps(
                        {"metrics": app.performance.snapshot(), "preview": app.preview.snapshot() if app.preview else None},
                        indent=2) + "\n", encoding="utf8")
                self.journal.emit("finalize", {"outcome": reason, "errors": self._errors + (app.errors if app else []),
                                               "stats": stats})
            finally:
                self.journal.close()
                self.journal = None
        if self.run_dir is not None:
            (self.run_dir / "teleop-ended.json").write_text(json.dumps(
                {"reason": reason, "stats": stats,
                 "stop_semantics": "captured measured hold returned as the last action; nothing published by the teleop"},
                indent=2), encoding="utf-8")
