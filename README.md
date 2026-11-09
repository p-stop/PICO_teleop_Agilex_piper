# PICO_teleop_Agilex_piper
# 代码结构
## tasks
脚本入口
## profiles
配置文件，包含相机配置、VR遥操配置以及映射、网络通信配置、本机路径配置。
## plugins
封装的lerobot插件，将真机和遥操设备注册到lerobot框架中。
### `pyproject.toml`  `__init__.py`
包名称，封装的python包可以被发现和注册。
### `config_bi_piper_ros.py`
一个lerobot定义的配置类，存储该任务的配置信息
### `bi_piper_ros.py`
统筹相机、机械臂与网关的核心代码