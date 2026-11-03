# 真机观测与WebXR独立输入

更新：2026-10-16。实施计划004。此入口采集输入，不创建机器人命令端口；M1 fake CLI和当前真实输入记录是独立格式。

## WebXR

```bash
python3 -m robot_infra.webxr_input --host 0.0.0.0 --port 8445 \
  --cert /absolute/path/cert.pem --key /absolute/path/key.pem \
  --output /new/run/xr-input.jsonl --duration 1800
```

服务只需stdlib；源码部署设置PYTHONPATH=/absolute/checkout/src。TLS材料留在设备本机、不入Git。默认监听127.0.0.1，LAN访问需显式host；端口、运行路径、证书均由部署指定。地址变化需要更新访问URL/证书，与机器人SDK配置无关。进程持续指定duration后自动退出；停止只影响独立输入服务。

PICO浏览器打开该HTTPS地址，确认浏览器允许此站点/证书，页面会报告secure_context、webxr_present、immersive_vr。若无法提供安全上下文或immersive-vr为false，保留诊断而不是宣称已支持PICO；不要求放宽浏览器全局安全设置。WebXR必须由用户点击进入VR；参考空间local-floor/local由页面明确选择，不静默转换。

进入后依次测试头部、左右手柄、扳机/握把/摇杆、遮挡/追踪丢失、退出重进及参考空间reset。头显内青色/橙色点分别显示左右输入位置；原始buttons按浏览器索引保留，不默认映射deadman或夹爪。设置内的实际型号/系统/浏览器仍需记录。

GET /api/status用于开发端检查最近输入、事件数、来源session、序号缺口、年龄/fresh；fresh只表示最近frame到达，不证明head/grip均有效。记录raw_input及服务器UTC/monotonic收取时间；client时间、XRFrame时间和host时间关系为unmeasured，不当作跨设备同步。getPose失败保留null，reset增加epoch，退出保留session_end。WebXR输入参考API：[requestSession](https://developer.mozilla.org/en-US/docs/Web/API/XRSystem/requestSession)、[getPose](https://developer.mozilla.org/en-US/docs/Web/API/XRFrame/getPose)。

webxr-input/1原始JSONL是本轮独立诊断数据，后续由观测adapter接入统一记录/MCAP；不伪装为M1契约事件或完整机器人episode。输出须新文件；session数、请求大小和录制容量有界，错误明确返回，客户端保留发送失败与跳帧计数。

## 相机短样本

复制[模板](../configs/realsense-rgb.example.json)到profiles/local/并替换SDK serial；未替换模板会明确校验失败。roles可改名/增减，参数由profile指定，不将本实验台serial写入驱动。USB descriptor serial与RealSense SDK serial可能不同，必须用驱动描述和物理端口关联；见[实测身份表](validation/2026-10-16-a4s-live-observation.md)。

在设备主机加载ROS环境后运行（源码方式需先设置PYTHONPATH）：

```bash
source /opt/ros/jazzy/setup.bash
python3 -m robot_infra.adapters.realsense_ros \
  --config profiles/local/bench.realsense.json \
  --driver /opt/ros/jazzy/lib/realsense2_camera/realsense2_camera_node \
  --output /new/run/rgb-sample --duration 15 --max-frames 3
```

ROS路径/driver是该已测主机示例，其他distro显式替换并验证，不作为核心常量。需要rclpy、sensor_msgs、realsense2_camera_msgs及原生驱动；未加载ROS时缺依赖会明确失败。按现场DDS域配置ROS_DOMAIN_ID，避免与现有驱动重名或争抢同一相机；此工具不关闭他人进程。驱动只开RGB，不开depth/IMU；输出须新目录。每路保存有界raw+PNG、hash、CameraInfo、原始metadata和收取时间，统计所有到达帧；不等于全程视频或episode。退出只停止本次创建的相机子进程。

## 双臂纯接收短样本

接口名来自已确认profile；当前can0左/can2右仅是该实验台示例。先确认供电及接口状态，DOWN时报告失败，不自动UP或发SDK查询。用户已在本机终端激活后可运行：

```bash
python3 -m robot_infra.adapters.socketcan_rx \
  --channel left.arm=can0 --channel right.arm=can2 \
  --decoder piper-v2-joints --output /new/run/can-sample --duration 3
```

接收器只使用SocketCAN接收，不初始化SDK，不使能电机；默认decoder=none，其他机器人可只保留原始帧或注入专用解码器。Piper解码显式采用已审SDK0.6.1反馈协议，将millidegrees转radians并保留原始值/分组收取时间；不是设备级同步状态。每通道保存最多600原始帧，统计后续到达但不持续保存，3秒退出。输出缺帧/接口错误为非零退出；固件、夹爪单位与控制模式不从这些帧猜测。

## 当前验证与接续

本轮[报告](validation/2026-10-16-a4s-live-observation.md)记录两次PICO输入、三路RGB和双臂反馈，及仍存在的输入seq缺口、画面曝光/白平衡问题。输入webxr-input/1、相机与CAN诊断格式分开，不冒充统一MCAP episode。接着完成多端点/组授权、持续记录及时间质量，再做显式模型/映射/IK与受控遥操；底盘/升降保持本切片范围之外。
