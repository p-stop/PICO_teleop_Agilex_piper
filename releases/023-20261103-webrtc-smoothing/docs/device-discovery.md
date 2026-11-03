# 设备发现、识别与角色绑定

更新：2026-10-16。已实现最小被动发现；设备协议探测、运行状态订阅和真实驱动仍待实现。

## 功能定位

需要自动发现，架构原有discover/probe方向保留，但应明确四个独立步骤：

1. **枚举**：OS可见的USB、CAN、串口、视频接口。得到候选、serial/VID/PID/路径与OS状态，不打开串口或SDK。
2. **识别/描述**：厂商插件结合设备身份、已安装SDK、已有驱动描述，报告型号/固件/能力与证据。CAN适配器不等于Piper，USB可见不等于视频流可用。
3. **协议检查与状态**：按具体插件读取固件/关节/错误/流能力。有些“读取”需要发查询包或初始化，必须声明副作用；不能向所有串口广播猜测报文。运行状态由实际backend提供，不能把枚举时刻的静态元信息当实时反馈。
4. **绑定/配置**：用户将稳定设备身份绑定到left.arm.transport、right_wrist等角色；动作/帧/标定在各自profile中表达。匹配器不猜测左右、工具、夹爪单位或变换。

这四步可用于CLI、将来的配置GUI与部署预检。厂商识别规则、平台枚举、身份绑定与运行驱动分离，避免每台实验台写一份扫描脚本。

## 本轮可运行接口

```bash
# 完整安装后的统一入口
robot-infra discover --output artifacts/discovery.json
robot-infra discover --snapshot artifacts/discovery.json --bindings profiles/local/bench.json

# 尚未安装依赖时，在源码根目录也可用；只需要Python3.11+
python3 tools/discover_devices.py --output artifacts/discovery.json
python3 tools/discover_devices.py --snapshot artifacts/discovery.json --bindings configs/device-bindings.example.json
```

输出不覆盖已有文件。退出码0表示报告生成且请求的绑定满足；2是配置/文件错误；3表示绑定未就绪。无绑定参数时，退出0不证明发现完整或有设备，需查看diagnostics。Windows当前没有被动OS collector，明确报告passive_collector_unavailable；可以离线处理Linux报告。

`device-discovery/1`报告包含UTC采集时间、OS、scope、候选列表和诊断；输出外层是`{"discovery": ...}`，带绑定时另有bindings。snapshot接受原报告或该输出封套。

候选字段：candidate_id（本次kind+locator的确定性ID）、kind、locator、resource_id、identity、state、evidence、device_io=not_opened。identity允许null，不补造serial；USB身份中serial保持兼容，同时给出usb_serial与serial_namespace=usb_descriptor。这不是厂商SDK serial；例如RealSense SDK身份需独立描述并有端口关联证据，见[ADR-0008](adr/0008-independent-live-input-and-identity-namespaces.md)。保留VID/PID原值及sysfs/by-id/by-path证据。candidate_id随端口变化可能改变，稳定匹配用明确serial等选择器。

Linux collector读取/sys和/dev的目录/符号链接元信息，不打开/dev设备；枚举usb_device、can_interface、serial_port、video_interface。视频多个节点按USB物理资源分组；CAN按通道分组。串口优先展示by-id/by-path，但无唯一serial时仍可能依赖物理端口，应在profile声明这一限制。每类最多1024项，截断和权限错误写入diagnostics；这不是扫描整个网络或猜测波特率的工具。

## 模板与绑定规则

从[模板](../configs/device-bindings.example.json)复制到gitignored的profiles/local/，填入现场身份、确认后再将confirmation设为confirmed。例子中的五个角色只是一份A4-S模板；代码不限制角色数目、名称或机器人型号，不将硬件serial/IP固化到框架。

每个角色声明kind、非空精确match、confirmation，exclusive默认true。所有match字段同时成立才匹配；缺失/multiple/unconfirmed分别报告missing/ambiguous/matched_unconfirmed，不选择第一个设备。复用同一个独占resource_id报告resource_conflict；明确共享时所有相关角色都须exclusive=false。候选搜索不完整时ready=false。ready只代表身份绑定成立，不授予控制权，也不证明CAN正在运行或相机帧可读。

缺少serial时可以使用明确usb_path/by_path等选择器；工具不会静默降级到“同型号第一台”。多通道CAN共享一个serial时加通道选择器；换口/换设备后重新枚举并检查diff。逻辑上的一个物理设备可有多种能力，绑定不取代端口manifest或执行组。

## 扩展边界与后续顺序

`Collector`协议返回candidates/diagnostics；`discover(collectors=...)`支持显式注入，新增Windows枚举、受限网络目录或已有ROS描述源不需要改绑定器。仅安装插件不自动执行探测。当前尚无插件自动加载/注册CLI，新增collector先在组合入口显式接入并加fixture。

下一步优先：把发现结果接入M2具名端点/backend的预检；使用配置选择SDK或现有ROS边界；独立RealSense RGB、CAN接收与VR输入已有[有限实测](validation/2026-10-16-a4s-live-observation.md)，接着补持续记录、质量检查和统一观测入口。主动probe统一声明所需依赖、读/查询/配置副作用、超时、资源与版本，结果带来源时间和有效期；固件未知明确保留unknown。先完成A4-S需要的插件，再扩展Windows、网络和热插拔监听；不为“通用扫描”安装全部SDK或重构M1控制协议。
