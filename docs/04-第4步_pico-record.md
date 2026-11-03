# 第 4 步：pico-record —— VR 数采经 lerobot-record 录 LeRobot 数据集

日期：2026-11-03。状态：**离线部分完成（全 fake 后端端到端跑通：保存、丢弃重录、时限三条路径）；真机录 3–5 条待用户在场执行。**

范围（用户 11-03 确认）：只要求 VR 数采 + 机械臂能通过 lerobot-record 正常采数据；**不要求**与 robot-infra collect 转出来的数据互通，也不做两者对比。

## 1. 做法

`lerobot-record` 原版按固定时长录（`episode_time_s` 录、`reset_time_s` 复位），提前结束/重录要在机器人终端按方向键，戴头显的人按不了。pico-record 是一个很薄的包装入口：命令行和 lerobot-record 完全一样，只把「一条从哪开始、到哪结束、存不存」交给头显里 023 collect 的原有流程：

```
STANDBY  A → 回 home → READY
READY    A → lerobot 开始录这一条 → TELEOP（握侧键跟随，扳机控夹爪）
TELEOP   A → 这一条结束 → REVIEW（HUD 显示帧数、时长、QC）
REVIEW   A → 保存（dataset.save_episode）    X → 丢弃并重录（clear_episode_buffer）
         → COMMITTING → STANDBY，等下一条
```

实现要点：

- `record_bridge.py`：`EpisodeBridge` 实现 023 `TeleopSession` 用的录制器接口（`start/finish/decide/snapshot`，和 collect 的 `EpisodeRecorder` 同名同语义），装进会话的 `recorder`。所以头显 HUD、A/X 状态机、暂停/断线时把这一条送进 REVIEW 等行为，**全部是 023 原有代码**，没有改 023。
- `pico_record.py`：替换 `lerobot_record.record_loop`，然后调用原版 `lerobot_record.record()`。
  - 录制段：先在不录的状态下跑遥操（get_action → send_action，30 Hz），等头显 A 开始；然后调用**原版** `record_loop` 录帧；A 结束时桥接器置 `events["exit_early"]` 让它退出；再等 A 保存 / X 丢弃。
  - lerobot 的复位段直接跳过（复位由头显流程代替）。
  - 保存/丢弃时（lerobot 主线程在编码视频）起一个保活线程继续 get_action → send_action，机械臂一直受控，不会因 `action_timeout_s` 掉控制权再重新接管。
- 键盘（lerobot 自带监听，能用时）照样可用：→ 结束这一条 / 审阅时保存，← 丢弃重录，Esc 保存当前这条并停止。
- `--dataset.episode_time_s` 只当安全上限（脚本默认 600 s）；到时限这一条照样进 REVIEW，QC 标「episode_time_s reached」，由人决定存不存。

### 1.1 文件

| 文件 | 内容 |
|---|---|
| `plugins/lerobot_teleoperator_pico_vr/lerobot_teleoperator_pico_vr/record_bridge.py` | 桥接器（新） |
| `plugins/lerobot_teleoperator_pico_vr/lerobot_teleoperator_pico_vr/pico_record.py` | 包装入口（新），`python -m lerobot_teleoperator_pico_vr.pico_record` |
| `plugins/lerobot_teleoperator_pico_vr/lerobot_teleoperator_pico_vr/sim_headset.py` | 加了 `--record sds`：按会话状态按键的录制脚本（s=A 保存，d=X 丢弃）；服务端退出时正常结束。原文件备份在 `backups/20261103-pico-record/` |
| `tasks/pico_record.sh` | 入口，默认 `--dataset.fps=30 --dataset.push_to_hub=false --dataset.episode_time_s=600 --dataset.reset_time_s=0 --play_sounds=false`，任务文本默认 "pick up pens on the table and put them into pen holder"，都可以在后面覆盖 |

机械臂插件、遥操插件本体、023 均未改。

## 2. 录出来的数据集

lerobot 标准格式（v3.0），只有 lerobot-record 自己的字段：

