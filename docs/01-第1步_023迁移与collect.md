# 第 1 步：迁移到 PICO-ACT，用 023 跑通 collect

日期：2026-11-03。状态：**离线部分完成；现场 collect 已跑（19:21–19:41），抖动指标达标；QC 因 WebRTC 中断未通过、该条未保存；主观确认待用户答复。**

## 1. 023 是怎么来的

- 位置：`PICO-ACT/releases/023-20261103-webrtc-smoothing/`，`PICO-ACT/current` 指向它。
- 以 `~/robot-infra/releases/021-20261024-webrtc-r3` 为底，合并 022 的遥操平滑。
- **核实结果：022 的实际基底是 018-formal-collection，不是 020。** 对所有旧 release 做 `diff -rq` 比较，018 与 022 的 src 只差 `teleop_session.py`，tests 只差 `test_teleop_session.py`，其余文件只有 README/CHANGELOG 各加了一段说明。所以：
  - 022 的平滑改动 = `diff 018→022` 的这两个文件，补丁见 `docs/023-merge/smooth.diff`、`smooth_test.diff`。
  - 021-r3 和 022 之间其他所有差异（`live_teleop.py`、`provenance.py`、`real_episode.py`、`session_launcher.py`、`web/*.js|html`、缺失的 `control_webrtc.py` 等）都是 020/021 的新功能，022 只是没有它们，**一律以 021-r3 为准**，不需要逐行挑。
- 合并方法：把 `smooth.diff` 以 018 为基底三方打到 021-r3 的 `teleop_session.py` 上（patch 全部 hunk 成功，只有 1 行偏移，无冲突），测试同理。021 相对 018 在该文件的 3 处改动全部保留：
  - 输入校验允许 `'webrtc'`（第 190 行）；
  - `TeleopSession.__init__(..., metrics=None)`；
  - 控制循环的 `control.tick_interval` / `control.tick_work` 统计。
- 新增的平滑内容：`_OneEuro`/`_VectorFilter`/`_QuaternionFilter`、`GripFilter`（锚点平移死区 2.5 mm、旋转死区 0.0175 rad）、IK 收敛门槛（converged 或残差 ≤ 5 mm 才跟随）、`_shape_command`（alpha=0.35 一阶混合 + 0.8 rad/s 限速，headroom 0.9）、`teleop_filter` 校验。参数可在 session.json 加 `teleop_filter` 段覆盖；当前 profile 没有这一段，用默认值。
- CHANGELOG.md、README.md 顶部各加了一条 023 说明。pyproject 版本号未改（运行时不用）。

## 2. PICO-ACT 目录

```
PICO-ACT/
├── 022-20261103-teleop-smoothing/        用户复制过来的 022，原地未动
├── bin/robot-infra                       复制自 ~/robot-infra/bin/robot-infra，未改
├── current -> releases/023-20261103-webrtc-smoothing
├── releases/023-20261103-webrtc-smoothing/
├── releases/022-20261103-teleop-smoothing -> ../022-20261103-teleop-smoothing
├── python-deps/  python-deps-mp4/  python-deps-webrtc-021/    原样复制
├── profiles/collection/{deployment,session,cameras}.json cert.pem key.pem   （目录 700，key.pem 600）
├── tasks/fill_pen_holder.sh  tasks/store_tools_in_toolbox.sh
├── dataset/  runs/
└── docs/
```

- `session.json`、`cameras.json`、`cert.pem`、`key.pem` 与 `~/robot-infra/profiles/local/collection-current/` 字节一致。
- `deployment.json` 只改了 6 个键：`config`、`camera_config`、`cert`、`key` → `PICO-ACT/profiles/collection/`；`output_root` → `PICO-ACT/runs`；`python_paths` → `PICO-ACT/releases/023-.../src` + PICO-ACT 下三个 deps（固定写 release 路径，不经 `current`，便于溯源）。其余（相机驱动、ROS 域 64、端口 8445、advertise_host 192.168.87.148、setup_scripts）不变。
- 两个任务脚本统一成同一格式，都用 `profiles/collection/deployment.json`、数据写 `PICO-ACT/dataset`、从 0 编号跳过已有、MP4。注意：原 `store_tools_in_toolbox.sh` 用的是另一个 profile `021-full-webrtc-qos-ip126`，现在改为与 fill_pen_holder 共用同一 profile。
- 顺带发现：`~/robot-infra/current` 指向的 `releases/022-...` 已不存在（022 被移到了 PICO-ACT），这是个悬空链接。按守则没有改动 `~/robot-infra`。

