"""Scripted virtual headset: talks to the VR page server exactly like xr-transport.js
(HTTPS offer -> WebRTC data channel 'robot-input', webxr-input/1 packets with the server
freshness ticket). For offline tests only; it never touches hardware by itself.

Script --record sds: pico-record episodes driven by the polled session state (RecordScript).
Script (default): neutral -> A (home) -> wait -> A (start) -> squeeze right grip and move
the right hand on a slow circle (and rotate a little), trigger ramp -> release -> A (end).
"""
import argparse
import asyncio
import json
import math
import ssl
import time
import urllib.request
import uuid

BUTTONS = 7  # PICO/Quest gamepad: 0 trigger, 1 squeeze, 4 A/X, 5 B/Y


def hand(side, position, yaw=0.0, buttons=None):
    values = [0.0] * BUTTONS
    for index, value in (buttons or {}).items():
        values[index] = value
    return {"handedness": side, "source_id": side,
            "grip": {"position_m": list(position), "orientation_xyzw": [0.0, math.sin(yaw / 2), 0.0, math.cos(yaw / 2)]},
            "target_ray": None,
            "gamepad": {"buttons": [{"value": v, "pressed": v > 0.5, "touched": v > 0} for v in values],
                        "axes": [0.0, 0.0, 0.0, 0.0]}}


def default_script(t, *, home_wait=6.0, move_s=10.0, radius=0.05, reach=1.0):
    """(left_hand, right_hand) at script time t; None when the script is over."""
    left0, right0 = (-0.2, 1.0, -0.3), (0.2, 1.0, -0.3)
    a_home, a_start = 1.0, 1.0 + home_wait
    engage = a_start + 1.0
    release = engage + move_s
    a_end = release + 1.0
    right, yaw, rbuttons = right0, 0.0, {}
    if a_home <= t < a_home + 0.2 or a_start <= t < a_start + 0.2 or a_end <= t < a_end + 0.2:
        rbuttons[4] = 1.0  # A (primary)
    if engage <= t < release:
        s = t - engage
        # Like an operator: first lift and reach forward slowly (out of the folded home pose),
        # then a slow circle with a little wrist yaw. Robot = alignment @ hand: hand +y -> up, hand -z -> forward.
        lift = min(1.0, s / 2.5)
        lift = lift * lift * (3 - 2 * lift)
        ramp = min(1.0, max(0.0, (s - 2.5) / 1.0))
        c = max(0.0, s - 2.5)
        right = (right0[0] + ramp * radius * math.sin(2 * math.pi * c / 4.0),
                 right0[1] + 0.10 * reach * lift + ramp * radius * (1 - math.cos(2 * math.pi * c / 4.0)),
                 right0[2] - 0.08 * reach * lift - ramp * 0.03 * math.sin(2 * math.pi * c / 8.0))
        yaw = ramp * 0.15 * math.sin(2 * math.pi * c / 6.0)
        rbuttons[1] = 1.0  # squeeze (clutch)
        rbuttons[0] = min(1.0, s / move_s * 2) if s < move_s / 2 else max(0.0, 2 - s / move_s * 2)  # trigger
    if t > a_end + 1.0:
        return None
    return hand("left", left0), hand("right", right, yaw, rbuttons)


