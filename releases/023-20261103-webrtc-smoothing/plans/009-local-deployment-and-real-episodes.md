# 009：机器人独立启动、可配置相机与真实 episode

2026-10-17开始，2026-10-18 complete（A4-S原始RGB采集切片）。保留现有未提交改动，无远程发布。

## 顺序和验收

1. 审查现有部署与QuestArm/Franka采集参考；当前机器人已有源码、无Windows运行依赖，补稳定设备端入口及可迁移部署配置。
2. 显式相机v2配置：capture RGB/depth、preview、record分别设置，默认三RGB640x480x30，预览缩放独立；保留v1相机配置。屏幕距离2.20→2.21m。
3. 无硬件episode存储/异步录制/MCAP/QC：任务/路径/起始号/已有编号策略由CLI明确指定。任务锁、incomplete/episodes/discarded/backup分区；覆盖仅完整新数据提交时移动旧版备份，跳过扫描已占编号；不删除用户数据。
4. session按键接入：READY A→准备录制→遥操；A结束→异步flush/QC→REVIEW；A保存/X丢弃后待机。VR失联中止录制，保留interrupted证据并等待审阅，不能自动继续拼接连续episode。
5. 真实ROS采集与预览扇出：原始图像独立MCAP二进制通道，非预览JPEG；保留camera_info/metadata/原始时间戳/意图/命令/反馈。采集和磁盘工作分开、按bytes与条数限队列，溢出报错不默默丢。时间对齐离线索引、标记误差，不改原始时间。
6. Windows fake/集成/配置/故障测试，Ubuntu同源码离线测试；部署机器人用户目录、本地命令和说明。30fps相机只读观测先验，再用户现场保存/丢弃和暂停测试；未测试深度/高分辨率不宣称硬件支持。

## 决定与边界

复用MCAP库、Pillow和现有ROS驱动；不引入训练器/数据平台。核心存储不导入ROS/硬件SDK，命令仍过唯一网关。正式采集用独立real-episode/1，M1/fake collection契约不变。QoS BEST_EFFORT损失可能在进入进程前发生，QC须测实收FPS/时间间隙，不仅检查应用队列。源配置和实测配置分别保存。录制分辨率与预览分辨率独立；深度原始uint16/float与字节序完整保留，不猜测米制缩放。进程崩溃的.incomplete不自动算已保存。

默认已有策略error；用户显式skip或overwrite才生效。任务文本与路径目录ID区分，任务可中文，路径ID确定性编码。用户本轮确认主机在线且稍后现场配合；先实现、测试、相机观测；运动阶段再确认现场就绪。远端只读检查约653GB空闲、8445关闭。

## checkpoint

**最终2026-10-18：本切片完成。** 用户确认“一切正常”；episode2实际保存26.179121925s、MCAP2,182,403,012bytes/24,380消息，三RGB784/784/785帧、29.9406/29.9391/29.9860fps，最大帧间隔64.4/68.7/37.7ms。0应用丢样、0规格失配/源时间倒退、785对齐参考0invalid，QC及deep SHA256/CRC/footer/count/raw解码全通过。路径 `~/robot-infra/validation-data/a4s-session009-validation/episodes/episode_000002`；MCAP SHA256 `1001920b33a75dff5f7f1487e0391726fed1e9a0cd99bdca7a8c578d12ef1835`。两份incomplete/三份discarded保留，不改历史失败。

最终部署已切换 `~/robot-infra/current -> releases/009-20261018-validated`，仅补最终文档，执行源码树hash与r8完全相同。归档 `artifacts/preflight/009-source-validated.zip` SHA256 `9159202343d642a6d5a4d612a6da178c885efb4da7040b36ea82e5025834be74`，机器人release-manifest.json记录版本/hash/验收episode。设备本地collect --check-only最终退出0，未启动硬件，8445/8446仍关闭且无任务锁。wheel/sdist构建与排除检查通过，输出 `artifacts/dist-009-validated`；小型验收元数据存于本地ignored `artifacts/validation/009-20261018/009-validation-evidence.zip`，未下载2GB原始影像。无Git推送。