| 字段 | shape / 类型 | 内容 |
|---|---|---|
| `action` | 14 × float32 | 左 joint1..6（rad）+ 左夹爪开口（m）+ 右同；= 遥操输出的绝对关节目标（跟踪器 (b) 之前） |
| `observation.state` | 14 × float32 | 同顺序的反馈关节和实际夹爪开口 |
| `observation.images.left_wrist` / `scene_fixed` / `right_wrist` | 480×640×3 视频 | lerobot 默认编码 AV1，crf 30，30 fps |
| `timestamp`、`frame_index`、`episode_index`、`index`、`task_index` | | 30 Hz 等间隔 |

没有深度、原生频率数据、collect 的 QC/溯源（按范围不需要）。遥操和机械臂两个 run 目录（`runs/*_pico_vr_*`、`runs/*_lerobot_*`）照常写事件日志，可以用 `teleop_report.py` / `analyze.py` 分析。

## 3. 离线验证（全 fake 后端，不碰硬件）

复现（在 bimanual 上）：

```bash
cd ~/zero-wam/PICO-ACT; D=/tmp/pico_rec_test; mkdir -p $D
.venv/bin/python -m lerobot_teleoperator_pico_vr.sim_headset https://127.0.0.1:18445/ --start-delay 8 --jitter-s 0.03 --record sds --move-s 6 &
tasks/pico_record.sh --robot.backend=fake --robot.output_root=$D --teleop.backend=fake --teleop.host=127.0.0.1 \
  --teleop.port=18445 --teleop.output_root=$D --dataset.repo_id=local/pico_record_fake --dataset.root=$D/ds --dataset.num_episodes=2
rm -rf $D   # 用完删
```

| 项 | 结果 |
|---|---|
| 流程 | 第 0 条 A 保存；第 1 条 X 丢弃 → 重录 → A 保存；录满 2 条自动退出，退出码 0 |
| 状态序列 | STANDBY→HOMING→READY→PREPARING→TELEOP→FINALIZING→REVIEW→COMMITTING→STANDBY，每条都对 |
| 数据集 | total_episodes 2，total_frames 450（每条 225 帧 = 7.5 s），timestamp 间隔恒为 1/30 s；三路视频各 450 帧 |
| 控制连续性 | 机械臂 4863 次下发，拒绝 0、重新接管 0；send_action 最大间隔 37 ms（含两次保存，每次约 1.8 s） |
| lerobot 循环 | 没有出现「Record loop is running slower」 |
| 时限路径 | `--dataset.episode_time_s=4`：4.0 s 自动结束，REVIEW 里 QC 标 episode_time_s reached，A 保存成功 |
| 原有测试 | 遥操插件 3 passed，机械臂插件 7 passed |

未覆盖：键盘按键路径（这里没有 TTY）；Esc 中途停止。

## 4. 真机录制（待用户在场）

前提：现场有人、急停可用；没有 collect / teleoperate 在跑；桌面按任务摆好；先看左腕相机 USB。

```bash
cd ~/zero-wam/PICO-ACT
tasks/pico_record.sh --dataset.repo_id=local/put_blocks_into_plate \
  --dataset.root=/home/ros/zero-wam/PICO-ACT/dataset/lerobot/put_blocks_into_plate --dataset.num_episodes=5
```

会发生什么：起 HTTPS/WebRTC → 拉起两个驱动和三路相机 → 自检 → **使能、4 s 平滑回 home**；终端打印头显网址。头显里每条：A 回 home → A 开始 → 握侧键操作 → A 结束 → A 保存 / X 丢弃。录满 5 条自动退出；中途 Ctrl+C 也行（已保存的条目保留）。退出时实测保持，不失能、不回 home、不关爪。驱动速度仍是 20%。

注意：
- `--dataset.root` 目录不能已存在（lerobot 新建）；要接着录同一个数据集加 `--resume=true`。
- 每条保存时要编码三路 AV1 视频，真实画面 60 s 一条预计十几秒；这期间头显显示「正在提交采集结果」，机械臂保持受控，等回到 STANDBY 再按 A。
- 先试一条 `--robot.dry_run=true`（会启动驱动和相机，机械臂不动）也可以。

验收：数据集能被 `LeRobotDataset` 读出、条数/帧数对、三路视频完整；`teleop_report.py` 看抖动和延迟与第 3 步同量级。

## 5. 现场第一次录制（11-03 23:03）与修改

