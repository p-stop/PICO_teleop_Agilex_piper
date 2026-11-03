# 2026-10-22正式采集配置验证

计划018。机器人SSH新IP192.168.87.138，原current=014，双臂CAN为DOWN，8445/8446无服务。用户指定任务fill_pen_holder、根目录~/robot-infra/dataset、起始0；本轮不启动机械臂或创建正式任务episode。

## 软件

Windows284通过/10跳过，Ubuntu297通过（含ROS localhost，无设备）。新增6项用例：夹爪默认打开/按压闭合/松开打开、home/暂停/缺控制器无副作用，进入行为配置校验；自定义头部角色与身份保持、原配置不变、错误角色/重复输出拒绝、无设备CLI，以及3 RGB MP4＋仅头部depth的字节精确保留和deep QC。

初版相机测试的源码树SHA256 `1ac2dcd6f2f49dd858d2ba2c14d11494989ac192fe78d4d8463873fa8f32ac7a`；测试快照018-source.zip SHA256 `33d5c87370c1d2d38b779481fb4c39f71a98dc8f0b5fb4d514abda3748dd9214`。部署最终状态/hash见计划018及release-manifest。

随后补充了“手柄没有扳机按钮时不得猜松开”的准入和测试；最终源码树为`d0fe3be2c2e3d29db89f45adf63dc851bf20caa0405c11383b5c0186c0739590`。相机记录/编码实现与上述实测一致；最终回归/部署收据区分这两份代码身份。

最终代码重新通过Windows284/Ubuntu297回归，已部署到releases/018-20261022-formal-collection并切换current，旧014保留。完整collect --check-only如预期因can0 DOWN返回2，没有构建设备；先由操作者激活CAN再启动。收据offline-tests-018-final.json、offline-deployment-018.json与camera-probe-018.json。最终文档归档与wheel/sdist内容检查收据见018-final-package.json。

## 相机独立真机检查

使用原有RealSense ROS driver，只启动相机，无Piper驱动/robot命令topic。实际三RGB rgb8与scene_fixed/depth 16UC1均为640×480，配置30fps。10秒通过同一EpisodeRecorder后台写盘：三路RGB为MP4，头部depth原始字节在MCAP，腕部无depth。camera_info包含各流内参/光学frame。

capture QC和deep完整性均通过，三个相机进程退出码[0,0,0]，脚本无错误。诊断位于~/robot-infra/runs/018-camera-only，只保留为待审阅诊断，不是fill_pen_holder示范；没有消耗其episode编号。脚本副本artifacts/preflight/018-camera-probe.py，远端018-camera-probe.py；收据camera-probe-018.json，完整结果runs/018-camera-only/result.json。

实际每路RGB300帧、头部depth295帧；各流在其首末帧区间约29.98–29.99fps，最大间隔33.8–36.0ms，源时间无回退、profile无不匹配。不同流在录制边界的帧数不必相等，QC通过不等同相机曝光同步。三路MP4完整解码各300帧，头部保留scene_fixed_depth_optical_frame和实际深度内参。

未安装pyrealsense2，未改变系统包；通过已有ROS驱动实际验证流。深度仅保留16UC1数值，不将未知depth scale标成已校准米，不默认声称与RGB逐像素对齐。独立相机测试不覆盖PICO/双臂/完整并发遥操；新夹爪进入行为只有fake测试，首条正式短episode需由操作者确认。

## 运行配置

~/robot-infra/profiles/formal-018/deployment.json选择生成的session.json和cameras.json。两臂trigger_pressed=close、teleop_start=follow_trigger，保持独立夹爪；三RGB640×480×30，scene_fixed depth640×480×30，腕部depth=null。原相机序列号/CAN/驱动/IK/20%原生速度、预览480×360×8保留。原~/robot-infra/deployment.json及其profiles不改动，避免旧实验自动换行为。

启动前先按手册激活can0/can2，再运行显式formal deployment的collect命令。CAN DOWN时完整collect --check-only应报错，不能把配置/编码检查通过当成已满足硬件启动条件。退出不额外夹爪闭合或home。
