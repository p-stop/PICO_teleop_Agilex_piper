# 双 Piper / 三相机 / WebXR 采集数据格式报告

面向 supervisor、数据使用者及训练开发者。更新：2026-10-18，计划012。

2026-10-19增量：真实MP4与四路末端已有new_test样本；两集capture QC/deep通过、一集局部帧间隔失败，见[审计](research/2026-10-19-new-test-audit.md)。以下原始字段表保留；训练action选择、夹爪目标和转换见[训练报告](training-data-format-report.md)。新代码增加context.initial_targets（发布后目标快照）、图像capture_sequence（回调累计序号）和manifest.frame_capture_stats（到writer/主动筛选/写入计数）；诊断日志改为summary.segments列出的追加分段，旧events.jsonl仍可读。这些是可选加法字段，不回填旧集。

本文描述**当前代码实际写出的字段**，不把架构草案中尚未实现的能力列为已采数据。运行方法见[操作手册](episode-collection.md)，设备/编码配置见[技术说明](episode-storage-and-configuration.md)。

## 1. 系统采集了什么

这套系统保存的是一次示范过程中的多源时间序列：操作者看到了什么、手柄怎样动、框架希望机器人怎样动、发布了什么命令、机器人反馈了什么，以及当时的配置和质量检查结果。它不是已经统一采样好的 `[T, D]` 训练张量。

| 数据 | 当前实现与存储 | 语义 / 证据边界 |
|---|---|---|
| 左腕、右腕、固定相机 RGB | 原始 MCAP 或每路 MP4；当前台架配置640×480、30fps | 实际原始模式真机 episode 已验；MP4已有真实图像离线编码/解码证据，实时 MP4 session 尚待验证 |
| 双臂关节位置、夹爪开口 | `/feedback/left`、`/feedback/right`，JSON in MCAP | 驱动反馈；不是发出的目标；现场已验 |
| 原生末端 XYZ + RX/RY/RZ | `/pose_feedback/left_native`、`right_native` | SDK 原始整数及其原生单位；**没有转换成四元数**。2026-10-19 new_test已实际记录，10月18日旧集没有这些流 |
| 末端四元数位姿 | 新增 `/pose_feedback/left_quaternion`、`right_quaternion` | 独立来源；**ROS 驱动从原生欧拉角转换**，不是 CAN 原生四元数。可通过配置删除这些来源，仅采原生欧拉角 |
| PICO/Quest 头部和左右手柄位姿、按钮、摇杆 | `/event/raw_input` | WebXR 原始已传输输入包；包含跟踪丢失、参考空间及浏览器时间信息；不是机器人末端位姿 |
| 遥操锚点、笛卡尔目标、IK结果 | `/event/mapping_anchor`、`intent`、`motion_result` | 推导 / 控制过程数据；不是传感器测量 |
| 最终关节/夹爪命令、检查决策、发布回执 | `/event/command`、`guard`、`receipt` | 可追踪软件发布链路；回执只表示已发布，**不是硬件执行 ACK** |
| 相机内参、RealSense metadata | context快照 + `/event/camera_info`、`device_metadata` | metadata依赖已安装消息包和实际发布，字段随设备/驱动变化；不是已标定手眼外参 |
| 深度图 | 可选 `/camera/<role>/depth`，始终原始 MCAP | 默认关闭；保存原生值及编码，不统一猜成米；尚未做本项目深度真机验收 |
| 任务、配置、模型/源码身份、文件hash、QC、对齐 | JSON / JSONL sidecar | 便于复现和筛选；QC通过不等于示范任务成功 |

**目前不采或不完整：** 关节速度/力矩数组未从 ROS JointState 复制入 episode；没有腕部六维力传感器、触觉、音频、IMU、点云、底盘/升降轨迹、完整 CAN 原始帧、完整 SDK 原始状态包；没有连续全字段 arm_status 流。没有任务成功标签界面、操作者标识、物体标签、经过实测的全局外参、完整固件版本清单或完整 LeRobot v3 导出。不能用“SDK能读到”代替“本次文件确实记录了”。

## 2. Piper 的原生位姿与转换来源

