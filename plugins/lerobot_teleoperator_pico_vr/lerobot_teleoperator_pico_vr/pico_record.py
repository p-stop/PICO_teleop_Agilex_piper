"""pico-record: lerobot-record where the PICO headset buttons drive the episodes.

Same command line as lerobot-record (--robot.type=bi_piper_ros --teleop.type=pico_vr
--dataset.*). The only change is how an episode starts and ends: instead of fixed
episode/reset timers, the 023 collect workflow in the headset decides:

    A (STANDBY) home -> A (READY) start: lerobot starts recording this episode
    squeeze to follow ... A (TELEOP): episode ends -> REVIEW in the headset
    A (REVIEW): save (dataset.save_episode)    X (REVIEW): discard and re-record

Keyboard (lerobot's listener, if it works on this terminal) still works:
right arrow = end episode / save it in review, left arrow = discard and re-record,
Esc = save the current episode and stop. --dataset.episode_time_s is only a safety
limit (the episode then goes to review like an A end); --dataset.reset_time_s is unused.

Saving runs in the background (background_save.py / save_worker.py): A save queues the
episode and the headset is back in STANDBY at once, so the next episode can be recorded
while the previous ones are written, one process per episode, in order, at nice 10.
At the end (episodes done, Esc or Ctrl+C) pico-record waits for the queued saves.

Between episodes (waiting for A start, review) and while waiting for the saves at the
end, the teleop keeps commanding the robot (measured hold, home trajectory), so the
robot never loses control.
"""
import concurrent.futures
from contextlib import contextmanager
import json
import os
import logging
import threading
import time

from lerobot.datasets import dataset_metadata
from lerobot.datasets.feature_utils import validate_episode_buffer
from lerobot.scripts import lerobot_record as lr
from lerobot.utils.import_utils import register_third_party_plugins
from lerobot.utils.robot_utils import precise_sleep

from .background_save import SaveQueue
from .record_bridge import EpisodeBridge

logger = logging.getLogger("pico_record")
_original_record_loop = lr.record_loop
ENCODER_NICE = 10


def _say(event, **fields):
    print(json.dumps({"event": event, **fields}, ensure_ascii=False), flush=True)


