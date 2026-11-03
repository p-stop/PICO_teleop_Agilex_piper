# ADR-0008：独立真实输入/观测与设备身份命名空间

日期：2026-10-16。状态：accepted。关联：[计划004](../../plans/004-live-observation-and-webxr-input.md)、[实测报告](../validation/2026-10-16-a4s-live-observation.md)。

## 决定

先提供无机器人命令端口的WebXR输入服务、ROS域RealSense RGB采样adapter与纯SocketCAN接收采样器。浏览器输入、记录器、设备适配器分离；相机/通道角色由配置注入，Piper协议解码需显式选择。ROS/SDK不进入核心依赖，不复用含隐式enable/底盘启动的旧整机launch。

webxr-input/1、camera-sample/1、can-rx-sample/1及realsense-rgb-sample/1为独立诊断版本；不改M1 0.3.0-m1，不将若干短样本称为完整episode。后续多端点runtime和统一MCAP记录单独设计迁移。真实命令继续经过所有权/guard，不从输入服务直接调用SDK。

保留WebXR参考空间与reset epoch、null追踪状态、按钮原始索引、客户端时间、设备metadata/ROS header及host收取时间；不静默选择坐标映射或同步关系。HTTP有界队列跳帧、seq缺口和发送错误作为质量证据，连接成功不能替代时序验收。

设备identity必须带命名空间。被动USB枚举保留兼容serial并增加usb_serial和serial_namespace=usb_descriptor；RealSense开流明确要求realsense_sdk。两个标识之间的关联需实际设备端口/驱动证据，不能按相似数字或型号推断。旧绑定文件仍可用，新增字段为兼容扩展。

## 原因与后果

真机实测证明同一相机的USB descriptor serial与RealSense SDK serial不同。旧源码中的SDK serial实际上有效；把USB枚举当SDK设备列表会误判并导致开流失败。身份发现、厂商识别与驱动连接需要保留各自来源。

本切片使输入/图像/反馈可独立复测且无需先完成动作执行；代价是短期存在独立诊断格式与启动进程。此边界明确且可迁移，不为赶进度放松M1固定拓扑或引入第二条物理命令入口。已验证范围见报告，运动、持续数据和跨平台适配仍需后续证据。
