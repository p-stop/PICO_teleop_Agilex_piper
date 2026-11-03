# 参考仓库索引与借鉴边界

审计：2026-10-16。只读盘点14份本地仓库，重点抽查Piper、QuestArm、GELLO/FR3、RealSense；其余为入口级检查。未运行第三方安装、launch、测试或硬件命令。下列HEAD只标识下载版本，不证明工作区无修改，更不等于实验室已安装版本。

## 新增优先参考：实验室现有移动Piper工作流

在14份本地仓库之外，ranger-piper上的`~/ros2_ws/src/mm_bringup`、已安装Piper驱动/SDK、XLeVR改版和`~/real_robot_client.py`应作为独立的实验室参考来源。它们已有主从采集产物、旧右侧VR/IK日志及策略EXEC历史记录，比通用示例更贴近现场；不是本项目已复现的完整闭环，也不是一个版本统一的新Git仓库。

详见[完整研究报告：功能、用法、数据流与证据](research/2026-10-16-existing-robot-workflow.md)。优先借鉴ROS后端边界、相对映射、现有IK/模型、MCAP/QC和OpenPI观测/动作契约。原方案主要是左执行臂+底盘+两图的10维策略；A4-S双执行臂/三图另适配。38份历史清单中两份MCAP未正常结束，旧相机左右逻辑名与当前物理安装相反，训练/服务端谱系仍待核查。原工程继续保留，不整包复制或自动运行。

## 本地版本与优先用途

| 本地目录 | HEAD前12位 | 下一阶段用途 |
|---|---|---|
| questarm-real-robot-deployment | 8c47a5fc82db | 优先：双臂WebXR、IK、episode、CamBot/RealSense、部署边界；不是可直接照搬的安全启动器 |
| pyAgxArm | d90e234ba8e4 | 优先：CAN状态/动作编码、固件分支、夹爪、虚拟CAN；优先核对现有设备实际使用版本 |
| agx_arm_ros | ceda56575818 | 优先：ROS2节点/namespace/控制门与驱动生命周期，README列Humble/Jazzy |
| librealsense | c84fe6438bd1 | 优先：序列号绑定、三相机、内外参、时间戳/时间域、逐帧metadata |
| gello_software | 204f53a64bef | A1：ros2/FR3-Humble、输入校准和关节映射；不直接采用其自动位置同步 |
| franka_ros2 | 4acc05c01ebf | A1：设备本机控制器、反馈、生命周期、fake hardware；必须与机器人系统匹配 |
| libfranka | e88d08f64cbf | A1：FCI/实时接口、错误/停止、版本兼容；不从Windows执行控制 |
| franka-data-collect | 3f7f13b1afb1 | A1：现有采集组织、双相机/GELLO经验；抽查发现部分相机metadata仅写host time、点云TODO，不能直接当完整数据契约 |
| piper_ros | ac41fcbcdda5 | 旧环境参考：本地README为Ubuntu20.04/ROS1 Noetic，不作为A4-S Ubuntu24.04新底座 |
| tidybot2 | c8dd23819f9c | 后续手机与远程策略：clutch、RPC进程隔离；全向底盘逻辑不迁移为自制底盘默认值 |
| OrbbecSDK | 7fa1485e751a | 将来相机插件比较；当前明确RealSense的A4-S/A1/A2不依赖它 |
| OrbbecSDK_v2 | 85e94c4ee403 | 同上，型号与SDK代际另核验 |
| unitree_sdk2 | d1abf001220d | A6后续，先确定G1-D实际产品及接口；不从G1支持表推断 |
| unitree_sdk2_python | 814556d15970 | 同上，不在当前Piper/FR3路径导入 |

本轮不自动下载、更新或作为依赖安装这些仓库；也不将14个嵌套Git仓库整体提交到主项目。建立主项目Git基线时明确排除参考目录或另作版本化引用。后续实现前重新核对HEAD与dirty状态。

## 最值得读的现有代码

### QuestArm快照：最接近A2，也包含A4-S可用的片段

