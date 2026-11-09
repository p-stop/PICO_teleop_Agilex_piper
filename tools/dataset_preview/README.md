# LeRobot 数据集预览（上传 Hugging Face 前检查）

在 bimanual 上启动（只读，不改数据集）：

    cd /home/ros/zero-wam/PICO-ACT
    bash tasks/dataset_preview.sh                    # 列出 dataset/lerobot 和 ~/.cache/huggingface/lerobot 下的全部数据集
    bash tasks/dataset_preview.sh /某个/数据集目录     # 只看指定的数据集（或它的上级目录）
    bash tasks/dataset_preview.sh --port 8900        # 换端口

然后在同一局域网的电脑上用浏览器打开 http://192.168.87.148:8899/ （启动时会打印地址），Ctrl+C 停止。

- 「概览与检查」：格式版本、回合数、时长、任务描述、特征表；逐帧检查（回合编号、帧数、index、时间戳、NaN、
  文件缺失或多余、视频时长、stats.json 是否过期、录制残留的 images/ 目录、特别短或特别长的回合、关节读数不变、动作跳变、重复回合）。
- 「回合浏览」：三路视频同步播放，14 个关节的 state/action 曲线，点曲线跳帧；
  快捷键：空格 播放，←/→ 逐帧（Shift 跳 1 秒），↑/↓ 换回合，X 标记不要。
- 标记存在 ~/.cache/lerobot_preview/marks/，不写进数据集；概览页会给出用 lerobot-edit-dataset 删掉这些回合、另存为新数据集的命令（只给命令，不执行）。

文件：tools/dataset_preview/server.py（Python 标准库 + numpy + pyarrow，用 PICO-ACT/.venv）、index.html（没有外部依赖）、tasks/dataset_preview.sh（启动脚本）。