class Driver:
    """Runs on lerobot's main thread; owns the bridge between the headset session and lerobot."""

    def __init__(self):
        self.bridge = self.robot = self.teleop = self.dataset = self.session = None
        self.saver = None
        self.next_index = None  # episode index of the buffer being recorded (saves may still be queued)
        self.synced = 0  # saver.done when the dataset's info was last reloaded
        self.events = None
        self.fps = 30
        self.lock = threading.Lock()  # one caller of get_action/send_action at a time

    # ---------------------------------------------------------------- setup
    def install(self, kw):
        if self.bridge is not None:
            return
        teleop, dataset = kw.get("teleop"), kw["dataset"]
        app = getattr(teleop, "app", None)
        if app is None or getattr(app, "session", None) is None:
            raise RuntimeError("pico-record needs --teleop.type=pico_vr (the headset session drives the episodes)")
        self.robot, self.teleop, self.dataset, self.session = kw["robot"], teleop, dataset, app.session
        self.events, self.fps = kw["events"], kw["fps"]
        self.next_index = dataset.num_episodes
        self.bridge = EpisodeBridge(kw.get("single_task"), events=self.events,
                                    episode_index=dataset.num_episodes, saved=dataset.num_episodes)
        with self.session.lock:
            if self.session.recorder is not None:
                raise RuntimeError("teleop session already has a recorder")
            self.session.recorder = self.bridge
        self.saver = SaveQueue(dataset, nice=ENCODER_NICE, on_saved=self._saved, on_failed=self._save_failed)
        self._wrap_dataset(dataset)
        app.emit("pico_record", {"event": "bridge_installed", "dataset_root": str(dataset.root),
                                 "repo_id": dataset.repo_id, "start_episode": dataset.num_episodes})

    def _wrap_dataset(self, dataset):
        save, clear, finalize = dataset.save_episode, dataset.clear_episode_buffer, dataset.finalize

        def save_episode(episode_data=None, parallel_encoding=True):
            if episode_data is not None:  # not used by lerobot-record: lerobot's own in-process save
                return save(episode_data, parallel_encoding)
            writer, index = dataset.writer, self.next_index
            try:
                with self.keepalive():
                    writer._wait_image_writer()  # this episode's PNG frames are complete on disk
                buffer = writer.episode_buffer
                frames = int(buffer["size"])
                validate_episode_buffer(buffer, index, dataset.meta.features)
                pending = self.saver.submit(index, buffer)
            except BaseException as exc:
                self.bridge.fail(f"save_episode: {type(exc).__name__} {exc}".strip())
                raise
            self.next_index = index + 1
            writer.episode_buffer = writer._create_episode_buffer(episode_index=self.next_index)
            self.bridge.committed(True, self.next_index)
            self._log("save_queued", episode=index, frames=frames, pending=pending)

        def clear_episode_buffer(*a, **k):
            with self.keepalive():
                result = clear(*a, **k)
            # lerobot numbers a new buffer by the saved episodes; queued saves are not counted there yet
            dataset.writer.episode_buffer = dataset.writer._create_episode_buffer(episode_index=self.next_index)
            recorded = self.bridge.state == "DISCARDING"
            self.bridge.committed(False if recorded else None, self.next_index)
            if recorded:
                self._log("discarded", episode=self.next_index)
            return result

        def finalize_dataset(*a, **k):
            self.wait_for_saves()
            self._sync_info(strict=True)
            return finalize(*a, **k)

        dataset.save_episode, dataset.clear_episode_buffer = save_episode, clear_episode_buffer
        dataset.finalize = finalize_dataset

    # ---------------------------------------------------------------- background saves
    def _saved(self, episode, result, pending):  # saver thread
        self._log("saved", episode=episode, save_s=result["save_s"], pending=pending)

    def _save_failed(self, episode, error, job_dir):  # saver thread
        self._log("save_failed", episode=episode, error=error, job_dir=job_dir)
        self.bridge.fail(f"background save: {error}")

    def _check_saver(self):
        if self.saver.error:
            raise RuntimeError(f"pico-record background save failed: {self.saver.error}")

    def _sync_info(self, strict=False):
        """Reload info.json (episode/frame totals) after background saves; main thread only."""
        done = self.saver.done
        if done == self.synced:
            return
        try:
            self.dataset.meta.info = dataset_metadata.load_info(self.dataset.meta.root)
        except Exception:
            if strict:
                raise
            return  # a save process may be rewriting info.json right now; next time
        self.synced = done

    def wait_for_saves(self):
        if self.saver is None or self.saver.wait_idle(0):
            return
        self._log("waiting_for_saves", pending=self.saver.pending)
        with self.keepalive():
            while True:
                try:
                    if self.saver.wait_idle(0.5):
                        break
                except KeyboardInterrupt:
                    # Stopping now would leave the dataset with half-written episodes; the save
                    # processes run in their own session and are not hit by Ctrl+C.
                    logger.warning("pico-record: still saving %d episode(s); waiting for them (robot stays held)",
                                   self.saver.pending)
        if self.saver.error:
            logger.error("pico-record: background save failed: %s", self.saver.error)

    # ---------------------------------------------------------------- control without recording
    def step(self):
        with self.lock:
            self.robot.send_action(self.teleop.get_action())

    def idle_until(self, done, timeout=None):
        period = 1.0 / self.fps
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            t = time.perf_counter()
            if done():
                return True
            if deadline is not None and time.monotonic() > deadline:
                return False
            self.step()
            precise_sleep(max(0.0, period - (time.perf_counter() - t)))

    @contextmanager
    def keepalive(self):
        """Keep the teleop -> robot loop alive while lerobot's main thread is busy."""
        stop = threading.Event()

        def run():
            period = 1.0 / self.fps
            while not stop.is_set():
                t = time.perf_counter()
                try:
                    self.step()
                except Exception as exc:  # surfaces again on the main loop's next step
                    logger.warning("pico-record keepalive: %s", exc)
                    stop.wait(0.2)
                stop.wait(max(0.0, period - (time.perf_counter() - t)))
        thread = threading.Thread(target=run, name="pico-record-keepalive", daemon=True)
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join(2)

    # ---------------------------------------------------------------- episode
    def _log(self, event, **fields):
        _say("pico_record_" + event, **fields)
        try:
            self.teleop.app.emit("pico_record", {"event": event, **fields})
        except Exception:
            pass

    def _session_state(self):
        with self.session.lock:
            return self.session.state

    def _commit_session(self, save):
        """A keyboard decision: move the headset session on like A/X in REVIEW would."""
        deadline = time.monotonic() + 2.0
        while self._session_state() == "TELEOP" and time.monotonic() < deadline:
            self.step()
            time.sleep(1.0 / self.fps)
        with self.session.lock:
            if self.session.state in ("FINALIZING", "REVIEW"):
                self.session._transition("COMMITTING", "saving_episode" if save else "discarding_episode")

    def episode(self, kw):
        events, bridge, dataset = self.events, self.bridge, self.dataset
        self._check_saver()
        self._sync_info()
        index = self.next_index
        self._log("waiting", episode=index, saves_pending=self.saver.pending, hint="headset: A home -> A start")

        def start():
            self._check_saver()
            return events["stop_recording"] or bridge.begin_recording()
        self.idle_until(start)
        if bridge.state != "RECORDING":  # Esc before the episode started: nothing to save
            events["rerecord_episode"], events["exit_early"] = True, False
            return
        events["exit_early"] = events["rerecord_episode"] = False
        self._log("recording", episode=index)
        t0 = time.perf_counter()
        _original_record_loop(**kw)
        elapsed = time.perf_counter() - t0
        frames = _buffered_frames(dataset)
        if events["stop_recording"]:
            reason = "keyboard_stop"
        elif events["rerecord_episode"]:
            reason = "keyboard_rerecord"
        elif kw.get("control_time_s") is not None and elapsed >= kw["control_time_s"] - 1.0 / self.fps:
            reason = "episode_time_limit"
        else:
            reason = "keyboard_end"  # only used if the session did not end it (A end / pause set their own)
        bridge.end_recording(frames, self.fps, reason)
        events["exit_early"] = False  # a late A-end flag must not count as a keyboard save
        qc = bridge.snapshot()["qc"]
        self._log("review", episode=index, qc=qc, hint="headset: A save / X discard")

        def decided():
            if bridge.state in ("SAVING", "DISCARDING"):
                return True
            if events["rerecord_episode"]:
                save = False
            elif events["stop_recording"] or events["exit_early"]:
                save = True
            else:
                return False
            events["exit_early"] = False
            bridge.external_decision(save)
            self._commit_session(save)
            return True
        self.idle_until(decided)
        if bridge.state == "DISCARDING":
            events["rerecord_episode"] = True
        else:
            events["rerecord_episode"] = False
        events["exit_early"] = False


