# RescueTwin AI

## Gemelo digital de un robot cuadrúpedo para rescate en derrumbes

RescueTwin AI es un proyecto de Ciencia de Datos que propone el desarrollo de un gemelo digital para un robot cuadrúpedo utilizado en operaciones de rescate urbano, especialmente en zonas de derrumbe.

El sistema utiliza datos de sensores ambientales, químicos, estructurales y operativos para predecir el nivel de riesgo de una zona y recomendar una acción operativa para el robot.

---

## Objetivo del proyecto

El objetivo principal es construir un modelo predictivo capaz de clasificar el nivel de riesgo operativo de una zona de derrumbe a partir de datos de sensores simulados e integrados desde distintas fuentes públicas.

La salida del sistema permite indicar si el robot debe:

- Avanzar.
- Avanzar con precaución.
- Cambiar de ruta.
- Detenerse.
- Enviar una alerta al equipo de rescate.

---

## Problemática

En situaciones de derrumbe, enviar personal humano a inspeccionar una zona puede representar un riesgo elevado. Pueden existir obstáculos, vibraciones estructurales, gases peligrosos, baja visibilidad, falta de comunicación o posibles nuevos colapsos.

Un robot cuadrúpedo puede ingresar primero, recolectar datos del entorno y enviar información al equipo de rescate. A partir de esos datos, el gemelo digital permite tomar decisiones más seguras y basadas en información.

---

## Hipótesis

A partir de datos de sensores ambientales, estructurales y operativos de un robot cuadrúpedo, es posible predecir el nivel de riesgo de una zona de derrumbe y recomendar acciones que reduzcan la exposición del personal de rescate.

---

## Dominio del negocio

El proyecto se ubica dentro del dominio de:

**Robótica aplicada a emergencias, rescate urbano y seguridad operativa.**

Posibles usuarios o clientes:

- Bomberos.
- Defensa Civil.
- Equipos de búsqueda y rescate.
- Municipios.
- Empresas industriales.
- Mineras.
- Organismos de respuesta ante catástrofes.

---

## Propuesta de valor

RescueTwin AI aporta valor porque permite:

- Reducir la exposición humana en zonas peligrosas.
- Tomar decisiones basadas en datos.
- Priorizar zonas de búsqueda.
- Detectar condiciones ambientales o estructurales críticas.
- Estimar si el robot puede continuar operando.
- Recomendar acciones operativas en tiempo real.
- Mejorar la planificación de recorridos en operaciones de rescate.

---

## Fuentes de datos utilizadas

No existe un único dataset público que represente completamente a un robot cuadrúpedo operando dentro de una zona de derrumbe. Por ese motivo, se construyó un dataset integrado a partir de varias fuentes públicas y variables simuladas coherentes con el caso de uso.

| Fuente                         | Tipo de dato                   | Uso dentro del proyecto                                                |
| ------------------------------ | ------------------------------ | ---------------------------------------------------------------------- |
| Indoor Environmental Dataset   | Sensores ambientales           | Temperatura, humedad, presión, luz, sonido, CO2 y partículas           |
| UCI Gas Sensor Dataset         | Sensores químicos              | Tipo de gas y concentración estimada                                   |
| NASA Battery Dataset Cleaned   | Datos de batería               | Batería restante, voltaje, temperatura de batería y autonomía estimada |
| SARD Search and Rescue Dataset | Imágenes de búsqueda y rescate | Referencia para simular detección de personas atrapadas                |

---

## Dataset final

El dataset final generado se encuentra en:

```text
data/processed/rescuetwin_dataset.csv
```
