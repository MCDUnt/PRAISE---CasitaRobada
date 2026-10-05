import sys
import time
import math
import pygame
from renderers import IRenderer


SUIT_SYMBOLS = {
    "oros": "O",
    "copas": "C",
    "espadas": "E",
    "bastos": "B",
    "joker": "J"
}

RANK_NAMES = {
    1: "1",
    2: "2",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
    10: "10",
    11: "11",
    12: "12",
    None: "JK"
}

SUIT_COLORS = {
    "oros": "red",
    "copas": "red",
    "espadas": "black",
    "bastos": "black",
    "joker": "red"
}


def card_to_str(card_dict):
    suit = card_dict["suit"]
    rank = card_dict["rank"]
    symbol = SUIT_SYMBOLS.get(suit, "?")
    rank_str = RANK_NAMES.get(rank, str(rank))
    return f"{rank_str}{symbol}"


def format_hand(hand):
    return "  ".join([f"[{i}] {card_to_str(c)}" for i, c in enumerate(hand)])


def format_table(table):
    return "  ".join([f"[{i}] {card_to_str(c)}" for i, c in enumerate(table)])


class ConsoleRenderer(IRenderer):
    def __init__(self):
        self.buffer = None

    def observe(self, buffer):
        self.buffer = buffer

    def render(self):
        state = self.buffer.get_state()
        if not state:
            return

        print("\n" + "=" * 70)
        print(f"CASITA ROBADA  |  Ronda {state['round']}  |  Turno: Jugador {state['current_player']}")
        print("=" * 70)

        print(f"\nMAZO: {state['deck_size']} cartas")

        print(f"\nMESA ({len(state['table'])} cartas):")
        if state['table']:
            print(f"  {format_table(state['table'])}")
        else:
            print("  (vacia)")

        print("\nCASITAS:")
        for pid in range(state['num_players']):
            casita = state['casitas'].get(str(pid), state['casitas'].get(pid, []))
            if casita:
                top = card_to_str(casita[-1])
                print(f"  Jugador {pid}: {len(casita)} cartas  [TOPE: {top}]")
            else:
                print(f"  Jugador {pid}: vacia")

        print(f"\nMANOS (todas visibles):")
        for pid in range(state['num_players']):
            hand = state['hands'].get(str(pid), state['hands'].get(pid, []))
            if hand:
                print(f"  Jugador {pid}: {format_hand(hand)}")
            else:
                print(f"  Jugador {pid}: (vacia)")

        valid = state.get('valid_actions', {})
        if valid.get('take_from_table'):
            print("\n>>> ACCIONES: LLEVARSE DE MESA")
            for opt in valid['take_from_table']:
                matches = [card_to_str(state['table'][j]) for j in opt['matches']]
                print(f"    Carta [{opt['card_index']}] coincide con: {', '.join(matches)}")

        if valid.get('steal_casita'):
            print("\n>>> ACCIONES: ROBAR CASITA")
            for opt in valid['steal_casita']:
                print(f"    Carta [{opt['card_index']}] roba casita de Jugador {opt['target_player']}")

        if valid.get('must_discard'):
            print("\n>>> DEBE DESCARTAR")

        if state['game_over']:
            print("\n" + "*" * 70)
            print("¡JUEGO TERMINADO!")
            scores = {pid: len(cards) for pid, cards in state['casitas'].items()}
            print(f"Puntuaciones: {scores}")
            winner = max(scores, key=scores.get)
            print(f"GANADOR: Jugador {winner} con {scores[winner]} cartas!")
            print("*" * 70)


