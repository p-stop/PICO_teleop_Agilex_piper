# 采集技术说明：部署、相机配置、数据格式与 QC

## 正式配置与迁移（2026-10-22）

当前fill_pen_holder使用`~/robot-infra/profiles/formal-018/deployment.json`，原deployment与机器身份配置保留。两侧gripper.trigger_pressed=close、teleop_start=follow_trigger；进入遥操的有效扳机输入立即控制夹爪，松开为上限开口。省略teleop_start时默认preserve，即先保留开口，扳机变化后接管。缺少扳机按钮数据不当成松开；启动/home/暂停均不主动开合。

可在另一份已验证的机器deployment上生成同类型配置（输出目录必须不存在）：

```bash
~/robot-infra/bin/robot-infra collect-configure \
  --deployment ~/robot-infra/deployment.json \
  --output ~/robot-infra/profiles/formal-new \
  --trigger-pressed close --teleop-start follow_trigger \
  --image-storage mp4 \
  --depth-role scene_fixed --depth-profile 640 480 30
```

此命令只生成session.json、cameras.json、deployment.json，不构建设备。角色参数可替换，`--depth-role`可重复；仅指定角色启用capture/record.depth，其余角色关闭depth，RGB/预览与序列号/驱动/单位保留。新deployment使用绝对解析路径，可放到独立目录；不能跨机器直接复制旧机器的绝对路径和序列号。

RGB MP4与头部原生16UC1深度共用现有有界队列/独立writer及QC；depth保留MCAP原始字节、时间戳、CameraInfo与optical frame，不默认对齐RGB，不擅自假定depth scale。实际相机检查和测试边界见[018验证](validation/2026-10-22-formal-collection.md)。以下为更早采集切片的技术细节。

日常操作请先读[操作员手册](episode-collection.md)。本文保留部署、相机、格式/时间戳、故障语义和QC细节；默认raw_mcap保留原始MCAP，另可选MP4后端，见[视频存储说明](recording-storage-options.md)。

2026-10-17。自由遥操切片之上增加真实 `real-episode/1` 采集；控制仍经过同一个本机网关。原 M1 和 fake `collection-plan/1` 不变，不把真实数据交给 fake reader。

2026-10-18验收：用户确认完整流程正常，首个episode2保存26.179秒、2.18GB，三原生RGB约30fps，QC和deep完整性检查通过。独立夹爪无需侧握已现场确认；临时实验栈正常停止，稳定本地入口保留。数据与边界见[验收报告](validation/2026-10-18-a4s-link-and-episodes.md)。以下命令应在机器人终端运行，新的正式任务使用你指定的任务名/路径，不把本次validation任务当训练任务。

## 末端位姿观测配置

2026-10-19新增软件：`diagnostics`配置可声明segment_bytes（默认128MiB）、max_bytes（默认null，不设会话总上限）和min_free_bytes（默认1GiB）；追加分段不删除旧日志，summary含segments/bytes/hash。读取整场日志需跟随segments。原始episode仍由独立writer记录，不因诊断分段改变采样率。

capture FPS与record FPS相同时保留每个收到的帧；显式降低record FPS时才按RateGate降采样。图像新增capture_sequence，manifest新增frame_capture_stats，分别观察回调序号和writer接收/筛选/写入。context.initial_targets保存开始前已确认发布的目标快照，为夹爪训练标签保留目标证据；不知道的目标不编造。ACK的server_timing.input_ms与后续输入previous_server_input_ms仅用于处理耗时诊断，不等同网络单向延迟。

完整字段和读取方法见[数据格式报告](collection-data-format-report.md)。新版本可在session配置的`pose_feedback` map中配置任意具名观测来源；示例配置为每臂原生Euler和驱动转换Quaternion两路。删除Quaternion来源即可只采原生Euler；删除整个`pose_feedback`则不要求任何末端观测，不改变旧数据格式。

每来源显式包含`topic`、`format`（`native_pose_json`或`pose_stamped`）、`provenance`、`source_clock_domain`、`reference_frame`、`tracked_frame`、`frame_status`、`orientation_provenance`（native/converted/unknown）和`conversion`。转换结果必须填conversion说明，原生结果为null。frame未知可填null；仅填写名称不会执行变换。见[可运行配置模板](../configs/teleop-session.example.json)。