def _buffered_frames(dataset):
    # lerobot 0.6.1 keeps the episode buffer on dataset.writer (older versions: on the dataset).
    holder = getattr(dataset, "writer", None) or dataset
    buffer = getattr(holder, "episode_buffer", None)
    return int(buffer["size"]) if buffer else 0


DRIVER = Driver()


def pico_record_loop(**kw):
    if kw.get("dataset") is None:
        return  # lerobot's reset phase: the headset workflow (A home, A start) replaces it
    DRIVER.install(kw)
    DRIVER.episode(kw)


class _NiceProcessPool(concurrent.futures.ProcessPoolExecutor):
    """lerobot encodes each camera's video in a worker process when an episode is saved.
    Run those workers at low priority so the VR link and the control loop keep their CPU.
    (Saves now run in save_worker processes, already at nice 10; kept for lerobot's own paths.)"""

    def __init__(self, *args, **kwargs):
        if kwargs.get("initializer") is None:
            kwargs["initializer"], kwargs["initargs"] = os.nice, (ENCODER_NICE,)
        super().__init__(*args, **kwargs)


def main():
    concurrent.futures.ProcessPoolExecutor = _NiceProcessPool  # used by lerobot's DatasetWriter.save_episode
    lr.record_loop = pico_record_loop
    register_third_party_plugins()
    lr.record()


if __name__ == "__main__":
    main()
