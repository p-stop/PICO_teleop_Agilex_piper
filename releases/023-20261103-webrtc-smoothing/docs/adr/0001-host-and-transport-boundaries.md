# ADR-0001：传输无关核心与主机角色分离

日期：2026-10-11。状态：设计决定，待首个实现切片验证。

## 背景

Windows 仅开发；FR3、Piper 与双 Piper 移动实验台分别使用 Ubuntu22.04、20.04、24.04。厂商 SDK、ROS、Python、GPU 和实时环境无法合理统一成一个安装包。

## 决定

- 核心契约、图校验、session、数据与 fake/replay 不依赖 ROS 或厂商 SDK。
- 显式声明 development/control-plane、device、inference、simulation 主机角色；角色可同机，但资源与延迟测试必须分别通过。
- 设备侧驱动、所有权、最终安全检查、执行调度与 watchdog 留在本地；GPU 推理只返回意图，无硬件写权限。
- ROS2/DDS 在同一已测试环境内可优先使用；老驱动与跨 distro 用边界 adapter，不承诺跨版本透明互通。
- 管理面先考虑 HTTPS JSON + WebSocket 事件；跨机推理候选 gRPC/显式二进制 schema；采集/视频独立通道。具体库/版本由 fake 网络切片决定；禁止网络反序列化任意 pickle 对象。
- 依赖与能力按 host/plugin/profile 锁定并 probe。核心跨 OS 通过不等于设备驱动支持。
- 开发用 SSH/Codex remote 或远端 CLI；不把开发连接纳入运动实时环。

## 后果与替代方案

需要额外的协议、时间域、序号、重连与兼容测试，但设备环境可独立演进。拒绝全平台强制同一 ROS distro/系统 Python，也不因容器可构建就声称宿主硬实时可用。暂不同时引入多套编排中间件。

验证：Windows 与三个 Ubuntu 版本的核心契约/fake 测试；单独的驱动构建、只读 probe 和物理准入证据。参见[跨机工作流](../development-and-validation.md)。