Piper wrapper只在每臂配置`native_pose_topic`时增加SDK缓存的原生只读发布；该字段应与对应native来源topic一致，且不得与控制话题重合。不增加SDK连接或位姿查询，不把原生Euler改成Quaternion。原生`position.values`是0.001mm整数、`orientation.values`是0.001degree整数；原始Quaternion话题的值已由厂商ROS驱动转换，另流明确标记。

显式配置的来源都会进入本集expected_streams与QC/对齐；未发布或异常会显示QC问题，不填假数据。新增流与raw/MP4共用存储、保存/丢弃流程。本轮不启动物理实验，实际源流率/并发负载留待现场验收。

## 脱离 Windows 运行

机器人端部署根目录为 `~/robot-infra`，设备内的源码、Python依赖、证书、ROS和供应商工作区提供运行环境。Windows、SSH端口转发、代理和外部CDN均不在运行链路中。PICO仍需能访问机器人局域网HTTPS地址。

在机器人自己的终端执行：

```bash
~/robot-infra/bin/robot-infra collect \
  --deployment ~/robot-infra/deployment.json \
  --task "把积木放进盒子" \
  --dataset-root ~/datasets/robot-experiments \
  --start-episode 0 --existing skip
```

入口自动读取设备端 `~/robot-infra/deployment.json`，source其中声明的ROS环境，然后启动本机双臂驱动、相机、IK、网页及录制器。无需先开Windows对话。只做自由遥操：`~/robot-infra/bin/robot-infra device-teleop`。终端Ctrl+C正常停止；原生驱动不自动失能、回位或关爪。

入口区别：裸 `robot-infra collect` / `python3 -m robot_infra collect` 必须传 `--deployment`；设备专用脚本才提供默认值。脚本配置优先级为显式 `--deployment PATH` 或 `--deployment=PATH` → `ROBOT_INFRA_DEPLOYMENT` → `<device-root>/deployment.json`。ROS setup与PYTHONPATH均来自同一份被选中的文件，显式参数不再被默认配置覆盖。直接Python入口需自行准备相应环境。

`--task`、`--dataset-root`、`--start-episode`、`--existing` 在采集命令中均必填，防止使用上次任务而不自知。`--duration 0` 表示一直运行到Ctrl+C；设备默认0，现场验证使用明确有限时长。先加 `--check-only` 可做不构造设备的静态检查。CAN需已由实验室激活，工具不调用sudo。双臂、相机被其他程序占用时先退出对应程序。

链路排查时，可在进入VR前取消“显示相机预览”，再只移动手柄而不按A或侧握，比较开关预览时HUD的控制RTT。关闭的仅是浏览器JPEG请求，不关闭原生相机或修改录制配置。诊断信息和原始输入保留各路fetch/decode耗时、bytes及失败数；单次请求失败仍保留最后成功图像，超过1.5秒无更新才标红。控制传输失败会清空待发队列并停止自动重试，页面提示退出/刷新，不自动接续运动或拼接episode。该诊断入口不代表已解决特定网络故障。

也可打开 `https://<robot-ip>:8445/?preview=off`，直接以关闭预览状态进入；HUD应显示“预览已关闭”，原始输入中的client_media.enabled应为false，才算有效的OFF对照。RTT较低不保证输入持续：还需比较相邻浏览器/XR帧时间和服务器接收间隙，排除头显帧回调停顿。不要跨不同session/epoch拼接计算连续控制间隔。

机器人IP变化不影响本地程序运行，头显改用新地址 `https://<robot-ip>:8445/`；可用 `hostname -I` 查地址，启动时 `--advertise-host <robot-ip>` 可打印正确访问URL。测试证书的SAN需覆盖当前地址，重新生成方法见[证书说明](live-teleop.md)。设备时间和证书有效期也需要正确。网页及Three.js全部本机提供。

部署布局：

```text
~/robot-infra/
  bin/robot-infra             # 本机入口（ROS环境与Python路径）
  deployment.json            # 本机路径/ROS环境/domain/端口/日志位置
  profiles/robot.session.json # 模型/控制/按键/页面/录制/QC配置
  profiles/robot.cameras.json # 相机身份、原生流、预览、录制分支
  profiles/tls/              # 本机证书，私钥权限0600，不提交
  releases/<snapshot>/       # 已校验的源码快照
  current -> releases/...    # 当前版本，更新时显式切换
  python-deps/               # 独立纯Python依赖；不改ROS/系统Python
  release-manifest.json      # 源码归档hash及部署方式
  runs/                      # 每次进程日志/有效配置/诊断
```

