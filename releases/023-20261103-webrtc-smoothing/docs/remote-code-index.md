# ranger-piper前人工程索引与接入结论

审查：2026-10-16，SSH只读。下面全部为**远端绝对路径**；本地参考目录与它们不是同一版本。先从本索引接续，不必重新扫描或直接运行launch。

后续计划005已沿调用关系深入核查，补读实验便笺、历史数据元信息和ROS日志，并离线读取一个bag的数值样本。完整的[功能/使用方式/数据流与闭环研究](research/2026-10-16-existing-robot-workflow.md)是这部分的最新入口。下面“未读取数据”等描述若属首轮范围，以后续结果为补充；不代表已经运行旧控制工程。

## 范围与证据

目录索引覆盖/home/ros、/opt、/srv、/mnt、/media，深度最多7，跳过隐藏目录、环境、缓存、build/install/log及数据目录；遍历17357个文件名，未触及80000上限。后续定点读取74份机器人源码/文档，并核对已安装副本、venv metadata、ROS package.xml、udev与启动配置。不是逐文件阅读整台机器，也不覆盖其他账号/受限目录。数据仅查看目录存在，不下载原始episode、模型或图像。

原始审计在本地ignored artifacts/preflight/：ranger-piper-source-index.json、ranger-piper-source-audit.json、ranger-piper-installed-audit.json、ranger-piper-install-config-audit.json。保存路径、HEAD/dirty及选中文件SHA256；源码副本仅为本地审计证据，不纳入发布。没有运行旧工程测试、设备SDK或服务。

## 优先参考入口

| 远端路径 | 内容和借鉴方式 |
|---|---|
| `/home/ros/ros2_ws/src/mm_bringup/launch/bringup.launch.py` | 实验台组合：左右臂、底盘、升降、模型；left=can0、right=can2，auto_enable默认false，但chassis/lift默认true；不是A4-S专用启动器 |
| `/home/ros/ros2_ws/src/mm_bringup/mm_bringup/vr_teleop_bridge.py` | XLeVR输入→左右pose/夹爪及底盘；默认sides仅right，含固定VR旋转矩阵、绝对XLeVR路径和底盘发送线程。可借输入/离合思路，需拆离设备映射/底盘 |
| `/home/ros/XLeRobot/XLeVR/vr_monitor.py`、`xlevr/inputs/vr_ws_server.py`、`web-ui/index.html` | WebXR服务、controller/buttons/quaternion和显示代码；config.yaml列HTTPS8443/WS8442及SO100串口模板，不代表Piper或PICO已验证。私钥未读取/复制 |
| `/home/ros/ros2_ws/src/mm_bringup/mm_bringup/arm_ik_node.py` | Pinocchio DLS IK、关节步长/限位参数；URDF路径写死、auto_enable默认true、默认right。拆为配置化模型/IK及具名端点输出，不复用隐含启用 |
| `/home/ros/ros2_ws/src/mm_bringup/mm_bringup/whole_body_reach.py` | target_pose到臂IK、位置和升降指令的协调；A4-S只取明确的固定平台变换，不引入升降命令 |
| `/home/ros/ros2_ws/src/mm_bringup/scripts/ros_episode_recorder.py`、`README.md` | ROS MCAP+manifest；默认**左臂/底盘/两相机**，不是双臂三相机。--master-slave会启动右臂输入→左臂输出并使能，--arm-teach会发送示教切换；不能因名为recorder就当纯观测程序 |
| `/home/ros/ros2_ws/src/mm_bringup/scripts/right_to_left_master_bridge.py` | 右臂作主输入、左臂作执行输出；不等于两台Piper均作为独立执行臂 |
| `/home/ros/ros2_ws/src/mm_bringup/scripts/replay_episode.py`、`replay_left_arm.py`、`/home/ros/replay_episode_both.sh` | 物理动作回放相关，不能替代本项目只读MCAP回放 |
| `/home/ros/real_robot_client.py`、`deploy_checklist.md` | OpenPI移动Piper客户端/部署线索：左臂+底盘、top/left_wrist两图，状态/动作10维。默认DRY但仍连接策略服务，--execute才发布动作；旧action保留/异步结果无epoch等需要重新适配 |
| `/home/ros/openpi_client/` | WebSocket、msgpack/numpy、action_chunk_broker与runtime；后续策略adapter参考，先遥操数采，不接管现有服务 |
| `/home/ros/export_episode_demo.py`、`audit_episode_vla.py` | 数据导出/QC原型；未执行，消费格式及对齐规则需对应真实数据契约另验 |
| `/home/ros/ros2_ws/src/mm_description/urdf/mm_robot.urdf.xacro`、`piper_arm.macro.xacro` | 双臂/升降/三相机资产；文件明确写占位尺寸与近似相机初值，不能当已标定外参 |
| `/home/ros/start_cam_stream.sh`、`https_mjpeg_proxy.py` | 视频显示/同源代理线索；启动脚本会pkill旧进程，不用于无副作用输入测试 |
| `/home/ros/datasets/mm_episodes` | 后续已读38份清单/36份非空bag metadata并离线抽查一个bag；85/88缺正常结束结构。未下载原始数据集，不能统称完整可训练 |