## 3. 离线验收（已完成）

复现（在 bimanual 上）：

```bash
P=~/zero-wam/PICO-ACT; R=$P/releases/023-20261103-webrtc-smoothing
source /opt/ros/jazzy/setup.bash; source ~/ros2_ws/install/setup.bash
mkdir -p $R/artifacts && cd $R
PYTHONPATH=$R/src:$P/python-deps-webrtc-021:$P/python-deps:$P/python-deps-mp4:$PYTHONPATH python3 -m pytest -q -p no:cacheprovider
$P/tasks/fill_pen_holder.sh --check-only
```

| 检查 | 结果 |
|---|---|
| 023 pytest（系统 pytest 7.4.4） | **309 passed + 1 skipped**；跳过的那条需要 rclpy（全量跑时 PYTHONPATH 被覆盖掉了 ROS 路径），按上面带 `$PYTHONPATH` 的写法重跑 `test_pose_feedback.py` + `test_teleop_session.py` 为 41 passed |
| 021-r3 基线（复制到 /tmp 跑，跑完删除） | 305 passed + 1 skipped；023 多出的 4 条是 022 的平滑测试 |
| `web-transport.test.mjs` | 机器上没有 node，未跑；023 的 `web/` 与 021-r3 完全相同 |
| import | robot_infra 来自 023；aiortc 1.15.0、av 16.1.0、pinocchio 4.0.0、scipy 1.18.0、numpy 2.5.0、rclpy 均可 import |
| session profile 校验 | `validate_session_profile` 通过 |
| `fill_pen_holder.sh --check-only` | `passed_without_device_construction`，exit 0；模型 sha256 22c15f95…，三相机，MP4 |
| `store_tools_in_toolbox.sh --check-only` | exit 0 |
| CAN | can0、can2 均 UP |
| 残留进程 | 无 |
| 023 源码树 sha256（provenance） | `1ab03bf70d1825b0bc8be1b641a6fbb5c3cef57eb297416384b6852abe1f3a8f` |

`--check-only` 不校验驱动模块 hash（启动驱动时才校验），也不连 VR、不开相机。

## 4. 现场采集（待做，需用户在场）

在机器人桌面终端：

```bash
~/zero-wam/PICO-ACT/tasks/fill_pen_holder.sh
```

PICO 浏览器打开 `https://192.168.87.148:8445/`。右手 A 回 Home → A 开始 → 遥操 → A 结束（等写盘和 QC）→ A 保存（左手 X 丢弃）。录 1–2 条后回终端 Ctrl+C。不自动回 Home、不下电、不关爪。

验收：
- episode 的 `qc.json` 通过；
- 用 `analyze.py`（2080 本机 `/home/ccguest/wangxr/tmp/teleop_jitter/`）看指令高频抖动，应与 022 那次（约 1–2 mrad）同一量级，明显低于 021（关节 2 达 34–77 mrad）；
- 用户主观确认抖动减轻。

## 5. 现场结果（2026-11-03 19:21–19:41，收尾记录）

### 5.1 六次启动

| run | 结果 | 原因（看各 run 的相机日志和 `stack-ended.json`） |
|---|---|---|
| `20261103T112147Z_db76821e` | 未进遥操 | 19:25:50 `left_wrist` 报 `VIDIOC_QBUF ... No such device`，左腕相机掉线 |
| `20261103T112549Z_ae073b66` | 未进遥操 | `left_wrist` `VIDIOC_S_FMT ... Device or resource busy` |
| `20261103T112647Z_671e483c` | 未进遥操 | 同上，且 `left_wrist` 进程段错误退出（exit -11） |
| `20261103T112814Z_0df5615d` | 未进遥操 | `left_wrist` busy |
| `20261103T113039Z_c14c4c21` | 未进遥操 | `left_wrist` 序列号 022422072252 一度找不到、`UVCIOC_CTRL_QUERY Protocol error`；`scene_fixed` 进程段错误（exit -11） |
| `20261103T113341Z_85797019` | **遥操 122.3 s，录了 1 条** | 见下 |

