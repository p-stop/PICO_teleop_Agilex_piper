# 第 3 步：VR 遥操插件 pico_vr，跑通 lerobot-teleoperate

日期：2026-11-03。状态：**完成：离线验证 + 真机遥操（22:22）；抖动、延迟结果见第 6 节。用户主观手感待补。**

## 1. 做法：把 023 collect 的遥操原样搬进 lerobot 进程

新建插件包 `plugins/lerobot_teleoperator_pico_vr`（可编辑安装进 `.venv`），注册 `--teleop.type=pico_vr`。lerobot 只按「发行包名以 `lerobot_teleoperator_` 开头」自动发现插件，所以它和机械臂插件 `lerobot_robot_pico_piper` 是同一目录 `plugins/` 下的两个包。

核心思路：**进程内直接用 023 的 `LiveApp` + `TeleopSession`，一行都不改**，只把 `LiveGateway` 的后端换成 `CaptureBackend`。它什么都不发布，把网关「本来要发给驱动的目标」截下来，作为 `get_action()` 的返回值。

```
PICO 头显 ──HTTPS 8445 页面 + WebRTC 数据通道──▶ LiveApp / TeleopSession（023 原样）
   One-Euro 手柄滤波 + 锚点死区 → (a) 0.1 s 固定延迟插值 → IK 子进程（latest-target）
   → 收敛门槛 + (c) 一致性门槛/腕部加权 → 一阶混合 + 限速 → LiveGateway（限位/时效/唯一控制权）
   → CaptureBackend（不发布）──get_action()──▶ lerobot ──send_action()──▶ bi_piper_ros
   → (b) 二阶跟踪器 100 Hz → 机械臂自己的 LiveGateway → 驱动
反馈、相机：遥操插件自己在同一组 ROS 话题上多挂一个订阅者（域 64）
```

所以以下几项都和 023 collect **是同一份代码**：手感参数（profile 的 `teleop_filter`、`ik`）、A/X 流程（A 回 home → A 开始 → 握侧键跟随 → A 结束）、离合锚点（锚点用实测关节的 FK）、夹爪 `independent_trigger`（`follow_trigger` 起始）、插值 (a)，以及 (c) 的门槛和腕部加权（按第 1 步的结论，profile 里都已打开）。VR 页面、证书、端口和 advertise_host 也都一样。

### 1.1 文件

| 文件 | 内容 |
|---|---|
| `config_pico_vr.py` | 配置项，默认指向 PICO-ACT 的 collection profile |
| `pico_vr.py` | Teleoperator 实现 |
| `capture.py` | `CaptureBackend`：截下网关的目标；会话自检时等待 lerobot 循环开始 |
| `fake.py` | fake 反馈：模拟臂跟随本插件自己的输出，相机为灰图（走真实的 CameraIngress/预览） |
| `sim_headset.py` | 脚本化的「虚拟头显」：和 `xr-transport.js` 一样走 HTTPS offer → WebRTC `robot-input` 通道，发 webxr-input/1 包 |
| `tests/test_pico_vr.py` | 3 个测试 |
| `tasks/lerobot_teleop.sh` | 入口：`lerobot-teleoperate --robot.type=bi_piper_ros --teleop.type=pico_vr --fps=30 "$@"` |
| `tools/teleop_report.py` | 遥操报告：输入频率、IK、指令抖动、分段延迟 |

### 1.2 行为

