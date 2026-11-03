# 2026-10-23通信与相机性能隔离验证

计划020，Ubuntu24.04机器人，SSH alias ranger-piper 当前解析到192.168.87.139。开始时没有运行采集/相机服务，current为018。本轮相机诊断不构造模型、机械臂驱动或运动发布器；没有运动命令或正式任务episode。用户报告Quest3能正常操作，单独记录为用户经验，不将其当成PICO性能复现。

## 版本与软件验证

- 初版候选：`releases/020-20261023-profiling-candidate`，core hash `e18fefab08e13db9718a0b5ca378d1eb75bd2f5e209b755caa6887866d4f53fb`，用于六组off/encode/archive测试。
- v2候选：`releases/020-20261023-profiling-v2`，core hash `100b86a67499b26a9544c77204ba2d1ee58e2061cef7e5250bc851f1e9f3011e`。增加显式Image QoS对照、实际publisher/RMW记录、诊断页面标题、预览失败后不再入预览槽；用于RELIABLE与头显诊断。
- 文件级SHA256及zip校验清单：本地`artifacts/preflight/020-candidate*-identity.json`，机器人保留同名副本。hash计算按排序的src文件名、空格、文件SHA256和换行拼接后SHA256，源码文本LF规范化；不要与018不同算法的tree hash直接作字节级同算法比较。
- Windows最终291 passed / 10 skipped（Pinocchio/ROS/Linux专属）；Node输入传输2 passed。Ubuntu最终304 passed，包含ROS localhost和Pinocchio离线测试。初次候选Ubuntu回归因新目录缺artifacts父目录失败，补建测试输出目录后通过；新增审计夹具随后显式使用NONE压缩，适配未安装可选zstandard的机器人环境，未更改运行时或安装依赖。Windows修订夹具使用独立basetemp单项复验通过，避免默认测试目录清理权限问题。
- 新增7项测试覆盖有界指标、慢预览不阻塞原始帧入队、最新预览替换、无人订阅不编码、归档选择、租约到期、编码错误、线程关闭、HTTP帧身份/无运动输入回显、源时间回退、原始帧字节/写入计数不变及缺Image但有metadata的离线识别；配置错误也有覆盖。
- 最终清洁候选目录`releases/020-20261023-profiled`，纯runtime hash为`66f6fa10659d3e08306d25462f7cdd28e8a64e85a8843cb34432e854ef2a54d9`。排除生成的egg-info后，Python/web资源逐文件与实测v2相同；不是再次改变运行时代码。最终源码/配置/必要文档包及逐文件清单见`artifacts/preflight/020-final.zip`、`020-final-identity.json`，Ubuntu收据`offline-tests-020-clean-final.json`。后补文档不冒充新的硬件测试。

## 七组独立相机对照

相同正式018相机配置：3 RGB640×480×30 MP4＋固定头部16UC1深度640×480×30 MCAP。使用同一个CameraIngress / PreviewWorker / EpisodeRecorder；每组60秒，分别重启相机，未使用头显网络。先off→encode→archive，再反序；每组独立输出，不覆盖原数据。复测期间曾有少量只读ROS参数查询，未获得有效参数结果，不能将六组当严格随机化基准或唯一因果证明。

| 模式 | 最大图像接收间隔 | 诊断进程CPU（单核100%） | capture/deep QC |
|---|---:|---:|---|
| off | 66.88ms | 69.0% | 通过 |
| encode，无JPEG归档 | 66.64ms | 77.9% | 通过 |
| archive | 165.77ms | 79.5% | 固定RGB frame gap失败；深度及媒体解码完整 |
| archive复测 | 134.71ms | 82.6% | 通过 |
| encode复测 | 69.10ms | 82.2% | 通过 |
| off复测 | 67.14ms | 68.4% | 通过 |
| archive＋Image RELIABLE | 42.62ms | 81.5% | 通过 |

CPU只含诊断进程在录制窗口的process_time，不含独立相机驱动，不是全机CPU。性能窗口分位数与全局最大值分开；指标还包含录制前后少量相机运行期，QC表取episode时间索引。

所有测试相机子进程退出码[0,0,0]、线程清理正常。关闭预览的两组没有编码预览；encode没有JPEG侧车；archive显式归档。所有原始writer没有报告溢出/写入错误。各组记录队列最大等待约18–35ms，未见100ms量级排队。记录边界/启动稳定期不同会影响各流帧数，不能要求RGB/深度恰好一样多，也不能以QC通过证明每次曝光全部收到。