class PyGameRenderer(IRenderer):
    CARD_W = 70
    CARD_H = 100

    PLAYER_POS = {
        0: (600, 720),   # abajo - humano
        1: (600, 80),    # arriba
        2: (120, 400),   # izquierda
        3: (1080, 400),  # derecha
    }

    CASITA_OFFSET = {
        0: (0, -160),
        1: (0, 160),
        2: (160, 0),
        3: (-160, 0),
    }

    TABLE_CENTER = (600, 400)
    TABLE_COLS = 3
    TABLE_ROWS = 2
    TABLE_CARD_GAP = 8

    COLORS = {
        'bg': (30, 30, 40),
        'table_bg': (200, 200, 200),
        'table_border': (0, 120, 0),
        'card_face': (255, 255, 255),
        'card_border': (50, 50, 50),
        'red_suit': (200, 30, 30),
        'black_suit': (20, 20, 20),
        'black': (0, 0, 0),
        'card_back': (180, 20, 20),
        'card_back_dark': (120, 10, 10),
        'casita_bg': (40, 40, 50),
        'casita_border': (100, 100, 120),
        'text': (220, 220, 230),
        'text_dim': (150, 150, 170),
        'turn_highlight': (255, 215, 0),
    }

    SUIT_SYMBOLS = {
        "oros": "♦",
        "copas": "♥",
        "espadas": "♠",
        "bastos": "♣",
        "joker": "★"
    }

    RANK_NAMES = {
        1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
        10: "10", 11: "11", 12: "12", None: "JK"
    }

    def __init__(self):
        self.screen = None
        self.buffer = None
        self.font = None
        self.font_small = None
        self.font_big = None
        self.initialized = False
        self._card_face_cache = {}
        self._card_back_cache = None
        self._card_back_rotated_cache = {}

    def observe(self, buffer):
        self.buffer = buffer

    def _init_pygame(self):
        if not self.initialized:
            pygame.init()
            self.screen = pygame.display.set_mode((1200, 800))
            pygame.display.set_caption("Casita Robada")
            self.font = pygame.font.Font(None, 22)
            self.font_small = pygame.font.Font(None, 16)
            self.font_big = pygame.font.Font(None, 48)
            self._build_card_cache()
            self.initialized = True

    def _build_card_cache(self):
        c = self.COLORS
        w, h = self.CARD_W, self.CARD_H

        for suit in ["oros", "copas", "espadas", "bastos"]:
            is_red = suit in ("oros", "copas")
            color = c['red_suit'] if is_red else c['black_suit']
            symbol = self.SUIT_SYMBOLS[suit]
            for rank in [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]:
                rank_str = self.RANK_NAMES[rank]
                surf = pygame.Surface((w, h), pygame.SRCALPHA)
                pygame.draw.rect(surf, c['card_face'], (0, 0, w, h), border_radius=4)
                pygame.draw.rect(surf, c['card_border'], (0, 0, w, h), 2, border_radius=4)

                fs = self.font_small
                fb = self.font_big

                txt_rank = fs.render(rank_str, True, color)
                txt_suit = fs.render(symbol, True, color)
                surf.blit(txt_rank, (4, 2))
                surf.blit(txt_suit, (4, 18))
                surf.blit(txt_rank, (w - txt_rank.get_width() - 4, h - txt_rank.get_height() - 2))
                surf.blit(txt_suit, (w - txt_suit.get_width() - 4, h - txt_suit.get_height() - 18))

                big_suit = fb.render(symbol, True, color)
                surf.blit(big_suit, (w//2 - big_suit.get_width()//2, h//2 - big_suit.get_height()//2))

                self._card_face_cache[(suit, rank)] = surf

        joker_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(joker_surf, c['card_face'], (0, 0, w, h), border_radius=4)
        pygame.draw.rect(joker_surf, c['red_suit'], (0, 0, w, h), 3, border_radius=4)
        pygame.draw.rect(joker_surf, c['red_suit'], (8, 8, w-16, h-16), 2, border_radius=3)
        txt = self.font.render("COMODIN", True, c['red_suit'])
        joker_surf.blit(txt, (w//2 - txt.get_width()//2, h//2 - txt.get_height()//2))
        star = self.font_big.render("★", True, c['red_suit'])
        joker_surf.blit(star, (w//2 - star.get_width()//2, h//2 - star.get_height()//2 - 30))
        self._card_face_cache[("joker", None)] = joker_surf

        back_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(back_surf, c['card_back'], (0, 0, w, h), border_radius=4)
        pygame.draw.rect(back_surf, c['card_back_dark'], (0, 0, w, h), 3, border_radius=4)
        pygame.draw.rect(back_surf, c['card_back_dark'], (5, 5, w-10, h-10), 2, border_radius=3)
        for i in range(3):
            for j in range(5):
                cx = 12 + i * 18
                cy = 12 + j * 16
                pygame.draw.circle(back_surf, (200, 60, 60), (cx, cy), 3)
                pygame.draw.circle(back_surf, c['card_back_dark'], (cx, cy), 3, 1)
        self._card_back_cache = back_surf

    def _get_card_face(self, suit, rank):
        return self._card_face_cache.get((suit, rank), self._card_face_cache.get(("espadas", 1)))

    def _get_card_back(self):
        return self._card_back_cache

    def _get_rotated_back(self, angle):
        key = int(angle)
        if key not in self._card_back_rotated_cache:
            self._card_back_rotated_cache[key] = pygame.transform.rotate(self._card_back_cache, angle)
        return self._card_back_rotated_cache[key]

    def _get_rotated_face(self, suit, rank, angle):
        key = (suit, rank, int(angle))
        if key not in self._card_face_cache:
            base = self._get_card_face(suit, rank)
            self._card_face_cache[key] = pygame.transform.rotate(base, angle)
        return self._card_face_cache[key]

    def _draw_card_at(self, surface, x, y, suit, rank, angle=0, face_up=True, selected=False):
        c = self.COLORS
        if angle == 0:
            if face_up:
                card_surf = self._get_card_face(suit, rank)
            else:
                card_surf = self._get_card_back()
        else:
            if face_up:
                card_surf = self._get_rotated_face(suit, rank, angle)
            else:
                card_surf = self._get_rotated_back(angle)
        
        rect = card_surf.get_rect(center=(x, y))
        surface.blit(card_surf, rect)
        
        if selected:
            pygame.draw.rect(surface, c['turn_highlight'], rect, 3, border_radius=4)

    def _draw_straight_hand(self, surface, cx, cy, cards, face_up, horizontal=True, selected_idx=None):
        c = self.COLORS
        n = len(cards)
        if n == 0:
            return
        
        total_w = n * self.CARD_W + (n - 1) * 8
        start_x = cx - total_w // 2 + self.CARD_W // 2
        
        for i, card in enumerate(cards):
            x = start_x + i * (self.CARD_W + 8)
            y = cy
            suit = card["suit"]
            rank = card["rank"]
            is_sel = (i == selected_idx)
            self._draw_card_at(surface, x, y, suit, rank, angle=0, face_up=face_up, selected=is_sel)

    def _draw_fanned_hand(self, surface, cx, cy, cards, face_up, spread_angle=25, base_angle=90, selected_idx=None):
        c = self.COLORS
        n = len(cards)
        if n == 0:
            return
        
        start_angle = base_angle - (spread_angle * (n - 1) / 2)
        radius = 120
        
        for i, card in enumerate(cards):
            angle = start_angle + i * spread_angle
            rad = math.radians(angle)
            x = cx + radius * math.cos(rad)
            y = cy + radius * math.sin(rad)
            suit = card["suit"]
            rank = card["rank"]
            is_sel = (i == selected_idx)
            self._draw_card_at(surface, x, y, suit, rank, angle=angle, face_up=face_up, selected=is_sel)

    def _draw_table_grid(self, surface, state):
        c = self.COLORS
        cx, cy = self.TABLE_CENTER
        table = state['table']
        
        grid_w = self.TABLE_COLS * self.CARD_W + (self.TABLE_COLS - 1) * self.TABLE_CARD_GAP
        grid_h = self.TABLE_ROWS * self.CARD_H + (self.TABLE_ROWS - 1) * self.TABLE_CARD_GAP
        
        table_rect = pygame.Rect(cx - grid_w // 2 - 10, cy - grid_h // 2 - 10, grid_w + 20, grid_h + 20)
        pygame.draw.rect(surface, c['table_bg'], table_rect, border_radius=8)
        pygame.draw.rect(surface, c['table_border'], table_rect, 3, border_radius=8)
        
        start_x = cx - grid_w // 2 + self.CARD_W // 2
        start_y = cy - grid_h // 2 + self.CARD_H // 2
        
        for idx, card in enumerate(table):
            row = idx // self.TABLE_COLS
            col = idx % self.TABLE_COLS
            x = start_x + col * (self.CARD_W + self.TABLE_CARD_GAP)
            y = start_y + row * (self.CARD_H + self.TABLE_CARD_GAP)
            suit = card["suit"]
            rank = card["rank"]
            self._draw_card_at(surface, x, y, suit, rank, angle=0, face_up=True)
            
            idx_txt = self.font_small.render(str(idx), True, c['text_dim'])
            surface.blit(idx_txt, (x - self.CARD_W // 2 + 2, y - self.CARD_H // 2 + 2))

    def _draw_casita(self, surface, cx, cy, casita_cards, label):
        c = self.COLORS
        box_w, box_h = 100, 130
        
        rect = pygame.Rect(cx - box_w // 2, cy - box_h // 2, box_w, box_h)
        pygame.draw.rect(surface, c['casita_bg'], rect, border_radius=6)
        pygame.draw.rect(surface, c['casita_border'], rect, 2, border_radius=6)
        
        label_surf = self.font_small.render(label, True, c['text_dim'])
        surface.blit(label_surf, (cx - label_surf.get_width() // 2, cy - box_h // 2 - 20))
        
        count_surf = self.font.render(f"{len(casita_cards)}", True, c['text'])
        surface.blit(count_surf, (cx - count_surf.get_width() // 2, cy + box_h // 2 + 5))
        
        if casita_cards:
            top_card = casita_cards[-1]
            self._draw_card_at(surface, cx, cy - 5, top_card["suit"], top_card["rank"], angle=0, face_up=True)

    def _draw_turn_indicator(self, surface, cx, cy, pid):
        c = self.COLORS
        if pid == 0:
            y = cy + self.CARD_H // 2 + 25
            pts = [(cx, y), (cx - 10, y + 15), (cx + 10, y + 15)]
        elif pid == 1:
            y = cy - self.CARD_H // 2 - 25
            pts = [(cx, y), (cx - 10, y - 15), (cx + 10, y - 15)]
        elif pid == 2:
            x = cx - self.CARD_W // 2 - 25
            pts = [(x, cy), (x - 15, cy - 10), (x - 15, cy + 10)]
        else:
            x = cx + self.CARD_W // 2 + 25
            pts = [(x, cy), (x + 15, cy - 10), (x + 15, cy + 10)]
        pygame.draw.polygon(surface, c['turn_highlight'], pts)

    def _draw_hud(self, surface, state):
        c = self.COLORS
        
        title = self.font.render(f"Casita Robada  |  Ronda {state['round']}  |  Turno: Jugador {state['current_player']}", True, c['text'])
        surface.blit(title, (20, 15))
        
        deck_txt = self.font.render(f"Mazo: {state['deck_size']} cartas", True, c['text_dim'])
        surface.blit(deck_txt, (20, 45))
        
        valid = state.get('valid_actions', {})
        info_x = 950
        info_y = 15
        
        if valid.get('take_from_table'):
            txt = self.font.render("ACCIONES:", True, c['turn_highlight'])
            surface.blit(txt, (info_x, info_y))
            info_y += 25
            for opt in valid['take_from_table']:
                matches = [card_to_str(state['table'][j]) for j in opt['matches']]
                txt = self.font_small.render(f"  Carta [{opt['card_index']}] -> {', '.join(matches)}", True, c['text'])
                surface.blit(txt, (info_x + 10, info_y))
                info_y += 20
        
        if valid.get('steal_casita'):
            txt = self.font.render("ROBAR CASITA:", True, c['turn_highlight'])
            surface.blit(txt, (info_x, info_y))
            info_y += 25
            for opt in valid['steal_casita']:
                txt = self.font_small.render(f"  Carta [{opt['card_index']}] -> J{opt['target_player']}", True, c['text'])
                surface.blit(txt, (info_x + 10, info_y))
                info_y += 20
        
        if valid.get('must_discard'):
            txt = self.font.render("DESCARTAR", True, c['red_suit'])
            surface.blit(txt, (info_x, info_y))
            info_y += 25

    def _draw_game_over(self, surface, state):
        c = self.COLORS
        overlay = pygame.Surface((1200, 800))
        overlay.fill(c['black'])
        overlay.set_alpha(180)
        surface.blit(overlay, (0, 0))
        
        scores = {pid: len(cards) for pid, cards in state['casitas'].items()}
        winner = max(scores, key=scores.get)
        
        go = self.font_big.render("¡JUEGO TERMINADO!", True, c['turn_highlight'])
        surface.blit(go, (400, 250))
        
        for pid, score in scores.items():
            color = c['turn_highlight'] if pid == winner else c['text']
            txt = self.font.render(f"Jugador {pid}: {score} cartas", True, color)
            surface.blit(txt, (450, 320 + pid * 40))
        
        win = self.font_big.render(f"GANADOR: Jugador {winner}!", True, c['turn_highlight'])
        surface.blit(win, (400, 500))

    def render(self):
        self._init_pygame()
        state = self.buffer.get_state()
        if not state:
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        c = self.COLORS
        self.screen.fill(c['bg'])
        
        self._draw_table_grid(self.screen, state)
        
        for pid in range(state['num_players']):
            self._render_player_area(self.screen, state, pid)
        
        self._draw_hud(self.screen, state)
        
        if state['game_over']:
            self._draw_game_over(self.screen, state)
        
        pygame.display.flip()
        time.sleep(0.05)

    def _render_player_area(self, surface, state, pid):
        px, py = self.PLAYER_POS[pid]
        hand = state['hands'].get(str(pid), state['hands'].get(pid, []))
        casita = state['casitas'].get(str(pid), state['casitas'].get(pid, []))
        is_current = (pid == state['current_player'])
        
        if pid == 0:
            self._draw_straight_hand(surface, px, py, hand, face_up=True, horizontal=True, selected_idx=None)
        elif pid == 1:
            self._draw_straight_hand(surface, px, py, hand, face_up=False, horizontal=True)
        elif pid == 2:
            self._draw_fanned_hand(surface, px, py, hand, face_up=False, spread_angle=30, base_angle=90)
        elif pid == 3:
            self._draw_fanned_hand(surface, px, py, hand, face_up=False, spread_angle=30, base_angle=-90)
        
        cxo, cyo = self.CASITA_OFFSET[pid]
        self._draw_casita(surface, px + cxo, py + cyo, casita, f"CASITA {pid}")
        
        if is_current:
            self._draw_turn_indicator(surface, px, py, pid)