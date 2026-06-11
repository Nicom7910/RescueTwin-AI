from setuptools import setup
import os
from glob import glob

package_name = 'rescuetwin_sim'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.world')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='rescuetwin',
    maintainer_email='rescuetwin@example.com',
    description='Simulación ROS/Gazebo para RescueTwin AI',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
    'console_scripts': [
        'motion_node = rescuetwin_sim.motion_node:main',
        'sensor_sim_node = rescuetwin_sim.sensor_sim_node:main',
        'risk_ai_node = rescuetwin_sim.risk_ai_node:main',
        'decision_node = rescuetwin_sim.decision_node:main',
        'mission_logger_node = rescuetwin_sim.mission_logger_node:main',
    ],
},
)