"""Read-only export: one episode of a converted collect dataset -> LeRobot dataset with a 14-d `action`.

The converted datasets (e.g. ICL037_fill_pen_holder) have no default `action` column, and
lerobot-replay reads exactly `action` with names from meta/info.json. This writes a small copy:

  action             float32[14]  left_joint1..6.pos, left_gripper.pos, right_joint1..6.pos, right_gripper.pos
                                  = source action.joint (rad, published targets) + action.gripper_width (m)
  observation.state  float32[14]  same names, = source observation.joint + observation.gripper_width

No images (replay does not need them). The source dataset is opened read-only and never modified.
"""
import argparse
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

SIDES = ("left", "right")
NAMES = [f"{s}_{n}.pos" for s in SIDES for n in (*(f"joint{i}" for i in range(1, 7)), "gripper")]


def to14(joint12, grip2):
    j, g = np.asarray(joint12, dtype=np.float32), np.asarray(grip2, dtype=np.float32)
    return np.concatenate([j[:6], g[:1], j[6:], g[1:]]).astype(np.float32)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", required=True, help="converted LeRobot dataset root (read only)")
    p.add_argument("--episode", type=int, required=True)
    p.add_argument("--output-root", required=True, help="new dataset root (must not exist)")
    p.add_argument("--repo-id", required=True)
    args = p.parse_args()
    src, out = Path(args.source), Path(args.output_root)
    if out.exists():
        raise SystemExit(f"output exists: {out}")
    if out.resolve().is_relative_to(src.resolve()):
        raise SystemExit("output must not be inside the source dataset")
    info = json.loads((src / "meta/info.json").read_text())
    frames = []
    for f in sorted(glob.glob(str(src / "data/*/*.parquet"))):
        df = pd.read_parquet(f, columns=["episode_index", "frame_index", "timestamp", "action.joint",
                                         "action.gripper_width", "observation.joint", "observation.gripper_width", "task_index"])
        df = df[df.episode_index == args.episode]
        if len(df):
            frames.append(df)
    if not frames:
        raise SystemExit(f"episode {args.episode} not found")
    df = pd.concat(frames).sort_values("frame_index")
    tasks = pd.read_parquet(src / "meta/tasks.parquet")
    task = tasks.index[tasks.task_index == int(df.task_index.iloc[0])][0] if "task_index" in tasks else str(tasks.index[0])

    from lerobot.datasets import LeRobotDataset
    features = {
        "action": {"dtype": "float32", "shape": (14,), "names": NAMES},
        "observation.state": {"dtype": "float32", "shape": (14,), "names": NAMES},
    }
    ds = LeRobotDataset.create(args.repo_id, fps=int(info["fps"]), features=features, root=out,
                               robot_type="bi_piper_ros", use_videos=False)
    for row in df.itertuples(index=False):
        ds.add_frame({"action": to14(row[3], row[4]), "observation.state": to14(row[5], row[6]), "task": task})
    ds.save_episode()
    ds.finalize()
    a = np.stack([to14(r[3], r[4]) for r in df.itertuples(index=False)])
    summary = {"source": str(src), "source_episode": args.episode, "frames": len(df), "fps": info["fps"],
               "duration_s": len(df) / info["fps"], "task": task, "names": NAMES,
               "first_action": a[0].tolist(), "action_min": a.min(0).tolist(), "action_max": a.max(0).tolist(),
               "source_info_sha_note": "source opened read-only via pandas; nothing written there"}
    (out / "export-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps({k: summary[k] for k in ("source_episode", "frames", "duration_s", "task")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