从[README](../relevant-repo/questarm-real-robot-deployment/README.md)、[来源记录](../relevant-repo/questarm-real-robot-deployment/metadata/SOURCE_SNAPSHOT.md)、[离线验证记录](../relevant-repo/questarm-real-robot-deployment/metadata/VALIDATION.md)进入。快照包含dirty工作树和补丁，嵌入SDK/CamBot版本与顶层同名仓库不同，不能任意混搭；其原环境含Foxy和独立Python3.12。上游记录的离线测试不是本项目独立运行的结果。

- [双Piper WebXR launch](../relevant-repo/questarm-real-robot-deployment/ros2_ws/src/oculus_reader/launch/teleop_double_piper_webxr.launch.py)：双CAN/namespace与左右手连接；含`auto_enable=true`，不能用作只读盘点命令。
- [WebXR桥](../relevant-repo/questarm-real-robot-deployment/ros2_ws/src/oculus_reader/scripts/webxr_piper_bridge.py)：controller_pose、按钮映射、过期状态、tracking/world frame与head pose分离。借鉴消息边界，不照搬VR→机器人旋转矩阵/比例。
- [IK](../relevant-repo/questarm-real-robot-deployment/ros2_ws/src/oculus_reader/scripts/arm_ik_pose_node.py)及[参数](../relevant-repo/questarm-real-robot-deployment/ros2_ws/src/oculus_reader/config/arm_ik_pose_node.piper.yaml)：Pinocchio/CasADi、TCP、关节顺序。当前配置关闭碰撞检查，0.13m工具偏置是原设备参数。
- [episode recorder](../relevant-repo/questarm-real-robot-deployment/ros2_ws/src/oculus_reader/scripts/piper_episode_recorder.py)、[LeRobot导出](../relevant-repo/questarm-real-robot-deployment/ros2_ws/src/oculus_reader/scripts/export_lerobot_v3.py)：状态、episode及导出分层；需对接本项目实际命令/receipt/时间域而不是仅记录目标。
- [CamBot app](../relevant-repo/questarm-real-robot-deployment/python/cambot/cambot/teleop/app.py)、[浏览器客户端](../relevant-repo/questarm-real-robot-deployment/python/cambot/cambot/teleop/client/index.html)、[capture](../relevant-repo/questarm-real-robot-deployment/python/cambot/cambot/teleop/capture.py)：已有WebXR/RealSense和无机器人选项，先审计依赖与初始化路径再做独立输入录制。A4-S只取输入/显示，不引入不需要的视觉臂。
- questarm_deploy：后续策略适配、SHADOW/ARMED、profile和诊断。用户当前先采集，推理组件不阻塞首轮。

快照内标定/绝对路径只用于追溯，不能作为本台架外参或回零位。[第三方声明](../relevant-repo/questarm-real-robot-deployment/THIRD_PARTY_NOTICES.md)还说明整体许可未统一；本轮不复制发布其中代码，实现复用时按具体组件保留来源与许可。

### Piper驱动与模型

[ROS节点](../relevant-repo/agx_arm_ros/src/agx_arm_ctrl/agx_arm_ctrl/agx_arm_ctrl_single_node.py)默认`auto_enable=True`、`control_enabled=True`；初始化会connect、可能enable、设置TCP，并初始化夹爪。`control=false`等参数不能直接推断为“总线零写入”，须核对各层路径。

[SDK connect](../relevant-repo/pyAgxArm/pyAgxArm/protocols/can_protocol/drivers/core/arm_driver_abstract.py)启动通信与后台线程；[Piper动作编码](../relevant-repo/pyAgxArm/pyAgxArm/protocols/can_protocol/drivers/piper/default/driver.py)包含rad到协议mdeg转换和clamp。适配器需明确最终下发值、模式/固件和SDK潜在改写，不能将proposal伪装成未经修改的实际命令。

