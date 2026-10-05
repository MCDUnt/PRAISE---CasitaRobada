# Casita Robada

Implementación del juego de cartas **Casita Robada** como entorno multiagente, desarrollada para el **proyecto PRAISE** del grupo de investigación de la **UTN – Facultad Regional Concepción del Uruguay (UTN FRCU)**.

El juego está construido sobre el framework de agentes provisto por los profesores (agentes, sensores, actuadores, entornos simulados y *state buffers*), y permite jugar bots contra bots o con un jugador humano, en consola o con interfaz gráfica (PyGame).

---

## Tabla de contenidos

- [Reglas del juego](#-reglas-del-juego)
- [Instalación](#-instalación)
- [Cómo ejecutarlo](#-cómo-ejecutarlo)
- [Arquitectura](#-arquitectura)
- [Estructura del repositorio](#-estructura-del-repositorio)
- [Crear tu propio agente](#-crear-tu-propio-agente)
- [Créditos](#-créditos)

---

## Reglas del juego

### Materiales y participantes

- **Baraja:** baraja española (con comodines opcionales).
- **Comodín:** vale como el número que elija quien lo tenga.
- **Jugadores:** de 2 a 4.

### Preparación

- Se reparten **3 cartas** a cada jugador.
- Se colocan **6 cartas boca arriba** en el centro de la mesa.

### Turnos

En tu turno tenés que jugar **una carta de tu mano** para hacer una de estas acciones:

| Acción                  | Condición                                                                        | Resultado                                                                 |
|-------------------------|---------------------------------------------------------|------------------------|---------------------------------------------------------------------------|
| **Llevarse de la mesa** | Tu carta tiene el mismo número que una o más cartas de la mesa                   | Te llevás todas las cartas coincidentes **junto con la tuya** a tu casita |
| **Robar la casita**     | Tu carta tiene el mismo número que la carta superior de la casita de un oponente | Te llevás **toda su casita** y la ponés sobre la tuya                     |
| **Tirar carta**         | No podés hacer ninguna de las anteriores                | Dejás una carta de tu mano **boca arriba en la mesa** (se expanden las cartas jugables de la mesa) |

### La casita (tu mazo)

- Cada vez que ganás cartas, las agrupás en un mazo a tu lado llamado **casita**.
- La **última carta que ganaste** queda siempre **boca arriba en la cima**. Es la carta que tus oponentes intentarán igualar para robarte toda la casita.

### Nuevas rondas

- Cuando **todos** se quedan sin cartas en la mano, se reparten **3 cartas más** a cada jugador.
- **No** se agregan cartas nuevas a la mesa, salvo que la mesa esté **vacía** (en ese caso se colocan 6).
- Se repite hasta que se agota el mazo.

### Fin del juego y ganador

- El juego termina cuando **se acaba el mazo de reparto**.
- Si quedan cartas sueltas en la mesa, se las lleva **el último jugador que haya ganado cartas**.
- **Gana quien tenga más cartas en su casita.**

---

## ⚙️ Instalación

**Requisitos**

- Python 3.10 o superior (se usa la sintaxis `dict | None`)
- [PyGame](https://www.pygame.org/) (solo para la interfaz gráfica)

```bash
git clone <URL-DEL-REPOSITORIO>
cd <NOMBRE-DEL-REPOSITORIO>

pip install pygame
```

---

## ▶️ Cómo ejecutarlo

```bash
python casitamain.py [opciones]
```

| Opción           | Descripción                                                   | Por defecto |
|------------------|---------------------------------------------------------------|-------------|
| `--players=N`    | Cantidad de jugadores (2 a 4)                                 | `4`         |
| `--jokers`       | Incluye comodines en la baraja                                | desactivado |
| `--human`        | El jugador 0 es controlado por una persona (por consola)      | desactivado |
| `--pygame`       | Muestra la interfaz gráfica con PyGame en lugar de la consola | desactivado |

**Ejemplos**

```bash
# Partida de 4 bots en consola
python casitamain.py

# 3 jugadores, con comodines, interfaz gráfica
python casitamain.py --players=3 --jokers --pygame

# Jugar vos (jugador 0) contra 3 bots
python casitamain.py --human

# Jugar vos contra 1 bot, con interfaz gráfica
python casitamain.py --players=2 --human --pygame
```

### Comportamiento del bot por defecto

El `CasitaAgent` base juega una política simple:

1. Si puede **llevarse cartas de la mesa**, elige una de esas jugadas al azar.
2. Si no, y puede **robar una casita**, elige una de esas jugadas al azar.
3. Si no tiene jugadas, **descarta una carta al azar**.

Este bot es un punto de partida: está pensado para ser reemplazado por agentes más inteligentes.

---

## 📁 Estructura del repositorio

```
.
├── casitamain.py        # Punto de entrada: arma el juego y corre el bucle principal
├── casitaworld.py       # Entorno: cartas, mazo, reglas, turnos y rondas
├── casitaagent.py       # Agentes (bot y humano), sensores y actuador
├── casitarenderer.py    # Renderers de consola y PyGame
├── agents.py            # Framework base: Agent, Sensor, Actuator
├── environments.py      # Framework base: SimulatedEnvironment, sensor/actuador simulados
├── renderers.py         # Interfaz IRenderer y NullRenderer
├── statebuffer.py       # IStateBuffer y GlobalStateBuffer
└── Vacuum_version/      # Ejemplo de referencia (Vacuum World) de la cátedra
```

> Los archivos `agents.py`, `environments.py`, `renderers.py` y la carpeta `Vacuum_version/` provienen del material provisto por los profesores acargo del grupo de investigacion GIICOS.

---

## 🤖 Crear tu propio agente

Heredá de `CasitaAgent` y sobrescribí `function(percept)`, que recibe lo que el agente percibe y devuelve la acción a ejecutar:

```python
from casitaagent import CasitaAgent

class MiAgente(CasitaAgent):
    def function(self, percept):
        valid = percept["valid_actions_sensor"]
        hand = percept["hand_sensor"]

        # Ejemplo: priorizar robar casitas
        if valid["steal_casita"]:
            a = valid["steal_casita"][0]
            return {
                "name": "play_card",
                "params": {
                    "card_index": a["card_index"],
                    "action_type": "steal_casita",
                    "target_player": a["target_player"],
                },
            }

        if valid["take_from_table"]:
            a = valid["take_from_table"][0]
            return {
                "name": "play_card",
                "params": {"card_index": a["card_index"], "action_type": "take_from_table"},
            }

        return {
            "name": "play_card",
            "params": {"card_index": 0, "action_type": "discard"},
        }
```

Luego usalo en `run_game()` de `casitamain.py` en lugar de `CasitaAgent`.

---

## 🎓 Créditos

Proyecto desarrollado en el marco de **PRAISE**, grupo de investigación **GIICOS** de la **UTN FRCU** (Universidad Tecnológica Nacional – Facultad Regional Concepción del Uruguay).

- Framework de agentes y entornos: cátedra / profesores acargo del grupo.
- Implementación del juego Casita Robada: *<Sarlinga Matias>*.
