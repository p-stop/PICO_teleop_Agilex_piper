# 2026-10-19：new_test 三集数据与卡顿审计

本次只读检查机器人原始目录和日志；深检及对齐输出另存`~/robot-infra/runs/013-audit-20261019`。原manifest/QC/alignment/index逐一核对hash，均未改动；没有保存、丢弃或移动第三集，没有启动设备。

## 连接与实验身份

SSH配置已指向192.168.87.126。新IP没有独立known_hosts记录，严格校验首次拒绝；随后以旧IP192.168.87.130已信任密钥作为HostKeyAlias核验同一主机成功，未关闭主机身份校验。此次命令使用该选项；主机指纹确认后也可由操作者将新地址正常登记到known_hosts。

执行源码仍为012：core SHA256 `391d5adb0e802e1ac4dcc7a4de517537fdddac8a4c40aacbb7d862270ee12b35`，Ubuntu24.04/Python3.12.3/ROS Jazzy/PyAV16.1。当前8445/8446均关闭，相关会话已正常退出。

用户确认未更换相机，当前角色仍正确：左腕022422072252、右腕342522071110、固定254922307547。它们与更早文档中的序列号不同；本次以实际生效配置与用户确认作为本次身份依据，历史记录保留，不自动推断更换设备或重写旧数据。

用户说明三条只是测试手感与数据质量，**没有确定训练任务或成功/失败标签，统一为待人工标注**。因此它们可验证数据管线，不能直接宣称为成功任务示范。

## 逐集结果

| episode | 状态 | 时长(s) | 左/右/固定RGB帧数 | RTT median / p95 / max(ms) | 最大输入间隔(ms) | capture QC |
|---|---|---:|---|---|---:|---|
| 0 | 已保存 | 61.929 | 1844 / 1828 / 1841 | 13.0 / 89.3 / 165.9 | 187.1 | 通过 |
| 1 | 已保存 | 57.456 | 1721 / 1722 / 1723 | 21.5 / 191.3 / 557.7 | 538.9 | 通过 |
| 2 | .incomplete内review，未提交保存 | 32.143 | 959 / 957 / 950 | 19.8 / 138.3 / 271.0 | 305.3 | 固定RGB帧间隔不通过 |

三集均为real-episode/2、三路640×480 RGB/30fps、MP4。深度capture/record全部null，**没有三路深度，不能从RGB或metadata补出真实深度**。四路原生Euler/转换Quaternion末端流实际存在，约180–181Hz，无源时间回退、零stamp或非单位Quaternion。没有录制队列溢出、writer_error或interrupted标记。

三集的SHA256、MCAP footer/CRC/消息数、视频hash/完整解码/帧数/PTS、MCAP与视频索引引用均通过deep检查。第三集“文件完整”与“采样质量失败”同时成立；不能把deep通过写成capture QC通过。

三集IK中位耗时约1.3ms，最大分别14.64/7.87/4.41ms。存在配置允许的best-effort结果，但当前数据不支持“IK单次长时间阻塞造成这一轮高RTT”的解释。

## 第三集的QC究竟为什么失败

唯一issue：`camera/scene_fixed/rgb: frame gap`。固定RGB最大接收间隔197.477ms，超过150ms阈值；对应两帧源stamp差199.944ms，发生在本集约12.13–12.33秒。另有169.374ms间隔。全段固定RGB仍约29.549fps，所以平均帧率通过不代表没有局部空洞。

该空洞两端视频frame_index为354、355，源metadata帧号为9439、9445；这期间metadata中的9440…9444仍按约33ms连续收到。说明不是所有相机相关消息都同时停了，且丢掉的RGB像素不能由metadata恢复。尚不能从旧日志判定是ROS Image分发/QoS、回调排队还是record门控所致；metadata和Image是不同消息流。

已发现旧writer即便capture FPS等于record FPS，也按host接收时间做RateGate，抖动/批量交付时会无必要地筛掉真实帧。本轮修复为**同FPS逐帧保留，只有显式降FPS才筛选**。这消除了一个确定的软件丢帧点，但不能把它宣称为197ms空洞的已证实唯一原因。未来记录增加`capture_sequence`和`frame_capture_stats`，用于区分到达回调、到达writer、主动筛选和实际写入。

## RTT、视频卡和操作抖的证据

较大的控制延迟不只出现在第三集：第二集RTT峰值557.7ms，输入间隔538.9ms，却仍通过当前capture QC。当前QC主要看数据完整/采样/对齐，**不等于遥操响应质量、动作平滑度或任务质量评分**。训练筛选应另看这些指标。

整场会话accepted-input中RTT最大589ms，发生在episode窗口外。第三集结束并完成QC之后约11.6秒，浏览器报告 `stale server freshness ticket`，随错误上报的previous_rtt_ms为836.4。这次票据拒绝发生在第三集结束之后，不能当成该集相机QC失败的直接原因。它说明控制链有一次较长的端到端延迟/调度暂停。

浏览器记录的单帧JS工作大多不足1ms、最大约4ms；这不覆盖浏览器所有调度/网络/GPU工作，不能因此排除头显卡顿。相机preview fetch也出现百毫秒级波动。已有RTT包含网络、浏览器和服务器处理，旧日志没有同步Wi-Fi信号/重传/CPU调度指标，无法进一步唯一归因于无线抖动或主机处理。

本轮增加控制ACK的server input处理耗时，并在后续输入中回报`previous_server_input_ms`，方便将服务器处理与端到端RTT分开观察。它仍不构成单向网络延迟或跨机时钟同步。

## 独立的软件隐患：诊断日志上限

对应运行目录：`runs/20261019T125215Z_acf97d46`。六个子进程退出码均0，journal writer正常结束；gateway日志中的KeyboardInterrupt来自退出时被中断的IK子进程，不是本次运行中驱动崩溃证据。另一个`20261019T124843Z_e03069a1`是较早启动/退出的一场会话，不包含这三次teleop。

主会话journal写出494,556,694字节，约471.65MiB，已达旧512MiB上限的92%。其中大量是连续关节和新增末端观测。虽然本次error=null，继续运行可能很快触发`journal capacity reached`并导致控制停止，和本次Wi-Fi根因不是一回事。

本轮将诊断改为独立模块、默认每128MiB分段、不删除任何旧段、可选总量限制、可配置磁盘保留空间；摘要记录每段hash/bytes。episode原始采样不降频。读整场日志时应按summary.segments顺序，或使用`journal_segments()`，不能只读首个events.jsonl。

## 数据使用结论

episode0/1可用于训练管线工程验证；成功/任务文本仍待人工标注，episode1控制尾延迟值得人工回看。episode2默认不进训练，因为它未保存且QC不通过；如将来人工决定裁剪有效段，应生成新的派生片段并保留来源，而不是改原QC阈值或偷偷忽略失败。

缺失depth不能补零冒充传感器。原生末端已证实有实际数据，但base/TCP/外参语义仍未标定，不能直接拿来做统一世界系action。

复核命令（不会启动设备，也不改原数据）：

```bash
~/robot-infra/bin/robot-infra episode-audit \
  ~/robot-infra/dataset/new_test/episodes/episode_000000 \
  --output ~/robot-infra/runs/audit-copy-episode0 --deep
```

新增命令是否已部署以计划013最终checkpoint为准。原始证据根目录为`dataset/new_test`与上述两个session目录；派生审计本地副本在`artifacts/validation/013-data/013-audit-20261019`。没有进行运动、回放或策略实验。
