import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from statebuffer import GlobalStateBuffer
from casitaworld import CasitaEnvironment
from casitaagent import CasitaAgent, HumanCasitaAgent
from casitarenderer import ConsoleRenderer, PyGameRenderer


def run_game(num_players=4, use_jokers=False, use_pygame=False, human_player=False):
    env = CasitaEnvironment(num_players, use_jokers)
    agents = []

    for i in range(num_players):
        if human_player and i == 0:
            agent = HumanCasitaAgent(env)
            print(f"Jugador 0: HUMANO")
        else:
            agent = CasitaAgent(env)
            print(f"Jugador {i}: BOT")
        agents.append(agent)

    buffer = GlobalStateBuffer()
    env.set_buffer(buffer)

    console_renderer = ConsoleRenderer()
    console_renderer.observe(buffer)

    if use_pygame:
        pygame_renderer = PyGameRenderer()
        pygame_renderer.observe(buffer)
        renderer = pygame_renderer
    else:
        renderer = console_renderer

    print(f"\nIniciando Casita Robada con {num_players} jugadores")
    print(f"Comodines: {'Si' if use_jokers else 'No'}")
    print(f"Modo humano: {'Si (Jugador 0)' if human_player else 'No'}")
    print("-" * 50)

    while not env.game_over:
        current = env.current_player

        renderer.render()

        if human_player and current == 0:
            print(f"\n>>> TURNO DEL HUMANO (Jugador 0) <<<")
            agents[0].behave()
        else:
            agents[current].behave()
            time.sleep(0.5)

    renderer.render()

    print("\n" + "=" * 50)
    print("JUEGO TERMINADO")
    print("=" * 50)
    scores = env.get_scores()
    for pid, score in scores.items():
        print(f"  Jugador {pid}: {score} cartas")
    winner = env.get_winner()
    print(f"\nGANADOR: Jugador {winner}!")


if __name__ == '__main__':
    use_pygame = "--pygame" in sys.argv
    human = "--human" in sys.argv
    jokers = "--jokers" in sys.argv
    players = 4

    for arg in sys.argv:
        if arg.startswith("--players="):
            players = int(arg.split("=")[1])

    run_game(num_players=players, use_jokers=jokers, use_pygame=use_pygame, human_player=human)