from environments import SimulatedSensor, SimulatedActuator, SimulatedEnvironment
from agents import Agent
from random import randrange, choice


class HandSensor(SimulatedSensor):
    def sense(self):
        response = self._env.get_property(self._agent.id, property_name="hand")
        return response.get("hand", [])


class TableSensor(SimulatedSensor):
    def sense(self):
        response = self._env.get_property(self._agent.id, property_name="table")
        return response.get("table", [])


class CasitasSensor(SimulatedSensor):
    def sense(self):
        response = self._env.get_property(self._agent.id, property_name="casitas")
        return response.get("casitas", {})


class CurrentPlayerSensor(SimulatedSensor):
    def sense(self):
        response = self._env.get_property(self._agent.id, property_name="current_player")
        return response.get("current_player", -1)


class AgentIndexSensor(SimulatedSensor):
    def sense(self):
        response = self._env.get_property(self._agent.id, property_name="agent_player_index")
        return response.get("agent_player_index", -1)


class ValidActionsSensor(SimulatedSensor):
    def sense(self):
        response = self._env.get_property(self._agent.id, property_name="valid_actions")
        return response.get("valid_actions", {})


class GameOverSensor(SimulatedSensor):
    def sense(self):
        response = self._env.get_property(self._agent.id, property_name="game_over")
        return response.get("game_over", False)


class PlayCardActuator(SimulatedActuator):
    def act(self, card_index: int, action_type: str, target_player: int = None):
        params = {"card_index": card_index, "action_type": action_type}
        if target_player is not None:
            params["target_player"] = target_player
        self._env.take_action(self._agent.id, "play_card", params)


class CasitaAgent(Agent):
    def function(self, percept):
        valid_actions = percept["valid_actions_sensor"]
        hand = percept["hand_sensor"]

        if valid_actions["take_from_table"]:
            action = choice(valid_actions["take_from_table"])
            return {
                "name": "play_card",
                "params": {
                    "card_index": action["card_index"],
                    "action_type": "take_from_table"
                }
            }

        if valid_actions["steal_casita"]:
            action = choice(valid_actions["steal_casita"])
            return {
                "name": "play_card",
                "params": {
                    "card_index": action["card_index"],
                    "action_type": "steal_casita",
                    "target_player": action["target_player"]
                }
            }

        if hand:
            card_index = randrange(len(hand))
            return {
                "name": "play_card",
                "params": {
                    "card_index": card_index,
                    "action_type": "discard"
                }
            }

        return {"name": "play_card", "params": {"card_index": 0, "action_type": "discard"}}

    def __init__(self, env: SimulatedEnvironment):
        super().__init__()
        env.add(self.id)

        actuator = PlayCardActuator(env)
        actuator.agent = self
        self.add_actuator("play_card", actuator)

        sensors = [
            ("hand_sensor", HandSensor(env)),
            ("table_sensor", TableSensor(env)),
            ("casitas_sensor", CasitasSensor(env)),
            ("current_player_sensor", CurrentPlayerSensor(env)),
            ("agent_index_sensor", AgentIndexSensor(env)),
            ("valid_actions_sensor", ValidActionsSensor(env)),
            ("game_over_sensor", GameOverSensor(env))
        ]

        for name, sensor in sensors:
            sensor.agent = self
            self.add_sensor(name, sensor)

    def print_state(self):
        hand = self._sensors["hand_sensor"].sense()
        table = self._sensors["table_sensor"].sense()
        casitas = self._sensors["casitas_sensor"].sense()
        current = self._sensors["current_player_sensor"].sense()
        game_over = self._sensors["game_over_sensor"].sense()

        print(f"\n=== Player {self.id} ===")
        print(f"Current turn: Player {current}")
        print(f"Hand: {hand}")
        print(f"Table: {table}")
        for pid, casita in casitas.items():
            top = casita[-1] if casita else "empty"
            print(f"  Casita {pid}: {len(casita)} cards (top: {top})")
        print(f"Game over: {game_over}")

    def _perceive(self):
        percept = {}
        for sensor_name in self._sensors:
            percept[sensor_name] = self._sensors[sensor_name].sense()
        return percept

    def _act(self, percept):
        action = self.function(percept)
        actuator = self._actuators.get("play_card")
        if actuator:
            actuator.act(**action["params"])

    def behave(self):
        percept = self._perceive()
        if percept["agent_index_sensor"] == percept["current_player_sensor"] and not percept["game_over_sensor"]:
            self._act(percept)


class HumanCasitaAgent(CasitaAgent):
    def function(self, percept):
        valid_actions = percept["valid_actions_sensor"]
        hand = percept["hand_sensor"]

        print(f"\n{'='*50}")
        print(f"TU TURNO (Jugador {self.id})")
        print(f"{'='*50}")
        print(f"Mano: {hand}")
        print(f"Mesa: {percept['table_sensor']}")

        if valid_actions["take_from_table"]:
            print("\nPuedes LLEVARTE de la mesa:")
            for i, opt in enumerate(valid_actions["take_from_table"]):
                matches = opt['matches']
                print(f"  [{i}] Carta indice {opt['card_index']} -> coincide con mesa indices {matches}")

        if valid_actions["steal_casita"]:
            print("\nPuedes ROBAR casita:")
            for i, opt in enumerate(valid_actions["steal_casita"]):
                print(f"  [{i}] Carta indice {opt['card_index']} -> roba casita de jugador {opt['target_player']}")

        if valid_actions["must_discard"]:
            print("\nNo tienes jugadas -> DEBES DESCARTAR")

        while True:
            try:
                choice_input = input("\nElige opcion (numero): ")
                opt_idx = int(choice_input)

                if valid_actions["take_from_table"] and opt_idx < len(valid_actions["take_from_table"]):
                    opt = valid_actions["take_from_table"][opt_idx]
                    return {
                        "name": "play_card",
                        "params": {"card_index": opt["card_index"], "action_type": "take_from_table"}
                    }

                steal_start = len(valid_actions["take_from_table"])
                if valid_actions["steal_casita"] and opt_idx < steal_start + len(valid_actions["steal_casita"]):
                    opt = valid_actions["steal_casita"][opt_idx - steal_start]
                    return {
                        "name": "play_card",
                        "params": {"card_index": opt["card_index"], "action_type": "steal_casita", "target_player": opt["target_player"]}
                    }

                if valid_actions["must_discard"] and opt_idx == 0:
                    card_idx = int(input("Indice de carta a descartar: "))
                    if 0 <= card_idx < len(hand):
                        return {
                            "name": "play_card",
                            "params": {"card_index": card_idx, "action_type": "discard"}
                        }

                print("Opcion invalida")
            except ValueError:
                print("Ingresa un numero valido")
            except KeyboardInterrupt:
                print("\nSaliendo...")
                return {"name": "play_card", "params": {"card_index": 0, "action_type": "discard"}}