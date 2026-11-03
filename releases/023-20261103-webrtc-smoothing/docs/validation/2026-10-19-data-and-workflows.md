# 2026-10-19数据与工作流切片验证

范围：计划013；无硬件命令。已连接192.168.87.126，用旧可信主机密钥核验；没有改SSH配置/known_hosts，没有启驱动、相机、轨迹或策略。

## 真实文件审计

new_test三集源码身份012；episode0/1已保存且capture QC/deep通过，episode2为review未保存、唯一QC问题为固定RGB197.477ms间隔，deep通过。三集无depth，四个末端流实存。旧sidecar hash核对不变。派生报告在`~/robot-infra/runs/013-audit-20261019`，本地副本`artifacts/validation/013-data`。

服务器日志显示第二集RTT557.7ms；第三集结束后client_event上报836.4ms和stale ticket；相机空洞附近metadata帧9439…9445连续。根因无法唯一归到Wi-Fi、Image传输或门控。旧session journal约494.6MB，未触及但接近512MiB上限。报告区分明确的文件完整性、capture质量、控制响应与任务质量。

## 新软件验证

- Windows Python3.11：261通过、10跳过（Linux Bash/Pinocchio/ROS环境缺失）；Ubuntu24.04 Python3.12/Jazzy：274通过，包含实际ROS localhost回环，无物理设备。
- Node两项传输行为测试通过。新增ACK计时字段为可选加法字段。
- 新用例覆盖原始文件只读deep audit、因果state/图像采样、夹爪闭合目标与受阻实测值区分、未确认命令排除、journal初始目标、unknown掩码、深度缺失/scale未知、关节顺序、质量准入、三图连边/encoding检查、离线时间线、分段日志事件/hash保全、显式容量错误与同FPS突发交付不丢帧。
- 训练视图实际生成：episode0 1858行/740行完整有效，episode1 1724行/1722行有效，位于`runs/013-training-views`。episode0早段夹爪目标无证据，按unknown处理，未用反馈补标签。轨迹计划分别10509/8687条具名目标，未执行。

软件测试源码树SHA256 `0b366dade00cbfbb6048dd85c979ac86d5a423daf4ec429b29e9dec8cc43cf91`；归档`013-software.zip` SHA256 `c275023538a4bac2dbaf23987fdaa0d46ad65176757ca4f5d14de19a86f5f345`。Ubuntu隔离测试目录`releases/013-20261019-software-test`，收据`offline-tests-013.json`。

## 验证边界

新诊断分段、初始目标快照、ACK计时、同FPS记录改进尚未在新一次真机session验证；旧数据只能证明012实采情况。三图是静态计划，trajectory是离线计划；物理graph runner、真实轨迹重放、GPU模型桥接、LeRobot v3 writer未实现。任务文本/成功失败为用户确认的待人工标注；不能以740/1722有效行报告模型训练或任务成功率。

软件已部署到`releases/013-20261019-workflows-validated`，`current`已切换；旧012与配置备份保留。raw_mcap/mp4两种collect --check-only及三图静态计划全部通过，8445/8446仍关闭。最终快照SHA256 `590a3724194cdad1895ff812e6eb7a8a95e2e06d527f425b19cc349d55d3cf78`；离线wheel/sdist构建及内容排除检查通过。收据为本地`artifacts/preflight/013-package-validation.json`、`offline-deployment-013.json`、`offline-tests-013.json`，远端根目录亦保留部署收据。原始数据、未完成第三集及会话日志未改动。
