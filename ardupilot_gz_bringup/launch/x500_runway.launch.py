# Copyright 2023 ArduPilot.org.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Launch an x500 quadcopter in Gazebo and Rviz."""
import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.actions import OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution

from launch_ros.actions import Node


def _launch_gzebo_server(context, pkg_ros_gz_sim, pkg_project_gazebo):
    """Start the Gazebo server with the requested world.

    The "world" launch argument has to be resolved here rather than being
    interpolated into "gz_args" directly: that argument ends up in a shell
    command, so a LaunchConfiguration object would be printed as its repr
    instead of the path.
    """
    world = LaunchConfiguration("world").perform(context)

    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                f'{Path(pkg_ros_gz_sim) / "launch" / "gz_sim.launch.py"}'
            ),
            launch_arguments={"gz_args": f"-v4 -s -r {world}"}.items(),
        )
    ]


def generate_launch_description():
    """Generate a launch description for a x500 quadcopter."""
    pkg_project_bringup = get_package_share_directory("ardupilot_gz_bringup")
    pkg_project_gazebo = get_package_share_directory("ardupilot_gz_gazebo")
    pkg_ros_gz_sim = get_package_share_directory("ros_gz_sim")
    pkg_ardupilot_sitl = get_package_share_directory("ardupilot_sitl")
    pkg_ardupilot_gazebo = get_package_share_directory("ardupilot_gazebo")

    # The default parameter set has to be repeated here, because an empty
    # launch argument would override the default of x500.launch.py with an
    # empty string.  SITL accepts a comma separated list of files and
    # applies them in order, so the last one wins.
    default_params = (
        os.path.join(
            pkg_ardupilot_sitl,
            "config",
            "default_params",
            "copter.parm",
        )
        + ","
        + os.path.join(
            pkg_ardupilot_gazebo,
            "config",
            "gazebo-x500.parm",
        )
    )

    # X500.
    robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                PathJoinSubstitution(
                    [
                        pkg_project_bringup,
                        "launch",
                        "robots",
                        "x500.launch.py",
                    ]
                ),
            ]
        ),
        launch_arguments={
            # Spawn position of the vehicle.
            "x": LaunchConfiguration("x"),
            "y": LaunchConfiguration("y"),
            "z": LaunchConfiguration("z"),
            "R": LaunchConfiguration("R"),
            "P": LaunchConfiguration("P"),
            "Y": LaunchConfiguration("Y"),
            # SITL parameter file(s), comma separated.
            "defaults": LaunchConfiguration("defaults"),
            # MAVROS can be switched off when only a GCS is needed.
            "use_mavros": LaunchConfiguration("use_mavros"),
            # The name of the Gazebo world.  It has to match the <world
            # name="..."> in the SDF file, because the bridge subscribes to
            # /world/<world_name>/model/<robot_name>/joint_state.
            "world_name": LaunchConfiguration("world_name"),
            # Extra serial ports for SITL, e.g. SERIAL1 for the Pozyx
            # beacon protocol.
            **{
                f"serial{label}": LaunchConfiguration(f"serial{label}")
                for label in range(10)
            },
        }.items(),
        condition=IfCondition(LaunchConfiguration("spawn_robot")),
    )

    # Gazebo.
    # The world is selected with the "world" launch argument, which is a
    # full path.  "gz sim -s" looks for a file of that name and does not
    # search the world's share directory recursively, so a bare file name
    # would not be found.
    #
    # The path is resolved with an OpaqueFunction because "gz_args" is
    # concatenated into a shell command; passing a LaunchConfiguration
    # object there would print its repr instead of the path.
    gz_sim_server = OpaqueFunction(
        function=_launch_gzebo_server,
        args=[pkg_ros_gz_sim, pkg_project_gazebo],
        condition=IfCondition(LaunchConfiguration("use_gz_sim_server")),
    )

    gz_sim_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f'{Path(pkg_ros_gz_sim) / "launch" / "gz_sim.launch.py"}'
        ),
        launch_arguments={"gz_args": "-v4 -g"}.items(),
        condition=IfCondition(LaunchConfiguration("use_gz_sim_gui")),
    )

    # RViz.
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        namespace="x500",
        arguments=["-d", f'{Path(pkg_project_bringup) / "rviz" / "x500.rviz"}'],
        condition=IfCondition(LaunchConfiguration("rviz")),
        remappings=[
            ("/tf", "tf"),
            ("/tf_static", "tf_static"),
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_gz_sim_server",
                default_value="true",
                description="Run the Gazebo server.",
            ),
            DeclareLaunchArgument(
                "world",
                default_value=f'{Path(pkg_project_gazebo) / "worlds" / "runway.sdf"}',
                description="Full path to the SDF world file to load.",
            ),
            DeclareLaunchArgument(
                "use_gz_sim_gui",
                default_value="true",
                description="Run the Gazebo GUI.",
            ),
            DeclareLaunchArgument(
                "spawn_robot",
                default_value="true",
                description="Spawn the robot and start SITL+ROS.",
            ),
            DeclareLaunchArgument(
                "rviz", default_value="true", description="Open RViz."
            ),
            DeclareLaunchArgument(
                "x",
                default_value="0.0",
                description="The initial 'x' position of the vehicle (m).",
            ),
            DeclareLaunchArgument(
                "y",
                default_value="0.0",
                description="The initial 'y' position of the vehicle (m).",
            ),
            DeclareLaunchArgument(
                "z",
                default_value="0.2",
                description="The initial 'z' position of the vehicle (m).",
            ),
            DeclareLaunchArgument(
                "R",
                default_value="0.0",
                description="The initial roll angle (radians).",
            ),
            DeclareLaunchArgument(
                "P",
                default_value="0.0",
                description="The initial pitch angle (radians).",
            ),
            DeclareLaunchArgument(
                "Y",
                default_value="0.0",
                description="The initial yaw angle (radians).",
            ),
            DeclareLaunchArgument(
                "defaults",
                default_value=default_params,
                description=(
                    "Comma separated SITL parameter files.  The last file "
                    "wins for any parameter that appears in more than one."
                ),
            ),
            DeclareLaunchArgument(
                "use_mavros",
                default_value="true",
                description="If True launch MAVROS.",
            ),
            DeclareLaunchArgument(
                "world_name",
                default_value="runway",
                description=(
                    "Name of the Gazebo world.  Must match the <world "
                    "name=\"...\"> attribute of the loaded SDF file."
                ),
            ),
            # Extra serial ports for SITL, e.g. SERIAL1 for the Pozyx beacon
            # protocol.  Empty means the port stays closed.
            *[
                DeclareLaunchArgument(
                    f"serial{label}",
                    default_value="",
                    description=f"Device string for SITL SERIAL{label}.",
                )
                for label in range(10)
            ],
            gz_sim_server,
            gz_sim_gui,
            robot,
            rviz,
        ]
    )