本次为源码快照部署，尚未发布Git远程或宣称按uv.lock重建了设备ROS环境。换设备复制模板 `configs/deployment.example.json`，重新填写路径、模型、驱动hash和设备身份，并复验。设备本地配置与私钥不进入发布包；不要把参考仓库或实验数据打包。

## 三条相机分支

`realsense-streams/2` 在具体RealSense适配层描述源，核心录制只认识具名stream和图像元信息。每台相机示例：

```json
{
  "role": "scene_fixed",
  "serial_namespace": "realsense_sdk",
  "serial": "填设备SDK序列号",
  "capture": {
    "rgb": {"width": 640, "height": 480, "fps": 30},
    "depth": null
  },
  "preview": {"width": 480, "height": 360, "fps": 8, "jpeg_quality": 75},
  "record": {
    "rgb": {"width": 640, "height": 480, "fps": 30},
    "depth": null
  },
  "driver_parameters": {"rgb_camera.enable_auto_exposure": true}
}
```

- `capture`：硬件/驱动原生分辨率、帧率。配置目标与状态页的实收尺寸/FPS分别展示；不支持的模式可能由驱动拒绝或回退，QC记录profile不一致。
- `preview`：从RGB独立缩放/限频/JPEG编码，只影响VR和诊断预览，不改变原始录制。浏览器按该分支帧率轮询；实际网络/编码显示帧率可低于目标。
- `record`：RGB可与原生相同，也可显式缩小分辨率/降低采样率。缩小时记录原始几何和resize变换，保留原生camera_info；消费者按变换调整内参，不能把原内参直接用在缩小后的图像。默认录制原生640×480/30，保存原始RGB字节而非预览JPEG。
- 开深度：把 `capture.depth` 与 `record.depth` 都设为同一个原生profile，如640×480/30。当前不缩放深度，不把uint16随意转成米，原生字节序、编码、步长与SDK metadata完整保留。米制解释需核对该设备depth scale/标定。默认不开深度；三相机同时RGB+depth或高分辨率需另外测USB/CPU/磁盘预算。
- `driver_parameters`：显式传原生参数（例如曝光/增益）；身份、启停和profile等保留字段由结构化配置唯一管理，不能从旁覆盖。参数名/范围需匹配实际安装的驱动。对应参数依据[RealSense官方ROS文档](https://github.com/realsenseai/realsense-ros#parameters)；本轮运行版本以设备证据为准。

旧 `realsense-rgb-sample/1` 继续接受，归一化为RGB原生录制+旧预览设置。不要只改旧session中展示用的camera_profiles；完整启动器以camera-config生成本轮 `effective-config.json`，避免两个来源互相矛盾。修改配置后重启会话；没有实现运行中热切换图像规格。

`vr_layout.distance_m` 已由2.20改为2.21m，主画面/腕屏/HUD随布局一起后移1cm，画面仍固定于进入时的空间参考；后续可继续在同一配置调整。

HUD新增 `vr_layout.hud_face_viewer=true`，上下HUD分别向进入时的观察点倾斜；关闭时可用 `hud_tilt_deg` 指定角度。它不跟随实时头部旋转。控制默认通过 `webxr_transport.input=websocket`、port=8446独立WSS连接，视频/状态留在8445；不与三路图片共用HTTP请求队列。对应可选依赖为 `teleop`（websockets16）。旧HTTP输入保留兼容，未配置时不强制WSS。第一次若控制连接报证书错误，在网页“检查控制连接”打开同机器人8446处理证书，再刷新主页面。网络需要同时可达这两个端口。

现场初轮15fps预览时出现控制输入HTTP尾延迟>.6秒且用户感到画面/跟手延迟，记录被正确标中断；未把超时放宽。新版预览默认8fps，并优先控制消息；`preview_congestion_rtt_ms=100`、`preview_congestion_fps=2`在控制RTT较高时降低显示轮询，不改变原始采集30fps。浏览器优先级是提示，独立持久连接与实测延迟才是验证依据。

## 按键流程与磁盘目录

1. 启动和动态自检后待机，A回home；home期间不录episode、不改变夹爪开口。
2. 准备就绪按A，异步创建临时episode。显示PREPARING时不会跟随；录制器就绪才进入遥操。按侧握控制同侧臂；扳机独立控制同侧夹爪，按下开/松开关，不需要侧握。刚进入遥操时先记当前扳机状态，第一次主动改变扳机后才开始发夹爪目标，避免按A时自动关爪。
3. 按A结束：立即撤销控制并保持，停止接收新录制样本；磁盘线程排空队列、写MCAP footer/摘要、生成QC和对齐索引。结束时间取A触发时刻，不能把磁盘排空时间加到episode时长里。
4. 显示REVIEW后：A保存，X丢弃。两个动作均异步提交，完成回待机。按住A不会自动跨越多个阶段；只有新上升沿触发。
5. 退出VR、跟踪/输入失联时，活动episode停止并标记interrupted。重进后审阅这份数据；不会把重连后的操作拼接进同一连续episode。中断或QC不通过仍可由用户保存用于排错，但 `qc.passed=false`，不能当合格示范。

任务文字原样保存；便携ASCII名称直接作为目录ID，含中文/空格等名称生成确定性的任务ID，`task.json`保留原文。各任务编号独立。

```text
<dataset-root>/<task-id>/
  task.json
  .collector.lock             # 同任务只允许一个采集进程
  .incomplete/episode_000000_<uuid>/
  episodes/episode_000000/    # A保存后的数据
    streams.mcap             # 原始图像/metadata/意图/命令/反馈等
    manifest.json            # 配置/模型/时间域/计数/hash/QC状态
    index.jsonl              # MCAP sequence到流/原始时间的索引
    alignment.jsonl          # 参考图像逐帧最近邻匹配与误差
    qc.json
    commit.json
  discarded/episode_000001_<uuid>/  # X丢弃的证据，保留而非删除
  backups/episode_000000_<uuid>/    # 显式覆盖时的旧版
```

`error`：起始号已有保存或未完成目录就报错；`skip`：跳过已保存和未完成编号，保留旧数据；`overwrite`：本轮录制完成且按A保存后，旧版本先移到backups，再提交新目录；失败时尽力还原旧版。录制开始时绝不先删旧episode。X丢弃后重用当前编号，成功保存后加1。磁盘清理应由用户另外管理，此工具不删除历史备份/丢弃证据。

进程异常退出的 `.incomplete` 不自动算保存。任务锁包含host/pid/token；确认同主机旧进程已死后，可在启动命令加 `--recover-lock`，程序会核验，不抢占活跃采集任务。跨主机锁不自动恢复。目录提交有事务记录和旧版备份，但不宣称任意断电时跨多个rename原子完成；异常后以这些路径恢复证据。

## 记录内容、时间与 QC

### MP4 编码配置

`collect --image-storage mp4` 可覆盖会话默认值；`--image-storage raw_mcap`显式选择原始模式。也可在会话JSON的 `recording.storage` 持久设置：

```json
{
  "image_backend": "mp4",
  "video": {
    "codec": "libx264",
    "pixel_format": "yuv420p",
    "options": {"crf": "20", "preset": "veryfast"},
    "gop_size": 30,
    "threads": 1
  }
}
```

编码器、像素格式和FFmpeg字符串选项都可配置；options整体替换默认字典，切换编码器时应给出对应选项。yuv420p要求录制宽高为偶数，工具拒绝不兼容设置而不偷偷改尺寸。每个RGB流独立视频，BGR/行stride在存储后端处理；深度保持原始编码。内部编码线程数可调，但帧入队、编码/写盘、控制仍分层。

新环境需安装可选 `mp4` extra（PyAV16.1，依赖隔离于ROS/system Python）；Windows项目可用 `uv --cache-dir .uv-cache sync --locked --extra dev --extra video --extra mp4 --python 3.11`。设备端请把相应wheel或虚拟环境加入deployment.python_paths；当前台架使用独立 `python-deps-mp4`。普通raw模式不导入PyAV，也不依赖它。

MP4输出使用 `real-episode/2`，原始模式继续 `real-episode/1`。v2的 `videos/` 包含按流名hash生成的视频，manifest.media记录流名/路径、帧数、尺寸/FPS、编码、bytes/hash；MCAP的JSON引用和index保存每帧source/receive时间、源图像metadata及frame_index/PTS/time_base。视频时间按收到帧的序号/FPS生成dense CFR，不补帧、不等同真实曝光时刻；训练导出应使用原始时间索引选取采样，不以MP4时长冒充采集时长。

两种模式都用同一有界队列/worker和整目录保存、丢弃、备份流程。MP4普通QC检查文件/header/帧数/索引，deep还验证视频hash、全帧解码/PTS与MCAP引用；编码/flush失败会留下incomplete，不会伪装保存成功。视频模式不是完整LeRobot v3，Parquet导出、统计和训练动作映射仍待实现。

回调/控制线程只复制样本并入有界队列，磁盘线程独占MCAP writer与文件。队列同时按字节和条数计量，默认256MiB/16384条。内存不足、队列满或磁盘保留空间不足会中止/故障并留证据，不静默丢帧后报成功。默认至少保留1GiB；`flush_timeout_s`控制排空等待，超时保留未完成状态。原生640×480 RGB三路30fps约83MB/s、5GB/分钟，录制前应按任务时长准备空间或显式选择较低录制分辨率/帧率。

每条图像保存ROS header stamp/frame、host monotonic/Unix接收时间、width/height/step/encoding/endian。原始模式保存原像素；MP4为有损RGB视频和源metadata引用。SDK metadata独立记录。关节反馈保留设备/ROS时间；原始WebXR包保留浏览器时间、seq、session、epoch，不能当作与设备同步的时钟。原始意图、IK结果、guard、实际发布命令和发布回执也记录；发布回执不是厂家执行确认。

独立扳机模式 `gripper_control_mode=independent_trigger` 为每臂显式配置 `gripper_command_topic`，最终网关检查后经独立夹爪适配入口发送，不附带机械臂关节目标；旧clutch模式保留兼容。暂停/回位不新发夹爪目标。SDK配置开口上限当前70mm，反馈达到该值也不等同于物体已释放，放物是否成功需现场/任务标注；不自动扩展SDK范围。HUD显示IK位姿误差和最近关节限位余量；例如第5关节达到配置约70°时，软件只能给出限位内best-effort，松开侧握调整手柄再握住可重新锚定。

每轮有效配置与episode context还包含运行源码树hash、Python/平台/ROS和关键依赖版本；原生模型/驱动hash与相机配置一并保留。设备现有jsonschema4.10.3已通过完整Ubuntu套件，项目依赖下限调整为该实测版本，未用系统pip替换ROS依赖；锁文件仍为可重建的新环境解析结果，不冒充设备当前安装版本。

对齐在原始记录之上生成，默认固定相机RGB为参考，按同主机接收monotonic时间最近邻匹配其他图像/反馈，保留每个匹配的sequence和delta，默认50ms容差，超限为invalid。未做曝光硬同步、未做跨时钟隐式转换，也不把“最近收到”冒充曝光一致。训练导出可换对齐算法/插值，原始证据不被重写。

QC检查必需流/事件、实收FPS与覆盖率、最大间隙、时间倒退、源规格是否匹配、对齐无效比例、录制中断/队列损失/写入错误与最短时长。阈值在session的recording.qc与recording.alignment配置。BEST_EFFORT DDS可能在进入应用前丢样本，因此即使应用队列dropped=0也需要FPS/间隙检查。QC通过表示本轮记录满足这些配置阈值，不是任务成功标签或外部TCP精度证明。

离线完整验证（不会连接机器人）：

```bash
~/robot-infra/bin/robot-infra episode-qc \
  ~/datasets/robot-experiments/<task-id>/episodes/episode_000000 --deep
```

退出0为QC通过，3为QC问题，2为格式/完整性错误。该命令会更新QC/对齐sidecar。`--deep`还检查MCAP/索引SHA256、footer、CRC、消息数和原始图像包解码；自动收尾先做写入时hash和流索引QC，深度扫描另跑，避免在按键线程读几GB数据。

## 可复用边界与参考

`episode_store.py`管理任务/编号/提交；`real_episode.py`负责队列和MCAP；`episode_qc.py`只处理磁盘证据；`image_codec.py`不导入ROS；`camera_config.py`分离消费者配置。ROS图像采集在adapter入口、最终机械命令仍经live gateway。换输入/机器人时复用录制与存储逻辑，并重新验证端点、帧和时间语义。

借鉴本地QuestArm的 `.incomplete→episodes/discarded`、状态驱动录制和独立writer；借鉴Franka采集/写盘分离、原始与处理数据分层。不复制其机器人话题、固定目录、静默队列丢弃或写盘时间替代源时间。实现决策见[ADR0012](adr/0012-real-episodes-and-camera-fanout.md)，实际测试见[计划009](../plans/009-local-deployment-and-real-episodes.md)。LeRobot导出、任务成功标注界面、曝光级同步及跨主机对齐后续单独实现。
