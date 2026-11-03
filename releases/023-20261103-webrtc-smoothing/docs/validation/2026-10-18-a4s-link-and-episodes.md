# A4-S 恢复、链路诊断与首个保存 episode 验收

2026-10-18，用户明确恢复实验。已完成上轮残留/数据核查、预览ON/OFF对照和首个A保存episode的完整性/QC验收，用户反馈“一切正常”。通过范围为当前A4-S原始RGB采集切片，不代表长期时序稳定性或完整M2完成。

## 恢复检查

旧supervisor15177及其子进程均不存在，8445/8446关闭；旧run没有正常退出摘要，不认定为正常停止。锁属于已消失的同机PID15243，通过既有 `--recover-lock` 恢复，保留两份incomplete和三份discarded，saved=0。旧12.224秒记录约1.018GB，完整MCAP/hash/CRC/消息数/图像解码检查通过，QC仍明确报interrupted；没有改名或算作成功保存。

can0/can2 UP，can2 bus-errors0，三秒纯接收关节对完整，无发送。机器人仍在HCP-203A的5GHz Wi-Fi；用户确认PICO同SSID，控制连接对端为192.168.87.113。SSID相同不等于频段或端到端性能已确认。未改网络配置、坐标、home或限位。

## 已部署与验证边界

r7部署了传输失败锁定/停止重试、预览开关、fetch/decode指标和RTT HUD。Windows218通过/1跳过（无Pinocchio）、Ubuntu222通过（含Pinocchio）、Node2传输行为测试通过。r8相对r7仅改两处前端：支持 `?preview=off` 初始关闭预览、明确页面版本标记；Node及语法检查通过，Python源码相同，不重复伪造新的Python测试批次。

r7 run `runs/20261018T120426Z_ac5eb0c5` 六子进程均正常退出0，journal error=null/writer_stopped=true。当前r8 run与PID以计划009为准。两轮都从待机开始，不自动使能，未由工具发运动命令。

## 诊断证据

首轮r7共1000个输入包，client_media.enabled全部true，因此不是有效的OFF对照，尽管用户原计划关闭预览。用户报RTT约7–173ms且无控制断开，与日志中位约12ms/p95约89ms/max约177ms接近；三路fetch错误数0。

同一session/epoch中曾有相邻XR帧时间差约1.139秒，浏览器采样差1.191秒、服务器接收差1.149秒，frame_seq只差1；相邻RTT约7.5/93.5ms。因此这段空窗至少包含头显XR帧回调暂停，不能全部归因无线往返或服务器负载。该事件的设备内部原因仍未知，未通过放宽超时掩盖。

r8再次要求OFF对照；截至中间检查，原始包仍标true。先用仅一个参数的 `https://<robot-ip>:8445/?preview=off` 确认复选框、图像停止刷新、HUD“预览已关闭”以及原始包false四者一致，再对比输入间隙。没有这项证据时不宣称预览关闭测试通过。

随后已取得有效OFF数据，用户确认HUD与画面状态，原始包也为false：

| r8模式 | 输入帧 / 时长 | RTT中位 / p95 / 最大 | 最长输入间隔 | >600ms间隔 |
|---|---|---|---|---|
| ON | 1417 / 69.842s | 11.2 / 92.2 / 188.7ms | 198.6ms | 0 |
| OFF | 933 / 47.926s | 19.1 / 102.2 / 201.1ms | 302.0ms | 0 |

两轮均无client error。OFF的各路fetch/decode为null、bytes0，证明关闭了浏览器图像请求；相机原生仍约30fps。OFF未显著降低延迟，且不同时间窗口的无线状态可能变化，因此不能认定媒体预览是唯一原因或网络问题已经彻底解决。r7的长帧停顿证据仍保留。

## 保存与 deep QC 验收

用户确认本轮回位、独立夹爪、双臂跟随、A结束/A保存及画面正常。实际录制26.179121925秒，保存到机器人：

```text
/home/ros/robot-infra/validation-data/a4s-session009-validation/episodes/episode_000002
```

| 项目 | 实测 |
|---|---|
| 原始MCAP | 2,182,403,012 bytes，24,380消息 |
| 左腕RGB640×480 | 784帧，29.9406fps，最大间隔64.395ms |
| 右腕RGB640×480 | 784帧，29.9391fps，最大间隔68.671ms |
| 固定RGB640×480 | 785帧，29.9860fps，最大间隔37.707ms |
| 左/右关节反馈 | 4696/4700条，约179Hz |
| 队列/规格/时间 | 0应用丢样、0规格失配、0源时间倒退 |
| 最近接收时间对齐 | 785参考行，0invalid；不等于曝光同步 |
| QC / deep | 均通过，issues=[]；SHA256、CRC、footer、消息数、原始图像解码均通过 |

记录还含camera_info/SDK metadata、518条原始输入、428条意图/运动结果，以及guard/command/receipt。网关诊断确认夹爪单独命令左913/右826次，用户确认不按侧握也可开合；这些命令不附带臂目标。MCAP SHA256：`1001920b33a75dff5f7f1487e0391726fed1e9a0cd99bdca7a8c578d12ef1835`。

保存trial的控制RTT中位17.8ms/p95 101.5ms/max299.2ms，最大输入接收间隔211.1ms；没有输入超时中断。home→READY约4.522s，A结束→REVIEW约0.522s，保存提交约0.017s。后两者不含操作者等待；“保存提交”是异步写入已完成后的目录提交，不能当作2GB文件写盘耗时。

实际执行包源码树SHA256：`356fa01edbaf0044d301d6b1495a3dd24693a19f04fb9576fc462a205e6e0999`。Ubuntu24.04/Python3.12.3/ROS Jazzy，运行依赖MCAP1.5.0、jsonschema4.10.3、Pillow10.2.0、Pinocchio4.0.0、SciPy1.18.0、websockets16.0；没有改系统包/供应商源码。构建wheel/sdist通过，网页资源/本地启动脚本/Node测试包含正确，参考仓库、实验数据、私钥、artifacts排除检查通过。

## 清理与后续

r8 supervisor4314经精确PID/cmdline核验后SIGINT停止；六子进程全部exit0，journal error=null/writer_stopped=true，8445/8446关闭、任务锁释放，扫描无本项目网关或IK子进程残留。run `~/robot-infra/runs/20261018T120845Z_78c23da9` 中保留stack-ended.json和episode/journal-summary.json。两份incomplete、三份discarded及本次saved均保留；后续skip会跳过占用编号，不删除旧数据。

稳定入口 `~/robot-infra/bin/robot-infra collect` 可在机器人本机终端运行，操作见[采集手册](../episode-collection.md)。下一步是重复任务采集/长时间时序验证、任务标签与训练导出，再接真实策略。旧头显帧停顿的唯一根因未定位；本次通过不等于网络故障永久消失。深度、其他分辨率、曝光同步、外部TCP精度和任务成功率均未因此取得验证。