- **connect()**（lerobot 先连遥操、后连机械臂）
  1. 读 deployment → session.json / cameras.json，用 023 的 `validate_profile`、`bind_cameras` 校验。关掉录制；相机管线去掉深度（VR 只要 RGB 预览）。
  2. 检查没有别的 collect/驱动/相机进程（规则与机械臂插件相同）。
  3. 新建 `runs/<时间>_pico_vr_<随机>/`，写 `effective-config.json`、`plugin-config.json`，事件日志 `episode/events*.jsonl`（格式与 collect 相同，`analyze.py` 可以直接分析）。
  4. 建 `LiveApp`：2 个 IK 子进程（spawn）、会话控制线程 60 Hz、看门狗。启动 IK 子进程时临时隐藏 lerobot 主脚本路径，免得子进程把 lerobot/torch 整个再导入一遍。
  5. 本进程建 rclpy 节点（独立 Context，域 64），订阅双臂反馈、状态（`err_code`/`arm_status` 非零 → 遥操网关 fault）、三路 RGB 和 camera_info。**不创建任何发布者**，所以机械臂插件「每个命令话题恰好 1 发布者」的检查不受影响。
  6. 起 HTTPS（`deployment.json` 的 host/port，证书同 profile）和 WebRTC 输入。终端打印 `pico_vr_ready` 和网址。
- **会话自检**：等 lerobot 循环开始（第一次 `get_action`）、反馈新鲜、三路图像到达、IK 子进程就绪。在第一次 `get_action` 之前一直刷新自检计时，所以机械臂连接、回 home 用多久都不会触发 30 s 的自检超时。
- **get_action()**：不阻塞（离线实测 p95 < 5 ms），返回 14 维，键名和顺序与 `bi_piper_ros` 完全相同（测试里核对过）。
  - 内容是网关最后一次「本应下发」的目标：TELEOP 握侧键时是 IK 跟随的关节指令；A 回 home 时是 4 s smoothstep 回 home 的轨迹；松开侧键、暂停、A 结束、VR 断开时，是网关做的**实测保持**（只锁存一次当时的实测值，之后不再变，不会跟着重力下沉慢慢漂）。
  - 某臂从没被命令过时，返回第一次调用时的实测值。夹爪同理，返回值裁剪到 0–0.07 m。
  - 第一次调用会等反馈（默认 10 s），等不到就报错「is the robot stack running?」。
- **send_feedback()**：空操作。锚点用自己订阅的反馈，不依赖 lerobot。
- **disconnect()**：关 WebRTC（会话暂停）→ `app.close()`（会话关闭 → 网关停止 → 截下实测保持、关 IK 子进程和预览）→ 关 HTTPS → 停 ROS → 写 `performance.json`、`teleop-ended.json`。遥操插件本身从不使能、不发布。

### 1.3 配置项（`--teleop.xxx=`）

| 项 | 默认 | 说明 |
|---|---|---|
| `backend` | `ros` | `fake`：无 ROS，模拟臂 + 灰图，用于离线测试 |
| `host` / `port` | deployment（0.0.0.0:8445） | 测试时用 127.0.0.1 和别的端口 |
| `advertise_host` | deployment（192.168.87.133） | 只影响打印的网址 |
| `cameras_enabled` | true | false：VR 里没有相机画面，自检也不等相机 |
| `input_delay_s` | profile（0.1） | 临时改插值 (a) 的延迟，0 为关闭 |
| `first_feedback_timeout_s` | 10 | |
| `check_conflicts` | true | |

**注意**：机械臂用 `--robot.cameras_enabled=false` 时，相机节点不会启动，遥操也要加 `--teleop.cameras_enabled=false`，否则会话自检一直等相机。

### 1.4 VR 按键（这一版没做的部分）

A/X 用的是 023 会话自己的流程：STANDBY 时按 A 回 home，READY 时按 A 开始，TELEOP 时按 A 结束。另外加一个 B 键回 home 意义不大，所以没有加。`lerobot-record` 用的 A 结束一条、X 重录（接 lerobot 的 `events`），需要一个很薄的包装入口（如 `pico-record`），**按交接要求先问用户要不要做，本步没有做**。

## 2. 离线验证

复现（在 bimanual 上，不 source ROS，免得 ROS 的 pytest 插件干扰）：

```bash
cd ~/zero-wam/PICO-ACT/plugins/lerobot_teleoperator_pico_vr
../../.venv/bin/python -m pytest -q -p no:cacheprovider tests        # 3 passed
cd ../lerobot_robot_pico_piper && ../../.venv/bin/python -m pytest -q -p no:cacheprovider tests   # 7 passed（未受影响）
```

