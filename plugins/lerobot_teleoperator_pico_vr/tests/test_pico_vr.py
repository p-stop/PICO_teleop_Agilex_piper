"""Offline tests: fake feedback, real LiveApp/TeleopSession/IK workers/HTTPS/WebRTC. No ROS, no hardware."""
import asyncio
import json
import math
from pathlib import Path
import threading
import time

import numpy as np
import pytest

from lerobot_teleoperator_pico_vr import PicoVR, PicoVRConfig
from lerobot_teleoperator_pico_vr.pico_vr import motor_keys
from lerobot_teleoperator_pico_vr import sim_headset

PICO = Path("/home/ros/zero-wam/PICO-ACT")
pytestmark = pytest.mark.skipif(not (PICO / "profiles/collection/deployment.json").exists(), reason="needs PICO-ACT profile")


def make(tmp_path, **kw):
    cfg = PicoVRConfig(backend="fake", host="127.0.0.1", port=0, output_root=str(tmp_path),
                       calibration_dir=tmp_path / "cal", **kw)
    return PicoVR(cfg)


def packet(seq, t, right_pos, *, a=False, squeeze=False, trigger=0.0):
    rb = {4: 1.0 if a else 0.0, 1: 1.0 if squeeze else 0.0, 0: trigger}
    return {"schema_version": "webxr-input/1", "event": "frame", "session_id": "test", "seq": seq, "epoch": 0,
            "reference_space": "local-floor", "client_time_ms": t * 1000.0, "client_unix_ms": 1.0,
            "visibility": "visible", "head": {"position_m": [0.0, 1.6, 0.0], "orientation_xyzw": [0.0, 0.0, 0.0, 1.0]},
            "inputs": [sim_headset.hand("left", (-0.2, 1.0, -0.3)), sim_headset.hand("right", right_pos, 0.0, rb)],
            "last_server_s": time.monotonic()}


def fk_xyz(model, q):
    return np.array([row[3] for row in model.fk(q)[:3]])


def right_q(action):
    return [action[f"right_joint{i}.pos"] for i in range(1, 7)]


def left_q(action):
    return [action[f"left_joint{i}.pos"] for i in range(1, 7)]


def test_features_match_robot_plugin(tmp_path):
    t = make(tmp_path)
    assert list(t.action_features) == motor_keys() and len(motor_keys()) == 14
    assert t.feedback_features == {}
    try:
        from lerobot_robot_pico_piper.bi_piper_ros import motor_keys as robot_keys
    except ImportError:
        pytest.skip("robot plugin not installed")
    assert motor_keys() == robot_keys()


def test_workflow_hold_follow_release(tmp_path):
    t = make(tmp_path)
    t.connect()
    try:
        state = lambda: t.status()["state"]  # noqa: E731
        first = t.get_action()
        assert max(abs(v) for v in left_q(first) + right_q(first)) < 0.01  # fake arms start at the profile home
        seq, t0, timings = 0, time.monotonic(), []
        right0 = (0.2, 1.0, -0.3)

        def run(seconds, until=None, **kw):
            nonlocal seq
            end = time.monotonic() + seconds
            actions = []
            while time.monotonic() < end:
                now = time.monotonic()
                pos = kw["pos_fn"](now) if "pos_fn" in kw else kw.get("pos", right0)
                t.app.input(packet(seq, now - t0, pos, a=kw.get("a", False), squeeze=kw.get("squeeze", False)))
                seq += 1
                began = time.perf_counter()
                actions.append(t.get_action())
                timings.append(time.perf_counter() - began)
                if until and until():
                    return actions
                time.sleep(1 / 40)
            return actions

        run(10, until=lambda: state() == "STANDBY")
        assert state() == "STANDBY"
        run(0.2, a=True)
        run(12, until=lambda: state() == "READY")
        assert state() == "READY"
        run(0.3)
        run(0.2, a=True)
        run(3, until=lambda: state() == "TELEOP")
        assert state() == "TELEOP"
        before = t.get_action()
        p_before = fk_xyz(t.model, right_q(before))
        # squeeze, then raise the right hand 6 cm over 2 s (hand +y -> robot +z through the alignment)
        run(0.5, squeeze=True)
        t_up = time.monotonic()
        run(2.0, squeeze=True, pos_fn=lambda now: (right0[0], right0[1] + 0.06 * min(1.0, (now - t_up) / 2.0), right0[2]))
        held = run(1.5, squeeze=True, pos=(right0[0], right0[1] + 0.06, right0[2]))
        moved = fk_xyz(t.model, right_q(held[-1])) - p_before
        assert moved[2] > 0.045 and abs(moved[0]) < 0.015 and abs(moved[1]) < 0.015, moved
        assert max(abs(a - b) for a, b in zip(left_q(held[-1]), left_q(before))) < 1e-9  # left untouched
        # release: actions hold (measured hold latched once), no drift
        released = run(1.0, pos=(right0[0], right0[1] + 0.10, right0[2]))
        tail = [right_q(a) for a in released[10:]]
        assert max(abs(a - b) for q in tail for a, b in zip(q, tail[0])) < 1e-9
        run(0.2, a=True)
        run(3, until=lambda: state() == "STANDBY")
        assert state() == "STANDBY"
        assert np.percentile(timings, 95) < 0.005  # get_action never blocks
    finally:
        t.disconnect()
    ended = json.loads((t.run_dir / "teleop-ended.json").read_text())
    assert ended["stats"]["captured"]["send"] > 50
    kinds = set()
    for f in (t.run_dir / "episode").glob("events*.jsonl"):
        kinds |= {json.loads(line)["kind"] for line in f.open()}
    assert {"raw_input", "intent", "motion_result", "command", "feedback", "session_state", "lerobot_teleop_action"} <= kinds


def test_webrtc_sim_headset_end_to_end(tmp_path):
    t = make(tmp_path)
    t.connect()
    stop = threading.Event()
    actions = []

    def loop():  # lerobot's 30 Hz loop
        while not stop.is_set():
            actions.append((time.monotonic(), t.get_action(), t.status()["state"]))
            time.sleep(1 / 30)
    worker = threading.Thread(target=loop, daemon=True)
    try:
        worker.start()
        port = t._server.server_address[1]
        script = lambda s: sim_headset.default_script(s, home_wait=6.0, move_s=6.0)  # noqa: E731
        stats = asyncio.run(sim_headset.run(f"https://127.0.0.1:{port}/", rate_hz=40, script=script,
                                            jitter_s=0.03, log=lambda *_: None))
        time.sleep(0.5)
    finally:
        stop.set()
        worker.join(2)
        t.disconnect()
    assert stats["acks"] >= stats["sent"] * 0.95 and stats["error_count"] == 0, stats
    states = [s for _, _, s in actions]
    assert {"HOMING", "READY", "TELEOP", "STANDBY"} <= set(states), set(states)
    assert states[-1] in ("STANDBY", "PAUSED")  # page gone -> webrtc_channel_closed pause
    teleop = [a for _, a, s in actions if s == "TELEOP"]
    span = np.ptp(np.array([right_q(a) for a in teleop]), axis=0)
    assert span.max() > 0.02  # the circle moved the right arm
    assert np.ptp(np.array([left_q(a) for a in teleop]), axis=0).max() < 1e-9