双臂home约4.522s，用户确认独立夹爪/双臂操作、结束和保存正常。诊断中夹爪单独命令左913/右826；物理trial518个输入，RTT中位17.8/p95 101.5/max299.2ms，最大接收间隔211.1ms。执行源码树SHA256 `356fa01edbaf0044d301d6b1495a3dd24693a19f04fb9576fc462a205e6e0999`；Ubuntu222/Windows218+1skip/Node2/包构建与排除检查通过。首个成功episode不是长期网络可靠性证明；旧长XR帧间隙仍保留，未通过放宽超时或home容差掩盖。

supervisor4314已精确SIGINT停止，六子进程exit0，journal error=null/writer_stopped=true，8445/8446关闭，任务锁释放，无活动实验。run `runs/20261018T120845Z_78c23da9`，stack-ended.json和episode/journal-summary.json有实际证据。设备本地入口保留；后续重复任务采集/长时稳定性、标签与训练导出、真实策略另排切片；深度、其他分辨率、完整M2/A1/A2不在本次通过范围。

以下为历史过程记录，活动PID和待验描述不代表当前状态。

2026-10-18有效对照已拿到（同r8 run）：ON一轮1417输入/69.842s，RTT中位11.2/p95 92.2/max188.7ms，最长输入间隔198.6ms；OFF一轮933输入/47.926s，原始包enabled=false且fetch/decode均null，RTT中位19.1/p95 102.2/max201.1ms，最长间隔302.0ms。两轮无client error、无>.6s输入空窗；不同时间窗口不构成严格网络负载随机实验，OFF未显著改善，不能认定媒体是唯一原因。用户确认HUD预览关闭、无实时画面/无断开。r7先前1.149s间隙仍需保留，不以这两轮覆盖旧失败。

最新服务仍r8/supervisor4314，PAUSED(pagehide)/resume STANDBY，录制IDLE，episode2，双臂err0、新鲜，三原生RGB约30。已请用户开 `?v=collection009g`（preview默认ON），A回位→A开始→独立扳机+侧握小幅双臂8–10s→A结束→A保存→退出VR；待用户结果后检查实际提交与deep QC，不自动代用户按保存。

2026-10-18 r7首轮：用户确认PICO在HCP-203A，报RTT约7–173ms无断开；但1000个原始包全部client_media.enabled=true，不能当预览OFF对照。RTT中位约12ms、p95约89ms、max约177ms；抓到同session/epoch连续两XR帧之间约1.139s、浏览器采样约1.191s的间隙，接收间隙1.149s，而相邻RTT约7.5/93.5ms。证明至少一次空窗包含头显帧回调停顿，不能全部归因无线往返。三路fetch错误计数0。未发物理命令。r7精确SIGINT正常停止，六子进程全exit0，journal error=null/writer_stopped=true。

为确保OFF状态，加显式诊断参数preview=off（只设浏览器开关，不改相机/记录），并更新页面版本标记。r8归档SHA256 `f297bda1eb1fd10f7f29e3ef7e771175f743ea894602d0febcea13e0e205b6a0`，`releases/009-20261018-r8` 已激活；相对r7仅两处前端改动，Node2和模块语法通过，Python222证据属于r7同Python源码。supervisor4314，metadata `runs/collection-validation-06-supervisor.json`，run `runs/20261018T120845Z_78c23da9`，待机无错误，duration1800。已请用户打开 `?v=collection009f&preview=off`，核对HUD“预览已关闭”，VR30秒不按控制键，等待数据。

2026-10-18当前：r7归档SHA256 `372c078084a4dce3f09fb1ca9f3c013d0f7ae07982f87850c7c0639feb0630f2`，已部署 `releases/009-20261018-r7`，Ubuntu222/Windows218+1skip/Node2通过。r7归档排除docs/.obsidian，比旧归档少4个无关工作区文件；Node测试加入MANIFEST。旧12.224s/1.018GB的MCAP deep哈希/CRC/消息数/解码均通过，仍因interrupted QC未过，不保存不改名。使用--recover-lock恢复死PID15243锁，跳过两个incomplete编号，当前待录episode2。

supervisor3375 metadata `runs/collection-validation-05-supervisor.json`，run `runs/20261018T120426Z_ac5eb0c5`，duration1800秒；用户尚未发送输入时STANDBY，双臂err0、三相机约30fps。已请PICO打开`?v=collection009e`关闭“显示相机预览”→VR30秒→退出，不按A/侧握/扳机；待用户反馈及原始RTT指标再开预览对比，不能擅自进入物理测试。当前尚无successfully saved episode。

