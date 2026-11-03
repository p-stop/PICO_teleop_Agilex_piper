# 遥操作数采、推理部署与运动控制调研

调研日期：2026-10-11。对应架构 v0.4。此文区分**上游公开证据**与**本项目设计建议**；本项目未安装或运行下列系统，所有实验室组合都尚未验证。检索覆盖 GitHub、arXiv、作者项目页和官方文档，是面向当前验收任务的候选筛选，不是穷尽式综述。可变分支链接只代表查阅入口；实际接入时必须固定 commit、许可证、依赖和资产 hash。

## 1. GELLO：优先用于 FR3 的关节遥操

[GELLO 论文，arXiv:2309.13037](https://arxiv.org/abs/2309.13037)描述为目标臂制造同运动学结构的低成本主臂，读取关节位置来控制从臂；作者给出了 Franka、UR5、xArm 设计及数采用户实验。其“通用”指构建方法，不意味着一个七关节主臂能直接控制任意机器人。

[软件仓库](https://github.com/wuphilipp/gello_software)包含 Dynamixel 输入、机器人接口、校准与采集模块。[FR3 ROS 2 文档](https://github.com/wuphilipp/gello_software/blob/main/ros2/README.md)明确提供 Humble 路径，并要求匹配机器人系统与 libfranka/franka_ros2 版本。公开代码路径已经存在；实验室 FR3 和现有 GELLO 的匹配情况仍未知。

**接入设计**：只包装主臂读数为 `JointIntent`，保留电机 ID、原始角度、夹爪读数、时间戳；`GelloJointMapper` 显式配置关节名、符号、零偏、比例、夹爪量程和初始匹配条件。FR3 驱动独立运行，主臂不能直接调用其 SDK。启用时先检查主从差值并同步参考；不沿用上游脚本启动即位置同步的行为。异构接入只能经已标定重定向，或主臂 FK → TCP 意图 → 从臂 IK，且该路径另行验收。

**最小验证**：录制一段不连接从臂的 GELLO 读数；用 fake/仿真检查逐关节正负号、夹爪和跳变；断串口、卡住读数、重新插拔、启用时主从位置不匹配均须拒绝或停止。最后才由用户明确安排 FR3 低速验证。论文用户实验结果不能代替实验室自己的精度、舒适度、有效 episode 比率和接管测试。

## 2. TidyBot2：手机姿态、相对映射与分机推理

名称辨析：`jimmyyhwu/tidybot2` 对应 **TidyBot++**，[论文 arXiv:2412.10447](https://arxiv.org/abs/2412.10447)；不要与早期 `tidybot` 的任务级 LLM 系统混用。

[使用指南](https://tidybot2.github.io/docs/usage/)给出 iPhone 的 XR Browser/XRViewer、按住使能、手机与机器人起始方向对齐及臂/底盘模式。[发布范围表](https://tidybot2.github.io/docs/)的手机遥操覆盖 Kinova、ARX5，不能从 Franka 硬件设计栏推出 FR3 手机软件已验证。

[policies.py](https://github.com/jimmyyhwu/tidybot2/blob/main/policies.py)将手机位姿转换到控制坐标，按使能捕获参考位姿，支持主手机控制臂或底盘、第二手机控制底盘，并在底盘移动时补偿臂参考。它也展示了消息过期过滤。**本项目吸收的是这些分层机制**：`PhonePoseInput`、相对位姿 mapper、clutch、具名 `arm/base` 目标、时间与故障记录；其时间阈值和全向底盘映射不直接复制到实验室自制轮式底盘。

[README 的推理章节](https://github.com/jimmyyhwu/tidybot2#policy-inference-1)提供 GPU 服务器、ZMQ 和提前请求下一动作序列的 `PolicyWrapper`，并用带模拟延迟的 stub 解释调度。它支持“计算与执行分机”和“用 stub 先测延迟”的工程选择；其示例频率和延迟预算属于作者环境，不是本项目默认值，也不等于 RTC 的采样器 inpainting。

**最小验证**：先仅显示手机位姿并记录输入；验证 tracking 丢失、屏幕锁定、后台挂起、离合器释放、参考重置、网络断开。再用 MuJoCo 控制单臂。手机的 OS、型号、浏览器及 6DoF 能力必须进入设备 profile；不支持追踪时明确失败，不能用 IMU 旋转冒充位置。

## 3. 其他实用数采候选

以下“优先级”是插件研发次序建议，不覆盖用户六项场景的验收排序。

| 候选与原始来源 | 公开能力 / 适合用途 | 纳入框架的边界与优先级 |
|---|---|---|
| [LeRobot Phone](https://huggingface.co/docs/lerobot/phone_teleop) | iOS 用 HEBI Mobile I/O（ARKit）；Android 用 WebXR `teleop`，已有相对位姿、使能、IK 处理范例 | 与 TidyBot2 对照，优先试手机输入；iOS 原生输入与用户要求的 WebXR 分开验收，不能用原生成功替代 WebXR 成功。SO100 示例不是 FR3 兼容证明。 |
| [XLeRobot / XLeVR](https://github.com/Vector-Wangel/XLeRobot) | Quest3、键盘、Xbox/Switch 输入及 MuJoCo 参考路径 | 优先试 Quest 手柄输入。拆原始 XR 数据与机器人映射，剔除内置回零/直接发送路径；按实际底盘版本核对运动学。 |
| [CamBot](https://github.com/open-thought/cambot) | 6DoF 舵机视觉臂，Quest3 头显控制、WebXR/HTTPS/WebSocket、WebRTC 回传 | 第二场景重点候选。公开测试环境 Ubuntu 24.04、Python 3.12+、ZED Mini；实验室的 Ubuntu20.04 + D435i 是新的移植组合。 |
| [robosuite 设备文档](https://github.com/ARISE-Initiative/robosuite/blob/master/docs/modules/devices.md) | 键盘、SpaceMouse、DualSense 控制仿真机器人；可扩展 Device | 键鼠先用于 fake/MuJoCo 验证和微调。游戏手柄可做底盘/夹爪/离合器，6DoF 臂要显式模式切换；记录按键释放与焦点丢失。HID 型号及 OS 要逐一测试。 |
| [Diffusion Policy](https://github.com/real-stanford/diffusion_policy) | 真实数采/部署和 SpaceMouse 参考代码，滚动预测动作序列 | SpaceMouse 是桌面单臂 TCP 遥操的实用备选；不能沿用 Linux 输入依赖就声明 Windows 支持。deadzone、尺度、轴序均为 mapper 参数。 |
| [UMI 论文](https://arxiv.org/abs/2402.10329) / [代码](https://github.com/real-stanford/universal_manipulation_interface) | 手持夹爪和相机采集人类演示，离线重建相对轨迹、延迟匹配后部署 | 中期作为 `DatasetImporter` 与专用采集协议，而非在线遥操驱动。保存视频、SLAM 轨迹及质量标志，不虚构机器人反馈/实际命令；有效数据受跟踪、末端与相机匹配限制。 |
| [FastUMI](https://arxiv.org/abs/2409.19499) | 用现成位姿跟踪模块简化 UMI 数采管线 | 中期比较位姿精度、遮挡/漂移、成本和部署耗时；本轮只核对论文，未完成代码/设备复现审计。 |
| [FACTR Teleop](https://github.com/JasonJZLiu/FACTR_Teleop) / [论文](https://arxiv.org/abs/2502.17432) | 力反馈、重力/摩擦补偿的主臂方案，面向接触任务 | 后期；主动主臂本身也是执行端，反向力反馈命令也须经过其 guard。需要额外硬件、反馈语义和双向时延验证，不能作为被动 GELLO 的纯软件开关。 |
| [Open-TeleVision](https://github.com/OpenTeleVision/TeleVision) | 沉浸主动视觉反馈、手部姿态与重定向 | 后期灵巧手/人形拓展；手柄与裸手追踪是不同输入能力，遮挡及重定向须单独测。 |
| [Unitree 官方 XR](https://github.com/unitreerobotics/xr_teleoperate) | 仓库列 G1 多种 DoF、末端和 Quest3 等 XR 路径；给出 Ubuntu20.04/22.04 测试说明 | 为第六场景提供厂商候选入口；不能把 G1 条目视为用户“G1-D”的已核对型号。先确认产品、末端、SDK 与控制模式。 |
| [TacUMI](https://arxiv.org/abs/2601.14550) | 2026 年的触觉、力矩、位姿等多模态手持采集研究 | 研究储备，提示传感器端口/质量标志应可扩展；本轮未完成代码可用性和硬件复现审计，不进入首版依赖。 |

建议首批：GELLO + Quest/WebXR + 键盘 fake 输入；手机及游戏手柄按实际持有设备安排。SpaceMouse 为低成本桌面替代，UMI 独立作为数采模式，FACTR/裸手/触觉扩展留后期。取舍依据是已有硬件、工程路径和验证成本，不按论文新旧排序。

### CamBot + D435i 的专项差异

CamBot 原项目是 ZED Mini 立体彩色显示；[RealSense SDK](https://github.com/realsenseai/librealsense)提供 RGB/depth/IR/IMU 等能力，但实际流需 probe。D435i 的 RGB、depth 和左右 IR 不能自动当成 ZED 的左右彩色图像。

第二场景首版建议**单路 RGB 回传，头显中显式标为单目显示**；是否需要左右 IR 立体显示或深度重投影另建 profile 并实测，不把一张 RGB 复制到双眼称为立体视觉。需要确认 D435i 支架、臂负载/惯量、线缆、相机 optical frame、随臂外参，以及编码/USB 带宽。CamBot 原 watchdog 可触发回 home；本项目不继承“失联自动回零”，使用现场验证的 stop 行为。

## 4. 推理与控制技术的不同职责

| 技术 | 实际解决的问题 | 适用条件及不适用情况 | 推荐接入层 |
|---|---|---|---|
| Action chunking | 每次预测多个未来动作，减少模型调用并形成时间一致性 | 需模型输出时域定义；长时间开环降低反应速度；chunk 不是控制器轨迹保证 | 策略输出契约 + ActionScheduler |
| Temporal ensemble (TE) | 合并不同预测时刻对**同一执行时刻**的动作 | 需一致坐标/动作语义；多峰分布平均可能不可行；不能随意平均四元数、离散夹爪或不同来源动作 | 显式 ChunkFusion 插件 |
| 普通异步推理 | 当前动作执行时计算下一段，减少等待 | 任何能定义时间对齐的模型可试；不自动解决块边界跳变或超时 | 设备端队列 + 推理端 worker |
| RTC（此处指 Real-Time Chunking） | 用正在承诺执行的动作前缀约束新 chunk 的生成，改善异步连续性 | 原论文是 diffusion/flow 采样器 inpainting；ACT 或离散 token 模型不自动适用 | 模型 adapter 内采样器 + scheduler 协议 |
| IK / differential IK | TCP 目标转换为关节目标或速度，处理冗余和局部约束 | 需要正确模型/状态；局部 IK 不等于全局可达、无碰撞路径或动力学控制 | MotionMapper / servo solver |
| 插值 / jerk 限制轨迹生成 | 低频目标到受速度、加速度、jerk 约束的跟踪参考 | 会引入延迟并改变模型动作；位置关节轨迹不能盲目套到 torque 输出 | 设备端 MotionExecutor |
| 路径规划 | 在场景/碰撞模型中找从起点到目标的路径 | 需要场景新鲜度；规划时长与动态障碍是额外问题；不宜每个遥操帧全局重规划 | 可选 GoalPlanner |
| MPC | 用模型、代价和约束滚动优化控制输入 | 需要模型、状态估计、控制模式、求解时限与失败路径；不是推理加速器，也不天然保证安全 | 可选 TrackingController |

[ACT 论文](https://arxiv.org/abs/2304.13705)与[作者代码](https://github.com/tonyzhaozh/act/blob/main/imitate_episodes.py)提供 chunk 和时间聚合参考。复现需记录窗口、权重方向与查询频率；不要默认“越新权重越高”就是作者实现，也不要用零值判断动作是否有效。新的实现用显式 valid mask。

[RTC 论文 v2](https://arxiv.org/html/2506.07339v2)定义预测 horizon、执行 horizon 和推理 delay；异步推理之外，还在采样期间施加前缀和 soft-mask 约束。工程上必须知道哪些目标已承诺、哪些被 guard 修改/拒绝；实际轨迹与前缀不符时不能继续宣称 RTC 连续性成立。需要丢弃旧结果、重新观测并生成新段，严重时停机。

[LeRobot 异步推理](https://huggingface.co/docs/lerobot/async)和[RTC 文档](https://huggingface.co/docs/lerobot/rtc)已有服务器/客户端、队列和 flow 模型 RTC 入口。优先试其模型 adapter，封装为意图源；上游 RobotClient 的直接执行不能绕过本项目 guard。RTC 支持要基于固定版本和采样器能力测试，而非仅由模型名称判断。

**RTC + TE**：首版作为不同调度 profile，对比测试，不默认串联；不同 horizon/队列参数在上游实现中可能同名但含义不同，配置必须保存 adapter 名称和精确定义。**IK + 轨迹生成**可以按语义串联；**MPC + 轨迹生成**通常应选择一个明确的跟踪职责，避免双重 retiming。路径规划优先用于回位、接近、任务级 waypoint，接触操作的策略动作不自动送全局 planner 改写。

### 一个动作块时序例子

以下仅为算法示意参数，不能用作真机设置：模型输出50个动作、dt=20ms，则预测覆盖1秒；从观测到结果可用耗时160ms，期间有8个动作时刻已经过去。同步方案在等待期间缺新动作；普通异步方案继续消费旧段，按新段的原时间锚跳过过期样本；RTC还让采样器以这段已承诺动作作为前缀条件。不能在收到结果时把第0个动作重新当“现在”，否则队列延迟会转化为落后动作。

若保留12个旧样本，覆盖240ms，在该示意条件下有80ms余量；一旦耗时超过240ms就仍可能欠载，RTC也不能凭空生成动作。实际阈值同时考虑观测年龄、网络、映射、guard和设备执行耗时，故障路径先于性能优化实现。位置delta若相对每次观测状态，则必须按其参考状态重建目标；不能把两个不同参考状态的delta直接平均。

### MPC 怎样接策略目标

用状态估计 `x` 和模型 `x[k+1]=f(x[k],u[k])`，在有限时域里优化目标跟踪误差、控制代价和平滑项，同时施加关节、速度、碰撞等约束；只执行首个控制输入，下一周期重新估计/求解。这是 MPC 的滚动闭环，与神经网络预测动作块然后消费队列的机制不同。

只用关节位置/速度模型的 kinematic MPC 可以研究运动可行性；要做动力学/力矩 MPC，还需惯量、负载、接触、状态与控制模式证据。本项目 v0.2 命令示意未定义 torque 原生接口，因此不能借 MPC 引入隐式力矩旁路。每种模型/求解器/profile须说明输出类型、截止期、残差和不可行行为；模型误差或缺失障碍感知会破坏其约束假设，最终guard仍独立。

## 5. 运动模块选型建议

| 候选 / 原始来源 | 用途 | 设计决定 |
|---|---|---|
| [Mink](https://github.com/kevinzakka/mink) | 基于 MuJoCo 的 differential IK，有关节/速度/碰撞约束 | 最先在 MuJoCo 中比较 IK 残差、奇异位形及失败行为；有 Panda 示例不代表 FR3/Piper 已适配。 |
| [Pinocchio](https://github.com/stack-of-tasks/pinocchio) | FK/Jacobian/刚体动力学与模型基础 | 给 Linux 设备侧模型/IK 插件留入口；它本身不是完整规划器或安全系统。 |
| [Ruckig](https://github.com/pantor/ruckig) | 状态到状态的速度/加速度/jerk 受限在线轨迹 | 候选设备侧 trajectory executor；首版只用本地可运行能力。Community 中间 waypoint 使用云 API、tracking 为 Pro，不能默认为免费离线功能；关节位置/碰撞限制仍由本项目检查。 |
| [MoveIt 规划架构](https://moveit.picknik.ai/main/doc/concepts/motion_planning.html) | 场景、IK、规划器、约束与轨迹后处理 | Linux 侧任务级路径规划候选；作为外部插件，不引进跨所有 OS 的强依赖。 |
| [cuRobo](https://github.com/NVlabs/curobo) | GPU 运动生成/碰撞计算候选 | 后期按明确版本、CUDA/GPU 和资产测试；不能把上游性能数字写成本实验室实时保证。 |
| [OCS2](https://github.com/leggedrobotics/ocs2) | 非线性最优控制、MPC 和模型/约束工具 | 双臂移动/人形阶段的候选；先做仿真时限与模型误差测试。无需求证据时不在 FR3 数采 MVP 内实现 MPC。 |

首版运动 profile：`native`、`cartesian_servo_ik`、`joint_trajectory`。后续才增加 `goal_planner` 和 `mpc_tracker`。`native` 保留模型动作表示，但仍做解码、所有权、有效期与最终安全检查；没有对应硬件控制模式即拒绝，不自动转换。

## 6. 推理部署与优化顺序

1. **先建立未优化基线**：固定模型/权重、normalization、图像角色、预处理、动作语义、随机种子与依赖。ACT 或 Diffusion Policy 适合作为可理解的首个 adapter，实际首模型待用户任务/数据决定；不预先承诺通用 VLA 可以直接控制 FR3。
2. **再拆观测与动作时序**：观测快照含各流原始时间、偏差和有效性；request 与 response 均带 session、epoch、request ID、观测序号。GPU worker 不拿设备 lease，结果进入设备本地调度器；断网/重连不重放积压命令。
3. **优化数据路径**：先测采集、图像传输、解码/resize、CPU↔GPU 拷贝和推理各项耗时；稳定分辨率、batch=1、预热、有界队列。视频显示压缩流与模型输入/原始记录分开，显示方便不能牺牲训练/推理输入一致性。
4. **模型计算优化**：按模型/后端分别试 reduced precision、编译、ONNX/TensorRT、采样步数；变化必须比较输出误差、动作跳变和任务结果。不是所有算子/动态形状/采样器都能导出；RTC 的梯度 guidance 与纯前向 engine 有额外兼容门槛。[ONNX 量化说明](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html)、[TensorRT 性能指南](https://docs.nvidia.com/deeplearning/tensorrt/latest/performance/best-practices.html)用于建立后端测试，不作为统一加速保证。
5. **时序优化**：顺序比较 synchronous chunk → async queue → TE 或 RTC。记录成功率、动作年龄和块间跳变；不能仅因 GPU 平均耗时更低就采纳。
6. **运动优化**：按任务选择 IK/轨迹/MPC；每次改变执行轨迹都保存 raw output、后处理结果、guard 决策和实际反馈。大量 guard 修正提示语义/策略不匹配，应中断评测，不能一直裁剪掩盖问题。

延迟预算采用设备端时钟估计：`L = observation_age + preprocess + request/response + inference + schedule + map/track`。跨主机时钟先估偏差/不确定性，不直接相减两个主机 monotonic 值。以 p50/p95/p99、最大实测耗时和 deadline miss 计数报告；p99 只是统计量，不是硬实时保证。余队列覆盖时间要大于下一次结果预算并留余量；不足时撤销策略授权，执行经过验证的停止，不永久保持最后动作。

## 7. 最小评测矩阵（计划，尚未执行）

| 维度 | 用例 | 证据 / 判定 |
|---|---|---|
| 输入 | GELLO、Quest/手机录制流、键鼠/手柄 | 单位/坐标/按键/离合器正确；丢追踪不产生命令；记录原始与映射结果 |
| 推理 | stub 延迟：小于、一倍、超过队列覆盖时间；乱序/重复/重连 | 旧 epoch/过期结果拒绝；队列无静默欠载；接管后旧 chunk 永不执行 |
| 调度 | 同模型同观测下 native chunk、async、TE、RTC（支持时） | 动作年龄、跳变/jerk、延迟、任务成功率；模型不支持 RTC 时预检失败 |
| 运动 | 不可达 TCP、奇异位形、限位、碰撞场景、MPC 超时 | 返回明确失败，无 NaN/越界动作；停止路径和拒绝原因可回放 |
| 平台 | Windows + Ubuntu20.04/22.04/24.04 的核心与消息测试 | 每个平台单独出报告；依赖不支持的插件显示 unsupported，不假装全绿 |
| 采集 | 相机掉帧、磁盘慢/满、进程退出 | episode aborted、流质量与控制证据保留；关键事件写入失败触发预定停止 |

真机阈值（控制频率、速度、停止时限、对齐误差）在只读 probe 和低速基线之后写入设备 profile，并在真机运行前固定。无实测时不填通用“安全数值”。

## 8. 尚待确认的事实

- 手机 OS/型号、WebXR 浏览器和追踪能力；Quest 固件/浏览器版本；是否必须立体视频，单目显示能否满足第二场景。
- FR3 robot system、FCI、夹爪、实时内核、GELLO 运动学版本；Piper/CamBot 具体型号、固件、接口与机械安装。
- 自制底盘差速/全向/其他运动学、里程计与停止机制；“G1-D”的确切产品与末端配置。
- GPU 型号、网络、第一批模型/权重和训练动作定义；不因此阻塞核心 fake 切片。
- 本轮未验证上游仓库构建、许可证依赖闭包和真实任务效果。原架构的 PhyAgentOS 比较保留为历史调研，不据本轮推断其当前设备支持。
