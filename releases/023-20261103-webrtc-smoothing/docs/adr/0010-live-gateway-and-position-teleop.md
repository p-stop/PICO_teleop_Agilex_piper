# ADR-0010：有界真机网关、位置遥操与独立预览

日期：2026-10-16。状态：accepted（实验切片；不是完整M2）。

用户明确请求真实双臂运动、框架IK和三相机头显显示，并在现场操作/观察。沿用已安装Piper ROS驱动，核心不导入SDK。collection-plan/1仍严格fake-only，不通过修改mode让fake执行器写真实设备。

新增独立 `live-teleop/1` profile、`live-teleop-event/1` JSONL诊断格式和 `live-teleop-status/1`。复用具名CommandSet/EndpointTarget，但设备本地使用真实monotonic、锁保护的单组owner/epoch、后台watchdog、完整双臂预检和逐侧发送前复查。发送只承诺 published_not_acknowledged，实际运动通过反馈与现场观察另验。物理组暂只含两臂；夹爪禁写，四端点完整采集后续实现。

映射使用显式alignment/scale/clutch；接合时实测FK建锚点，首轮保持末端朝向，仅跟随位置。模型由路径、hash、base、tip、joint_names确定，不分发现场第三方URDF。内置标准库串联链FK和局部DLS IK，拒绝未收敛目标；不提供全局规划/避碰。IK与最终网关分离，未来策略解码后的具名目标可复用网关，真实策略调度尚未实现。

反馈零位噪声按显式measurement_tolerance_rad处理：仅允许小误差下的种子投影，投影幅度写入IK结果，原始反馈保留；命令仍受原模型限位约束。初始严重越限拒绝使能，不能通过放大模型范围掩盖。历史首轮初始保持后joint2/joint3趋零，说明下游可能裁剪越限值；新路径不再将“发送测量保持”等同“设备必然无跳变”。

旧驱动JointState第七velocity是整臂速度百分比，适配器显式编码。必须auto_enable=false、gripper_exist=false；旧enable_srv含夹爪动作，本轮不调用。独立ROS域、重映射和唯一publisher/subscriber检查用于协调现有进程，不构成DDS鉴权或硬件总线独占保证。

三路RGB使用独立最新帧缓存/Pillow JPEG线程，桌面与immersive均为中央固定相机大图、两侧腕部小图。WebXR使用单在途请求和最新帧替换，不积压旧目标。原始时钟保留但尚无跨时钟同步保证。JPEG为有损诊断预览，不声称原始RGB采集episode。

停止/超时撤权，若反馈新鲜且在测量容差内则发布模型限位内的保持目标；不自动失能、回零或关闭夹爪。ROS信号处理由应用持有，先保持/撤权、停止线程、结束ROS，再独立关闭日志。日志故障不能阻止尝试保持。该进程本身崩溃、CAN断线或驱动失效时的独立硬件停止尚未验证。

本轮拒绝了完全无限幅/100%速度的实际启动，自动审批判其超出窄范围实体运动约束；采用10厘米/0.6rad偏移/0.4rad/s/20%速度的现场配置完成双臂验证。配置能力与实际获准、实际验证的范围分开记录。证据见[现场报告](../validation/2026-10-16-a4s-live-control.md)。
