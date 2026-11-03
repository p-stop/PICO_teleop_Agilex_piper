"""Report for a pico_vr teleop run (lerobot-teleoperate / lerobot-record with --teleop.type=pico_vr).

Usage (PICO-ACT venv; robot_infra from the 023 release):
  .venv/bin/python tools/teleop_report.py runs/<..._pico_vr_...> [--robot-run runs/<..._lerobot_...>] [--json out.json]

- input: raw_input rate and gaps (host arrival), WebRTC ack timing is not visible here;
- lerobot loop: get_action rate and gaps;
- IK: results per side, follow ratio, reasons, goal -> result latency;
- command jitter: HF RMS (deviation from a 0.25 s moving average) of the teleop's output joints
  (same metric as analyze.py) and, with --robot-run, of the robot's tracker output;
- latency by velocity cross-correlation, only while the clutch is held:
  hand (raw_input grip mapped by the profile alignment) -> IK target (intent; input delay (a) + grip
  filter) -> teleop command (FK; IK + gates + shaping) -> robot command (FK; tracker (b)) -> arm
  feedback (FK). A lag at the search limit or a low correlation means the stage was saturated
  (rate limits, unreachable targets), not a pure delay. Host arrival of the packet is the start: headset-to-host network time
  (about RTT/2 on the page HUD) comes on top.
"""
import argparse
import glob
import json
import sys

import numpy as np

SRC = "/home/ros/zero-wam/PICO-ACT/releases/023-20261103-webrtc-smoothing/src"


def load(run):
    files = sorted(glob.glob(run + "/episode/events*.jsonl"), key=lambda p: (p.count("."), p))
    for f in files:
        for line in open(f):
            if '"kind": "camera' in line or '"kind": "pose_feedback"' in line:
                continue
            yield json.loads(line)


def windows_of(events, state="TELEOP"):
    out, current, since = [], None, None
    for t, s in events:
        if current == state and s != state:
            out.append((since, t))
        if s != current:
            current, since = s, t
    if current == state:
        out.append((since, float("inf")))
    return out


def inside(t, windows):
    t = np.asarray(t)
    mask = np.zeros(t.shape, bool)
    for a, b in windows:
        mask |= (t >= a) & (t <= b)
    return mask


def gaps(t):
    d = np.diff(np.asarray(t))
    if len(d) < 2:
        return None
    return {"n": len(t), "rate_hz": float(1 / np.median(d)), "mean_rate_hz": float(len(d) / (t[-1] - t[0])),
            "gap_ms_p50": float(1e3 * np.median(d)), "gap_ms_p95": float(1e3 * np.percentile(d, 95)), "gap_ms_max": float(1e3 * d.max())}


def hf_rms_mrad(t, q):
    t, q = np.asarray(t), np.asarray(q)
    if len(t) < 60:
        return None
    w = max(3, int(round(0.25 / np.median(np.diff(t)))))
    k = np.ones(w) / w
    hf = (q - np.vstack([np.convolve(q[:, j], k, "same") for j in range(q.shape[1])]).T)[w:-w]
    return [round(float(1e3 * np.sqrt(np.mean(hf[:, j] ** 2))), 2) for j in range(q.shape[1])]


