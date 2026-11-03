# ADR-0007：被动设备发现与显式身份绑定

日期：2026-10-16。状态：accepted，最小实现完成；平台/设备支持按实际验证报告。

远端同时存在多套旧SDK/ROS与旧相机serial配置。直接复制launch会将现场身份和应用流程耦合；CAN/串口存在也不能证明具体机器人身份或已可执行。

决定：设备发现模块独立于SDK/backend/映射和M1事件协议。先实现stdlib Linux sysfs枚举、可注入Collector、独立版本device-discovery/1和device-bindings/1、离线snapshot与配置驱动的精确匹配。无唯一身份/角色确认则不自动分配，多视频节点资源共享显式处理；部分搜索不能标记绑定完整。物理角色与主机配置放profiles/local，不内嵌serial、IP或USB端口到框架代码。

SDK识别、固件/状态查询、运行状态订阅分别由后续插件提供；被动枚举不打开tty/CAN/video，不执行ROS launch。该决定为功能分层和跨机器复用提供稳定入口，不新增通用主动扫描平台或改变M1契约0.3.0-m1。绑定通过只代表身份关系，不代替控制权或运行就绪检查。

详见[功能与格式](../device-discovery.md)、[本轮计划](../../plans/003-remote-audit-discovery-and-release.md)。M2多端点/组授权仍为下一控制切片。
