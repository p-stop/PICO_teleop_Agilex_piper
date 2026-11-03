from dataclasses import dataclass

from lerobot.robots.config import RobotConfig

PICO_ROOT = "/home/ros/zero-wam/PICO-ACT"


@RobotConfig.register_subclass("bi_piper_ros")
@dataclass
class BiPiperROSConfig(RobotConfig):
    """Dual Piper through the audited ROS driver wrapper and the robot_infra LiveGateway.

    Paths default to the PICO-ACT collection profile so replay/record use the same
    drivers, CAN ports, cameras, URDF and safety checks as 023 collect.
    """
    pico_root: str = PICO_ROOT
    deployment: str = PICO_ROOT + "/profiles/collection/deployment.json"
    # robot_infra code used in-process (gateway, model, journal) and by the driver children.
    robot_infra_src: str = PICO_ROOT + "/releases/023-20261103-webrtc-smoothing/src"
    output_root: str = PICO_ROOT + "/runs"
    # "ros": real stack. "fake": no ROS, no hardware; simulated arms and black frames.
    backend: str = "ros"
    # Start the 2 drivers + 3 RealSense nodes as children (False: attach to an already running stack).
    launch_stack: bool = True
    cameras_enabled: bool = True
    # dry_run: drivers/cameras run, feedback is read, the tracker runs, but nothing is enabled or published.
    dry_run: bool = False
    home_on_connect: bool = True
    selftest_timeout_s: float = 40.0
    # Interpolation (b): second-order tracker between lerobot actions and the gateway.
    tracker_hz: float = 100.0
    tracker_time_constant_s: float = 0.08
    tracker_max_velocity_rad_s: float = 0.8
    tracker_max_acceleration_rad_s2: float = 4.0
    # First action farther than this from the current command is reached by a blocking smooth move.
    first_action_tolerance_rad: float = 0.03
    approach_peak_velocity_rad_s: float = 0.3
    approach_settle_tolerance_rad: float = 0.05
    approach_timeout_s: float = 30.0
    # No new action for this long: stop renewing ownership -> gateway measured hold.
    action_timeout_s: float = 1.0
    max_image_age_s: float = 0.5
    gripper_resend_threshold_m: float = 0.0005
    gripper_refresh_s: float = 0.5