前 5 次都卡在相机，集中在左腕相机（USB 掉线或被占用）。建议下次现场先查左腕相机的 USB 线和 hub；与 023 的改动无关（023 没碰相机代码）。

### 5.2 录到的那一条

- 位置：`dataset/fill_pen_holder/episodes/episode_000000_de452bfa819d40609e111153f7a2ea7c/`（mcap 2.4 GB，三路 MP4 约 20 MB）。
- `qc.json`：**passed = false**，唯一问题 `episode interrupted: webrtc_transport_error`。三路相机 ~29.98 fps、最大间隔 ≤ 50 ms，反馈 179 Hz，对齐 3667 行 0 无效——除中断外其余指标都正常。
- 中断经过（`client_event`）：遥操约 122 s 时头显报「WebRTC 发送缓冲积压」，RTT 402 ms、未确认 13 包、缓冲 69 KB → 网关撤销控制权、实测保持 → 进入 REVIEW。之后没有按 A 保存或 X 丢弃，Ctrl+C 关闭，`manifest.json` 的 status 停在 `review`（既未保存也未丢弃）。
- 输入频率：raw_input 34.7 Hz，间隔 p50 28.8 ms、p95 101.6 ms、最大 433 ms（比 11-03 下午的 42 Hz 更差），说明当时无线链路拥塞。

### 5.3 抖动分析（analyze.py，同一套指标）

指令高频抖动 RMS（mrad，按末端高度分 4 段，每段 6 个关节）：

| 臂 | 各高度段的指令 HF RMS 范围 | 对比 |
|---|---|---|
| 左 | 0.60–1.47 | 022：约 1–2；021：关节 2 为 34–77 |
| 右 | 0.13–1.50 | 同上 |

- 指令速度换向：左 0.4–0.6 次/s、右 0.2–0.3 次/s 每关节（几乎不来回摆）。
- **结论：023 的指令抖动与 022 同一量级，比 021 低一个数量级以上，指标验收通过。**
- 附带发现：右臂 IK 有 68% 是 best_effort，位置误差 p95 78 mm，末端高度 0.12–0.22 m 段 cond(J6)=119（接近奇异）。说明右手常把目标带到够不着或姿态冲突的位置，平滑门槛会把这些解挡掉，手感上可能表现为「右臂跟不上」。这条和抖动无关，供调参参考。

### 5.4 其他

- `deployment.json` 的 `advertise_host` 现在是 192.168.87.133（交接时是 .148）；证书是绑 .148 的自签证书，如果头显每次都要手动信任，可以考虑按新 IP 重签。
- 原先放在 PICO-ACT 下的 `022-20261103-teleop-smoothing/` 和 `releases/022-...` 链接在 19:42 左右已不在了（不是本会话删的）。023 不依赖它；`docs/023-merge/` 里的补丁保留了 022 的全部平滑改动。

### 5.5 第 1 步还差的

1. 用户主观确认抖动是否减轻；
2. QC 通过的一条：下次现场（网络正常时）再录 1 条短的，A 保存；
3. 插值 (a)(c) 要不要加进 023 的 collect 由用户定。(b) 二阶跟踪器已在第 2 步的 lerobot 插件里实现，collect 侧暂未加。

复现：

```bash
# 在 2080 上把 analyze.py 传到远端临时目录后（在 bimanual 上）：
P=~/zero-wam/PICO-ACT; R=$P/releases/023-20261103-webrtc-smoothing
PYTHONPATH=$R/src:$P/python-deps python3 analyze.py $P/runs/20261103T113341Z_85797019
```


