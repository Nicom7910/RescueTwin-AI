from enum import Enum


class RobotAction(str, Enum):
    AVANZAR = "AVANZAR"
    GIRAR_IZQUIERDA = "GIRAR_IZQUIERDA"
    GIRAR_DERECHA = "GIRAR_DERECHA"
    RETROCEDER = "RETROCEDER"
    ESCANEAR = "ESCANEAR"
    ENVIAR_ALERTA = "ENVIAR_ALERTA"
    VOLVER_BASE = "VOLVER_BASE"


ACTIONS = [action.value for action in RobotAction]
