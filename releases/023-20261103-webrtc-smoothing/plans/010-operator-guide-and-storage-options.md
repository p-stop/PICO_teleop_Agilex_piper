# 010：操作员采集手册与存储方案说明

2026-10-18，complete。用户要求解释MCAP/MP4体积与LeRobot v3衔接，并补齐deployment参数、提供简洁操作手册。

范围：保留旧技术说明到独立文档，重写操作员入口；核对实际CLI及设备启动脚本，修复显式--deployment被默认配置覆盖的问题。解释压缩与后续视频分支设计，但不在本轮实现/宣称已支持MP4或LeRobot导出，不改既有数据和机器人控制。

验收：操作手册命令与CLI一致；设备脚本支持默认、环境变量、显式两种参数写法且显式优先，ROS和Python路径与同一deployment一致；Linux无硬件脚本测试、CLI/配置测试通过；源码/技术文档保留当前raw记录边界。允许机器人端不构造设备的--check-only，不启动实验。

调研：Hugging Face官方LeRobot v3、video encoding、streaming video文档；MCAP官方规范。实测episode2含2353 RGB帧，像素2,168,524,800bytes，占总2,182,403,012bytes的99.364%；源码Writer为CompressionType.NONE。视频压缩率只能编码后实测，不编造大小或兼容性。

## checkpoint

最终完成：操作员文档约2948字符（技术说明保留8184字符），明确--deployment、任务/路径/编号、按键/保存、退出和常见错误；技术说明与MP4/LeRobot v3方案独立。相关本地链接已检查。未实现视频或导出、不改变原始数据。

机器人已安装 `current -> releases/010-20261018-operator-final`，源码包SHA256 `0d73af23e717dc8dfc878aee5de2b66925d65b3959023e44f6caf4f96628c1e8`。启动脚本SHA256 `19c724c0a4db98bfb5db988aa95b924fc1a30fc9627ec7d16ea91c3b84cfb8dc`，旧入口备份 `bin/robot-infra.pre-010`。安装前确认无活动服务，显式deployment的collect --check-only退出0，8445/8446仍关闭。核心Python/Web源码树与此前实测r8一致；仅外部启动脚本/测试/文档变化。Ubuntu231通过，Windows219通过/9跳过，无物理实验。release-manifest记录新部署hash。

操作员手册已重写、原文保留为技术说明；主命令显式带deployment，补入口差异、编号、A/X、保存路径、退出及常见故障。视频体积/LeRobot官方来源和后续方案在独立文档，未实现MP4或修改旧数据。

设备脚本已修复显式配置优先（支持两种写法）、环境/CLI同源、路径带空格、缺参报错；8项Linux真实Bash+stub Python测试确保不加载ROS/设备。Ubuntu全套231通过，Windows219通过/9跳过；直接Python缺deployment行为有回归测试。测试归档SHA256 `f3faf6241cfb2f9528270c3b5a430faca19490d52d181e01f4c23c2c19500fa3`，机器人隔离目录 `releases/010-20261018-operator`。
