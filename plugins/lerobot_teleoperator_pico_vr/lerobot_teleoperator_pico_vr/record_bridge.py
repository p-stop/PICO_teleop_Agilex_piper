"""EpisodeBridge: the 023 teleop session's episode recorder, backed by lerobot-record.

TeleopSession drives a recorder through start / finish / decide / snapshot (the same
calls as robot_infra.real_episode.EpisodeRecorder in collect). The bridge implements
that interface, but the frames are written by lerobot's record loop, so the headset
workflow is exactly the collect workflow:

    STANDBY  A -> HOMING -> READY
    READY    A -> PREPARING (bridge STARTING; lerobot starts the episode) -> TELEOP
    TELEOP   A -> FINALIZING (lerobot loop ends) -> REVIEW
    REVIEW   A -> save (dataset.save_episode)   X -> discard (re-record, clear buffer)
    then COMMITTING -> STANDBY when lerobot is done.

Bridge phases: IDLE -> STARTING -> RECORDING -> FINALIZING -> REVIEW -> SAVING|DISCARDING -> IDLE.
Methods called by the session run under the session lock and only change memory;
pico_record's loop (lerobot's main thread) moves the phases forward.
"""
import threading
import time


class EpisodeBridge:
    def __init__(self, task, *, events=None, episode_index=0, saved=0):
        self.cond = threading.Condition(threading.RLock())
        self.events = events if events is not None else {}
        self.task = task
        self.state = "IDLE"
        self.error = None
        self.episode = episode_index
        self.saved = saved
        self.discarded = 0
        self.stop_reason = None
        self.qc = None
        self.frames = 0
        self.started_s = self.ended_s = None
        self.last_commit = None

    # ---------------------------------------------------------------- session side
    def start(self, context):
        with self.cond:
            if self.state != "IDLE":
                raise RuntimeError("recorder is not idle")
            self.state, self.error, self.qc, self.stop_reason = "STARTING", None, None, None
            self.cond.notify_all()

    def finish(self, interrupted=None):
        with self.cond:
            if self.state == "RECORDING":
                self.state, self.stop_reason, self.ended_s = "FINALIZING", interrupted, time.monotonic()
                self.events["exit_early"] = True  # ends lerobot's record_loop on its next tick
            elif self.state == "STARTING":
                self.state, self.stop_reason = "IDLE", interrupted or "cancelled_before_recording"
            self.cond.notify_all()

    def decide(self, save):
        with self.cond:
            if self.state != "REVIEW":
                raise RuntimeError("episode is not ready for review")
            self.state = "SAVING" if save else "DISCARDING"
            self.cond.notify_all()

    def snapshot(self):
        with self.cond:
            return {"state": self.state, "error": self.error, "task": self.task, "task_path": None,
                    "episode": self.episode, "image_storage": "lerobot", "saved_episodes": self.saved,
                    "discarded_episodes": self.discarded, "queue_bytes": 0, "queue_items": 0, "dropped": 0,
                    "qc": dict(self.qc) if self.qc else None, "last_commit": self.last_commit,
                    "pending_path": None, "frames": self.frames}

    # ---------------------------------------------------------------- lerobot side
    def wait_state(self, states, timeout):
        with self.cond:
            self.cond.wait_for(lambda: self.state in states, timeout)
            return self.state

    def begin_recording(self):
        with self.cond:
            if self.state != "STARTING":
                return False
            self.state, self.started_s, self.ended_s, self.frames = "RECORDING", time.monotonic(), None, 0
            self.cond.notify_all()
            return True

    def end_recording(self, frames, fps, reason=None):
        """lerobot's loop returned (A end, pause, keyboard or episode time limit)."""
        with self.cond:
            if self.state == "RECORDING":
                self.stop_reason, self.ended_s = reason, time.monotonic()
            self.frames = int(frames)
            duration = frames / fps if fps else 0.0
            issues = []
            if self.stop_reason and self.stop_reason not in ("episode_time_limit", "keyboard_end"):
                issues.append(f"episode interrupted: {self.stop_reason}")
            if self.stop_reason == "episode_time_limit":
                issues.append("episode_time_s reached")
            if frames < max(1, int(fps)):
                issues.append(f"too short: {frames} frames")
            self.qc = {"passed": not issues, "issues": issues, "frames": int(frames), "duration_s": round(duration, 2)}
            self.state = "REVIEW"
            self.cond.notify_all()

    def external_decision(self, save):
        """Keyboard decision (right arrow / Esc save, left arrow discard)."""
        with self.cond:
            if self.state == "REVIEW":
                self.state = "SAVING" if save else "DISCARDING"
                self.cond.notify_all()
            return self.state

    def committed(self, saved, episode_index=None):
        with self.cond:
            if saved is True:
                self.saved += 1
            elif saved is False:
                self.discarded += 1
            self.last_commit = {"saved": bool(saved), "episode": self.episode, "frames": self.frames}
            if episode_index is not None:
                self.episode = episode_index
            self.state = "IDLE"
            self.cond.notify_all()

    def fail(self, error):
        with self.cond:
            self.error, self.state = str(error), "ERROR"
            self.cond.notify_all()
