# 双臂真机遥操：部署、运行与停止

**当前新入口为[自由遥操 session / live-teleop/2](teleop-session.md)**：A回位/A开始/A结束、侧握跟随、扳机夹爪、退出VR暂停。以下记录v1位置遥操的历史流程与证书/日志方法；不要把v1的入VR自动申请控制、禁用夹爪或测试限幅套用于v2。

本入口是实验性有界双臂位置遥操，独立于M1/fake collection。先读[现场结果](validation/2026-10-16-a4s-live-control.md)和[数据流](a4s-dataflow.md)。当前没有常驻服务；本轮临时进程已停止。运行命令不替代现场用户授权。

## 现场配置

复制 `configs/live-a4s.example.json` 至忽略提交的 `profiles/local/<host>.live.json`，填入实际URDF路径/hash、CAN角色和话题。模型必须与机器人版本匹配，base/tip/joint_names必须明确。当前测试使用gripper_base，不是实测指尖TCP。相机从 `configs/realsense-rgb.example.json` 复制并填写SDK serial，不能填USB descriptor serial；现场已有的绑定留在本地profile。

模型校验可以离线执行，既不导入ROS也不连接CAN：

```bash
PYTHONPATH=src python3 - <<'PY'
import json
from robot_infra.live_teleop import validate_profile
from robot_infra.kinematics import SerialModel
c = validate_profile(json.load(open('profiles/local/robot.live.json')))
m = SerialModel(**c['model'])
print(m.sha256, m.names, m.limits)
PY
```

样例中的模型路径/hash和CAN别名是占位符，必须替换。该validator不是任意graph编译器；启动器目前固定支持两台现有Piper驱动的已审计消息方言。

本轮使用的运动配置为：scale=1、侧握button1、保持朝向、夹爪禁写；每次接合目标范围0.10m、相对启动关节偏移0.6rad、速度0.4rad/s、目标与反馈最大偏差0.08rad、驱动速度20%、输入超时0.6s、反馈超时0.25s、测量噪声容差0.005rad。容差用于近限位测量/IK种子，不扩展命令限位。上下/左右由用户初步现场确认，前后与安装变换仍需专项核验。

## 环境和证书

在设备Ubuntu主机运行，保留原ROS/SDK环境。需要Python>=3.11、系统可用的ROS消息和Pillow；核心安装的video extra声明Pillow版本范围。本轮使用现成系统Python3.12/ROS Jazzy/Pillow，无系统pip安装。Windows只运行fake/静态测试。不要把Windows二进制依赖复制到Ubuntu。

```bash
source /opt/ros/jazzy/setup.bash
source /home/ros/ros2_ws/install/setup.bash
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
```

上述ROS路径来自本次主机，换机时按实际安装路径替换。CAN需已由现场配置为正确接口/比特率，停止其他会写这两条总线的旧应用。本工具不运行sudo、不自动激活CAN、不清理他人进程。

使用实验室受信证书，或在设备端生成只用于测试的证书。下面的 `<device-ip>` 替换为当时设备地址；IP变化需更新证书SAN。私钥只留设备本地，不提交或复制回源码目录。

```bash
mkdir -p profiles/local/tls
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout profiles/local/tls/key.pem -out profiles/local/tls/cert.pem \
  -days 3 -subj '/CN=<device-ip>' -addext 'subjectAltName=IP:<device-ip>'
chmod 600 profiles/local/tls/key.pem
```

头显浏览器遇到测试证书提示需操作者手动处理。网页必须走HTTPS，不能把HTTP局域网地址当作可用WebXR安全上下文。

## 启动整套临时进程

确保没有本项目旧栈或其他应用在占用这两台机械臂/三相机。新output目录必须不存在。以下实际驱动路径仅适用于已审计主机，换机须替换并重新审计驱动方言/使能行为。

```bash
python3 tools/launch_live_stack.py \
  --config profiles/local/robot.live.json \
  --camera-config profiles/local/robot.realsense.json \
  --arm-driver /home/ros/ros2_ws/install/piper/lib/piper/piper_single_ctrl \
  --camera-driver /opt/ros/jazzy/lib/realsense2_camera/realsense2_camera_node \
  --ros-domain-id 64 --host 0.0.0.0 --port 8445 \
  --cert profiles/local/tls/cert.pem --key profiles/local/tls/key.pem \
  --duration 1800 --output artifacts/live-session-001
```

启动器只创建自己的子进程：两个隔离话题的Piper驱动、三相机驱动和HTTPS网关。驱动auto_enable=false/gripper_exist=false，启动网页不会使能。进程信息写入output/processes.json。SDK初始化可能发送设备查询，因此启动驱动本身也属于实际设备操作。

如果驱动已由本项目以同样配置独立启动，只运行网关：

```bash
ROS_DOMAIN_ID=64 python3 -m robot_infra.live_teleop \
  --config profiles/local/robot.live.json --output artifacts/live-diagnostic-001 \
  --host 0.0.0.0 --port 8445 --duration 1800 \
  --cert profiles/local/tls/cert.pem --key profiles/local/tls/key.pem
```

此命令不启动相机或机械臂驱动。不要同时运行两个完整启动器。完整启动器代码已加入并做静态检查，本轮实际部署使用等价的分阶段脚本；它本身尚未重新执行全栈物理验收。

## 头显操作

1. 打开 `https://<device-ip>:8445/?v=<current-build>`，先不勾选控制，进入VR确认三路画面和左右角色。更新时重新输入带新版本参数的URL，PICO可能保留旧页面。
2. 退出VR，勾选允许控制并重新进入。服务等待可见、有跟踪的稳定帧后使能双臂，初始位置来自实时反馈，不使用固定home。
3. 按住同侧手柄侧握键移动；松键清除该侧参考并保持当前位置。重新握键从新位置建立锚点。扳机/摇杆不会操作夹爪、底盘或升降。
4. 首先逐轴确认方向；模型限位/IK失败或调试范围拒绝时，不会追随不可用目标。HUD/网页status里的reason可区分test_envelope、tracking_error、超时等；IK完整原因在motion_result事件中。
5. 点击网页停止或退出VR后，检查enabled=false、owner=null。visible-blurred/hidden表示不可见/失焦，会撤销控制；正常可见性变化不再显示为clientError。

组控制权撤销后需重新进入VR申请，不会在跟踪恢复后自动重启运动。

## 停止和证据

先在网页停止并确认机械臂静止，再在启动器终端Ctrl+C。启动器先关闭网关，再关闭自己的相机/驱动；不使用pkill。定时结束同样收尾。软件停止尝试保持当前位置，不自动失能、回零或关闭夹爪；机械臂电源/急停按实验室现场流程处理。

检查episode/events.jsonl最后的finalize、journal-summary.json的error/writer_stopped/计数，再对图像索引与hash做QC。缺少结束记录就标诊断不完整；不能只补一个complete标签。当前格式是JSONL+有损JPEG预览，不是完整MCAP原始采集；正式训练数据采集仍需后续接入原始帧与统一episode协议。
