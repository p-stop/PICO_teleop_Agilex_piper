# 第 2 步：机械臂插件 bi_piper_ros，用 lerobot-replay 回放已转好的数据

日期：2026-11-03。状态：**离线部分完成（虚拟环境、插件、导出、预演、fake 端到端回放）；真实硬件的 dry-run 和回放待用户在场执行。**

## 1. 虚拟环境 `PICO-ACT/.venv`（2.2 GB）

- `python3 -m venv`（系统 Python 3.12.3），不继承系统包。
- 先按 `~/robot-infra/tools/lerobot-conversion/requirements.lock.txt`（副本在 `docs/lerobot-conversion.requirements.lock.txt`）装，与转换环境版本完全一致：lerobot 0.6.1、torch 2.7.1+cpu、torchvision 0.22.1+cpu、numpy 2.2.6、av 15.1.0、scipy 1.16.3 等。
- 再装 `pin==4.0.0`（cmeel，与 `~/.local` 的系统版本一致）、`aiortc==1.15.0`、`pynput`、`evdev==1.9.3`。
  - pip 自己解出的 aiortc 1.15.0 接受 av 15.1，**av 没有被升级**，与 lerobot 共存。
  - evdev 固定 1.9.3：pip 缓存里有本机编好的 wheel，新版 2.0.0 只有源码包要现场编译。
- 下载量：几乎全部命中本机 pip 缓存，实际只新下载了 torchcodec 的 1.2 MB。日志：`docs/venv-setup.log`、`docs/venv-setup-extra.log`。
- 核实（先 source ROS 两个 setup）：numpy 2.2.6、pinocchio 4.0.0（venv 内）、av 15.1.0、aiortc 1.15.0、torch、lerobot 0.6.1、`rclpy`、`sensor_msgs`、`piper_msgs` 都能在同一进程 import；用 023 的 `PinocchioModel` 加载 URDF（sha256 22c15f95…）、FK 正常；`rclpy.init(domain_id=…)` 建节点正常。
- **没有**把 `python-deps-webrtc-021` 放进 PYTHONPATH。入口 `tasks/lerobot_env.sh` 只 source ROS 和 venv。

## 2. 插件 `plugins/lerobot_robot_pico_piper`（可编辑安装）

注册 `--robot.type=bi_piper_ros`；`register_third_party_plugins()` 能自动发现。

| 文件 | 内容 |
|---|---|
| `config_bi_piper_ros.py` | 配置项，默认全部指向 PICO-ACT 的 collection profile |
| `bi_piper_ros.py` | Robot 实现 |
| `tracker.py` | 插值 (b) 二阶跟踪器（纯 Python） |
| `fake.py` | fake 后端：无 ROS、无硬件，模拟臂按一阶滞后 + 限速跟随，黑图 |
| `tests/` | 7 个测试 |

### 2.1 行为

- **connect()**
  1. 读 `profiles/collection/deployment.json` → session.json / cameras.json，用 023 的 `validate_profile`、`bind_cameras` 校验，用 `create_model` 建 Pinocchio 模型。
  2. 检查没有别的 piper / realsense / robot_infra 进程，检查 can0、can2 是 UP。
  3. 新建 `runs/<时间>_lerobot_<随机>/`，写 `effective-config.json`、`plugin-config.json`。
  4. 与 collect 完全相同地拉起 2 个驱动（`/usr/bin/python3 -m robot_infra.adapters.piper_driver`，厂商驱动 hash 校验照旧，不自动使能）和 3 个 RealSense 节点，ROS 域 64，日志写进 run 目录。
  5. 本进程建 rclpy 节点（独立 Context，domain 64），用 023 的 `PiperROSBackend` + `LiveGateway`；订阅反馈、状态（`err_code`/`arm_status` 非零 → 网关 fault 停止）、三路 RGB。
  6. 自检：双臂反馈新鲜、`backend.ready()`（每个命令话题恰好 1 发布者 1 驱动订阅者）、三路图像 1.5 s 内到达；默认 40 s 超时。
  7. `gateway.arm` + `activate`（使能）→ `home_on_connect`（默认开）：4 s smoothstep 回 home（profile 的全 0），要求误差 ≤ 0.02 rad 并保持 0.3 s。
