from dataclasses import dataclass, asdict
from typing import Dict


@dataclass
class RobotPose:
    x: int
    y: int
    direction: str = "N"


@dataclass
class SensorReading:
    temperature: float
    gas: float
    vibration: float
    inclination: float
    battery: float
    obstacle_distance: float
    victim_signal: float


@dataclass
class PerceivedState:
    x: int
    y: int
    direction: str
    risk_score: float
    risk_level: str
    battery_level: str
    obstacle_level: str
    victim_detected: bool
    visited_ratio: float

    def to_dict(self) -> Dict:
        return asdict(self)
