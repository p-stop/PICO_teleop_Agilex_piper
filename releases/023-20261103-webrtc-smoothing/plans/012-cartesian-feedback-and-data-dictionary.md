# 012：可配置末端位姿观测与采集数据字典

2026-10-18，complete（软件、数据字典及部署静态检查；新增流现场采集未验）。

目标：只读核查当前安装的 Piper SDK/ROS 驱动；若有末端反馈，作为独立观测流加入 raw/MP4 episode；提供 supervisor 可阅读、可据此写 reader 的详细字段字典。用户补充：原生Euler可直接接收，转换必须明确标记为转换。保持驱动、控制、输入和存储解耦，不自动推断坐标变换、工具点或时钟同步。

审查结论：安装的 SDK0.6.1 `GetArmEndPoseMsgs` 返回 XYZ（0.001mm）和 RX/RY/RZ（0.001degree），不是原生四元数。已审计 ROS 驱动 `PublishArmEndPose` 发布 Pose/PoseStamped，米与 SciPy `from_euler('xyz').as_quat()` xyzw。frame_id 空；SDK stamp 来自接收消息而非已证实硬件时钟；三组 CAN 分量非原子。现有 wrapper 已调用该发布函数，不需要新增 SDK 连接或命令。

范围：可选 `pose_feedback` 配置，任意具名 PoseStamped/native_pose_json 来源；独立只读 ROS 适配器及 ROS 无关 payload；Piper wrapper仅增加已连接SDK缓存的原生整数/单位/秒stamp发布，不查询或另连硬件；公共 MCAP/index/QC/对齐支持新流；配置不含该字段时保持旧行为。新 payload `pose-feedback/1` / `native-pose/1` 为加法扩展，不改变 episode v1/v2 或既有 feedback。原生XYZ/Euler不转换，驱动已转Quaternion单独流且标记conversion，不自动归一化/补帧；有限但非单位四元数保留并标记 QC，不进入控制。

验收：配置无效提前失败；通用来源名、原始 frame/stamp/xyzw 保留；ROS 假节点只订阅不创建 publisher；缺失/无效位姿 QC 失败；raw/MP4 编码、对齐和 deep QC；旧测试回归。只运行无设备测试/检查，不启相机、驱动或运动。报告覆盖已采数据与可选数据、完整字段、类型/形状、单位、命名/版本、时间域、reader、训练映射与未采内容。

checkpoint：已读取架构/状态/当前实现和测试。安装 ROS 驱动 SHA256 `a897239cf674d62428bee96ca4c9cca8eca0bc7fb2111edd8d99c5848e57c7a2`；SDK interface_v2 SHA256 `2d4fdcd65cedfcfcc0c7347feba1f693c28ab4a7b27c66f9dfca931fc407d7dc`。待实现、测试、详细报告及机器人软件更新静态检查；实时新增流留待下次现场验证。

实现及报告完成：原生SDK缓存bridge、通用只读订阅、显式conversion及unknown frame、MCAP/index/expected/QC、raw/MP4整目录事务。完整字段字典为`docs/collection-data-format-report.md`。Windows250通过/10跳过、Ubuntu263通过，含实际ROS消息本机回环，无设备。初始远端测试缺artifacts父目录，ROS测试对独立Context误用默认executor；均修正测试harness后全套通过。核心源码树SHA256 `391d5adb0e802e1ac4dcc7a4de517537fdddac8a4c40aacbb7d862270ee12b35`。初始归档`012-source.zip` SHA256 `88fa8c6a0986a950c89d360699357dc0116528e7655d8200fc8efa1aea2df91d`，仅ROS测试文件随后补丁，不涉及该核心源码hash。待最终快照部署/静态检查；不做物理实验。

部署完成：`~/robot-infra/current`→`releases/012-20261018-pose-validated`，最终归档SHA256 `af5d8c1ecc9450ec0636047388bbde285333b31e652bd032458b5d8361dc6847`。机器人session profile增加每臂native_pose_topic及四个独立来源（原生/converted），旧配置备份`profiles/robot.session.pre-012.json`。默认raw、相机/控制/driver hash及入口不改。raw_mcap/mp4正式入口`--check-only`都返回passed_without_device_construction，包含4来源；8445/8446关闭，不启动实验。收据为`offline-deployment-012.json`及release-manifest；本地证据归档`artifacts/validation/012-pose`。

下一步：现场采一个新episode检查四路存在、源stamp持续更新、左右身份/位姿趋势、QC以及RGB/VR负载。原SDK欧拉角轴/工具点/时间域仍未标定；SDK多CAN缓存和原生/转换两路并非原子。用户若仅需原生，可从pose_feedback配置删除两个*_quaternion来源。旧episode保持不变；勿用此软件结果替代实时硬件验收。

交付检查：wheel/sdist已生成并验证新增模块、测试/数据报告收录及私有/数据目录排除；报告本地链接和全部Python示例语法通过。package/doc receipts在`artifacts/validation/012-pose/package-and-docs.json`。未推送Git、未改厂商源码、未启动物理服务。