- **observation_features**：`left_joint1.pos … left_joint6.pos, left_gripper.pos, right_joint1.pos … right_gripper.pos`（14 个 float，rad / m）+ `left_wrist`、`right_wrist`、`scene_fixed`，形状 (480, 640, 3)。图像或反馈超过 0.5 s 没更新时 `get_observation` 报错。
- **action_features**：同样 14 个键，绝对关节目标 + 夹爪开口，语义 = 转换数据集的 `action.joint` + `action.gripper_width`。
- **send_action()**
  - 关节裁剪到 URDF 限位，夹爪裁剪到 0–0.07 m，写一条 `lerobot_action` 事件。
  - 如果当前不在跟随状态且目标离当前指令超过 0.03 rad：**阻塞式平滑移动过去**（smoothstep，峰值速度 0.3 rad/s，至少 1 s），反馈到位后再开始跟随。
  - 之后只更新跟踪器目标。后台线程按 100 Hz 运行跟踪器 (b)：$v_{des}=\mathrm{clip}((q_{tgt}-q_{cmd})/T,\pm v_{max})$，$v \mathrel{+}= \mathrm{clip}(v_{des}-v,\pm a_{max}\Delta t)$，$q_{cmd} \mathrel{+}= v\Delta t$；$T=0.08$ s，$v_{max}=0.8$ rad/s，$a_{max}=4$ rad/s²（都可用 `--robot.tracker_*` 改）。
  - 每个周期走 `gateway.command` + `gateway.submit`，限位、时效、唯一控制权、单发布者等检查全部保留。夹爪变化超过 0.5 mm 或每 0.5 s 走一次 `gripper_only`。
  - 返回值：最近一次实际下发的关节指令（最多晚一个跟踪周期）+ 夹爪目标。
  - 超过 `action_timeout_s`（默认 1 s）没有新动作：不再续约控制权，0.6 s 后网关看门狗做实测保持；下一次 `send_action` 自动重新接管（重新 arm/使能 + 必要时平滑接近）。
- **disconnect()**：网关 `stop` → 实测保持；停跟踪线程、销毁节点，按 SIGINT → SIGTERM → SIGKILL 停子进程，写 `stack-ended.json`。**不失能、不回 home、不关爪。**
- **dry_run**（`--robot.dry_run=true`）：驱动和相机照常起、读反馈、跑跟踪器，但不 arm、不使能、不发布任何指令，只把将要下发的指令记成 `dry_run_command` 事件，并在首帧记录离实测位姿多远。
- 事件日志格式与 collect 相同（`runs/<run>/episode/events*.jsonl`），跟随期间记 `session_state=TELEOP`，所以 `analyze.py` 可以直接分析。

### 2.2 离线测试

```bash
cd ~/zero-wam/PICO-ACT/plugins/lerobot_robot_pico_piper
../../.venv/bin/python -m pytest -q -p no:cacheprovider tests      # 7 passed
```

- 跟踪器：速度 ≤ 0.8 rad/s、加速度 ≤ 4 rad/s²、能收敛；15 Hz ±30 mrad 的来回抖动被压到峰峰值 < 20 mrad；拒绝 NaN。
- fake 端到端（经过真实 `LiveGateway`）：自检 → 回 home → 首帧离 0.3 rad 时阻塞平滑接近 → 跟随 → 停发 1.5 s 后网关实测保持 → 再发自动重新接管 → 超限的关节被裁剪而不是被拒 → 断开时有 `lerobot_disconnect` 实测保持、没有任何 disable。
- dry_run：fake 臂收到的指令数为 0，日志里只有 `dry_run_command`。

## 3. 回放数据：选择导出副本，而不是插件侧映射

**理由：** lerobot 0.6.1 的 `lerobot-replay` 写死读名为 `action` 的列，并用 `meta/info.json` 里 `action` 的 names 拼字典；插件侧映射改不了这一步，只能改 lerobot 的脚本。而且第 4 步训练 ACT 也要 `action` 这个特征，导出副本的键名与 `lerobot-record` 用本插件录出的完全一致，后面可以直接复用。原数据不动。

- 工具：`tools/export_replay_dataset.py`（只读打开原数据）。
- 产物：`dataset/lerobot/ICL037_replay_ep024/`（196 KB，repo_id `local/ICL037_replay_ep024`，episode 0）：
  - `action` float32[14] = 原 `action.joint`（左 6 + 右 6）+ `action.gripper_width`，按插件键名排成 左 6 + 左爪 + 右 6 + 右爪；
  - `observation.state` float32[14] = 原 `observation.joint` + `observation.gripper_width`，同样排列；
  - 不含图像；`export-summary.json` 记录来源。
- 来源：`~/robot-infra/dataset/lerobot/ICL037_fill_pen_holder` 的 episode_index 24（1018 帧，33.9 s）。