def lag(ta, a, tb, b, mask_windows, *, rate=200.0, max_lag=1.0):
    """Delay of b behind a (s) by cross-correlating velocities on a uniform grid, inside mask windows."""
    if len(ta) < 20 or len(tb) < 20 or not mask_windows:
        return None
    start = max(ta[0], tb[0])
    end = min(ta[-1], tb[-1])
    if end - start < 2:
        return None
    grid = np.arange(start, end, 1 / rate)
    A = np.vstack([np.interp(grid, ta, a[:, j]) for j in range(a.shape[1])]).T
    B = np.vstack([np.interp(grid, tb, b[:, j]) for j in range(b.shape[1])]).T
    k = np.ones(9) / 9  # light smoothing of finite differences
    va = np.vstack([np.convolve(np.gradient(A[:, j], 1 / rate), k, "same") for j in range(A.shape[1])]).T
    vb = np.vstack([np.convolve(np.gradient(B[:, j], 1 / rate), k, "same") for j in range(B.shape[1])]).T
    m = inside(grid, mask_windows)
    if m.sum() < rate:
        return None
    best, best_lag = -np.inf, None
    for s in range(0, int(max_lag * rate)):
        x = va[: len(grid) - s][m[: len(grid) - s]]
        y = vb[s:][m[: len(grid) - s]]
        denom = np.sqrt((x * x).sum() * (y * y).sum())
        if denom <= 0:
            continue
        c = float((x * y).sum() / denom)
        if c > best:
            best, best_lag = c, s / rate
    return None if best_lag is None else {"lag_ms": round(1e3 * best_lag, 1), "correlation": round(best, 3),
                                          "samples_s": round(float(m.sum() / rate), 1)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run")
    p.add_argument("--robot-run")
    p.add_argument("--json")
    args = p.parse_args(argv)
    sys.path.insert(0, SRC)
    from robot_infra.pinocchio_model import PinocchioModel
    cfg = json.load(open(args.run + "/effective-config.json"))
    m = cfg["model"]
    model = PinocchioModel(m["path"], m["base"], m["tip"], m["joint_names"])
    align = np.array(cfg["alignment"], float) * cfg["scale"]
    clutch, trigger = cfg["buttons"]["clutch"], cfg["buttons"]["trigger"]
    tip = lambda q: [r[3] for r in model.fk(q)[:3]]  # noqa: E731

    states, raw, acts = [], [], []
    hand = {"left": [], "right": []}
    engaged = {"left": [], "right": []}
    cmd = {"left": [], "right": []}
    fb = {"left": [], "right": []}
    ik = {"left": [], "right": []}
    goal = {"left": [], "right": []}
    followed = {"left": [], "right": []}
    accept_m = {"accept_max_position_error_m": 0.005, **(cfg.get("teleop_filter") or {})}["accept_max_position_error_m"]
    for e in load(args.run):
        k, pl, t = e["kind"], e["payload"], e["host_monotonic_ns"] * 1e-9
        if k == "session_state":
            states.append((t, pl["state"]))
        elif k == "raw_input":
            raw.append(t)
            for h in pl.get("inputs", []):
                side = h.get("handedness")
                if side in hand and h.get("grip"):
                    buttons = (h.get("gamepad") or {}).get("buttons", [])
                    pressed = len(buttons) > clutch and buttons[clutch]["value"] >= 0.7
                    hand[side].append((t, list(align @ np.array(h["grip"]["position_m"]))))
                    engaged[side].append((t, pressed))
        elif k == "lerobot_teleop_action":
            acts.append(t)
        elif k == "command" and "q" in pl and pl.get("operation") is None:
            cmd[pl["side"]].append((t, pl["q"]))
        elif k == "feedback":
            fb[pl["side"]].append((t, pl["q"]))
        elif k == "intent" and "target" in pl:
            goal[pl["side"]].append((t, [row[3] for row in pl["target"][:3]]))
        elif k == "motion_result" and "result" in pl:
            r = pl["result"]
            ik[pl["side"]].append((t, t - pl["created_s"], pl.get("usable"), r.get("reason"), r.get("accepted")))
            if pl.get("usable") and r.get("accepted") and (r.get("reason") in (None, "converged") or r.get("position_error_m", 1) <= accept_m):
                followed[pl["side"]].append((t, r["positions"]))
    teleop = windows_of(states)
    report = {"run": args.run, "teleop_windows_s": [round(b - a, 1) if b < 1e18 else "open" for a, b in teleop]}
    rt = np.array(raw)
    report["raw_input"] = gaps(rt[inside(rt, teleop)]) if len(rt) else None
    at = np.array(acts)
    report["get_action"] = gaps(at[inside(at, teleop)]) if len(at) else None

    robot_cmd = {"left": [], "right": []}
    if args.robot_run:
        for e in load(args.robot_run):
            k, pl, t = e["kind"], e["payload"], e["host_monotonic_ns"] * 1e-9
            if k == "command" and "q" in pl and pl.get("operation") is None:
                robot_cmd[pl["side"]].append((t, pl["q"]))
    for side in ("left", "right"):
        out = {}
        R = [x for x in ik[side] if inside([x[0]], teleop)[0]]
        if R:
            lat = np.array([x[1] for x in R]) * 1e3
            reasons = {}
            for x in R:
                reasons[str(x[3])] = reasons.get(str(x[3]), 0) + 1
            nf = sum(1 for t, _ in followed[side] if inside([t], teleop)[0])
            out["ik"] = {"results": len(R), "usable": int(sum(1 for x in R if x[2])), "followed_by_gate": nf, "reasons": reasons,
                         "goal_to_result_ms_p50": round(float(np.median(lat)), 1), "goal_to_result_ms_p95": round(float(np.percentile(lat, 95)), 1)}
        C = [(t, q) for t, q in cmd[side] if inside([t], teleop)[0]]
        if C:
            out["teleop_command"] = {**(gaps([t for t, _ in C]) or {}), "hf_rms_mrad": hf_rms_mrad([t for t, _ in C], [q for _, q in C])}
        RC = [(t, q) for t, q in robot_cmd[side] if inside([t], teleop)[0]]
        if RC:
            out["robot_command"] = {**(gaps([t for t, _ in RC]) or {}), "hf_rms_mrad": hf_rms_mrad([t for t, _ in RC], [q for _, q in RC])}
        F = [(t, q) for t, q in fb[side] if inside([t], teleop)[0]]
        if F:
            out["feedback_hf_rms_mrad"] = hf_rms_mrad([t for t, _ in F], [q for _, q in F])
        # clutch-held windows inside TELEOP
        held, since = [], None
        for t, pressed in engaged[side]:
            if pressed and since is None:
                since = t
            elif not pressed and since is not None:
                held.append((since, t)); since = None
        if since is not None:
            held.append((since, engaged[side][-1][0]))
        held = [(max(a, ta), min(b, tb)) for a, b in held for ta, tb in teleop if min(b, tb) - max(a, ta) > 0.5]
        out["clutch_held_s"] = round(sum(b - a for a, b in held), 1)
        stages = {}
        if held:
            H = [(t, p) for t, p in hand[side]]
            th, ph = np.array([t for t, _ in H]), np.array([p for _, p in H])
            series = {"hand": (th, ph)}
            if len(goal[side]) > 20:
                series["ik_target"] = (np.array([t for t, _ in goal[side]]), np.array([p for _, p in goal[side]]))
            for name, data in (("teleop_command", cmd[side]), ("robot_command", robot_cmd[side]), ("feedback", fb[side])):
                if len(data) > 20:
                    series[name] = (np.array([t for t, _ in data]), np.array([tip(q) for _, q in data]))
            names = [n for n in ("hand", "ik_target", "teleop_command", "robot_command", "feedback") if n in series]
            for a, b in zip(names, names[1:]):
                stages[f"{a}->{b}"] = lag(*series[a], *series[b], held)
            F, C = followed[side], cmd[side]
            if len(F) > 20 and len(C) > 20:  # joint space: shaping delay without IK reachability
                stages["ik_followed->teleop_command (joints)"] = lag(np.array([t for t, _ in F]), np.array([q for _, q in F]),
                                                                    np.array([t for t, _ in C]), np.array([q for _, q in C]), held)
            if "feedback" in series:
                stages["hand->feedback (end to end)"] = lag(*series["hand"], *series["feedback"], held, max_lag=1.5)
        out["latency"] = stages
        report[side] = out
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if args.json:
        open(args.json, "w").write(text + "\n")


if __name__ == "__main__":
    main()
