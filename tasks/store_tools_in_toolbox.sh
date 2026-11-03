#!/usr/bin/env bash
# PICO-ACT task entry point. Network/TLS/device settings live in profiles/collection/deployment.json.
set -euo pipefail
robot_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$robot_root/bin/robot-infra" collect \
  --deployment "$robot_root/profiles/collection/deployment.json" \
  --task store_tools_in_toolbox \
  --dataset-root "$robot_root/dataset" \
  --start-episode 0 \
  --existing skip \
  --image-storage mp4 \
  --duration 0 \
  "$@"
