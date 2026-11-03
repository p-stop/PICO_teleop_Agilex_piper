#!/usr/bin/env bash
# VR teleop of the dual Piper through lerobot-teleoperate (robot bi_piper_ros + teleop pico_vr).
# Teleop starts first (HTTPS page + WebRTC on the profile port), then the robot: drivers + cameras,
# self-check, enable, 4 s home. In the headset: A home -> A start -> squeeze to follow -> A end.
# Ctrl+C: measured hold, children stopped; no disable, no home, no gripper close.
# Usage: tasks/lerobot_teleop.sh [--fps=30] [--robot.dry_run=true] [--teleop.input_delay_s=0.06] ...
set -eo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$here/lerobot_env.sh"
exec lerobot-teleoperate --robot.type=bi_piper_ros --teleop.type=pico_vr --fps=30 "$@"
