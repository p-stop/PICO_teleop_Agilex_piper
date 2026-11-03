# 参考源码审计与新双Piper实验台验证准备

日期：2026-10-16。状态：complete（本轮审计、计划与盘点工具；M2运行时及现场验证未实施）。范围：只读检查relevant-repo、本项目实现和一手资料，更新设计/场景/下一切片与现场工作清单；不执行上游脚本或真实硬件命令。

## 目标

识别已有14份参考仓库中可借鉴的具体边界和缺口，新增A4-S：A4的静态双臂子集，双Piper+夹爪、双D435腕部、D435/D435i/D455固定、PICO首选/Quest3备选、Ubuntu24.04。按用户需求置于A1/A2前，保留A1–A6 ID；A4完整场景的底盘和协调控制另验。

## 基线

- 已读AGENTS、onboarding、project-status、架构验收/边界、开发流程与ADR-0005。
- M1仅固定fake，不能以改配置方式启用真实Piper；缺多执行端、后台watchdog、VR、IK/标定、相机及实际设备adapter。
- relevant-repo中的源码为参考，不导入运行、不改变第三方文件；下载代码不代表构建或硬件兼容验证。
- 用户确认主机已可分别控制两台Piper+夹爪；PICO型号待补，Quest3可能不可用；固定相机需适配三型号、实际装机型号待定；先遥操数采，再策略推理。已有控制能力为用户报告，不是本项目验证证据；用户稍后提供机器资料。

## 步骤

1. 记录本地仓库身份/版本或无Git信息状态，检查与A4-S/A1/A2直接有关的README和代码。
2. 补查缺少的PICO/Quest输入、IK、RealSense ROS wrapper、数据/推理适配等官方来源，区分必须/后续/可替代参考。
3. 更新架构/状态/入口中的A4-S与优先级；维持M1实际支持范围。
4. 制定M2最小实现计划和A4-S/A1/A2按static/fake/sim/read-only/physical逐级验证、现场盘点和证据要求。
5. 检查文档链接/一致性。只有改变可执行代码时才运行受影响功能测试；文档不能算作硬件验证。
6. 准备只读主机盘点脚本（stdlib、不导入SDK、不启用CAN/机器人、不启动相机）和相应测试，供三台主机回收环境信息；本机执行不代替Linux验证。

## 交付与接续

- 架构v0.6、ADR-0006、参考索引、M2计划与现场手册已更新。没有复制、安装或运行第三方控制程序。
- 新增主机盘点脚本及6项测试；2026-10-16 Windows/Python3.11.12全套86项通过，JUnit证据在artifacts/2026-10-16-pytest.xml。原M1核心/契约未修改。
- Linux命令分支仅用fake测试；Python3.8+目标和Linux运行尚未实机验证。现场相机、VR、CAN和物理控制均not_run。
- Windows CLI盘点smoke生成artifacts/preflight/windows-a4s-inventory.json，Linux探测如预期为not_applicable；28份项目Markdown、111个内部文件链接及代码围栏检查零问题，见artifacts/2026-10-16-doc-check.json（不包含第三方文档审计）。
- 下一任务从plans/002-a4s-teleop-acquisition.md的M2.1–M2.2多端点fake开始；现场M2.0可由用户收集资料。未知PICO型号、实际驱动版本/固件与安装外参不能自行补全。
