# Actualización: control anti-bucles del agente autónomo

Esta actualización mejora el agente Q-Learning nivel 1 para evitar comportamientos repetitivos.

## Problema detectado

Durante la evaluación, el robot podía quedar atrapado en patrones como:

```text
AVANZAR
AVANZAR
AVANZAR
```

contra un obstáculo, o:

```text
ESCANEAR
ESCANEAR
ESCANEAR
```

sin obtener nueva información.

## Solución aplicada

Se agregaron dos mejoras:

1. Penalización por repetición y estancamiento en `reward_function.py`.
2. Bloqueo temporal de acciones inútiles en `mission_runner.py` y `q_learning_agent.py`.

Esto no hardcodea escenarios. Es una regla general de seguridad y aprendizaje:

```text
Si una acción falla muchas veces en la misma posición, se bloquea temporalmente.
El agente debe elegir otra acción disponible.
```

## Archivos modificados

```text
app/autonomous/q_learning_agent.py
app/autonomous/reward_function.py
app/autonomous/experience_memory.py
app/autonomous/mission_runner.py
tests/test_autonomous_agent.py
```

## Cómo probar

```bash
pytest tests/test_autonomous_agent.py
```

## Entrenar nuevamente

Recomendado borrar o apartar la Q-table anterior, porque fue entrenada con la recompensa vieja:

```bash
mv models/autonomous/q_table.json models/autonomous/q_table_v1_backup.json
```

Luego ejecutar:

```bash
python scripts/run_autonomous_learning_mission.py --episodes 100 --max-steps 120
```

Después evaluar:

```bash
python scripts/run_autonomous_learning_mission.py --episodes 10 --max-steps 120 --eval
```

## Qué mirar

En consola ahora pueden aparecer acciones bloqueadas:

```text
bloqueadas=AVANZAR
```

En `experience_log.csv` se agregaron columnas:

```text
blocked_actions
repeated_action_count
same_position_count
```

Estas columnas permiten justificar que el robot detecta estancamiento y adapta su comportamiento.
