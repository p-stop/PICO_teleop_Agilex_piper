"""Offline plan015 evidence extraction. Never imports or starts robot adapters.

Run from repository root:
  python tools/analyze_signal_timing.py
Requires matplotlib only for the exportable figure; statistics use stdlib.
"""
from bisect import bisect_right
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets/signal-timing"
LOG = ROOT / "artifacts/validation/014-data/replay-014-physical-01/events/events.jsonl"
AUDIT = ROOT / "artifacts/validation/013-data/013-audit-20261019/summary.json"


def percentile(values, p):
    values = sorted(values)
    x = (len(values) - 1) * p
    a = int(x)
    return values[a] + (values[min(a + 1, len(values) - 1)] - values[a]) * (x - a)


def intervals(rows):
    gaps = [1000 * (b[0] - a[0]) for a, b in zip(rows, rows[1:])]
    return {
        "count": len(rows),
        "span_hz": (len(rows) - 1) / (rows[-1][0] - rows[0][0]),
        "gap_ms_median": statistics.median(gaps),
        "gap_ms_p95": percentile(gaps, .95),
        "gap_ms_max": max(gaps),
    }


def extract():
    events = [json.loads(line) for line in LOG.open(encoding="utf-8")]
    start = next(e["host_monotonic_ns"] for e in events
                 if e["kind"] == "workflow_state" and e["payload"]["state"] == "RUNNING")
    end = next(e["host_monotonic_ns"] for e in events
               if e["kind"] == "workflow_state" and e["payload"]["state"] == "COMPLETED")
    receipts = {(e["payload"]["side"], e["payload"].get("seq")): e["host_monotonic_ns"]
                for e in events if e["kind"] == "receipt" and
                e["payload"].get("status") == "published_not_acknowledged" and
                "seq" in e["payload"]}
    data, stats = {}, {}
    for side in ("left", "right"):
        commands, feedback, stamps = [], [], []
        for e in events:
            p, t = e["payload"], e["host_monotonic_ns"]
            if p.get("side") != side:
                continue
            if e["kind"] == "command" and "q" in p and (side, p.get("seq")) in receipts:
                t = receipts[side, p["seq"]]
                if start <= t < end:
                    commands.append([(t - start) / 1e9, *p["q"]])
            if e["kind"] == "feedback" and start <= t < end:
                feedback.append([(t - start) / 1e9, *p["q"]])
                stamps.append(p.get("device_stamp_ns"))
        commands.sort()
        feedback.sort()
        ct = [r[0] for r in commands]
        errors = []
        for row in feedback:
            i = bisect_right(ct, row[0]) - 1
            if i >= 0:
                errors.append([a - b for a, b in zip(commands[i][1:], row[1:])])
        stats[side] = {
            "commands": intervals(commands), "feedback": intervals(feedback),
            "unique_device_stamps": len(set(stamps)),
            "distinct_consecutive_targets": 1 + sum(a[1:] != b[1:] for a, b in zip(commands, commands[1:])),
            "error_definition": "latest confirmed publish target minus feedback, at feedback host event time; sample-weighted, no lag fit",
            "error_samples": len(errors),
            "rmse_rad": [math.sqrt(statistics.mean(r[j] ** 2 for r in errors)) for j in range(6)],
            "max_abs_error_rad": [max(abs(r[j]) for r in errors) for j in range(6)],
        }
        data[side] = {"commands": commands, "feedback": feedback}
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    episodes = [{
        "episode": e["episode"], "duration_s": e["duration_s"], "qc_passed": e["qc_passed"],
        "received_input_events": e["inputs"]["count"],
        "input_events_per_episode_second": e["inputs"]["count"] / e["duration_s"],
        "host_gap_ms": e["inputs"]["host_gap_ms"], "rtt_ms": e["inputs"]["rtt_ms"],
    } for e in audit["episodes"]]
    report = {
        "schema_version": "signal-timing-analysis/1", "date": "2026-10-20",
        "source_log": LOG.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(LOG.read_bytes()).hexdigest(),
        "audit_sha256": hashlib.sha256(AUDIT.read_bytes()).hexdigest(),
        "interval": "RUNNING <= host_monotonic_ns < COMPLETED; excludes alignment and stop holds",
        "running_duration_s": (end - start) / 1e9,
        "timestamp_semantics": "receipt is returned ROS publish, NOT hardware execution ACK; feedback event is host receipt, NOT known hardware sample time",
        "stats": stats, "episodes": episodes, "series": data,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    # Plain script data, allowing offline file:// without fetch or a local server.
    (OUT / "evidence.js").write_text("window.SIGNAL_EVIDENCE=" + json.dumps(report, separators=(",", ":")) + ";\n", encoding="utf-8")
    with (OUT / "replay-series.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["side", "series", "host_elapsed_s", *[f"q{j}_rad" for j in range(1, 7)]])
        for side, series in data.items():
            for name, rows in series.items():
                w.writerows([side, name, *row] for row in rows)
    return report


def plot(report):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "svg.fonttype": "none"})
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharex=True)
    for j in range(6):
        ax = axes.flat[j]
        for side, color in (("left", "#087f8c"), ("right", "#b35b1c")):
            series = report["series"][side]
            c, f = series["commands"], series["feedback"]
            ax.step([r[0] for r in c], [r[j + 1] for r in c], where="post",
                    color=color, ls="--", alpha=.8, label=f"{side}: target (publish returned)")
            ax.plot([r[0] for r in f], [r[j + 1] for r in f], color=color,
                    lw=1.5, label=f"{side}: received feedback")
        ax.set(title=f"Joint {j + 1}", ylabel="Angle (rad)")
        ax.grid(alpha=.2)
    for ax in axes[-1]:
        ax.set_xlabel("Time since RUNNING (s)")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2)
    fig.suptitle("Measured replay: published target vs received feedback\n2026-10-20 | first 3 s | no lag compensation | not continuous ground truth")
    fig.tight_layout(rect=(0, .065, 1, .94))
    fig.savefig(OUT / "replay-tracking.svg")
    fig.savefig(OUT / "replay-tracking.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    evidence = extract()
    plot(evidence)
    print(json.dumps({k: v for k, v in evidence.items() if k != "series"}, indent=2))
