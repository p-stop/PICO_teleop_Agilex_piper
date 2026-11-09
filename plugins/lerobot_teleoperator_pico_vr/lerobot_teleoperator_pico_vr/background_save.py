"""Background episode saving for pico-record.

Each saved episode becomes a job for save_worker.py (its own process, nice 10). Jobs run
one at a time in recording order: lerobot numbers episodes by the dataset's episode
count, so episode N can only be written after N-1. Meanwhile the recording process
goes on with the next episode; its frames go to their own episode-00000N image dirs.

If a save fails, the later queued jobs are not run (their numbering depends on it);
their jobs and PNG frames stay on disk and the error is reported.
"""
import json
import logging
import pickle
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

logger = logging.getLogger("pico_record")


class SaveQueue:
    def __init__(self, dataset, *, nice=10, on_saved=None, on_failed=None):
        self.dataset, self.nice = dataset, nice
        self.on_saved, self.on_failed = on_saved, on_failed
        self.jobs = queue.Queue()
        self.cond = threading.Condition()
        self.pending = 0  # queued or running
        self.done = 0
        self.error = None
        self.thread = threading.Thread(target=self._run, name="pico-record-saver", daemon=True)
        self.thread.start()

    def submit(self, episode, buffer):
        """Hand a finished episode buffer (PNG frames already flushed) to the saver."""
        with self.cond:
            if self.error:
                raise RuntimeError(f"an earlier background save failed: {self.error}")
        writer = self.dataset.writer
        job = {"episode": episode, "buffer": buffer, "repo_id": self.dataset.repo_id,
               "root": str(self.dataset.root), "rgb_encoder": writer._rgb_encoder,
               "depth_encoder": writer._depth_encoder, "encoder_threads": writer._encoder_threads,
               "nice": self.nice}
        job_dir = Path(tempfile.mkdtemp(prefix=f"pico_save_ep{episode:03d}_"))
        with open(job_dir / "job.pkl", "wb") as f:
            pickle.dump(job, f)
        with self.cond:
            self.pending += 1
            pending = self.pending
        self.jobs.put((episode, job_dir))
        return pending

    def wait_idle(self, timeout=None):
        with self.cond:
            return self.cond.wait_for(lambda: self.pending == 0, timeout)

    def _run(self):
        while True:
            episode, job_dir = self.jobs.get()
            with self.cond:
                skipped = self.error
            if skipped:
                err = f"episode {episode}: not saved, an earlier save failed ({skipped})"
                self._failed(episode, err, job_dir)
                continue
            try:
                proc = subprocess.Popen(
                    [sys.executable, "-m", "lerobot_teleoperator_pico_vr.save_worker", str(job_dir / "job.pkl")],
                    start_new_session=True)  # Ctrl+C on the terminal does not cut a save in half
                code = proc.wait()
                if code != 0:
                    raise RuntimeError(f"save process exited with code {code} (its log is above)")
                result = json.loads((job_dir / "result.json").read_text())
                if result["total_episodes"] != episode + 1:
                    raise RuntimeError(f"dataset has {result['total_episodes']} episodes after saving episode {episode}")
            except Exception as exc:
                self._failed(episode, f"episode {episode}: {exc}", job_dir)
                continue
            shutil.rmtree(job_dir, ignore_errors=True)
            with self.cond:
                self.pending -= 1
                self.done += 1
                pending = self.pending
                self.cond.notify_all()
            if self.on_saved:
                self.on_saved(episode, result, pending)

    def _failed(self, episode, err, job_dir):
        logger.error("pico-record background save failed: %s; job kept in %s", err, job_dir)
        with self.cond:
            self.error = self.error or err
            self.pending -= 1
            self.cond.notify_all()
        if self.on_failed:
            self.on_failed(episode, err, str(job_dir))