### 3.1 为什么选第 24 条（离线预演，`tools/replay_dryrun.py`）

原数据是 021（无滤波）录的，`action.joint` 是已发布的原始目标：全部 49 条的帧间速度峰值 1.8–20 rad/s，与反馈最大差 0.18–1.17 rad。所以回放必须经过跟踪器限速。预演了 4 条比较平稳的候选（起点 = home，60 Hz，T=0.08，v=0.8，a=4）：

| 条目 | 时长 | 首帧离 home | 原始动作速度 p95 / max (rad/s) | 跟踪器滞后 p95 / max (rad) | 跟踪器输出 − 原反馈 p95 / max (rad) |
|---|---|---|---|---|---|
| **24** | 33.9 s | 0 | 0.80 / 2.85 | 0.035 / 0.088 | **0.112 / 0.161** |
| 43 | 29.8 s | 0 | 0.85 / 1.82 | 0.027 / 0.062 | 0.213 / 0.256 |
| 25 | 36.3 s | 0 | 0.86 / 2.46 | 0.030 / 0.077 | 0.179 / 0.237 |
| 16 | 32.5 s | 0 | 0.85 / 2.22 | 0.038 / 0.135 | 0.300 / 0.396 |

第 24 条与原轨迹最接近，选它。完整结果：`docs/02-replay/dryrun_ep024.json`。注意「与原反馈的偏差」大头来自原数据本身（原始目标和反馈就差最多 0.18 rad，当时驱动 20% 速度跟不上），不是回放的问题。

### 3.2 fake 后端跑通真实命令

```bash
tasks/lerobot_replay.sh --robot.backend=fake --robot.output_root=/tmp/pico_fake_runs \
  --dataset.repo_id=local/ICL037_replay_ep024 --dataset.root=$HOME/zero-wam/PICO-ACT/dataset/lerobot/ICL037_replay_ep024 --dataset.episode=0
```

- 退出码 0；1018 帧全部发出，下发 3833 次，**网关拒绝 0 次**，下发速度最大 0.804 rad/s。
- `tools/replay_report.py` 的结果在 `docs/02-replay/fake_replay_report.json`（fake 臂是简化模型，数值只说明链路通了）。

## 4. 硬件回放（待用户在场）

前提：现场有人看着、急停可用；桌面按原任务摆好或清空（回放会按第 24 条的轨迹去够笔、开合夹爪）；没有 collect 在跑。

**第一步：真实 dry-run（会启动驱动和相机，不使能、不动）**

```bash
cd ~/zero-wam/PICO-ACT
tasks/lerobot_replay.sh --robot.dry_run=true \
  --dataset.repo_id=local/ICL037_replay_ep024 --dataset.root=$PWD/dataset/lerobot/ICL037_replay_ep024 --dataset.episode=0
```

看日志里 `first action: X rad from measured pose`，以及自检能否通过（相机能否起来）。

**第二步：真实回放（会使能、4 s 回 home、回放 34 s，结束后原地保持）**

```bash
tasks/lerobot_replay.sh \
  --dataset.repo_id=local/ICL037_replay_ep024 --dataset.root=$PWD/dataset/lerobot/ICL037_replay_ep024 --dataset.episode=0
```

驱动速度仍是 profile 的 20%。中途 Ctrl+C：网关实测保持、停子进程，不失能不关爪。

**验收：**

```bash
.venv/bin/python tools/replay_report.py runs/<最新的 *_lerobot_* 目录> \
  --dataset-root dataset/lerobot/ICL037_replay_ep024 --repo-id local/ICL037_replay_ep024 --json docs/02-replay/hw_replay_report.json
```

报告内容：下发与反馈的跟踪误差（含最佳滞后）、指令和反馈的高频抖动 RMS、回放反馈与原数据 `observation.state` 的偏差、夹爪偏差。也可以对同一 run 跑 `analyze.py` 与第 1 步的数字对比。

## 5. 尚未覆盖 / 注意

- 相机：第 1 步现场左腕相机多次掉线或被占用。插件自检要求三路图像都到；只验证回放动作时可以加 `--robot.cameras_enabled=false` 不起相机（这时观测里没有图像）。
- 回放开始时夹爪会直接走到数据第一帧的开口（夹爪不经过跟踪器，由驱动自己限速）。
- 跟踪器在 lerobot 侧加了约 0.1 s 的滞后（fake 实测最佳滞后 0.11 s）。
- collect（023）侧还没有加 (b)；要不要加由用户定。