### 5.1 发生了什么

run：`runs/20261103T150326Z_pico_vr_bf04a425` + `runs/20261103T150327Z_lerobot_a89000d4`，数据集 `dataset/lerobot/put_blocks_into_plate`。

- 录了一条 104 s（3123 帧，QC 通过），A 保存 → lerobot 开始 `save_episode`。
- lerobot 默认在保存时才编码视频：三路相机各一个进程，用 AV1（libsvtav1）编码 3123 帧，16 个核被占满将近一分钟。
- 保存第 29 s：VR 链路 RTT 涨到 754 ms，头显报 `stale server freshness ticket` → WebRTC 传输错误 → 会话 PAUSED，页面要求刷新。
- 保存第 52 s：`save_episode` 被中断（异常信息为空，与 Ctrl+C 相符）→ 这一条没有存下来，数据集 0 条，只留下三个未完成的临时 mp4。
- 机械臂一侧正常：下发 28385 次，拒绝 0、重新接管 0，驱动和相机都正常退出。

### 5.2 修改

1. **边录边编码，改用 H.264**（`tasks/pico_record.sh` 默认参数，可在后面覆盖）：
   `--dataset.streaming_encoding=true --dataset.encoder_threads=2 --dataset.rgb_encoder.vcodec=h264 --dataset.rgb_encoder.preset=veryfast --dataset.rgb_encoder.crf=23`
   - 远端实测（640×480、30 fps，随机噪声图，最坏情况）每路相机实时编码所需 CPU：AV1 默认 1.1–1.35 核，H.264 veryfast 0.3–0.4 核，ultrafast 约 0.1 核。三路 H.264 veryfast 合计约 1 核。
   - fake 验证：21.4 s 一条（642 帧），按 A 保存到保存完成 < 1 s；三路 h264 640×480 各 642 帧；机械臂拒绝 0、重新接管 0。
   - 数据集的视频编码从 AV1 变为 H.264（lerobot 照常解码）。
2. `save_episode` 失败时报出异常类型（之前 KeyboardInterrupt 显示为空）。
3. **VR 三角形布局**（见 023 CHANGELOG）：头顶相机在上方中间，左右腕部相机在下方左右。

备份：`backups/20261103-pico-record/*.v1`、`backups/20261103-vr-layout/`。

### 5.3 第二次现场断开（11-03 23:22）与修改

run：`runs/20261103T152234Z_pico_vr_8cbd7a13`。这次用的是边录边编码（5.2 第 1 条）。录制开始后控制通道 RTT 从几十 ms 一路涨到 600–770 ms，14 s 后头显报 `stale server freshness ticket` → 传输错误 → 这一条进 REVIEW（247 帧，QC 标中断），之后关闭，没有保存。服务端输入处理 p95 ≤ 50 ms，HTTPS 取画面约 30 ms，机械臂无拒绝。

对比：23:03 那次（保存时才编码）录制 104 s 期间 RTT p50 18 ms、p95 43 ms、最大 144 ms，很平稳。判断：边录边编码的线程和 aiortc（纯 Python 的 WebRTC）在同一个进程里，挤占了控制通道；另外这次录制前 RTT 就有 100 ms 左右的波动，无线链路本身也比 23:03 差一些。fake 回环测试复现不出来（回环没有无线，灰图编码负担也很小），所以这是根据两次现场数据做的判断，没有完全确证。

修改（`tasks/pico_record.sh` 默认参数 + `pico_record.py`）：
- 改回保存时编码（`--dataset.streaming_encoding=false`），保留 H.264 veryfast、每路 2 线程。
- lerobot 保存时为每路相机开一个编码进程；`pico_record` 让这些进程以 nice 10 运行（替换 `concurrent.futures.ProcessPoolExecutor`，加 `os.nice` 初始化），控制回路和 VR 链路优先。
- fake 验证：41.5 s 一条（1239 帧），保存 6.0 s，编码进程 nice 10 已确认，lerobot 循环无「running slower」，虚拟头显 RTT p50 3 ms / p95 6 ms。按比例，100 s 一条保存约 15 s，这期间机械臂保持受控。

备份：`backups/20261103-pico-record/*.v2`。