本地[agx_arm_ros .gitmodules](../relevant-repo/agx_arm_ros/.gitmodules)引用`agx_arm_urdf`，但对应目录本轮为空：这是IK/可视化/碰撞模型的实际缺口。优先固定模型commit与固件/TCP，再验证FK对齐；不要以下载了驱动就认为模型齐全。

### FR3与相机

[GELLO ROS2说明](../relevant-repo/gello_software/ros2/README.md)直接面向FR3/Humble，但提示启动时机器人会同步到GELLO位置，因此先记录输入/校准，后做受控交接。Franka驱动、libfranka和Robot System必须匹配，不使用下载main替换现有能工作的实验环境。

[RealSense多设备管理示例](../relevant-repo/librealsense/wrappers/python/examples/box_dimensioner_multicam/realsense_device_manager.py)可参考serial绑定和设备内参。多相机示例不保证跨设备同步，三相机带宽、时钟偏差、丢帧和深度干扰仍需实测。

## 还值得补充哪些仓库

不是全部安装；按当前阻塞项阅读或下载固定版本即可。

| 优先级 | 仓库 | 借鉴内容与范围 |
|---|---|---|
| 现在 | [agilexrobotics/agx_arm_urdf](https://github.com/agilexrobotics/agx_arm_urdf) | 补齐本地空submodule，核对6关节/夹爪/mesh/collision/工具frame；固定双臂安装外参由现场提供 |
| 现在，输入路线二选一 | [unitreerobotics/televuer](https://github.com/unitreerobotics/televuer) | PICO/Quest的WebXR姿态、controller与视频边界；只借输入层，不接Unitree机器人控制。README列具体PICO/Quest设备，不保证用户未知PICO型号 |
| 现在，PICO原生备选 | [XR-Robotics](https://github.com/XR-Robotics)的Unity Client、PC-Service、PC-Service-Pybind | PICO原生客户端/PC收流接口；按准确型号/OS选版本。服务文档列24.04，Python sample安装说明仅测试22.04，组件证据不可互相替代 |
| 数据导出阶段 | [huggingface/lerobot](https://github.com/huggingface/lerobot) | Dataset格式、processor、导出消费方校验、ACT与部署接口；先选明确版本，不跟main自动变更格式 |
| IK/最小sim阶段，按路线选择 | [stack-of-tasks/pinocchio](https://github.com/stack-of-tasks/pinocchio) / [kevinzakka/mink](https://github.com/kevinzakka/mink) | 前者贴近本地QuestArm现有IK；后者是MuJoCo differential IK候选。先验证一套，不同时重写两条完整运动链 |
| 若复用ROS摄像头路径 | [realsenseai/realsense-ros](https://github.com/realsenseai/realsense-ros) | serial/namespace、多相机、流/时间/标定参数；直接pyrealsense2也可，不要求核心依赖ROS |
| 策略阶段再补 | [Physical-Intelligence/openpi](https://github.com/Physical-Intelligence/openpi) | 独立策略服务、数据变换与norm、artifact；不能仅换权重就假定双Piper任务兼容 |
| 后续sim资产 | [google-deepmind/mujoco_menagerie](https://github.com/google-deepmind/mujoco_menagerie) | 高质量MuJoCo资产和FR3/Panda参考；不预先承诺包含可直接使用的精确Piper/FR3配置 |

原版CamBot已在QuestArm快照中有本地修改版；除非要对比差异，不必优先再下载一份。DORA、完整MoveIt、cuRobo、RL框架及更多VLA不作为A4-S遥操采集首轮前置依赖。

外部能力依据为本轮实际阅读的维护者README：[televuer](https://raw.githubusercontent.com/unitreerobotics/televuer/main/README.md)、[XR-Robotics组件说明](https://github.com/XR-Robotics)、[Python sample](https://github.com/XR-Robotics/XRoboToolkit-Teleop-Sample-Python)、[RealSense ROS](https://github.com/realsenseai/realsense-ros)、[Mink](https://github.com/kevinzakka/mink)。这不是本项目兼容测试；Tavily搜索曾遇到终端GBK编码问题，改UTF-8/文件输出后成功，随后用原始页面核对。