## 6. 增量：插值 (a)、(c) 加进 023 的 collect（2026-11-03 20:20）

按用户要求直接改在 023 里（没有另起 024）。改前的文件备份在 `backups/023-before-interp-ac-20261103/`（teleop_session.py、solver_worker.py、pinocchio_model.py、两份测试、CHANGELOG.md、session.json）。023 源码树 sha256 由 `1ab03bf7…` 变为 **`150a4655856cde5acaa1c8756207054e62cb64b8bd6983841d182e852e4ed2e0`**，19:33 那条录制记录的是旧值。

代码里新功能**默认全关**，旧行为不变；由 `profiles/collection/session.json` 打开：

| 项 | profile 键 | 采集 profile 取值 | 做法 |
|---|---|---|---|
| (a) 输入固定延迟插值 | `teleop_filter.input_delay_s` / `input_clock_window_s` | 0.1 s / 5 s | 用包里的 `client_time_ms` 加 5 s 滑动最小偏移换到本机时钟；控制周期取 now−0.1 s 处的手柄位姿，位置线性、姿态 slerp；缓冲不够时保持最后一帧，不外推。扳机和离合同样取延迟后的那一帧（与手臂同步）；A/X 按键沿不延迟。 |
| (c) IK 一致性门槛 | `teleop_filter.ik_gate_target_m` / `ik_gate_target_rad` / `ik_gate_joint_jump_rad` | 1 mm / 0.01 rad / 15 mrad | 目标相对上一次被跟随的目标移动 <1 mm 且 <0.01 rad、但关节跳 >15 mrad 时丢弃该解，记 `motion_gate` 事件。 |
| (c) 腕部奇异附近加平滑 | `ik.wrist_smooth_q5_rad` / `ik.wrist_smooth_multiplier` | 0.15 rad / ×10 | IK 种子（上一解）的 $\lvert q_5\rvert<0.15$ 时，关节 4、6 相对上一解的平滑权重乘 10；`motion_result` 里记 `wrist_smooth`。 |

(b) 二阶跟踪器没有加进 collect（collect 仍是 022 的一阶混合加 0.8 rad/s 限速）；(b) 只在 lerobot 插件里。

验证：

- 023 全部测试 **316 passed**（新增 6 个：插值换算到本机时钟和保持、遥操延迟 D 后才跟随且 goal 序号唯一、门槛丢弃与放行、参数校验、`smooth_scale`、求解进程只在 $q_5\approx0$ 时加权）。
- `tasks/fill_pen_holder.sh --check-only`：通过（exit 0）。lerobot 插件 7 个测试在新 profile 下照样通过。
- 用 19:33 那次的真实输入离线重放（60 Hz 控制节拍）：

| | 左手 | 右手 |
|---|---|---|
| 手柄位置高频抖动（mm） | 1.00 → 0.48 | 1.74 → 0.80 |
| 控制周期拿不到新位姿的比例 | 64% → 6% | 64% → 6% |
| 每周期位姿步长 p95（mm） | 2.19 → 1.28 | 3.07 → 2.14 |
| (c) 会被丢弃的 IK 解 | 2 / 1697（0.1%） | 12 / 1233（1.0%） |
| IK 解中 $\lvert q_5\rvert<0.15$ 的比例 | 1% | 12% |

  说明：输入只有约 35 Hz、一阵一阵到，原来 60 Hz 控制周期里有 64% 拿不到新数据（阶梯状）；插值后基本每个周期都有平滑的新位姿。(c) 在 023 数据上丢得很少，因为 022 的收敛门槛已经挡掉了大部分坏解；腕部加权主要作用在右臂。
- 代价：手到机械臂多约 0.1 s 延迟。不喜欢可以把 `input_delay_s` 改成 0（或调小，如 0.06）立即回到原行为，其余各项同理（门槛设 0 关闭，倍数设 1 关闭）。

待现场：用 `tasks/fill_pen_holder.sh` 录 1–2 条，A 保存，看 QC、用 analyze.py 对比指令抖动，请用户比较手感和延迟。
