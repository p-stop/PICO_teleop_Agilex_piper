# 011：可替换图像存储后端与 MP4 episode

2026-10-18，complete（软件及离线验证；实时MP4采集未验）。用户明确要求新增贴近LeRobot v3的视频保存选项，保持模块化、通用化。

范围：独立图像存储接口，raw_mcap默认兼容，mp4以PyAV/FFmpeg编码任意具名RGB流；控制事件仍入小型MCAP、深度保持原始格式。沿用独立有界磁盘线程和同一episode保存/丢弃事务，不改机器人/VR控制。MP4不是完整LeRobot v3导出，不创建Parquet/训练动作映射。

设计：新real-episode/2仅用于视频模式，旧real-episode/1 reader保持兼容；逐帧记录原始时间/接收时间、图像metadata与视频frame_index/PTS映射。视频按收到的帧构造dense CFR，不补帧或篡改源时间；源掉帧仍由QC报告。配置/CLI选择后端，编码器、像素格式、选项、GOP与线程数配置化，不包含左/右臂或相机型号假设。

验收：真实编码/解码、不同相机名/RGB与BGR/行padding/原生深度、时间索引、MP4 hash/帧数/PTS与QC；缺依赖/无效参数在设备启动前失败；编码/flush失败不保存成功；有界队列不阻塞控制；保存/X丢弃/覆盖完整文件组；raw回归与CLI/配置验证。Windows和Ubuntu无硬件测试分开报告，不进行真机实验。

参考：PyAV官方编码flush/close与容器API，LeRobot官方video encoding/streaming/v3文档。只复用编码依赖，不引入训练框架到核心。

## checkpoint

实现完成：image_storage协议/raw与MP4工厂、EpisodeWriter公共事件/索引、media_qc离线检查、v2/旧v1 reader、CLI选择/配置、预检、HUD模式提示。PyAV16.1为optional mp4 extra，原始与深度不引入有损编码。原始数据没有变更。

Windows235通过/9skip、Ubuntu247通过，Node2/语法通过。测试归档 `011-source.zip` SHA256 `d6fb8d63f0870ea5daaf24f12508fa8d1c9abd3851db14d124ccb37aa02d303b`，隔离源码 `releases/011-20261018-mp4-test`；项目隔离依赖 `python-deps-mp4` 来自锁定Linuxwheel，未修改系统包。初次回归测试错误地假设FFV1不能进MP4，已按实际库能力改为确实不支持的rawvideo，软件不硬编码该错误限制。

机器人无设备离线复用原始episode2：输出 `runs/011-offline-reencode`，原MCAP2,182,403,012bytes→视频4,176,429bytes＋事件MCAP14,089,005bytes，整个文件组20,445,574bytes；26.179秒源、编码及普通收尾9.453秒，785/784/784帧全部保留，deep/QC通过。工具源码树SHA256 `eb6c03fe15a7dbc3cf553cae89186aabd15c65fceb4a3b2561c2bf28f2926760`。派生manifest标注来源，未写回原始episode；不是实时性能或训练质量验证。

最终Windows236通过/9skip、Ubuntu248通过，新增活动录制close排空/incomplete保留/锁释放测试，补齐缺视频和不同流帧率验证。最终源树SHA256 `08c1244735ad1042d0346f7fe8d1fd320e7ebf876a3105a33b0ddb7fb2d7f546`；最终源码在 `releases/011-20261018-mp4-final`，同源码deep QC复验通过。构建wheel/sdist已通过。最终部署快照为 `releases/011-20261018-mp4-validated`，保持会话默认raw；以安装后的raw/mp4静态检查及release-manifest为部署依据。不做物理实验。

部署已完成：`current` 从010切到上述011 validated快照，归档SHA256 `623467498528419219531fe8a8095501aeaf1bd328763209a4fec8d97162ad96`。deployment仅追加隔离的`python-deps-mp4`，原配置备份为`deployment.pre-011.json`；默认相机/录制配置及设备入口hash不变。安装后的raw_mcap/mp4 `collect --check-only`均返回`passed_without_device_construction`，8445/8446均未启动。收据在机器人`offline-deployment-011.json`及`release-manifest.json`。下次现场只验证显式MP4完整session，不把离线编码吞吐当作实时结论。