实际RMW为`rmw_fastrtps_cpp`，三RGB及头部depth发布端均advertise RELIABLE。前六组订阅保持原sensor-data best_effort/5，末组只显式改Image订阅为RELIABLE/5，仍开启预览归档。单次60秒通过不是修复认证，也没有证明重传时的端到端延迟；需要长时完整并发重复测试。

## 缺帧进一步定位：图像空档里元数据连续

首轮archive失败段的原始索引：固定RGB视频frame_index1645之后直接到1646，两者接收间隔165.771088ms、源时间间隔167.235840ms。

同次MCAP的`device_metadata`显示：前一张对应frame_counter1653，后一张对应1658，**中间1654、1655、1656、1657的元数据全部存在，源时间连续、接收也约33ms一次**；`actual_fps`字段也没有表现出这段降到数Hz。

因此，至少对这次异常，驱动已经取得中间四帧的元数据，图像缺失发生在取得帧之后的图像处理/发布→DDS→订阅接收路径；不能只归因于相机曝光没发生、头显网络或writer丢帧。仍无法仅凭这些字段区分驱动图像发布丢失与DDS/RMW/订阅前转换损失；相机元数据到达不等于对应ROS Image成功发布。

这也解释了019为什么仅对比Image源时间仍不足以定位。原始元数据的保留提供了进一步证据，不应为了减日志省略它。暂不改曝光或USB配置；JPEG归档既有额外开销，但其复测通过，不能定为唯一原因。

## 头显相机/输入回显诊断

v2的`camera_benchmark --preview-mode demand --serve`只创建相机、HTTPS/WSS和输入诊断，不创建物理执行后端。Quest3两轮用户反馈：无预览RTT常见100–200ms、峰值600–700ms；有预览也常见100–200ms，并出现控制断连。不能宣称网络问题或预览延迟已经修复。

服务端共收到1,609条输入，按client_media.enabled区分：

| 阶段 | 样本数 | RTT中位数 / p95 / 最大 | app.input p95 |
|---|---:|---|---:|
| 关闭预览 | 1,017 | 33.9 / 217.6 / 684.0ms | 0.048ms |
| 开启预览 | 592 | 13.8 / 125.2 / 316.6ms | 0.046ms |

按成功包携带的上一包统计，超时请求不在这些RTT样本中；两阶段并非同时或随机化采样，开启预览时数值较小不能证明视频改善网络。用户看到的HUD瞬时值与整段中位数也不同。记录了一个client控制连接中断事件，服务端有keepalive ping timeout；未将退出/头显休眠后的所有断连都当成主动操作期间的网络丢包。

开启预览时三路JPEG获取p95约142–178ms；响应头里的服务端帧龄p95约127–138ms，均为输入重复携带的最新媒体统计，并非独立请求分布，也不是曝光到眼睛的延迟。整个300秒相机记录capture/deep QC通过，三RGB分别8976/8979/8975帧、深度8989帧，最大间隔约132.2ms；没有JPEG归档，preview worker与三相机均正常退出。这说明本机采集稳定性与头显连接质量可以分离，QC通过仍不等同零缺帧。

## 网络与服务端分层：无相机也存在尾延迟

使用[profile_input_transport.py](../../tools/profile_input_transport.py)，运行同一个生产ControlSocketServer监听器及约2KB假输入回显，连续30秒、目标30Hz、同样逐包等ACK，不构造ROS/机器人。单独生成7天诊断证书，只下载公钥证书到开发机进行TLS验证；正式证书未更换。原采集自签证书已过期，头显人工例外仍能访问；这会影响新设备首次连接体验，应单独更新，不能据此解释已建立连接中的RTT波动。

| 路径 | 成功包数 | RTT中位数 | p95 | 最大 |
|---|---:|---:|---:|---:|
| 机器人本机回环WSS | 898 | 0.395ms | 0.763ms | 1.339ms |
| Windows WLAN→机器人WSS | 518 | 47.0ms | 109.0ms | 297.0ms |

两端handler p95约0.006ms。listener及client所用websockets源码已经设置TCP_NODELAY，不能建议“补开这个选项”作为此次原因。单个业务ACK等待让无线路径实际只完成约17包/秒，即使目标是30Hz。

独立ICMP低频分层也观察到尾延迟（不是同包、同协议对照，不与WSS直接相减）：

