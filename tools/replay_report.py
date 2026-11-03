"""Acceptance report for a bi_piper_ros replay run (reads the run journal + the replayed dataset).

- tracking: measured feedback vs published command (zero-order hold), plus best lag
- jitter: high-frequency RMS (deviation from a 0.25 s moving average) of commands and feedback, mrad
- replay vs original: feedback at each replayed frame vs the recorded observation.state of that frame
"""
import argparse
import glob
import json
from pathlib import Path

import numpy as np

SIDES = ("left", "right")


def load(run):
    fb = {s: [] for s in SIDES}; cmd = {s: [] for s in SIDES}; acts = []; teleop = []; state = None; t_state = None
    files = sorted(glob.glob(str(Path(run) / "episode/events*.jsonl")), key=lambda p: (p.count("."), p))
    for f in files:
        for line in open(f):
            if '"kind": "pose_feedback"' in line:
                continue
            e = json.loads(line); k, p, t = e["kind"], e["payload"], e["host_monotonic_ns"] * 1e-9
            if k == "feedback":
                fb[p["side"]].append((t, p["q"], p["gripper"]))
            elif k == "command" and "q" in p and p.get("operation") is None:
                cmd[p["side"]].append((t, p["q"]))
            elif k == "lerobot_action":
                acts.append((t, p["index"], p["q"], p["gripper_m"]))
            elif k == "session_state":
                if state == "TELEOP":
                    teleop.append((t_state, t))
                state, t_state = p["state"], t
    if state == "TELEOP":
        teleop.append((t_state, 1e18))
    return fb, cmd, acts, teleop


def hf_rms(t, x, window_s=0.25):
    if len(t) < 20:
        return [float("nan")] * x.shape[1]
    w = max(3, int(round(window_s / np.median(np.diff(t)))))
    k = np.ones(w) / w
    sm = np.vstack([np.convolve(x[:, j], k, "same") for j in range(x.shape[1])]).T
    d = (x - sm)[w:-w]
    return (1000 * np.sqrt((d ** 2).mean(0))).round(2).tolist()


def stats(a):
    a = np.abs(np.asarray(a))
    return {"p50": round(float(np.median(a)), 4), "p95": round(float(np.percentile(a, 95)), 4), "max": round(float(a.max()), 4)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run")
    ap.add_argument("--dataset-root", required=True)
    ap.add_argument("--repo-id", required=True)
    ap.add_argument("--episode", type=int, default=0)
    ap.add_argument("--json")
    args = ap.parse_args()
    fb, cmd, acts, teleop = load(args.run)
    inside = lambda t: any(a <= t <= b for a, b in teleop)
    rep = {"run": str(args.run), "teleop_windows_s": [round(b - a, 1) if b < 1e17 else "open" for a, b in teleop],
           "actions": len(acts)}
    from lerobot.datasets import LeRobotDataset
    ds = LeRobotDataset(args.repo_id, root=args.dataset_root, episodes=[args.episode])
    S = np.stack(ds.hf_dataset.with_format("numpy")["observation.state"]).astype(float)
    for si, side in enumerate(SIDES):
        F = [(t, q, g) for t, q, g in fb[side] if inside(t)]
        C = [(t, q) for t, q in cmd[side] if inside(t)]
        if len(C) < 20 or len(F) < 20:
            rep[side] = "too few samples"; continue
        ft = np.array([x[0] for x in F]); fq = np.array([x[1] for x in F]); fg = np.array([x[2] for x in F])
        ct = np.array([x[0] for x in C]); cq = np.array([x[1] for x in C])
        r = {"feedback_hz": round(1 / np.median(np.diff(ft)), 1), "command_hz": round(1 / np.median(np.diff(ct)), 1)}
        best = None
        for lag in np.arange(0, 0.6, 0.01):
            idx = np.clip(np.searchsorted(ct, ft - lag, side="right") - 1, 0, len(ct) - 1)
            err = fq - cq[idx]
            rms = float(np.sqrt((err ** 2).mean()))
            if lag == 0:
                r["tracking_error_rad_lag0"] = stats(np.abs(err).max(1))
            if best is None or rms < best[1]:
                best = (lag, rms, err)
        r["tracking_best_lag_s"] = round(float(best[0]), 2)
        r["tracking_error_rad_at_best_lag"] = stats(np.abs(best[2]).max(1))
        r["tracking_error_rms_per_joint_mrad_at_best_lag"] = (1000 * np.sqrt((best[2] ** 2).mean(0))).round(1).tolist()
        r["command_hf_rms_mrad"] = hf_rms(ct, cq)
        r["feedback_hf_rms_mrad"] = hf_rms(ft, fq)
        cv = np.abs(np.diff(cq, axis=0)) / np.maximum(np.diff(ct), 1e-3)[:, None]
        r["command_speed_rad_s_max"] = round(float(cv.max()), 3)
        # replay vs original: feedback at the time each frame was sent vs recorded observation.state
        js = slice(0, 6) if side == "left" else slice(7, 13)
        gi = 6 if side == "left" else 13
        dev, gdev = [], []
        for t, index, _, _ in acts:
            if not inside(t) or index - 1 >= len(S):
                continue
            j = min(np.searchsorted(ft, t), len(ft) - 1)
            dev.append(fq[j] - S[index - 1, js]); gdev.append(fg[j] - S[index - 1, gi])
        if dev:
            dev = np.array(dev)
            r["replay_minus_original_state_rad"] = stats(np.abs(dev).max(1))
            r["replay_minus_original_state_rms_per_joint_mrad"] = (1000 * np.sqrt((dev ** 2).mean(0))).round(1).tolist()
            r["gripper_replay_minus_original_m"] = stats(gdev)
        rep[side] = r
    text = json.dumps(rep, indent=2)
    print(text)
    if args.json:
        Path(args.json).write_text(text)


if __name__ == "__main__":
    main()
