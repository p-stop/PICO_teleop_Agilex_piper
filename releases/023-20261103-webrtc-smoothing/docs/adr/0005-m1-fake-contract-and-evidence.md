# ADR-0005：M1的最小契约、fake运行与MCAP证据

日期：2026-10-15。状态：已实现并通过本机Windows fake验证；不构成物理控制准入。

## 决定

- 包名robot-infra，导入名robot_infra，Python最低声明3.11；本次实际验证3.11.12。setuptools构建，uv.lock固定依赖；JSON Schema Draft 2020-12由jsonschema验证，MCAP由官方mcap库读写。
- 实现契约版本为`0.3.0-m1`，表示历史拟议v0.3的实验性子集，不声称覆盖完整v0.3。未知版本、额外字段、不受支持节点/边均拒绝；历史v0.2示例不可直接运行，无自动迁移器。
- 图仅支持7种节点各一个的固定M1拓扑：fake遥操/stub策略→显式identity mapper→guard→fake机器人，机器人采样反馈至guard/recorder，fake相机至recorder。可变节点ID不改变固定角色。它不是通用插件发现或任意图执行器。
- 资产为两关节fake臂，显式rad、fake_base、joint_a/joint_b、限位；合成front相机仅2×2 RGB。默认动作周期20ms、状态年龄60ms、动作年龄100ms、lease TTL 5s，全部是fake测试参数。不是实机阈值或真实标定。
- 采用单线程session与ManualClock，以受控结果完成队列模拟延迟；支持一个in-flight请求、native双动作chunk和设备侧权威队列。无异步网络/GPU、TE/RTC/IK或自动规划。
- 人工接管、release、stop、reset、fault撤销lease并更换epoch/清空队列；迟到结果拒绝。lease过期成为fault，需要reset/start再申请。fake token可预测，只用于进程内逻辑测试，不是分布式认证/安全凭据。
- 只有guard的私有writer capability能调用fake机器人执行方法；Python对象不是对恶意同进程代码的安全隔离。SDK、总线、socket、物理控制入口均不存在。
- MCAP JSON事件分别保存意图、映射、guard、命令、receipt、反馈、观测、快照、策略请求/输出和chunk；命令必须关联最终guard，receipt/反馈关联实际命令。fake同步执行才标executed。
- 拒绝的NaN/±Inf用`{"non_finite":"nan/inf/-inf"}`标签保存，输出仍为合法JSON；不能将标签重新解码成可执行动作。
- finalize记录事件数量及规范化时间线SHA256；回放使用CRC、schema、序号/时间/epoch、最终hash和执行关联检查。MCAP schema随wheel打包；独立官方读取器也需能读取。
- 回放只返回验证后的事件，不创建session或设备。输出采用exclusive create，拒绝覆盖已有证据；缺失footer/finalize或损坏记录失败，不输出部分成功JSONL。可正常finalize的fault episode标aborted；异常中断留下不完整文件，M1不提供损坏文件修复。

## 后果与限制

先验证所有权、时序和证据的可组合性，避免SDK/网络/模型依赖掩盖设计错误。代价是固定拓扑、内存中保存整个小型episode、JSON图像、缓冲MCAP写入及手动tick；不提供崩溃耐久保证、后台watchdog、连续心跳/欠载停机、物理动力学/碰撞/速度加速度安全或真实传感器对齐。

后续Linux、MuJoCo、分布式adapter与物理设备必须分别验证；尤其不能把M1的fake stop、TTL或同步executed直接用于真实控制。新增节点/动作/模式需要扩展schema、适配消费方及测试，而非修改mode绕过预检。

官方API依据：[MCAP writer](https://mcap.dev/docs/python/mcap-apidoc/mcap.writer)、[MCAP reader](https://mcap.dev/docs/python/mcap-apidoc/mcap.reader)。实现与测试结果见[验证报告](../validation/2026-10-15-m1-windows.md)。