## SDK、ROS与环境

| 工程 | HEAD | 当前改动 |
|---|---|---|
| `/home/ros/piper_sdk` | c05c5454b1cf61c05ad26385e0c0a3aa6d3c7bad | master；末端控制demo修改，另有can1变体未跟踪 |
| `/home/ros/ros2_ws/src/piper_ros` | 017ffefa64511bc6325bd77ddc4e16065c152051 | humble分支；节点修改、备份及COLCON_IGNORE未跟踪；实际运行环境是Jazzy，不从分支名判断兼容 |
| `/home/ros/ranger_air/src/ranger_ros2` | fb96124fa68c49bab03d8ddd2294c2afd45af925 | air_delta；launch/chassis_service/socket_can修改 |
| `/home/ros/XLeRobot` | 51ca0ec31bdb48713b94bacdba828bf8d889296b | main；XLeVR输入/页面/monitor修改及备份 |

ROS路径/opt/ros/jazzy：rclpy7.1.11、realsense2_camera4.58.1、rosbag2_storage_mcap0.26.10、web_video_server3.1.0（package.xml只读证据，不等于功能测试）。

系统/usr/bin/python3是3.12.3，piper_sdk0.6.1位于/home/ros/.local/lib/python3.12/site-packages；venv_piper也是3.12.3、独立site-packages、有piper_sdk0.6.1。metadata不是模块导入测试；未激活或升级任一环境。系统用户目录和venv的SDK接口文件hash与审查源码一致。ROS安装的piper_ctrl_single_node.py与src hash一致，入口shebang为/usr/bin/python3。

## 初始化与停止：源码能确认什么

- SDK `piper_sdk/interface/piper_interface.py`和`piper_interface_v2.py`：构造器默认打开CAN对象；ConnectPort(L587)默认piper_init=True，PiperInit(L720)发送电机限制和固件查询。因此auto_enable=false并非无发送副作用。
- DisconnectPort(L691)关闭CAN，但不是物理停机；代码仅设置read stop事件，线程join属性检查/monitor退出处理也有疑点，需用fake CAN验证。不要将SDK断连等同于保持/制动/失能。
- ROS节点`.../piper/piper_ctrl_single_node.py`：L72–73构造SDK并ConnectPort，L352 enable回调会启用机械臂及夹爪，false分支会失能。L426 main的finally只destroy_node/rclpy.shutdown，未见显式SDK DisconnectPort或物理停止。
- 单独的stop demo调用MotionCtrl_1(0x01)，disable demo走DisablePiper；两者语义不同。设备断进程后的真实行为、停止时间和恢复方式尚未物理验证。
- `real_robot_client.py`退出时发布零底盘Twist；这不等于双臂停止协议。后续adapter保留原始策略动作、最终命令和反馈，不直接借上层topic发布替代本项目执行接口。

