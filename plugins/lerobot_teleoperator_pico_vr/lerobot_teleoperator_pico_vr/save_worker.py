"""Saves one recorded episode into the lerobot dataset, in its own process (pico-record).

pico_record hands each recorded episode over as a pickled job (the episode buffer:
joint values plus the paths of the PNG frames already on disk). This process reopens
the dataset (LeRobotDataset.resume), runs lerobot's own save_episode for that one
episode and finalizes, so data, metadata and videos are closed on disk when it exits.

Why a process: stats, parquet writing and video muxing used to run on the recording
process's main thread and starved the pure-Python WebRTC link to the headset (11-04,
RTT -> 780 ms while saving). Here they run at nice 10 with their own GIL, and the
recording process can record the next episode meanwhile.

Usage: python -m lerobot_teleoperator_pico_vr.save_worker <job.pkl>   (writes <job dir>/result.json)
"""
import json
import logging
import os
import pickle
import sys
import time
from pathlib import Path


def main():
    job_path = Path(sys.argv[1])
    with open(job_path, "rb") as f:
        job = pickle.load(f)
    os.nice(job.get("nice", 10))  # inherited by lerobot's per-camera encoder processes
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(asctime)s pico-save %(message)s")
    t0 = time.monotonic()

    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    dataset = LeRobotDataset.resume(
        job["repo_id"], root=job["root"], batch_encoding_size=1,
        rgb_encoder=job["rgb_encoder"], depth_encoder=job["depth_encoder"],
        encoder_threads=job["encoder_threads"], streaming_encoding=False,
    )
    dataset.writer.episode_buffer = job["buffer"]
    dataset.save_episode(parallel_encoding=job.get("parallel_encoding", True))
    dataset.finalize()
    result = {"episode": job["episode"], "total_episodes": dataset.meta.total_episodes,
              "total_frames": dataset.meta.total_frames, "save_s": round(time.monotonic() - t0, 2)}
    tmp = job_path.parent / "result.json.tmp"
    tmp.write_text(json.dumps(result))
    tmp.replace(job_path.parent / "result.json")


if __name__ == "__main__":
    main()
