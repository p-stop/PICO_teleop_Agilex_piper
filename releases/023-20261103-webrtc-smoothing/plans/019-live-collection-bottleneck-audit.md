# 019：正式采集帧间隔与VR预览延迟诊断

2026-10-22，completed（只读诊断；性能改造尚未实施）。用户反馈frame gap QC失败、VR视频延迟及摘下VR不能操作。只读当前数据/会话/系统状态，不启动、停止或修改正在进行的采集，不改QC阈值，不发送机器人/VR控制输入。

目标：分别定位原始camera/ROS→writer、本机JPEG→HTTPS→浏览器，以及VR生命周期→暂停；结合新capture_sequence/writer计数、源stamp、metadata、RTT与client媒体计时，区分证据和未定因果。检查当前进程CPU/IO/线程、无线链路信息仅作快照，不将事后CPU当故障时实测。

已读018状态/入口/架构与相关实现；robot .138上018正在运行，8445/8446开放，当前run=20261022T124015Z_2cef230e。fill_pen_holder已有一条saved/QC通过与多条discarded，失败含相机frame gap和输入超时。分析结果另存，源数据/配置/服务保持不变。

验收：覆盖saved/discarded、逐帧源时间与接收时间、记录器计数、控制/预览计时、VR状态与资源快照；结果区分已证实行为和候选原因，给出下一切片与对照方案，不改变采集。

结果见[现场报告](../docs/research/2026-10-22-collection-latency-audit.md)。十个已结束尝试中六个有frame gap；所有writer dropped=0/error=null且收到帧均写入。源stamp也有约167–300ms空档，不能定位USB/驱动/DDS/回调中的单一原因。输入RTT median27/p95121.8/max703.2ms，app.input p950.335ms只覆盖业务处理；8→2fps预览降级和逐包等ACK明确放大延迟。摘头显visible-blurred暂停有独立证据。两秒PAUSED/IDLE快照不是故障时性能追踪。

checkpoint：机器人派生JSON在runs/019-readonly-audit，本地artifacts/validation/019-data已下载四份；连续诊断日志分析固定读边界约2.056GB。仅创建派生报告、读取源数据；未发送控制、启停进程或改配置/QC。无运行时代码变更，未重跑与文档无关的单元/硬件测试。后续性能改造另开计划，现场运动测试需明确授权。部署仍为018。

验证：Windows解析四份JSON并重新核对十集/两集通过/六集gap/三集中断、所有writer计数与预览文件体积；报告本地链接检查和git diff --check通过（既有CRLF提示不影响结果）。Linux证据为现有物理记录与只读快照，不是新增并发测试。