| 测试 | 内容 |
|---|---|
| `test_features_match_robot_plugin` | 14 个键与 `bi_piper_ros.motor_keys()` 完全一致 |
| `test_workflow_hold_follow_release` | 直接喂 webxr 包：STANDBY → A → HOMING → READY → A → TELEOP；握右侧键、2 s 内把手抬高 6 cm → 右臂指令的 FK 末端上升 > 4.5 cm，x、y 偏差 < 1.5 cm；左臂输出不变；松开后输出保持不变；A → STANDBY；`get_action` p95 < 5 ms；日志里有 raw_input/intent/motion_result/command/feedback/session_state |
| `test_webrtc_sim_headset_end_to_end` | 虚拟头显走真实的 HTTPS + WebRTC（带一阵一阵的到达抖动），lerobot 循环线程 30 Hz 调 `get_action`：确认数 ≥ 95%、0 错误，经过 HOMING/READY/TELEOP/STANDBY，右臂动、左臂不动；头显断开后会话按设计进入 PAUSED |

### 2.1 真实 `lerobot-teleoperate` 命令，全 fake 后端

```bash
cd ~/zero-wam/PICO-ACT
.venv/bin/python -m lerobot_teleoperator_pico_vr.sim_headset https://127.0.0.1:18445/ --start-delay 6 --jitter-s 0.03 &
tasks/lerobot_teleop.sh --robot.backend=fake --robot.output_root=/tmp/pico_fake_runs \
  --teleop.backend=fake --teleop.host=127.0.0.1 --teleop.port=18445 --teleop.output_root=/tmp/pico_fake_runs --teleop_time_s=40
.venv/bin/python tools/teleop_report.py /tmp/pico_fake_runs/*_pico_vr_* --robot-run /tmp/pico_fake_runs/*_lerobot_*
```

结果见 `docs/03-teleop/fake_teleop_report.json`（默认动作）和 `fake_teleop_report_gentle.json`（`--reach 0.4 --radius 0.03 --move-s 12`）：

| 项 | 结果 |
|---|---|
| 退出码 | 0 |
| 虚拟头显 | 684 包全部确认，0 错误，RTT p50 3 ms（本机回环） |
| 机械臂 | 下发 4441 次，**网关拒绝 0**，重新接管 0 |
| 输入 | 39.7 Hz（带人为抖动，间隔 p95 56 ms） |
| lerobot 循环 | `get_action` 29.9 Hz，间隔最大 36 ms |
| IK | 结果延迟 p50 36.5 ms / p95 37.7 ms；从折叠的 home 位出发，56–68% 为 best_effort |
| 指令高频抖动 RMS（mrad，右臂 6 关节） | 遥操输出 1.2–3.3；跟踪器 (b) 之后 0.55–2.1 |

分段延迟（速度互相关，只算握侧键的时段）：

| 段 | 延迟 | 相关系数 | 说明 |
|---|---|---|---|
| 手 → IK 目标 | **100–105 ms** | 0.96–1.00 | 就是插值 (a) 的 D=0.1 s |
| IK 目标 → 遥操指令 | 测不准 | 0.55–0.64 | 被下面两条限速和翻转主导 |
| 遥操指令 → 机械臂指令 | **80–85 ms** | 0.99 | 跟踪器 (b)，T=0.08 s |
| 机械臂指令 → 反馈 | 10 ms | 0.997 | fake 臂，不代表真机 |

不受饱和影响时，各段合计约：0.1 s（插值）+ 37 ms（IK）+ ≤17 ms（控制节拍）+ 约 40 ms（一阶混合）+ 80 ms（跟踪器）≈ **0.27 s + 真机伺服 + 头显到主机的网络（约 RTT/2）**。

