# Source this: ROS + PICO-ACT venv for lerobot commands (bi_piper_ros plugin).
# Do not add python-deps-webrtc-021 to PYTHONPATH here (its av 16.1 conflicts with lerobot's av 15.1).
source /opt/ros/jazzy/setup.bash
source /home/ros/ros2_ws/install/setup.bash
source /home/ros/zero-wam/PICO-ACT/.venv/bin/activate
