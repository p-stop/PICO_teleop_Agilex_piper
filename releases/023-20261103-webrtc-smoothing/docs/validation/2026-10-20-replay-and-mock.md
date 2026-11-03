# 2026-10-20：轨迹回放与假模型验证

计划014已完成当前native短轨迹与fake推理切片。用户现场确认“双臂正常运动并停住，无异常”。证据只覆盖本次台架、片段和配置，不代表任意轨迹/机器人或真实模型部署。

已连接用户更新后的ranger-piper配置，同一可信主机密钥；旧current=013，双臂can0/can2为UP，没有8445/8446服务。已保存第二集的model hash/base/tip/关节名与当前设备配置一致。

最终软件：Windows278通过/10跳过、Ubuntu291通过（含ROS localhost，无物理设备）；新增17项workflow测试。覆盖起始对齐不动夹爪、原始时序/禁止追赶、反馈失鲜/ownership撤销/调度停顿、模型超时/错误/错epoch/空chunk/错单位/无效时间、队列耗尽、后台取消、未知初始目标/模型不匹配及HTTP真实RGB bytes传输。Ubuntu第一次隔离测试因未创建artifacts父目录产生fixture错误，补齐测试环境后通过；保留失败收据，不当成产品失败或通过证据。

源码树SHA256 `380ee1788a47160a48382610fc8826ebc6996ef4b89ec25d64eed7ef80014248`；被测试快照`014-validated.zip` SHA256 `6b36bd5ac92e817aff9e13b842a32ab728bcb408446865efea931e410fdbb88d`。部署到`~/robot-infra/releases/014-20261020-native-validated`，current已切换；旧013保留，机器session/deployment配置未改，只有新增回放profile。最终文档快照/包hash见计划014 checkpoint和release-manifest。

## 独立进程假模型

机器人`runs/014-20261020-offline`保存HTTP模型服务/客户端配置与日志。正常case为COMPLETED、190次控制命令集合，cleanup_errors=[]；模型错误case注入HTTP422，客户端为FAULT、退出码3、撤销ownership且清理无错。服务进程已退出。实际传输了三路48×64×3合成RGB及fake测量状态；模型响应包含输入像素hash、请求/epoch/观测时间、显式joint名字/frame/单位和具名chunk。

这是真实CPU进程间HTTP链路，不是GPU/ZeroWAM，不是真相机输入，不控制真机；没有测跨服务器网络延迟、VLA准确率或RTC。transport可配置in_process/http_json；model worker与执行/watchdog线程分离。

## 真机首轮

- 配置：`~/robot-infra/profiles/replay.validation014.json`；源`dataset/new_test/episodes/episode_000001`，原MCAP hash `dfee5e3847a221c7115e3aedde331f90a3d61f472958644f38507b55ee6ddfea`。
- 起始目标从前序session确认发布命令恢复：双臂六关节全0、夹爪0m。对齐阶段夹爪不动，RUNNING恢复已知夹爪目标；本片段夹爪始终闭合，没有开合变化验收。
- 对齐约4.501秒；随后原速播放0–3秒，实测RUNNING 3.000911秒。使用本机独立ROS driver，无相机进程、无VR/IK。
- 状态ALIGNING→RUNNING→COMPLETED，450次命令集合（含对齐），无guard拒绝、无清理错误；左右驱动退出码均0，现场确认无异常。
- 运行期间左右反馈各508条。关节运动范围（rad）：左`[.194466,.359521,.201897,.044517,.163747,.044081]`；右`[.192512,.411870,.333303,.030108,.035499,.030039]`，不能仅凭ROS publish声称运动。
- 原配置native速度20%未修改；播放截点最大关节目标/反馈差左.098176rad、右.051588rad。这是瞬时跟踪差，**不是精度达标结论**。COMPLETED表示源时间窗播放完毕并执行实测保持，不保证最终目标已精确到达。可后续降低source.speed或独立设计明确的终点稳定阶段，不在本轮自动延长动作。
- 停止使用新鲜反馈保持，无自动home/disable/jaw-close；原始MCAP再次hash一致。日志所有段hash一致、writer_stopped=true、error=null。

证据：远端`physical-replay-validation-014.json`、`mock-http-validation-014.json`、`offline-tests-014-final.json`，真机完整运行在`runs/replay-014-physical-01`。本地收据副本`artifacts/preflight/`。当前物理会话已退出，后续再执行需现场安排；没有对整条57秒示范、其它片段/速度、暂停续播、真机故障注入或其他机器人作支持承诺。