| 路径 | 应答/发送 | RTT中位数 / p95 / 最大 |
|---|---:|---|
| Windows→网关192.168.87.1 | 100/100 | 8 / 207 / 346ms |
| Windows→机器人.139 | 97/100 | 86 / 187 / 382ms |
| 机器人→网关 | 150/150 | 1.92 / 56.4 / 约199ms |
| 机器人→Windows.124 | 149/150 | 约172 / 945 / 约1868ms |

ICMP调度、限速和站点方向可能不同，不能把1868ms直接视为控制流的实测延迟。它独立说明链路/端点网络栈存在明显抖动，不依赖VR渲染、相机传输或IK。仍不能区分AP竞争、两端网卡、省电与驱动因素。

机器人当前HCP-203A/5200MHz，驱动rtw89_8852be；NetworkManager连接选择default，系统配置`wifi.powersave=3`，rtw89的disable_ps_mode=N。`iw`未安装，因此实际无线省电运行状态未直接读取；配置是待验证线索，不是已证实根因。没有安装包、修改省电/ASPM/接收缓冲或重连无线。rmem_max与ipfrag_high_thresh均为4MiB，且存在FastDDS SHM文件，不能未经传输确认就归因于UDP缓冲或建议任意调大。

用户离开后授权继续无人值守排查；仅运行限时相机、ICMP与假输入回显，没有VR操作和机械臂驱动。

## 延长QoS与同进程调度隔离

| 诊断 | 时长 | 最大图像间隔 | 单核CPU | capture/deep QC |
|---|---:|---:|---:|---|
| best_effort/5＋encode无归档 | 180s | 68.55ms | 80.4% | 通过 |
| RELIABLE/5＋encode无归档 | 180s | 45.90ms | 79.4% | 通过 |
| RELIABLE/5＋encode＋同进程WSS回显 | 60s | 44.83ms | 79.6% | 通过 |

长录制两组相机子进程退出[0,0,0]，无writer溢出/错误；两种接收方式都通过，不能把可靠传输表述为已确定的唯一修复。RELIABLE较少出现约两倍帧周期的间隔，是进一步完整并发验证的候选设置。

最后一组在同一Python进程内运行ROS接收、三RGB MP4＋depth记录、JPEG编码、诊断日志、HTTPS/WSS，再由本机相同client连续30秒测得899包：RTT中位0.386ms、p951.962ms、最大9.528ms；handler p950.026ms。相比纯回显p950.763ms，图像负载有开销，但此环境中没有复现100–700ms级应用接收等待。仍未覆盖真实双臂高频反馈、映射与控制线程，不能据此证明整个真机服务没有GIL/回调竞争。

本轮共11次相机诊断，19分钟定时录制（不含启动与QC），其中10次capture QC通过、一组archive出现原始图像gap；失败证据保留，没有改阈值。相机数据在独立runs目录，不消耗正式任务编号。最终没有robot_infra或相机驱动进程，8445/8446均无监听；current和formal-018配置未切换。

## 证据与下一步

机器人`runs/020-camera-{off,encode,archive}*`、`runs/020-camera-reliable`保存effective-config、MCAP/MP4/index、逐相机日志、QC及result.json。机器人`camera-summary-020.json`、`metadata-gap-analysis-020.json`，本地`artifacts/validation/020-data/`保留派生报告。参考QuestArm关键文件hash另存`questarm-snapshot.json`，未修改参考仓库。

尚未完成：正式双臂遥操并发回归、足够长/多次的RELIABLE时延与丢帧比较、驱动publish侧计数、DDS传输缓冲定位、浏览器到眼睛端到端延迟。ACK逐包等待、JPEG轮询和摘头显暂停语义都保留；独立进程图像接收/记录、流媒体与异步位姿传输是后续切片，不是本轮已实现功能。

下一切片优先级：现场可配合时先做无线省电/连接条件单因素对照；代码侧实现连续位姿最新值传输与离散按键可靠确认解耦，使用有界在途量/背压与既有时效/停止语义，先fake测试再真机。图像侧保留RELIABLE候选设置与元数据对照，补发布端计数；媒体流单独演进。不要延长输入超时掩盖断链，也不因当前回环表现就放弃后续完整服务的进程隔离评估。

部署current与正式formal-018配置未切换；候选可单独复现。不要把相机诊断数据并入fill_pen_holder示范，也不要因为相机测试通过就跳过现场完整采集验收。
