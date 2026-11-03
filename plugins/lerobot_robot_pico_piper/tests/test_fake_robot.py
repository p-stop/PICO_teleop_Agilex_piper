"""End-to-end through the real LiveGateway with the fake backend (no ROS, no hardware)."""
import json
from pathlib import Path
import time

import pytest

from lerobot_robot_pico_piper import BiPiperROS, BiPiperROSConfig
from lerobot_robot_pico_piper.bi_piper_ros import motor_keys

PICO = Path("/home/ros/zero-wam/PICO-ACT")
pytestmark = pytest.mark.skipif(not (PICO / "profiles/collection/deployment.json").exists(), reason="needs PICO-ACT profile")


def make(tmp_path, **kw):
    cfg = BiPiperROSConfig(backend="fake", output_root=str(tmp_path), selftest_timeout_s=5, calibration_dir=tmp_path / "cal", **kw)
    return BiPiperROS(cfg)


def events(robot_run):
    out = []
    for f in sorted((robot_run / "episode").glob("events*.jsonl")):
        out += [json.loads(line) for line in f.open()]
    return out


def test_features_without_connect(tmp_path):
    r = make(tmp_path)
    assert list(r.action_features) == motor_keys() and len(motor_keys()) == 14
    assert r.observation_features["scene_fixed"] == (480, 640, 3)
    assert set(r.cameras) == {"left_wrist", "right_wrist", "scene_fixed"}


def test_home_follow_timeout_rearm_disconnect(tmp_path):
    r = make(tmp_path, action_timeout_s=0.4)
    r.connect()
    try:
        obs = r.get_observation()
        assert max(abs(obs[f"left_joint{i}.pos"]) for i in range(1, 7)) < 0.03  # homed to zeros
        assert obs["right_wrist"].shape == (480, 640, 3)
        act = {k: 0.0 for k in motor_keys()}
        act["left_gripper.pos"] = act["right_gripper.pos"] = 0.05
        act["left_joint2.pos"] = 0.3  # 0.3 rad away -> blocking approach
        t0 = time.monotonic()
        sent = r.send_action(act)
        assert time.monotonic() - t0 > 1.0
        assert abs(sent["left_joint2.pos"] - 0.3) < 1e-6
        for k in range(30):  # 1 s of 30 Hz actions
            act["left_joint2.pos"] = 0.3 + 0.004 * k
            r.send_action(act)
            time.sleep(1 / 30)
        assert r._mode == "follow"
        time.sleep(1.5)  # no actions -> ownership expires -> measured hold
        assert r._mode == "idle" and not r.gateway.enabled
        r.send_action(act)  # re-arm
        assert r._mode == "follow" and r._stats["rearms"] == 1
        # joint limit: clipped, not rejected
        act["left_joint3.pos"] = 5.0
        sent = r.send_action(act)
        time.sleep(0.2)
        assert r._stats["rejected"].get("joint_limit", 0) == 0
    finally:
        r.disconnect()
    ev = events(r.run_dir)
    kinds = [e["kind"] for e in ev]
    assert "first_action" in kinds and "lerobot_action" in kinds
    states = [e["payload"]["state"] for e in ev if e["kind"] == "session_state"]
    assert states[0] == "STANDBY" and "HOMING" in states and "TELEOP" in states and states[-1] == "CLOSED"
    cmds = [e for e in ev if e["kind"] == "command" and e["payload"].get("operation") is None and "q" in e["payload"]]
    assert len(cmds) > 100
    # command speed never above tracker vmax (+ tolerance for timing jitter)
    left = [(e["host_monotonic_ns"] * 1e-9, e["payload"]["q"]) for e in cmds if e["payload"]["side"] == "left"]
    holds = [e for e in ev if e["kind"] == "stop"]
    assert any(h["payload"]["reason"] == "lerobot_disconnect" for h in holds)
    assert not any(e["kind"] == "guard" and e["payload"].get("operation") == "disable" for e in ev)
    ended = json.loads((r.run_dir / "stack-ended.json").read_text())
    assert ended["stop_semantics"].startswith("gateway measured hold")


def test_dry_run_publishes_nothing(tmp_path):
    r = make(tmp_path, dry_run=True)
    r.connect()
    try:
        act = {k: 0.0 for k in motor_keys()}
        r.send_action(act)
        time.sleep(0.2)
        assert not r.gateway.enabled
        assert r._fake.sends == {"left": 0, "right": 0}
    finally:
        r.disconnect()
    kinds = {e["kind"] for e in events(r.run_dir)}
    assert "dry_run_command" in kinds and "command" not in kinds