2026-10-18用户已回来并明确继续，暂停限制解除。恢复只读核验：旧supervisor/children均不存在、8445/8446关闭；旧run仍无stack-ended/journal-summary，不将异常停止伪装正常。task lock仍指旧PID15243，/proc/15243不存在且hostname仍ros，可用既有--recover-lock显式恢复；两份.incomplete和三份discarded保留，saved=0。当前can0/can2 UP、can2 bus-errors0；三秒纯接收证据 `runs/resume-rx-20261018T120233Z` 两臂各约9424帧、关节对完整，不发送命令。机器人IP未变，Wi-Fi HCP-203A/5200MHz，配置powersave=default，未改变网络设置。

本轮顺序：核验残留/旧数据→本地测试前端修复→源码r7部署和Ubuntu离线测试→PICO无运动关闭预览/开启预览对比输入RTT、间隔、fetch/decode指标→定位后再用户A回位/独立扳机/8秒A保存→deep QC。用户现场和头显网络信息已异步询问。不得仅放宽通信超时来宣称解决延迟；不改变home/坐标/物理限位，不删除旧数据。

最终暂停状态：已执行按PID验证→SIGINT→等待→核对清理的远端脚本，但SSH期间超时（无返回输出），随后ConnectTimeout5秒重试同样失败。**无法确认SIGINT是否实际执行、supervisor15177及子进程是否退出、任务锁是否释放、端口是否关闭**。不要把r5已清理证据挪作r6证据。r6配置duration1200秒，但不能用期限代替实际清理核验。下次用户恢复实验时先SSH连通性→核对原PID/cmdline/cwd和run stack-ended/journal-summary→必要时仅停止本项目残留；未获用户恢复前不启动设备。本地失败锁定/诊断前端改动保留，尚未部署。当前没有成功保存episode，故计划未完成，现场实验按用户请求暂停。

用户最新明确暂停真机实验、离开现场，等回来再继续。反馈“可以遥操，但依然闪红”，网络暂不调整；不再要求用户执行实验。r6实际home 4.526s→READY，用户随后开始遥操；12.224s后输入超时中断，REVIEW QC仅报interrupted，RGB29.838/29.996/29.933fps、0应用丢样/0对齐invalid；尚未保存。run `runs/20261017T145552Z_4fb30462`，pending `.incomplete/episode_000001_c38b9e2c1d0740779898948c583b87c2`。正在按用户要求停止supervisor15177及子进程，最终状态见后续补充。

本地另发现并修复：控制传输失败后XR帧仍反复尝试发送，造成重复HTTP stop/PAUSED↔REVIEW风暴。InputTransport现锁定失败、清队列、只发送一次stop并要求刷新，原始错误只报一次；新增Node两个行为测试，覆盖失联后300帧不再发请求、慢ack时按键不丢/运动保留最新。另增加预览开关用于无动作链路A/B诊断、每路fetch/decode耗时和错误计数、HUD RTT；短暂单次fetch失败不立即抹掉仍新鲜的旧图像，超过1.5s才变红。该前端增量仅本地实现/Node测试，**未部署至机器人、未做PICO验证**。不得标成已经解决网络问题。

r6补充：已部署 `/home/ros/robot-infra/releases/009-20261017-r6` 并切换current，归档SHA256 `f8f07ad941a2e5bd4f15c2a42db0ee2a12c0fe594e0213f618d97529498c15e7`；Ubuntu222通过（显式--basetemp），Windows218通过/1跳过，JS模块语法通过。supervisor15177，metadata `runs/collection-validation-04-supervisor.json`，日志同名前缀.log；duration1200秒，待机、双臂错误码0/反馈新鲜、三相机30fps。已请用户刷新`?v=collection009d`先A回位，等待结果。尚未宣称恢复成功。最新报告 `docs/validation/2026-10-17-a4s-collection.md`。