Ctrl+C（SIGINT 发给整个进程组，和真实终端一样）：1 s 内退出，两份结束记录都写出，没有残留进程。两条 KeyboardInterrupt 回溯来自 IK 子进程，collect 也一样。

### 2.2 ROS 代码路径（只读，没起驱动和相机）

只启动遥操插件（`backend=ros`）：节点只订阅 `/left_arm|right_arm` 的 `joint_states_feedback`、`arm_status`，以及三路 `color/image_raw`、`camera_info`、`metadata`；除了 ROS 默认的 `/rosout`、`/parameter_events`，**没有任何发布者**。会话停在 SELF_CHECK，等待 `lerobot_robot_loop` 和三路相机；没有机器人时 `get_action` 明确报错。

## 3. 离线发现的两点（023 collect 同样存在，供参考，未改）

1. **022/023 的指令整形实际限速约 0.39 rad/s，不是 0.72。** `_shape_command` 先做 alpha=0.35 的一阶混合，再按「目标与混合值之差」算限速比例。远离目标时，每拍实际步长 = 允许步长 × 0.35/0.65 ≈ 0.54 倍：$0.8\times0.9\times0.54\approx0.39$ rad/s。fake 中指令的最大关节速度正好是 0.39 rad/s。大动作时手感偏「拖」，可能有一部分来自这里。要改的话是改 023 的 `teleop_session.py`，会同时改变 collect 的手感，需要用户决定。
2. **腕部翻转。** 被跟随的 IK 解里，关节 4、6 偶尔反向跳约 0.5 rad（目标同时在转，(c) 的一致性门槛不拦）。指令按 0.39 rad/s 追要 1 s 多。真机上右臂姿态冲突多时，可能表现为手腕慢慢拧过去。

## 4. 真机测试（待用户在场）

前提：现场有人、急停可用；没有 collect 在跑；桌面清空或按任务摆好；PICO 和机器人在同一网段。左腕相机前几次在现场掉线过，先看一下 USB。

**第一段：不使能（会启动驱动和相机，机械臂不动）**

```bash
cd ~/zero-wam/PICO-ACT
tasks/lerobot_teleop.sh --robot.dry_run=true
```

头显打开终端打印的网址（`https://192.168.87.133:8445/`）。看：页面能进、WebRTC 连上、三路相机画面、HUD 状态。按 A：只有双臂**本来就在 home（误差 ≤ 0.02 rad）**时才会在约 4.5 s 后进入 READY，否则 20 s 后 HOMING 超时 FAULT（dry-run 里机械臂不动，这是预期的）。能进 TELEOP 时握侧键动一动，IK 输出会记进日志，不下发。Ctrl+C 结束。

**第二段：真实遥操（会使能、4 s 回 home，之后跟手）**

```bash
tasks/lerobot_teleop.sh
```

机械臂连接时自动回 home。头显里：A（回 home 的轨迹固定 4 s，已在 home 时约 4.5 s 后 READY）→ A 开始 → 握侧键跟随（扳机控夹爪）→ 松开即保持 → A 结束。玩 1–2 分钟，回终端 Ctrl+C：实测保持、停子进程，不失能、不回 home、不关爪。驱动速度仍是 20%。

**验收：**

```bash
T=$(ls -d runs/*_pico_vr_* | tail -1); R=$(ls -d runs/*_lerobot_* | tail -1)
.venv/bin/python tools/teleop_report.py $T --robot-run $R --json docs/03-teleop/hw_teleop_report.json
# analyze.py（2080 上 /home/ccguest/wangxr/tmp/teleop_jitter/）传到远端临时目录后：
PYTHONPATH=releases/023-20261103-webrtc-smoothing/src .venv/bin/python analyze.py $T   # 遥操输出
PYTHONPATH=releases/023-20261103-webrtc-smoothing/src .venv/bin/python analyze.py $R   # 跟踪器之后
```