机器人端实际安装版本审查：`piper_sdk 0.6.1` 的 `GetArmEndPoseMsgs()` 返回 `end_pose.X_axis/Y_axis/Z_axis/RX_axis/RY_axis/RZ_axis`，均为整数。XYZ每单位为0.001毫米，角度每单位为0.001度；官方[接口说明](https://github.com/agilexrobotics/piper_sdk/blob/master/asserts/V2/INTERFACE_V2.MD)也给出这些单位。

已安装 ROS 驱动 `PublishArmEndPose()` 的四元数来源明确：XYZ除以1,000,000得到米；RX/RY/RZ除以1000得到度，再转弧度，调用 SciPy `Rotation.from_euler('xyz', ...).as_quat()` 得到 `[x,y,z,w]`。这是驱动转换，不能称作原生四元数。这里不额外做一次转换，也不从四元数反推欧拉角伪装成原始反馈。

原生观测由我们现有的 Piper 驱动 wrapper 从**已连接 SDK 的内存缓存**复制并发布，未新建 SDK 连接、未发送位姿查询或控制命令；原生流与驱动四元数流分别订阅、分别保存。wrapper不改厂商源码。驱动各自读取缓存，因此两路相邻消息也不保证是完全相同的原子快照。

| 来源 | 原生/转换 | 坐标及时间边界 |
|---|---|---|
| `*_native` | 原生 XYZ整数、欧拉角整数；`orientation_provenance="native"`、`conversion=null` | 原生 SDK `time_stamp` 同时保存。三个分量组由多条 CAN 消息更新，并非已验证同时采样 |
| `*_quaternion` | `orientation_provenance="converted"`；`conversion`描述驱动、轴顺序和转换算法 | 米和xyzw原样接收；框架不归一化、不调序、不做坐标变换 |
| IK `intent.target` / `motion_result` | 框架推导 | URDF中的base→tip；不默认等于厂商原生工具点 |

当前驱动发出的 PoseStamped `header.frame_id` 是空字符串；配置中 `reference_frame`、`tracked_frame` 保留 `null`。可将原生值理解为厂商的末端反馈坐标，但**尚不能将其命名为实验室 world、相机光学系，或认定为已校准的夹爪TCP**。需要后续核对厂商工具点、零位和安装变换才能跨臂比较绝对位置。配置填写frame名称只增加声明，不会计算变换。

另一个现有驱动细节：关节反馈使用近似系数 `0.017444` 将度换成弧度，而非精确 `π/180`。本次保留该驱动输出，不偷偷修正历史数据；训练前宜审查这一约0.053%的比例误差。原生末端欧拉角保留整数，不受这条关节转换语句直接影响。

审查路径及hash：

- `/home/ros/.local/lib/python3.12/site-packages/piper_sdk/interface/piper_interface_v2.py`，SHA256 `2d4fdcd65cedfcfcc0c7347feba1f693c28ab4a7b27c66f9dfca931fc407d7dc`。
- `/home/ros/ros2_ws/src/piper_ros/src/piper/piper/piper_ctrl_single_node.py`，SHA256 `a897239cf674d62428bee96ca4c9cca8eca0bc7fb2111edd8d99c5848e57c7a2`。
- 当前 wrapper：[piper_driver.py](../src/robot_infra/adapters/piper_driver.py)；原生序列化：[piper_pose.py](../src/robot_infra/adapters/piper_pose.py)；通用只读订阅：[ros_pose.py](../src/robot_infra/adapters/ros_pose.py)。

## 3. 目录、事务与文件格式

```text
<dataset-root>/<task-id>/
  task.json
  episodes/episode_000000/
    manifest.json
    streams.mcap
    index.jsonl
    alignment.jsonl
    qc.json
    commit.json
    videos/stream_<流名hash>.mp4    # 仅MP4模式
  .incomplete/episode_<编号>_<uuid>/
  discarded/episode_<编号>_<uuid>/
  backups/episode_<编号>_<uuid>/
  .collector.lock                   # 采集进程活动期间
```

| 文件 | 内容 / 用法 |
|---|---|
| `task.json` | `schema_version="dataset-task/1"`、`task`原文、`task_id`目录ID；中文或含空格任务名映射成稳定hash ID |
| `manifest.json` | 本集规格、配置、期望流、时间边界、计数/hash、保存状态。完整描述见下一节 |
| `streams.mcap` | 框架自定义 MCAP；图像二进制或视频引用 + JSON事件。**不是ROS序列化bag**，不能按 ROS CDR 消息解码 |
| `index.jsonl` | 每个图像/关节反馈/末端观测的一行索引；JSONL即UTF-8，一行一个JSON对象 |
| `alignment.jsonl` | 固定相机每一帧对应其他流的最近邻索引，不复制或修改源数据 |
| `qc.json` | 帧率/间隔、缺流、时间回退、对齐、视频检查结果；可通过离线QC重新生成 |
| `commit.json` | `episode-commit/1`，source/target/backup路径；事务历史路径不代表移动后仍存在 |
| `videos/*.mp4` | MP4模式每路RGB一个视频；查 `manifest.media` 获取对应关系，不从hash文件名猜角色 |
| `failure.json` | 只在writer失败时出现，记录error和incomplete；不能将它所在目录当正常已保存episode |

录制先写 `.incomplete`，A结束后排空队列并QC，到待审阅后A保存或X丢弃。保存是整目录移动；X保留证据，不立即释放磁盘。覆盖已存在episode时先移入backups，不静默删除。退出进程正在录制的内容保留在未完成区，不自动当作已保存示范。

另有 `<deployment.output_root>/<session目录>/` 存进程日志、`effective-config.json`、`processes.json`、`stack-ended.json`，以及gateway的 `episode/events.jsonl`、`journal-summary.json`、JPEG预览旁文件。这是整场会话诊断，包含回位等录制区间外行为，**不是**上方dataset中的单集目录。JPEG预览也不是训练用RGB原始记录。

## 4. 类型约定、采样与时间轴

以下形状均是**单条样本**；`N`表示该流的实际条数，未保证各流N相等。JSON number被Python读成int或float；“float”不代表磁盘上已用固定float32张量存储。一般JSON浮点经Python双精度序列化，训练时可显式转float32。图像是二进制uint8/uint16/float32；视频解码后通常为RGB uint8。

| 时间字段 | 类型 / 单位 | 含义 |
|---|---|---|
| `host_monotonic_ns`、index的`received_ns` | int，ns | 本机单调时钟；事件为打点/入队前记录时刻，图像为ROS回调接收时刻，不是编码写盘完成时刻 |
| `host_unix_ns` | int，ns since Unix epoch | 同次接收/打点的系统墙钟，可受校时影响 |
| `stamp_ns`、`source_stamp_ns`、关节`device_stamp_ns` | int，ns；可null的索引字段 | 上游ROS/SDK提供的时间；名称含device不证明来自硬件时钟 |
| 原生位姿`native.sdk_time_stamp_s` | float，s | SDK原始float时间；另构造ns字段供MCAP/索引使用，保留原值避免假装有纳秒精度 |
| `received_s`、`device_changed_s`、`created_s` | float，s | 框架本机monotonic，用于新鲜度/IK截止期 |
| WebXR `client_time_ms`、`xr_frame_time_ms` | float，ms | 浏览器性能时钟/XR帧时间；与机器人monotonic没有已验证的同一零点 |
| WebXR `client_unix_ms` | number，ms | 头显系统墙钟；不保证与机器人同步 |
| MP4 `pts` × `time_base[0]/time_base[1]` | int × rational，s | 视频媒体时间轴；**不是曝光时间或硬件时间** |

所有ns字段请用Python int或int64/uint64读取，避免先经JavaScript Number而损失整数精度。不要直接相减来自不同设备/浏览器/ROS时钟的stamp来声称网络或动作延迟。SDK的native stamp是消息更新时间语义，当前未验证其为控制器硬件采样时钟。

频率：相机配置30fps；session控制循环配置60Hz；浏览器通常约每33ms提交最新输入，并优先保留按钮边沿，但会因网络/跟踪暂停而降低；驱动wrapper约每5ms发布状态，实际收到的关节/末端条数受调度和DDS影响。重复发布同一源stamp不代表新增硬件样本。不要将这些配置频率等同于严格周期或相互同步。

## 5. manifest.json 字段

| 字段 | 类型 / 形状 | 含义 |
|---|---|---|
| `schema_version` | str | 原始RGB模式`real-episode/1`；MP4模式`real-episode/2` |
| `task`、`episode`、`status` | str / int / str | 任务原文、编号、recording/review/saved/discarded；未完成状态须结合目录和failure判断 |
| `start_monotonic_ns`、`end_monotonic_ns` | int，ns | 捕获窗口；duration为两者差。初始嵌入MCAP的manifest早于最终落盘sidecar，分析应优先用最终manifest |
| `start_unix_ns` | int，ns | 开始时本机墙钟 |
| `recording` | object | 队列、存储后端、编码参数、QC、alignment、required_events，均为本集生效设置 |
| `camera_pipeline` | map role→object | 每角色capture/preview/record分支，RGB/depth是否启用及尺寸/FPS |
| `expected_streams` | map stream→object | 本集必须检查的流；图像定义含width/height/fps；关节/配置的pose来源为`{}` |
| `context.arms` | str[] | 执行臂ID；当前left/right |
| `context.pose_feedback` | map sourceID→配置 | 新增原生/四元数来源、话题、单位来源/转换声明、未知frame声明；旧集没有此字段 |
| `context.config` | object | 有效session配置；含关节名顺序、URDF路径/base/tip/hash、driver模块/hash、坐标alignment/scale、按键、网络、相机序列号等 |
| `context.config.runtime_identity` | object | 源码树SHA256、Python/platform/ROS及关键依赖版本；不是已发布Git commit的替代证明 |
| `context.camera_info` | map `role.stream`→object | 开始时最新内参；连续camera_info还记录成事件 |
| `context.arm_status` | map side→object | 开始时状态快照，仅`ctrl_mode`、`arm_status`、`err_code`三个整数；**不是连续全字段状态记录** |
| `context.clock_notes` | str | 时钟语义说明 |
| `interrupted`、`writer_error` | str或null | 正常结束为空；非空需保留并筛选 |
| `dropped` | int | 有界录制队列溢出次数；不等于传感器/USB/DDS全部丢帧总数 |
| `mcap_sha256`、`index_sha256` | str，64hex | MCAP/索引文件SHA256 |
| `mcap_messages` | int | 全MCAP消息条数，包含事件及图像/视频引用 |
| `counts` | map stream→int | 每个流/事件条数；键不带开头`/`，MCAP topic带`/` |
| `qc_passed` | bool | 收尾时QC结果；不能代替任务成功率标签 |
| `media` | map stream→asset | 仅MP4，见第9节 |

2026-10-18历史角色确认：left_wrist=D435 `022523021289`，right_wrist=D435 `342123026960`，scene_fixed=D455 `261143061977`；left=can0，right=can2。2026-10-19实际配置/用户确认的序列号为左腕`022422072252`、右腕`342522071110`、固定`254922307547`；用户说明未换相机，差异不自动解释成硬件更换。以每集context.config.camera_configuration实际配置与确认记录为准，reader不应硬编码序列号或臂数量。

## 6. MCAP 公共封装与反馈

MCAP profile为 `robot-infra-real-episode/1` 或 `/2`。MCAP内部`log_time`用host Unix ns，`publish_time`在图像/关节/pose时使用上游stamp，其余事件回退host Unix ns。跨时钟排序请用JSON中的monotonic或index，而非盲用publish_time。`sequence`是**整集消息全局序号**，不是各相机帧号，也不是手柄seq。

JSON消息使用UTF-8、message_encoding=`json`；原始图像message_encoding=`robot-infra-raw-image/1`。JSON事件公共外层：

| 字段 | 类型 | 含义 |
|---|---|---|
| `schema_version` | str | `real-episode-event/1` |
| `host_monotonic_ns`、`host_unix_ns` | int | 本机记录时刻，ns |
| `kind` | str | feedback/pose_feedback/raw_input/command等 |
| `payload` | object | 下述分类型内容；不同kind不能用同一数组盲目堆叠 |

### 6.1 关节与夹爪实测反馈：`/feedback/<side>`

| payload字段 | 类型 / 形状 | 单位 / 含义 |
|---|---|---|
| `side` | str | 执行臂ID |
| `q` | float[6]（一般为[J]） | 驱动发布的关节角，rad；顺序取`context.config.model.joint_names`，当前joint1…joint6 |
| `gripper` | float标量 | 总开口/行程坐标，m；0.07表示70mm，不是每根手指位移 |
| `received_s` | float | gateway处理回调时的host monotonic，s |
| `device_stamp_ns` | int | JointState header stamp；本驱动从SDK状态更新时间组合得到 |
| `device_changed_s` | float | 最后一次源stamp发生变化的host monotonic，s；位置没变化不代表stamp没更新 |

没有`velocity`/`effort`字段，不应凭空用零填成测量值。需要速度时可在导出层显式计算差分，标注derived且处理时间间隔/噪声。当前关节反馈SDK源stamp使用关节和高速反馈时间的组合，不能视作关节和夹爪严格同时采样。

### 6.2 原生末端：`/pose_feedback/<sourceID>`（当前`left_native`/`right_native`）

仍用公共事件外层，`kind="pose_feedback"`。payload如下：

| payload字段 | 类型 / 形状 | 单位 / 含义 |
|---|---|---|
| `schema_version` | str | `pose-feedback/1` |
| `source_id`、`topic` | str | 通用观测来源ID、原ROS topic；不从名字推断世界坐标 |
| `representation` | str | `native_euler` |
| `orientation_provenance`、`conversion` | str / null | `native` / `null`，未转换 |
| `source_stamp_ns`、`header_frame_id` | int / str | 源时间及原frame；当前frame为空 |
| `reference_frame`、`tracked_frame` | str或null | 配置声明；当前null；不是自动补上的base/TCP |
| `frame_status`、`provenance`、`source_clock_domain` | str | 来源、未知项和时钟解释 |
| `native.schema_version` | str | `native-pose/1` |
| `native.position.values` | int[3] | `[X_axis,Y_axis,Z_axis]`原始整数 |
| `native.position.axes`、`unit` | str[3] / str | `X,Y,Z` / `0.001mm` |
| `native.orientation.values` | int[3] | `[RX_axis,RY_axis,RZ_axis]`原始整数 |
| `native.orientation.axes`、`unit` | str[3] / str | `RX,RY,RZ` / `0.001degree` |
| `native.orientation.representation`、`convention` | str / str | euler及厂商原生约定说明；不强行称为已标定的通用RPY |
| `native.sdk_time_stamp_s` | float | SDK原始时间，s |
| `native.source_stamp_ns`、`header_frame_id` | int / str | 上方对应字段副本；按SDK秒字段拆分为ns，保留转换描述 |
| `native.timestamp_conversion`、`component_atomicity` | str | 时间单位换算、CAN缓存分量非原子说明 |

例：`position.values=[123456,-789,200000]` 表示 `[123.456,-0.789,200] mm`；`orientation.values=[90000,-45000,123]` 表示 `[90,-45,0.123] degree`。这些是说明用数值，不是当前机器人实测姿态。如训练需要米/弧度，可在导出层明确生成 `position_m = values × 1e-6`、`angles_rad = values × π/180000`，并记录转换版本，保留原字段。

### 6.3 驱动转换的末端四元数：`*_quaternion`

公共来源/frame字段同上，`representation="quaternion_xyzw"`，并有：

| 字段 | 类型 / 形状 | 含义 |
|---|---|---|
| `position_m` | float[3] | 驱动已换算成米的XYZ，原样记录 |
| `orientation_xyzw` | float[4] | `[qx,qy,qz,qw]`，无量纲，驱动转换结果 |
| `orientation_provenance` | str | `converted`，不能当作原生Quaternion |
| `conversion` | str | 明确记录原生Euler→degree/radian→SciPy xyz→xyzw转换方式 |
| `quaternion_norm`、`quaternion_unit` | float / bool | 框架计算范数及`abs(norm-1)≤0.001`检查；不修改原值，不合格则QC标记 |

四元数q与−q表示相同旋转；本记录不消除符号翻转。做插值、差分和训练前应处理这一等价性。原生和转换流按各自stamp保存，不强行拼成同一条原子测量。

## 7. RGB、深度和相机标定信息

### 7.1 原始图像：`/camera/<role>/rgb` 或 `/depth`

单条MCAP image body布局：`uint32 little-endian JSON长度` + `UTF-8 metadata JSON` + `原像素字节（含行padding）`。不是PNG/JPEG，也不是ROS Image二进制结构。

| metadata字段 | 类型 / 形状 | 含义 |
|---|---|---|
| `role`、`stream` | str | 相机角色及rgb/depth |
| `stamp_ns`、`frame_id` | int / str | ROS header原时间/坐标系名 |
| `width`、`height` | int | 存储图像W/H，像素 |
| `step` | int | 每行字节数；不保证等于W×通道数 |
| `encoding` | str | RGB常见rgb8/bgr8；深度16UC1/mono16/32FC1 |
| `is_bigendian` | int，0/1 | 多字节像素字节序 |
| `host_monotonic_ns`、`host_unix_ns` | int | 接收时刻，ns |
| `source_clock_domain` | str | ROS header时间，设备metadata另外记录 |
| `depth_unit` | str或null | RGB为null；深度声明保持native值，需另查scale |
| `source_geometry`、`resize` | object，仅发生RGB缩放时 | 原W/H/step/encoding，以及bilinear方法和scale_x/y；采集和保存尺寸可不同 |

| 像素编码 | 数组解释 | 单位 |
|---|---|---|
| rgb8 / bgr8 | uint8[H,W,3]，范围0…255；通道按encoding | 颜色数值 |
| 16UC1 / mono16 | uint16[H,W]，按字节序和step读取 | 原生深度数值；**本格式不保证乘0.001就是米** |
| 32FC1 | float32[H,W]，按字节序和step读取 | 上游约定；不能只根据dtype猜单位 |

深度若启用，当前记录的是depth/image_rect_raw，**没有实现自动对齐至RGB、depth resize或点云生成**。启用深度前须确认深度scale和有效/无效像素约定，并保存可核验的校准说明。

### 7.2 `/event/camera_info`

payload有role、stream、stamp_ns、frame_id、width、height、distortion_model，以及 `k:float[9]`、`d:float[D]`、`r:float[9]`、`p:float[12]`。K为3×3、R为3×3、P为3×4，均按行展开。K中的fx/fy/cx/cy以像素计，D是对应distortion_model的畸变系数；本台架常见5项，但D不是固定长度。P/R含义按上游ROS CameraInfo约定解释。

这些内参属于**capture图像尺寸**。record若缩放，事件不会偷偷改K；使用者须按图像metadata中的scale变换内参。`frame_id`本身不能提供外参。没有已标定的相机→机器人、左右臂→全局的数值变换。

### 7.3 `/event/device_metadata`

payload为 `role:str`、`stream:str`、`stamp_ns:int`、`frame_id:str`、`raw_json:str`。`raw_json`是RealSense驱动metadata字符串，可再次 `json.loads`；不同设备/版本可能包含不同帧号、曝光、增益和时间域字段。**不保证每个键存在，也不把其未知单位统一解释。** 消息包缺失时会记录运行错误提示，缺metadata不等于没有RGB图像。

## 8. WebXR输入与控制过程

### 8.1 `/event/raw_input` 的payload

| 字段                                                   | 类型 / 形状           | 含义                                                                                |
| ---------------------------------------------------- | ----------------- | --------------------------------------------------------------------------------- |
| `schema_version`                                     | str               | webxr-input/1                                                                     |
| `session_id`、`seq`、`epoch`                           | str / int / int   | 浏览器会话ID、实际传输包序号、参考空间重置epoch                                                       |
| `event`、`reference_space`、`visibility`               | str               | 当前页面通常frame、local-floor、visible；不追踪时pose可null                                     |
| `client_time_ms`、`client_unix_ms`、`xr_frame_time_ms` | number            | 三种浏览器/XR时间，见第4节                                                                   |
| `client_frame_seq`                                   | int               | 浏览器采样帧号；与传输seq不同，未传的最新帧可被合并                                                       |
| `previous_frame_work_ms`                             | float             | 上一帧JS工作耗时，ms；不是机器人动作延迟                                                            |
| `head`                                               | pose或null         | 头显位姿；pose含position_m[3]、orientation_xyzw[4]、emulated_position:bool                |
| `inputs`                                             | object[S]，S可变化    | 每个输入源；不要假设总有两个有效控制器                                                               |
| `inputs[].source_id`、`handedness`、`profiles`         | int / str / str[] | 浏览器输入源ID、left/right/none、浏览器公布的设备profile                                          |
| `inputs[].grip`、`target_ray`                         | pose或null         | 手持位姿与指向射线位姿，不能混用                                                                  |
| `inputs[].gamepad`                                   | object或null       | buttons与axes                                                                      |
| `gamepad.buttons`                                    | object[B]         | 每按钮value:number[0,1]、pressed:bool、touched:bool                                    |
| `gamepad.axes`                                       | number[A]         | 轴值[-1,1]；A/B由设备决定，缺项不能盲读                                                          |
| `last_server_s`                                      | float，s           | 最近服务器新鲜度票据；不是浏览器与服务器时钟同步结果                                                        |
| `transport`                                          | object            | skipped/errors:int、previous_rtt_ms:number或null；传输诊断                               |
| `client_media`                                       | object            | enabled:bool；streams按角色含fetch_ms/decode_ms:number或null、bytes:int、errors:int；仅预览诊断 |

WebXR使用右手参考空间，通常+X右、+Y上、−Z前；并不是Piper基座坐标。当前映射alignment为 `[[0,0,-1],[-1,0,0],[0,1,0]]`、scale=1，实际应读context中的配置。PICO本台架profile曾出现`pico-4u`；这只是浏览器报告，不等于独立硬件型号鉴定。

按钮索引也取配置：当前扳机0、侧握1、右A4、左X4。扳机按下开/松开关，独立于侧握；侧握控制位姿跟随。输入是操作者意图，不是可以直接拿去驱动机器人或当作训练action的执行命令。

### 8.2 过程事件字段

| kind / topic后缀                          | payload主要字段（类型/形状）                                                                                                                                       | 解释                                                                |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `mapping_anchor`                        | side:str、token:str、q:float[J]、hand:WebXR pose                                                                                                            | 侧握重新锚定时的关节与手柄快照；不连续                                               |
| `intent`                                | side:str、seq:int、token:str、created_s:float、target:float[4,4]、seed:float[J]                                                                               | 目标齐次矩阵，左上3×3旋转无量纲，最后一列前三项为米，最后一行为0,0,0,1；frame为URDF base→tip      |
| `motion_result`                         | side、usable:bool、type、token、goal_seq:int、created_s、result或error                                                                                          | IK进程结果；usable只说明session判断时的令牌/新鲜度合格                               |
| `motion_result.result`                  | positions:float[J]、accepted:bool、position_error_m:float、orientation_error_rad:float、iterations:int、elapsed_ms:float、reason:str、seed_projection_rad:float | 求解与投影诊断；accepted可含配置允许的best-effort，不等于目标精确达到                      |
| `command`（关节）                           | side、q:float[J]、gripper_m:float或null、seq:int、source:str                                                                                                  | 准备发布的关节绝对位置；q单位rad。独立夹爪模式中gripper_m常为null                         |
| `command`（夹爪）                           | side、operation="gripper_only"、gripper_m:float、seq、source                                                                                                 | 夹爪开口绝对目标，m；没有q字段                                                  |
| `command`（保持）                           | side、operation="measured_hold"、q、observed_q:float[J]、reason                                                                                              | 暂停/松握/停止时的测量保持；q可能因测量容差投影到模型限位                                    |
| `guard`（动作）                             | decision:str、reason:str或null、command:CommandSet、active_sides:str[]、jaw_sides:str[]                                                                       | 拒绝/接受与将执行的端点掩码；不能把command里所有端点都当已发送                               |
| `guard`（使能/保持）                          | decision、operation、side、epoch或reason                                                                                                                     | 不含完整CommandSet，需按operation区分                                      |
| `receipt`                               | side、seq或operation、status="published_not_acknowledged"                                                                                                   | 只确认ROS发布调用返回，不是执行完成/到位信号                                          |
| `ownership`                             | owner:str或null、epoch:int、reason、bounds（授予时）                                                                                                              | 控制归属和失效代次；bounds为每臂[J,2]rad                                       |
| `stop`                                  | reason、result、可选error                                                                                                                                    | 保持是否尝试、是否有新鲜反馈等                                                   |
| `session_state`                         | state:str、reason:str、trials:int                                                                                                                          | 录制期间的状态变化；回位通常发生在episode外，只在session journal中                      |
| `teleop_started` / `teleop_ended`       | trial:int、recording:bool                                                                                                                                 | 本次示范开始/结束                                                         |
| `observation_error`                     | source_id、topic、observation_kind、error:str                                                                                                               | 新增只读观测错误；无效数值不伪装成有效pose，不改变控制意图                                   |
| `recording_started`                     | start_monotonic_ns:int                                                                                                                                   | disk worker就绪后的有效捕获起点                                             |
| `episode_manifest` / `episode_finalize` | 初始manifest / 收尾updates                                                                                                                                   | 收尾含end_monotonic_ns/interrupted/dropped/writer_error；最终sidecar更完整 |

`CommandSet`字段：schema_version=`collection-event/1`；session_id/source/lease_token/snapshot_id为str或文中允许的null；seq/epoch为int；created_ns/target_ns/expires_ns为host monotonic ns；targets为具名端点列表。每个target有endpoint_id:str、names:str[J]、positions:number[J]、unit:str、frame_id:str。当前arm为rad，gripper为m。**这是一组候选目标契约，实际发布还要结合active_sides/jaw_sides和独立command事件。**

记录器只在episode有效窗口接收事件；启动回位、保存/丢弃后的按键、HTTP client_event、预览JPEG等不保证出现在单集MCAP里。完整诊断应同时查session journal。

## 9. MP4模式的额外字段

MP4下相机topic仍存在，但JSON消息变为 `schema_version="robot-infra-video-frame/1"`，不是上方event外层。body为 `image:<第7节metadata>` + `media:{path,frame_index,pts,time_base}`。

| 字段 | 类型 | 含义 |
|---|---|---|
| `media.path` | str | 相对episode目录的视频路径 |
| `media.frame_index` | int，0开始 | 本流收到并写入视频的帧序号 |
| `media.pts`、`time_base` | int / int[2] | 逻辑PTS=frame_index，逻辑time_base=[1,fps]；MP4容器可重标度time_base，比较时用有理秒值 |
| `manifest.media[stream]` | object | path、frames/width/height/fps:int、encoder/codec/pixel_format:str、pts_policy:str、time_base:int[2]、bytes:int、sha256:str |

默认libx264/yuv420p/CRF20/veryfast/GOP30/单编码器1线程；有损，具体读本集recording.storage.video。保存的视频按已收到的帧构造连续固定帧率时间轴，不插入复制帧来掩盖源掉帧。因此播放时长或frame_index/fps不能当原始采集时间。对齐、选训练帧时使用MCAP/index中的原始源/接收时间，再经frame_index定位视频帧。BGR源图像在视频解码后按RGB读取；metadata中encoding描述源，不表示解码数组必须仍为BGR。

深度和事件不进MP4。这个布局更便于复用视频，但**尚非完整LeRobot v3**：没有Parquet训练行、全局episode/task索引、统计量、训练action定义或标准多episode视频分片。

## 10. index、alignment和QC

`index.jsonl`：stream:str（无前导/）、sequence:int（MCAP全局序号）、received_ns:int（monotonic）、source_stamp_ns:int或null。图像另有profile_match:bool；MP4另有media对象；四元数pose另有quaternion_norm/unit。原生Euler没有quaternion字段。

`alignment.jsonl`：每行有reference_sequence:int、received_ns:int、clock_domain=`host_received_monotonic`、valid:bool、matches:map。每个match含sequence:int或null、delta_ns:int或null、valid:bool；delta=匹配流接收时刻−参考帧接收时刻。当前参考camera/scene_fixed/rgb，容差50ms。最近邻是离线选择，允许同一样本匹配多帧，**不是曝光硬同步、插值、严格因果训练视图或已完成延迟补偿**。

`qc.json`：schema_version=`episode-qc/1`、passed:bool、issues:str[]、duration_s:float、streams:map、media:map、alignment:object、deep_integrity_checked:bool。每流统计包括frames、fps_received、max_gap_ms、out_of_order、profile_mismatches、source_stamp_regressions；pose另含unique_source_stamps、zero_source_stamps、non_unit_quaternions。frames对pose/feedback表示收到的消息条数，不是硬件曝光帧。

默认检查图像帧率/覆盖不少于目标80%、最大帧间隔150ms、最短1s、无效对齐比例不超过10%；阈值见本集recording，不是整个框架的不可变常数。新增配置pose缺失、stamp为零/整段冻结、非单位四元数、observation_error也标为问题。帧率/最近邻无法穷尽USB/硬件内部丢包。

`--deep`另查MCAP/index哈希、footer/CRC/消息数、原图像封装；MP4另查视频哈希、全部解码/帧数/PTS与MCAP引用一致性。它不判断机械动作是否准确、物体是否抓取成功、RGB压缩是否影响策略训练。离线QC会更新本目录qc/alignment sidecar；如需冻结原始证据，先复制派生检查目录。

## 11. 怎么读取和使用

以下代码在有项目依赖的Python环境运行，均不打开硬件。路径由使用者指定。读取工具不需要ROS运行环境。

### 11.1 列出文件规格和JSON事件

```python
from pathlib import Path
import json
from mcap.reader import NonSeekingReader

episode = Path('/path/to/episode_000000')
manifest = json.loads((episode / 'manifest.json').read_text(encoding='utf-8'))
print(manifest['schema_version'], manifest['counts'])

with (episode / 'streams.mcap').open('rb') as source:
    for schema, channel, message in NonSeekingReader(source).iter_messages(log_time_order=False):
        if channel.topic.startswith(('/feedback/', '/pose_feedback/')):
            event = json.loads(message.data)
            print(channel.topic, message.sequence, event['host_monotonic_ns'], event['payload'])
```

### 11.2 读取原始RGB / 深度

```python
import numpy as np
from robot_infra.image_codec import decode_image, rgb_image

# message取自上方MCAP遍历，且message_encoding为robot-infra-raw-image/1
meta, raw = decode_image(message.data)
if meta['encoding'] in ('rgb8', 'bgr8'):
    rgb = np.asarray(rgb_image(meta, raw))  # uint8[H,W,3]，已处理BGR/行padding
else:
    dtype = np.dtype('f4' if meta['encoding'] == '32FC1' else 'u2')
    dtype = dtype.newbyteorder('>' if meta['is_bigendian'] else '<')
    depth_native = np.ndarray((meta['height'], meta['width']), dtype=dtype,
                              buffer=raw, strides=(meta['step'], dtype.itemsize)).copy()
    # 未确认depth_scale前，不把depth_native直接标为米。
```

NumPy属于该读取示例环境依赖；不意味着框架的原始MCAP读取必须安装完整训练框架。

### 11.3 用索引定位MP4帧

```python
import av

rows = [json.loads(line) for line in (episode / 'index.jsonl').read_text().splitlines()]
row = next(r for r in rows if r['stream'] == 'camera/scene_fixed/rgb' and 'media' in r)
asset = row['media']
with av.open(str(episode / asset['path'])) as container:
    for index, frame in enumerate(container.decode(video=0)):
        if index == asset['frame_index']:
            rgb = frame.to_ndarray(format='rgb24')
            capture_received_ns = row['received_ns']
            capture_source_ns = row['source_stamp_ns']
            break
```

上例按顺序解码，便于理解且结果明确；大量随机取帧应按GOP批量缓存，不能把任意frame_index当作容器seek的PTS。

### 11.4 导出训练张量时需要明确的决定

可选择构造 `observation.state = [left_q(6), left_gripper(1), right_q(6), right_gripper(1)]` 为float32[T,14]；这只是**建议的显式导出映射，当前文件没有自动生成该字段**。原生末端可以另成XYZ/Euler张量，并明确从原生整数换算的单位和坐标系。

action可选最终绝对关节目标或经审查的末端目标，但必须定义频率、绝对/相对、夹爪、有效掩码和时延。先过滤被guard拒绝的候选、单独识别保持与夹爪命令，再与实际feedback核对；不能把IK intent或published receipt直接当作动作执行成功。四元数、Euler、rotation matrix/6D旋转表示应在导出规范中固定，转换留痕。

建议保留原始层→对齐/筛选视图→训练导出三层，导出物记录来源episode/hash、导出脚本版本、时钟选择、目标采样率、状态插值方式、图像选帧方式、单位与action语义。几何上尚未确认的厂商末端坐标不能静默拼进跨机器人统一世界坐标。

## 12. 已有真实数据的规模和接下来的验证

原始现场episode2：26.179121925秒，MCAP2,182,403,012字节、24,380条消息；固定相机785帧、左腕784、右腕784，约30fps；关节反馈left4696/right4700条；WebXR输入518包、intent428、IK结果428、command2936（含保持/夹爪）、receipt2352。QC/deep通过。详见[现场验证](validation/2026-10-18-a4s-link-and-episodes.md)。**该旧集没有新增原生末端/四元数流。**

同一集离线MP4派生文件组约20.45MB，帧数一致、deep通过；有损编码、离线耗时和压缩比不证明实时采集或训练质量。详见[MP4验证](validation/2026-10-18-mp4-storage.md)。

本轮已通过Windows250项、Ubuntu263项无硬件测试，包含真实ROS本机消息序列化、raw/MP4记录/索引/deep QC和配置检查。已部署到机器人，四路来源的raw/MP4静态预检通过，未启动设备。详见[新增观测软件验证](validation/2026-10-18-native-pose.md)。现场还需检查左右来源、静止及小幅运动时原生XYZ/Euler连续性、源stamp更新、与转换四元数时间对应关系、数据增长和控制/相机并发负载。再单独做厂商工具点/URDF工具点与外参标定，不用一次软件测试替代这些物理验证。