这是源码审查结果，不需要为此启动控制程序；下一backend应提供独立describe/feedback/command生命周期并用fake CAN覆盖这些路径。

## 现场身份与旧配置差异

用户已确认，且本轮新被动发现绑定成功（只是身份匹配）：

| 角色 | 当前身份 | 证据 |
|---|---|---|
| 左臂传输 | can0 / USB 1-8；适配器serial 003E00314148570A20343133 | 用户接线确认 + sysfs |
| 右臂传输 | can2 / USB 1-10.1；适配器serial 004100284148571320343133 | 用户接线确认 + sysfs；以本地profile与原始报告为准 |
| 左腕 | D435 022523021289 / USB 2-3.2 | 用户确认 + sysfs |
| 右腕 | D435 342123026960 / USB 2-1 | 用户确认 + sysfs |
| 固定 | D455 261143061977 / USB 2-3.1 | 用户确认 + sysfs |

纠正：旧`cameras.launch.py`（src与install均核对）的254922307547/342522071110/022422072252是RealSense SDK命名空间，分别对应固定/右腕/左腕；后续开流日志以USB物理端口关联，证明这些serial有效。前次仅凭USB descriptor枚举判为失配的结论已撤回。右腕默认禁用仍需处理；现场身份由本地profile注入。随后用户激活can0/can2，纯接收取得双方六关节反馈；固件查询和运动/停止未验证，见[实测报告](validation/2026-10-16-a4s-live-observation.md)。

进一步纠正角色说明：旧launch将342522071110命名left_wrist_camera，将022422072252命名right_wrist_camera（默认禁用），与用户当前确认的物理左右相反。因此当前被默认关闭的是**物理左腕**；“旧右腕默认禁用”只能指旧逻辑名，不能解释为当前物理安装。旧serial有效不代表角色正确；历史安装是否相同仍未知，详见新研究的角色对照表。

`/etc/udev/rules.d/lift_rules.rules`仅按1a86:7523的VID/PID生成/dev/lift，而当前有两台同VID/PID USB串口；规则不足以唯一定位升降。这是通用发现需保留by-path/serial/歧义报告的实际例子，不在本轮改udev。

## 启动项与接续

系统/用户running service及enabled unit名称未发现机器人服务，选定的自定义systemd/autostart配置未发现匹配内容；crontab -l返回1，未提供机器人计划项证据。不能由此证明绝无其他启动渠道或后台写入者。

.bashrc有source /opt/ros/jazzy/setup.bash、~/ros2_ws/install/setup.bash、~/ranger_air/install/setup.bash；未在筛选的相关行发现自动launch。未修改shell/服务、udev、CAN或旧工程。

按[设备发现](device-discovery.md)与[M2计划](../plans/002-a4s-teleop-acquisition.md)接续：具名双臂/夹爪与三相机→有界记录/独立输入→配置化模型/IK→设备backend→现场遥操；策略客户端留待后续。后续独立WebXR实测已完成：浏览器UA自报PICO 4 Ultra Enterprise OS5.11.2，两次头/手柄/按键输入有效；不证明旧VR桥或机器人映射可用。见[实测报告](validation/2026-10-16-a4s-live-observation.md)。

## 本项目新增的实验遥操路径（计划007）

独立源码与诊断根：`/home/ros/robot-infra-runs/007-probe-20261016T142159Z`，含checkout、live-01/02/03、motion-evidence-03.json、shutdown-and-qc.json及evidence-007-v2.tar.gz。不是前人代码，所有临时物理进程已停止。驱动仍来自原ros2_ws，不改厂商源码。后续按[部署手册](live-teleop.md)在新输出目录复现；日志完整性与已知IK/收尾边界见[现场报告](validation/2026-10-16-a4s-live-control.md)。