- 手感接近 023 collect（用户主观）；
- 指令高频抖动和 023 那次（0.6–1.5 mrad）同一量级；
- 记录端到端延迟：报告里的分段延迟，加上 HUD 上的 RTT/2。比 collect 多了跟踪器 (b) 的约 80 ms。

## 5. 尚未覆盖 / 注意

- lerobot 每拍都调用机械臂的 `get_observation`：任一路相机超过 0.5 s 没新帧就报错，`lerobot-teleoperate` 会退出（退出时实测保持）。左腕相机不稳定时，可以两边一起加 `cameras_enabled=false` 先只测手感。
- `lerobot-teleoperate` 每拍打印一行循环耗时，终端会刷屏，这是 lerobot 自带的。
- 遥操插件的 fake 模式里，「臂」是插件自己模拟的，不是机械臂插件的 fake 臂；两者跟随同一串动作，只用于链路测试。
- `pico-record`：用户已决定做，见第 6 节末尾和 `04-第4步_pico-record.md`。

## 6. 真机遥操结果（2026-11-03 22:22，收尾记录）

run：`runs/20261103T142232Z_pico_vr_cc794a9c`（遥操）+ `runs/20261103T142232Z_lerobot_3619d0c0`（机械臂）。跟手 59.8 s（A 回位 → A 开始 → 跟随 → A 结束，再 A 回位一次后 Ctrl+C）。驱动、相机全部正常退出；机械臂下发 11025 次，**网关拒绝 0、重新接管 0**，无错误。报告：`docs/03-teleop/hw_teleop_report.json`。

**指令高频抖动 RMS（mrad，6 个关节的范围）**

| 位置 | 左臂 | 右臂 |
|---|---|---|
| 遥操输出 | 1.9–2.8 | 0.66–1.08 |
| 跟踪器 (b) 之后（实际下发） | **0.50–0.78** | **0.41–0.65** |
| 反馈 | 0.68–0.92 | 0.55–0.90 |
| 对照：023 collect 下发 | 0.53–1.24 | 0.59–1.24 |
| 对照：021（无滤波） | 关节 2 为 34–77 | |

`analyze.py` 分高度段：跟踪器之后各段 0.10–0.74 mrad，指令速度换向 0 次/s。**结论：与 023 collect 同一量级（略低），验收通过。**

**延迟（速度互相关，只算握侧键的时段）**

| 段 | 左 | 右 |
|---|---|---|
| 手 → IK 目标（插值 a） | 55 ms | 80 ms |
| IK 目标 → 遥操指令 | 115 ms | 75 ms |
| 遥操指令 → 下发（跟踪器 b） | 80 ms | 75 ms |
| 下发 → 反馈（伺服） | 70 ms | 60 ms |
| **手 → 反馈（端到端）** | **380 ms** | **315 ms** |

- 头显 RTT p50 46 ms、p95 202 ms、最大 401 ms → 总延迟约 0.34–0.40 s。对照 023 collect（带 a/c）端到端 300–345 ms。
- VR 相机画面：服务器帧龄 80–97 ms，头显取帧约 50 ms，解码约 4 ms。
- 输入 28.9 Hz（间隔 p95 73 ms、最大 163 ms）；`get_action` 27.6 Hz（目标 30）；IK 收敛：右 85%、左 66%，结果延迟 p50 约 43 ms。
- 用户主观手感：待补。

复现：

```bash
T=runs/20261103T142232Z_pico_vr_cc794a9c; R=runs/20261103T142232Z_lerobot_3619d0c0
.venv/bin/python tools/teleop_report.py $T --robot-run $R --json docs/03-teleop/hw_teleop_report.json
PYTHONPATH=releases/023-20261103-webrtc-smoothing/src .venv/bin/python tools/analyze.py $T
PYTHONPATH=releases/023-20261103-webrtc-smoothing/src .venv/bin/python tools/analyze.py $R
```

`pico-record`（A 结束、X 重录接 lerobot）：用户 11-03 决定做，见 `04-第4步_pico-record.md`。