class RecordScript:
    """State-driven script for pico-record: per episode A home -> A start -> move -> A end ->
    A save (or X discard). decisions: list of True (save) / False (discard), one per episode.
    Buttons are pressed when the polled session state asks for them (save time varies)."""
    stateful = True

    def __init__(self, decisions, *, move_s=6.0, radius=0.03, reach=0.4, log=print):
        self.decisions, self.move_s, self.radius, self.reach, self.log = list(decisions), move_s, radius, reach, log
        self.index, self.press_until, self.pressed_for, self.teleop_since, self.done_at = 0, -1.0, None, None, None
        self.pressed_hand = "right"
        self.trace = []

    def _press(self, t, state, hand="right"):
        self.press_until, self.pressed_for, self.pressed_hand = t + 0.2, state, hand
        self.trace.append((round(t, 2), state, hand))

    def __call__(self, t, state):
        left0, right0 = (-0.2, 1.0, -0.3), (0.2, 1.0, -0.3)
        right, yaw, rb, lb = right0, 0.0, {}, {}
        if state == "GONE":
            return None
        if self.done_at is not None:
            return None if t > self.done_at + 1.0 else (hand("left", left0), hand("right", right0))
        if t >= self.press_until and state != self.pressed_for:
            if state in ("STANDBY", "READY") and self.index < len(self.decisions):
                self._press(t, state)
            elif state == "STANDBY" and self.index >= len(self.decisions):
                self.done_at = t
            elif state == "TELEOP":
                if self.teleop_since is None:
                    self.teleop_since = t
                elif t - self.teleop_since > self.move_s + 1.0:
                    self._press(t, state)
                    self.teleop_since = None
            elif state == "REVIEW":
                save = self.decisions[self.index]
                self._press(t, state, "right" if save else "left")  # A save / X discard
                self.log(json.dumps({"event": "sim_headset_decision", "episode": self.index, "save": save}))
                self.index += 1
        if t < self.press_until:
            (rb if self.pressed_hand == "right" else lb)[4] = 1.0
        if state == "TELEOP" and self.teleop_since is not None and t - self.teleop_since < self.move_s:
            s = t - self.teleop_since
            lift = min(1.0, s / 2.0)
            lift = lift * lift * (3 - 2 * lift)
            c = max(0.0, s - 2.0)
            right = (right0[0] + self.radius * math.sin(2 * math.pi * c / 4.0),
                     right0[1] + 0.10 * self.reach * lift + self.radius * (1 - math.cos(2 * math.pi * c / 4.0)),
                     right0[2] - 0.08 * self.reach * lift)
            yaw = 0.1 * math.sin(2 * math.pi * c / 6.0)
            rb[1] = 1.0
            rb[0] = 0.5 * (1 - math.cos(2 * math.pi * s / self.move_s))
        return hand("left", left0, 0.0, lb), hand("right", right, yaw, rb)


