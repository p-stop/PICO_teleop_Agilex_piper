#!/usr/bin/env bash
# lerobot-record with the PICO headset driving the episodes (pico-record wrapper, 023 collect workflow):
#   A home -> A start (episode starts) -> squeeze to follow -> A end -> A save / X discard (re-record).
# Keyboard (if lerobot's listener works here): right arrow end/save, left arrow discard, Esc save and stop.
# Between episodes the teleop keeps commanding the robot (measured hold / home), also while videos encode.
# Videos: H.264 veryfast, encoded when an episode is saved, in 3 worker processes at nice 10, 2 threads each.
# Not streaming: in-process streaming encoders starved the pure-Python WebRTC link (RTT -> 770 ms, 11-03 23:22).
# Not lerobot's default AV1: it took every core for ~1 min at save time (11-03 23:03).
# Ctrl+C: measured hold, children stopped; no disable, no home, no gripper close.
# Usage: tasks/pico_record.sh --dataset.repo_id=local/<name> --dataset.root=<PICO-ACT/dataset/lerobot/name> \
#          --dataset.num_episodes=5 [--dataset.single_task="..."] [--robot.dry_run=true] ...
set -eo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$here/lerobot_env.sh"
exec python -m lerobot_teleoperator_pico_vr.pico_record \
  --robot.type=bi_piper_ros --teleop.type=pico_vr \
  --dataset.fps=30 --dataset.push_to_hub=false --dataset.episode_time_s=600 --dataset.reset_time_s=0 \
  --dataset.streaming_encoding=false --dataset.encoder_threads=2 \
  --dataset.rgb_encoder.vcodec=h264 --dataset.rgb_encoder.preset=veryfast --dataset.rgb_encoder.crf=23 \
  --dataset.single_task="pick up pens on the table and put them into pen holder" \
  --play_sounds=false "$@"