最新2026-10-17：r5已部署（source tree SHA256 `7bffc69bf7a2e92a2776c90919dc4986a01cd634cfbdf4fe8a052170c0c6d832`），机器人221测试通过。独立扳机走单独ROS话题/driver GripperCtrl，不启用或发送臂目标；进入只读扳机基线。用户反馈本轮A无反应/回位久/相机闪红，随后明确发现右臂驱动错误，重新set up。已停止supervisor13657及六子进程（全exit0），8445/8446关闭，run `runs/20261017T144049Z_4353d47c`；无录制episode。相机源仍30fps/预览8fps，服务器status约4.8ms；PICO WSS RTT中位54.9ms/最大721.3ms，JS frame work中位0.5ms/最大3.8ms。两次HOMING因输入超时中断；不能仅归因于网络或单点home容差。右臂反馈值曾变化，保留日志，不放宽home阈值。

恢复后纯接收证据 `runs/can-recovery-20261017T145313Z/summary.json`：can0/can2 UP，can2 ERROR-ACTIVE为CAN正常错误计数状态（不是BUS-OFF），零bus-errors；各关节对3秒600帧，右joint4=-2603毫度稳定，raw0x2A1 `0100010001000000` 末两字节err_code=0。无SDK初始化、无send调用；不证明物理回位已成功。机器通过5GHz Wi-Fi HCP-203A连接，当前可见信号89，未测得PICO网络身份；IP .111是Windows，ping数据不可冒充头显测量。

本地最新218通过/1跳过，新增home每臂误差诊断和tracking-loss暂停防抖，未部署。下一步归档r6→Ubuntu离线→无运动连接/状态检查→用户A回位、独立扳机→8秒A结束/A保存→离线deep QC。保存与QC待验证，不能标计划完成。r4曾有72.1588s正常A结束/X丢弃（29.947/29.711/29.776fps，右相机170ms间隙导致QC未过）；总计3份discarded、0份saved，旧incomplete保留。后续更新本节覆盖下方早期checkpoint。

已读AGENTS、架构/状态、计划001/008；已审查QuestArm的.incomplete/episodes/discarded和独立writer，以及Franka相机/写线程和原始与处理路径。借鉴分层/原始时间，不复制静默queue丢帧、写入时刻冒充采集时刻、阻塞回调或固定机器人话题。

实现已落地：camera_config/image_codec/episode_store/real_episode/episode_qc/deployment模块，CLI collect/device-teleop/episode-qc，本地bash入口，session PREPARING/FINALIZING/REVIEW/COMMITTING，原始MCAP和异步保存/丢弃。Windows214通过/1跳过，Ubuntu r2全套218通过。Windows另安装已声明Pillow12.3及websockets16.1.1至项目venv；机器人复用原有Pillow/Pin4.0/SciPy1.18/websockets16.0，未改系统包。UV锁新增可选teleop库。

设备部署 `/home/ros/robot-infra`：bin/robot-infra、deployment.json、profiles（原主机绑定/本机TLS）、python-deps（复制旧临时纯PythonMCAP）、current→releases/009-20261017-r2。原生三相机640x480x30无运动观测通过：29.979/29.980/29.988fps，三个驱动退出0，报告runs/camera30-probe/result.json。用户已恢复can0/can2 UP。

首轮完整采集监督器10515（已停止），run `runs/20261017T141257Z_482ded81`：两次真实episode因输入间断>.6s自动中断，均由用户X丢弃，原始三相机约29.84–29.94fps、0应用queue丢样/0对齐超差、QC如实失败；尚无保存成功。六子进程退出全0。日志比较浏览器采样间隔与接收间隔，存在采样已生成但接收晚300ms的HTTP尾延迟。用户确认未按A即自动待审阅、跟手与画面延迟；2.21m距离合适，并新增HUD面向操作者的倾角需求。

为解决控制与媒体共用HTTP资源，新增control_socket.py复用已安装websockets，以独立WSS端口8446接webxr-input/1并回ack（webxr-control/1），Origin检查/序号/唯一控制权仍保留，不放宽.6s。预览默认15→8fps，拥堵时可配置降至2fps；采集原生30不变。HUD按配置hud_face_viewer面向进入时的观察点。独立socket无硬件往返/错误/断线/退出测试通过；相关33项通过。准备r4归档→Ubuntu离线→再现场保存/X丢弃；r3归档只上传未激活，不用作实际验收。接下来更新docs/状态/ADR与最终清理证据。
