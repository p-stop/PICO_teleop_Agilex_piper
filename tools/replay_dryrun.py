"""Offline dry run of a replay: run the bi_piper_ros tracker on a dataset's `action` sequence.

No ROS, no hardware. Reports the first-frame distance from a start pose (default: profile home),
the raw action speeds, the tracker output speed/acceleration and its lag behind the actions,
and how far the tracker output is from the recorded observation.state.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/lerobot_robot_pico_piper"))
from lerobot_robot_pico_piper.tracker import JointTracker  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--repo-id", required=True)
    p.add_argument("--episode", type=int, default=0)
    p.add_argument("--start", default="home", help="'home' (zeros) or comma-separated 14 values")
    p.add_argument("--hz", type=float, default=60.0)
    p.add_argument("--T", type=float, default=0.08)
    p.add_argument("--vmax", type=float, default=0.8)
    p.add_argument("--amax", type=float, default=4.0)
    p.add_argument("--json", help="write the report here")
    args = p.parse_args()
    from lerobot.datasets import LeRobotDataset
    ds = LeRobotDataset(args.repo_id, root=args.root, episodes=[args.episode])
    names = ds.features["action"]["names"]
    hf = ds.hf_dataset.with_format("numpy")
    A = np.stack(hf["action"]).astype(float)
    S = np.stack(hf["observation.state"]).astype(float) if "observation.state" in ds.features else None
    fps = ds.fps
    J = [i for i, n in enumerate(names) if "gripper" not in n]
    start = np.zeros(14) if args.start == "home" else np.array([float(x) for x in args.start.split(",")])
    trk = {s: JointTracker(6, time_constant_s=args.T, max_velocity_rad_s=args.vmax, max_acceleration_rad_s2=args.amax) for s in (0, 1)}
    trk[0].reset(start[0:6]); trk[1].reset(start[7:13])
    dt = 1 / args.hz
    t_end = len(A) / fps + 1.0
    out_t, out_q = [], []
    t = 0.0
    while t < t_end:
        k = min(int(t * fps), len(A) - 1)
        trk[0].set_target(A[k, 0:6]); trk[1].set_target(A[k, 7:13])
        q = list(trk[0].step(dt)) + list(trk[1].step(dt))
        out_t.append(t); out_q.append(q); t += dt
    out_t, Q = np.array(out_t), np.array(out_q)
    v = np.diff(Q, axis=0) / dt; acc = np.diff(v, axis=0) / dt
    # sample tracker output at the action frame times (end of each frame period)
    idx = np.clip(np.searchsorted(out_t, (np.arange(len(A)) + 1) / fps), 0, len(Q) - 1)
    Qa = Q[idx]
    Aj = A[:, J]
    raw_v = np.abs(np.diff(Aj, axis=0)) * fps
    rep = {
        "frames": len(A), "duration_s": len(A) / fps,
        "first_action_distance_from_start_rad": float(np.abs(A[0, J] - start[J]).max()),
        "action_speed_rad_s": {"p95": float(np.percentile(raw_v.max(1), 95)), "max": float(raw_v.max())},
        "tracker_speed_rad_s_max": float(np.abs(v).max()),
        "tracker_accel_rad_s2_max": float(np.abs(acc).max()),
        "tracker_minus_action_rad": {"p50": float(np.median(np.abs(Qa - Aj).max(1))), "p95": float(np.percentile(np.abs(Qa - Aj).max(1), 95)), "max": float(np.abs(Qa - Aj).max())},
        "params": {"hz": args.hz, "T": args.T, "vmax": args.vmax, "amax": args.amax},
    }
    if S is not None:
        Sj = S[:, J]
        rep["action_minus_recorded_state_rad"] = {"p50": float(np.median(np.abs(Aj - Sj).max(1))), "p95": float(np.percentile(np.abs(Aj - Sj).max(1), 95)), "max": float(np.abs(Aj - Sj).max())}
        rep["tracker_minus_recorded_state_rad"] = {"p50": float(np.median(np.abs(Qa - Sj).max(1))), "p95": float(np.percentile(np.abs(Qa - Sj).max(1), 95)), "max": float(np.abs(Qa - Sj).max())}
        per = np.abs(Qa - Sj)
        rep["tracker_minus_recorded_state_rms_per_joint_mrad"] = (1000 * np.sqrt((per ** 2).mean(0))).round(1).tolist()
    text = json.dumps(rep, indent=2)
    print(text)
    if args.json:
        Path(args.json).write_text(text)


if __name__ == "__main__":
    main()
