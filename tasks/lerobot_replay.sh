#!/usr/bin/env bash
# Replay one episode of a LeRobot dataset (with a 14-d `action`) on the dual Piper.
# Starts drivers + cameras, self-check, enable, 4 s home, smooth approach to frame 0, replay, measured hold.
# Usage: tasks/lerobot_replay.sh --dataset.repo_id=local/x --dataset.root=... --dataset.episode=0 [--robot.dry_run=true]
set -eo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$here/lerobot_env.sh"
exec lerobot-replay --robot.type=bi_piper_ros --play_sounds=false "$@"