async def run(url, *, rate_hz=40.0, script=default_script, jitter_s=0.0, log=print):
    from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
    base = url.rstrip("/")
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    origin = base

    def post_offer(body):
        request = urllib.request.Request(base + "/api/webrtc/offer", data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json", "Origin": origin}, method="POST")
        with urllib.request.urlopen(request, context=context, timeout=15) as response:
            return json.loads(response.read())

    def get_state():
        request = urllib.request.Request(base + "/api/status")
        try:
            with urllib.request.urlopen(request, context=context, timeout=5) as response:
                return (json.loads(response.read()).get("session") or {}).get("state")
        except OSError:
            return "GONE"  # server closed (e.g. pico-record finished)

    pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    dc = pc.createDataChannel("robot-input", ordered=True)
    state = {"ticket": None, "acks": 0, "errors": [], "rtt": []}
    sent_at = {}
    ready = asyncio.Event()

    def on_message(raw):
        message = json.loads(raw)
        if "server_s" in message:
            state["ticket"] = message["server_s"]
        if message.get("type") == "ready":
            ready.set()
        elif message.get("type") == "ack":
            state["acks"] += 1
            if message["seq"] in sent_at:
                state["rtt"].append(time.monotonic() - sent_at.pop(message["seq"]))
        elif message.get("type") == "error":
            state["errors"].append(message.get("error"))
    dc.on("message", on_message)
    stats = {}
    try:
        await pc.setLocalDescription(await pc.createOffer())
        answer = await asyncio.to_thread(post_offer, {"type": pc.localDescription.type, "sdp": pc.localDescription.sdp})
        await pc.setRemoteDescription(RTCSessionDescription(**answer))
        await asyncio.wait_for(ready.wait(), 10)
        sid = "sim-" + uuid.uuid4().hex[:8]
        seq = 0
        period = 1.0 / rate_hz
        # Neutral frames until the session left its self-check (A is only meaningful in STANDBY).
        waited, checked, session_state, poll = time.monotonic(), 0.0, None, None
        neutral = script(0.0, None) if getattr(script, "stateful", False) else script(0.0)
        t0 = None
        next_t = time.monotonic()
        while True:
            now = time.monotonic()
            if t0 is None:
                if now - checked > 0.5:
                    checked = now
                    session_state = await asyncio.to_thread(get_state)
                    if session_state == "STANDBY":
                        t0 = now
                        log(json.dumps({"event": "sim_headset_start", "waited_s": now - waited}))
                    elif session_state == "FAULT" or now - waited > 120:
                        raise RuntimeError(f"session not ready: {session_state}")
                hands = neutral
            else:
                if getattr(script, "stateful", False):
                    if now - checked > 0.25 and (poll is None or poll.done()):
                        if poll is not None:
                            session_state = poll.result()
                        checked = now
                        poll = asyncio.ensure_future(asyncio.to_thread(get_state))
                    hands = script(now - t0, session_state)
                else:
                    hands = script(now - t0)
                if hands is None:
                    break
            packet = {"schema_version": "webxr-input/1", "event": "frame", "session_id": sid, "seq": seq, "epoch": 0,
                      "reference_space": "local-floor", "client_time_ms": (now - waited) * 1000.0,
                      "client_unix_ms": time.time() * 1000.0, "visibility": "visible",
                      "head": {"position_m": [0.0, 1.6, 0.0], "orientation_xyzw": [0.0, 0.0, 0.0, 1.0]},
                      "inputs": list(hands), "last_server_s": state["ticket"]}
            sent_at[seq] = now
            if dc.readyState != "open" and getattr(script, "stateful", False):
                break  # the server went away (pico-record finished)
            dc.send(json.dumps(packet))
            seq += 1
            next_t = max(next_t + period, now - period)
            if jitter_s:
                # Burst-y arrival like the headset: occasionally hold packets back, then flush.
                next_t += jitter_s if seq % 7 == 0 else 0.0
            await asyncio.sleep(max(0.0, next_t - time.monotonic()))
        await asyncio.sleep(0.3)
        rtt = sorted(state["rtt"])
        stats = {"sent": seq, "acks": state["acks"], "errors": state["errors"][:5], "error_count": len(state["errors"]),
                 "rtt_ms_p50": 1e3 * rtt[len(rtt) // 2] if rtt else None,
                 "rtt_ms_p95": 1e3 * rtt[int(len(rtt) * 0.95)] if rtt else None,
                 "duration_s": time.monotonic() - waited}
        log(json.dumps({"event": "sim_headset_done", **stats}))
    finally:
        await pc.close()
    return stats


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("url", help="e.g. https://127.0.0.1:18445/")
    p.add_argument("--rate-hz", type=float, default=40.0)
    p.add_argument("--home-wait", type=float, default=6.0)
    p.add_argument("--move-s", type=float, default=10.0)
    p.add_argument("--radius", type=float, default=0.05)
    p.add_argument("--reach", type=float, default=1.0, help="scale of the initial lift/forward reach")
    p.add_argument("--jitter-s", type=float, default=0.0)
    p.add_argument("--start-delay", type=float, default=0.0, help="wait before connecting (robot still connecting)")
    p.add_argument("--record", default=None, help="pico-record script: one letter per episode, s=A save, d=X discard (e.g. sds)")
    args = p.parse_args(argv)
    time.sleep(args.start_delay)
    if args.record:
        script = RecordScript([c == "s" for c in args.record], move_s=args.move_s, radius=args.radius, reach=args.reach)
    else:
        script = lambda t: default_script(t, home_wait=args.home_wait, move_s=args.move_s, radius=args.radius, reach=args.reach)  # noqa: E731
    stats = asyncio.run(run(args.url, rate_hz=args.rate_hz, script=script, jitter_s=args.jitter_s))
    return 0 if stats.get("acks") and not stats.get("error_count") else 1


if __name__ == "__main__":
    raise SystemExit(main())
