# ADR0013：可替换图像后端与外部MP4文件组

2026-10-18，已接受并实现；无硬件测试与既有数据离线重编码通过，实时MP4采集未验证。

用户要求提供MP4保存选项并保持模块化、通用化。将图像持久化从episode写入器拆为 `ImageStorage` 协议（frame/finish/abort），现有 `RawMCAPStorage` 与 `MP4Storage` 由工厂选择；backend只接收具名流/图像metadata/bytes/目标profile，不认识机器人、ROS、VR、左右臂或相机型号。`EpisodeWriter` 负责共同的事件MCAP、索引、manifest、QC；`EpisodeRecorder` 继续管理有界队列和保存/丢弃事务。

默认raw_mcap维持real-episode/1与原始图像通道；MP4使用real-episode/2、MCAP profile robot-infra-real-episode/2与JSON的robot-infra-video-frame/1引用。旧reader明确不支持v2，更新reader兼容v1/v2。real-episode-config/1增加可选storage字段，旧配置默认为raw_mcap；原M1/fake协议不变。CLI可覆盖backend，编码器/像素格式/options/GOP/线程数在配置中声明。

RGB采用可选PyAV16.1/FFmpeg，不引入LeRobot/PyTorch到核心。实际编码与文件I/O只在原有独立磁盘worker执行，编码器可用内部线程；控制/采样只入有界队列。编码阻塞导致队列溢出时保留错误并中止，不能静默丢帧后标成功。依赖、配置和MP4 muxer兼容性在启动设备前用内存容器检查，实际视频关闭时flush编码器和封装尾部，失败保留incomplete。

视频路径由流名hash生成，与机器人角色无关；manifest.media记录名称对应、编码、尺寸/FPS、帧数、bytes/hash。每条引用与index同时保留frame_index/PTS/time_base，MCAP引用保留完整源图像metadata（含stride、编码、resize与原始/接收时间）。视频采用dense CFR，PTS为帧序号/FPS，不插帧、不覆盖源时间；缺帧和真实时间间隙仍由原始索引QC判定。深度保持原始位深/字节序，继续进MCAP，不套用RGB有损编码。

A保存/X丢弃/覆盖以整个episode目录为单位，事件、视频和索引共同提交/保留。普通QC检查视频文件、header、帧数与索引一致性；deep另验视频hash、全帧解码/PTS以及MCAP与索引引用一致性。文件缺失、越界路径、编码/flush失败不算成功；QC模块保持无设备依赖。

该结构是接近LeRobot v3的视频与时间索引中间格式，不是完整LeRobot v3。Parquet动作/状态映射、任务/statistics、多episode分片仍留给独立导出模块，避免训练格式侵入驱动和控制。

验证依据：[计划011](../../plans/011-pluggable-image-storage.md)与[无硬件报告](../validation/2026-10-18-mp4-storage.md)。编码API复用[PyAV官方](https://pyav.org/docs/stable/cookbook/numpy.html)，格式衔接参考[LeRobot v3](https://huggingface.co/docs/lerobot/en/lerobot-dataset-v3)。
