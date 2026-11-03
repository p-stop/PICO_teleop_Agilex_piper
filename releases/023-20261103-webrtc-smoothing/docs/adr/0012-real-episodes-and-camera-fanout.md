# ADR0012：独立原始episode与相机消费者分支

2026-10-17提出，2026-10-18已接受并实现；A4-S三RGB采集切片现场验收通过，深度/其他分辨率仍未实测。证据见[当日验收](../validation/2026-10-18-a4s-link-and-episodes.md)及计划009。

用户要求机器人脱离Windows独立运行，配置相机原生/VR/录制流、30fps，任务与保存位置/起始号/已有编号策略，以及A保存/X丢弃。本次复用已验证v2控制面，数据层采用独立 `real-episode/1` 与 `real-episode-event/1`；旧M1/fake collection协议不混用。新增ROS相机配置 `realsense-streams/2`，继续接受旧RGB sample/1。

数据路径为源回调→有界字节/条数队列→独立磁盘worker→MCAP。控制/HTTP不等待磁盘，生命周期begin/finish/commit只发异步操作。回调仍保留原始源时间和接收时间；停止时先关闭采样边界，再排空队列，episode时长不含排空时间。溢出/磁盘错误不标成功，录制失效时撤销遥操控制。PREPARING/FINALIZING/REVIEW/COMMITTING状态显式显示，A/X仅在对应阶段生效。

图像使用MCAP内 `robot-infra-raw-image/1` 通道编码：4字节小端JSON头长度＋UTF8 JSON元信息＋完整原生图像bytes（包括行padding）。metadata含stamp/frame、host monotonic/Unix、尺寸/步长/encoding/endian。解码器公开在image_codec.py。RGB缩放时显式记录source_geometry和resize；depth保留原生字节/单位待校验，不擅自转米。当前MCAP用NONE压缩和数据CRC，便于复用现有依赖及顺序写；不生成有损训练录像。标准MCAP工具能枚举通道，图像显示需该编码的decoder，未宣称Foxglove原生可视化。

capture、preview和record配置分开：源只开一次，预览独立缩放/限频/JPEG，录制默认原生RGB，可显式缩放/降采样；深度原生profile单独声明。各消费者队列语义不同，预览可替换最新帧，正式记录不可静默丢。源目标规格与实收规格/FPS均保留。

任务存储分incomplete/episodes/discarded/backups，任务锁防止本工具多写。用户显式选择error/skip/overwrite；overwrite仅提交时移动旧版备份，新版失败尝试回滚，不删除旧数据；崩溃保留事务路径供恢复。保存和QC合格独立，QC失败仍可保留用于诊断。VR退出中止当前连续episode，保留interrupted并审阅，不自动把重连段拼接。

时间对齐是派生索引：默认按host received monotonic最近邻、阈值外标invalid，不篡改原始时间，不宣称曝光级同步。QC覆盖必需流/事件、FPS、间隙、倒退、规格、对齐误差与采集错误。deep离线再校验完整MCAP/hash/CRC/包格式。MCAP使用其[公开记录与索引格式](https://github.com/foxglove/mcap/tree/main/docs/specification)，不自建视频容器或JSON-base64大图日志。

设备入口通过robot-deployment/1声明ROS setup、Python路径、profile、证书和日志位置；完整离线网页包在机器人提供。不依赖Windows转发/代理/CDN，不写供应商工作区，不改系统Python，也不自动创建Git远程。当前为源码快照部署，正式可重建环境/跨OS设备支持另验。

首轮真实采集暴露HTTP控制与媒体尾延迟：用户未按A就因输入>.6s间断进入中断审阅，原始相机仍近30fps。保留超时语义，改用已安装websockets16的sync server独立线程/端口，输入包webxr-input/1不变，hello/ack封装webxr-control/1；媒体留HTTPS。每连接最多一条待ack输入，保留离散按键边沿与可替换最新运动采样，断线撤销控制、不自动恢复。Origin与网页同host/端口校验，TLS复用设备证书；握手/收发/退出由[websockets库](https://websockets.readthedocs.io/en/stable/reference/sync/server.html)承担，不自写协议。默认预览8fps、控制RTT高时可配置再降媒体频率，原始录制30fps不降。用户同时确认2.21m距离合适，HUD改为配置化面向进入时观察点。

用户随后明确选择扳机独立于侧握。新增independent_trigger模式与每臂独立夹爪话题/适配器方法，命令仍通过同一网关和最终检查；夹爪单独动作不启用机械臂、不发送JointCtrl。首次进入只采集扳机基线，主动改变后才发送，回位/暂停不隐式关爪；原clutch模式兼容。右臂现场第5关节饱和与约25mm/11°残差在HUD可观察，保留模型限位不伪造精确收敛。

运行环境指纹入有效配置/episode。设备jsonschema4.10.3虽低于原元数据最低4.23，但实际全套测试通过；当前仅用Draft202012等已支持API，因此声明下限扩展至4.10.3，以已验兼容范围复用原机依赖，不修改系统包。Windows较新jsonschema与Ubuntu现有版本分别测试，uv.lock不代表原机已按锁安装。

后续体积讨论见[视频存储说明](../recording-storage-options.md)：当前约99.4%体积来自原始RGB像素，可以评估独立视频分支与逐帧时间索引、保留小型事件MCAP；尚未实现或改变real-episode/1。不能仅替换图像载荷而沿用旧decoder/QC/hash假设，正式实现时需另定格式兼容与故障验收。
