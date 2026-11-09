#!/usr/bin/env bash
# 在浏览器里预览 LeRobot 数据集，上传 Hugging Face 前做检查（只读，不改数据集）。
# 用法:
#   bash tasks/dataset_preview.sh                       # 列出 PICO-ACT/dataset/lerobot 和 ~/.cache/huggingface/lerobot 下的全部数据集
#   bash tasks/dataset_preview.sh /path/to/数据集或上级目录 ...
#   bash tasks/dataset_preview.sh --port 8900           # 换端口
set -e
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PREVIEW_DEFAULT_ROOTS="$here/dataset/lerobot:$HOME/.cache/huggingface/lerobot"
exec "$here/.venv/bin/python" "$here/tools/dataset_preview/server.py" "$@"
