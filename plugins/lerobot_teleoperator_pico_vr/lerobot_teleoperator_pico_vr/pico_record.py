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

Between episodes (waiting for A start, review, saving) the teleop keeps commanding
the robot (measured hold, home trajectory), so the robot never loses control while
lerobot encodes the videos.
"""
import concurrent.futures
from contextlib import contextmanager
import json
import os
import logging
import threading
import time

from lerobot.scripts import lerobot_record as lr
from lerobot.utils.import_utils import register_third_party_plugins
from lerobot.utils.robot_utils import precise_sleep

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
        self.events = None
        self.fps = 30
        self.in_save = False
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
        self.bridge = EpisodeBridge(kw.get("single_task"), events=self.events,
                                    episode_index=dataset.num_episodes, saved=dataset.num_episodes)
        with self.session.lock:
            if self.session.recorder is not None:
                raise RuntimeError("teleop session already has a recorder")
            self.session.recorder = self.bridge
        self._wrap_dataset(dataset)
        app.emit("pico_record", {"event": "bridge_installed", "dataset_root": str(dataset.root),
                                 "repo_id": dataset.repo_id, "start_episode": dataset.num_episodes})

    def _wrap_dataset(self, dataset):
        save, clear = dataset.save_episode, dataset.clear_episode_buffer

        def save_episode(*a, **k):
            self.in_save = True
            try:
                with self.keepalive():
                    result = save(*a, **k)
            except BaseException as exc:
                self.bridge.fail(f"save_episode: {type(exc).__name__} {exc}".strip())
                raise
            finally:
                self.in_save = False
            self.bridge.committed(True, dataset.num_episodes)
            self._log("saved", episode=dataset.num_episodes - 1)
            return result

        def clear_episode_buffer(*a, **k):
            if self.in_save:  # internal call from save_episode
                return clear(*a, **k)
            with self.keepalive():
                result = clear(*a, **k)
            recorded = self.bridge.state == "DISCARDING"
            self.bridge.committed(False if recorded else None, dataset.num_episodes)
            if recorded:
                self._log("discarded", episode=dataset.num_episodes)
            return result

        dataset.save_episode, dataset.clear_episode_buffer = save_episode, clear_episode_buffer

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
        """Keep the teleop -> robot loop alive while lerobot's main thread encodes/clears."""
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
        index = dataset.num_episodes
        self._log("waiting", episode=index, hint="headset: A home -> A start")
        self.idle_until(lambda: events["stop_recording"] or bridge.begin_recording())
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
    Run those workers at low priority so the VR link and the control loop keep their CPU."""

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
