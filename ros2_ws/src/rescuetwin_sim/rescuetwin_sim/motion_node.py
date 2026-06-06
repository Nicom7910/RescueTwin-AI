import math

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import String


class MotionNode(Node):
    def __init__(self):
        super().__init__("motion_node")

        self.x = -4.0
        self.y = 0.0
        self.theta = 0.0

        self.linear_velocity = 0.0
        self.angular_velocity = 0.0

        self.last_time = self.get_clock().now()

        self.cmd_sub = self.create_subscription(
            Twist,
            "/robot/cmd_vel",
            self.cmd_callback,
            10
        )

        self.pose_pub = self.create_publisher(
            Odometry,
            "/robot/pose",
            10
        )

        self.status_pub = self.create_publisher(
            String,
            "/robot/status",
            10
        )

        self.timer = self.create_timer(0.1, self.update_motion)

        self.get_logger().info("Motion Node iniciado. Esperando comandos en /robot/cmd_vel")

    def cmd_callback(self, msg):
        self.linear_velocity = msg.linear.x
        self.angular_velocity = msg.angular.z

    def update_motion(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        self.theta += self.angular_velocity * dt
        self.x += self.linear_velocity * math.cos(self.theta) * dt
        self.y += self.linear_velocity * math.sin(self.theta) * dt

        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = "world"
        odom.child_frame_id = "base_link"

        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.45

        odom.twist.twist.linear.x = self.linear_velocity
        odom.twist.twist.angular.z = self.angular_velocity

        self.pose_pub.publish(odom)

        status = String()
        status.data = (
            f"Robot simulado | x={self.x:.2f}, y={self.y:.2f}, "
            f"theta={self.theta:.2f}, v={self.linear_velocity:.2f}, "
            f"w={self.angular_velocity:.2f}"
        )

        self.status_pub.publish(status)


def main(args=None):
    rclpy.init(args=args)
    node = MotionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
