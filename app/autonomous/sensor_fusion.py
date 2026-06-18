from app.autonomous.state import PerceivedState, RobotPose, SensorReading


class SensorFusion:
    """
    Convierte sensores crudos en un estado simplificado para el agente.

    Esta capa no decide acciones. Solo resume percepción:
    - riesgo estimado
    - nivel de batería
    - cercanía de obstáculos
    - posible detección de víctima
    """

    def build_state(self, pose: RobotPose, reading: SensorReading, visited_ratio: float) -> PerceivedState:
        risk_score = self.estimate_risk(reading)

        return PerceivedState(
            x=pose.x,
            y=pose.y,
            direction=pose.direction,
            risk_score=risk_score,
            risk_level=self._risk_level(risk_score),
            battery_level=self._battery_level(reading.battery),
            obstacle_level=self._obstacle_level(reading.obstacle_distance),
            victim_detected=reading.victim_signal >= 0.70,
            visited_ratio=visited_ratio,
        )

    def estimate_risk(self, reading: SensorReading) -> float:
        temp_score = min(1.0, max(0.0, (reading.temperature - 20) / 40))
        gas_score = min(1.0, reading.gas / 280)
        vibration_score = min(1.0, reading.vibration)
        inclination_score = min(1.0, reading.inclination / 25)
        obstacle_score = max(0.0, 1.0 - reading.obstacle_distance / 5)
        battery_risk = max(0.0, 1.0 - reading.battery / 100)

        risk = (
            0.20 * temp_score
            + 0.25 * gas_score
            + 0.20 * vibration_score
            + 0.15 * inclination_score
            + 0.10 * obstacle_score
            + 0.10 * battery_risk
        )

        return round(min(1.0, max(0.0, risk)), 3)

    def _risk_level(self, risk_score: float) -> str:
        if risk_score < 0.35:
            return "BAJO"
        if risk_score < 0.65:
            return "MEDIO"
        return "ALTO"

    def _battery_level(self, battery: float) -> str:
        if battery >= 60:
            return "ALTA"
        if battery >= 30:
            return "MEDIA"
        return "BAJA"

    def _obstacle_level(self, obstacle_distance: float) -> str:
        if obstacle_distance <= 1.2:
            return "CERCA"
        if obstacle_distance <= 3.0:
            return "MEDIA"
        return "LEJOS"
