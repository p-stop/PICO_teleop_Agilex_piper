# ranger-piper：SSH与只读主机盘点

日期：2026-10-16。级别：SSH / read-only host inventory；不是相机开流、机器人反馈或物理控制验证。目标为用户配置的SSH别名ranger-piper，账号ros；IP在用户SSH配置维护，不写入设备契约。

## 执行与证据

用户配置连接后，首次沙箱调用无法访问Windows用户的SSH配置；通过权限审核后使用系统OpenSSH连接成功。BatchMode=yes、StrictHostKeyChecking=yes、ConnectTimeout=10、ClearAllForwardings=yes。未改变用户配置，7897/1455两个转发均未用于本次盘点，未验证它们的可用性。

先执行`uname -sr`；随后将本地tools/collect_host_inventory.py经SSH stdin送给远端`python3 - --bench A4-S`，不在远端落盘。脚本只读取系统/包metadata、USB sysfs，并执行ip link show、lsusb -t、lspci -nn；三个探测均exit 0。无SDK导入/初始化、无CAN配置/写入、无相机流、无ROS节点/控制程序启动、无安装与sudo。

原始证据：[inventory JSON](../../artifacts/preflight/ranger-piper-2026-10-16.json)，远端采集UTC时间2026-10-16T08:44:19.966636+00:00；本地文件SHA256：`a531c08f3374bb54dd680573ca367c87907136a1b481eefec98d92a1576c0e8b`。文件含UTF-8 BOM，本地解析使用utf-8-sig。

## 观察结果

- Ubuntu24.04.4 LTS / x86_64，kernel 7.0.0-38-generic。
- 本次解释器/usr/bin/python3，Python3.12.3；未激活venv_piper。
- 此解释器可见piper_sdk包metadata版本0.6.1、jsonschema4.10.3；robot-infra/mcap/pyAgxArm/pyrealsense2元信息未发现。不能据此断言其他环境也未安装。
- can0→USB 1-8:1.0；can1→1-7.2:1.0；can2→1-10.1:1.0。三路当前均DOWN/STOPPED，收发计数为0；未更改状态。与手册正文USB路径吻合，但实际左右臂/底盘接线未验证，未设置比特率。

| sysfs USB路径 | 枚举产品名 | serial | 物理角色 |
|---|---|---|---|
| 2-1 | RealSense Depth Camera 435 | 342123026960 | 待现场确认 |
| 2-3.1 | RealSense Depth Camera 455 | 261143061977 | 待现场确认 |
| 2-3.2 | RealSense Depth Camera 435 | 022523021289 | 待现场确认 |

三个相机设备的sysfs speed均为5000。两个在同一USB3 hub下，USB树显示共同xHCI根；不据此推断三流稳定吞吐、同步或已完成相机支持。没有打开视频设备。

## 接续与边界

这次证明已配置认证可以无需交互地执行SSH，并证明盘点工具在该Ubuntu24.04/Python3.12环境能运行；不证明M1核心Linux测试、remote Codex安装/登录、桌面远程项目/handoff、模型/SDK或设备支持。

下一步只读核对/opt/ros、实际piper_sdk源码/dirty状态及venv_piper版本、初始化/停止路径和已有服务；再由现场人员确认左右CAN、相机安装角色、底盘/升降固定状态及PICO准确型号。任何CAN激活、SDK连接、launch和控制另按M2现场准入处理。

本轮未改变代码，未重跑Windows测试；未运行Linux M1测试、相机开流或真实命令。
