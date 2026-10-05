import random
from enum import Enum, unique
from statebuffer import IStateBuffer
from environments import SimulatedEnvironment


@unique
class Suit(Enum):
    OROS = "oros"
    COPAS = "copas"
    ESPADAS = "espadas"
    BASTOS = "bastos"
    JOKER = "joker"


@unique
class Rank(Enum):
    AS = 1
    DOS = 2
    TRES = 3
    CUATRO = 4
    CINCO = 5
    SEIS = 6
    SIETE = 7
    SOTA = 10
    CABALLO = 11
    REY = 12


class Card:
    def __init__(self, suit: Suit, rank: Rank = None):
        self.suit = suit
        self.rank = rank

    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        if self.suit == Suit.JOKER or other.suit == Suit.JOKER:
            return self.suit == Suit.JOKER and other.suit == Suit.JOKER
        return self.suit == other.suit and self.rank == other.rank

    def __hash__(self):
        return hash((self.suit, self.rank))

    def __repr__(self):
        if self.suit == Suit.JOKER:
            return "Joker"
        return f"{self.rank.name} de {self.suit.value}"

    def matches_rank(self, other: 'Card') -> bool:
        if self.suit == Suit.JOKER or other.suit == Suit.JOKER:
            return True
        return self.rank == other.rank

    def to_dict(self):
        return {"suit": self.suit.value, "rank": self.rank.value if self.rank else None}


class CasitaEnvironment(SimulatedEnvironment):
    def __new__(cls, num_players: int = 4, use_jokers: bool = False):
        if num_players < 2 or num_players > 4:
            raise ValueError("Players must be between 2 and 4")
        return super().__new__(cls)

    def __init__(self, num_players: int = 4, use_jokers: bool = False):
        super(CasitaEnvironment, self).__init__()
        self._num_players = num_players
        self._use_jokers = use_jokers
        self._deck = []
        self._table = []
        self._hands = {i: [] for i in range(num_players)}
        self._casitas = {i: [] for i in range(num_players)}
        self._agent_to_player = {}
        self._player_to_agent = {}
        self._current_player = 0
        self._last_taker = None
        self._game_over = False
        self._round = 0
        self._buffer = None
        self._initialize_deck()
        self._deal_initial()
        self._notify_buffer()

    def _initialize_deck(self):
        self._deck = []
        for suit in [Suit.OROS, Suit.COPAS, Suit.ESPADAS, Suit.BASTOS]:
            for rank in Rank:
                self._deck.append(Card(suit, rank))
        if self._use_jokers:
            self._deck.append(Card(Suit.JOKER))
            self._deck.append(Card(Suit.JOKER))
        random.shuffle(self._deck)

    def _deal_initial(self):
        for _ in range(3):
            for player_id in range(self._num_players):
                if self._deck:
                    self._hands[player_id].append(self._deck.pop())
        for _ in range(6):
            if self._deck:
                self._table.append(self._deck.pop())

    def add(self, agent_id: int) -> None:
        super(CasitaEnvironment, self).add(agent_id)
        if agent_id not in self._agent_to_player:
            player_idx = len(self._agent_to_player)
            if player_idx < self._num_players:
                self._agent_to_player[agent_id] = player_idx
                self._player_to_agent[player_idx] = agent_id

    def _get_player_index(self, agent_id: int) -> int:
        return self._agent_to_player.get(agent_id, 0)

    def remove(self, agent_id: int) -> None:
        super(CasitaEnvironment, self).remove(agent_id)
        player_idx = self._agent_to_player.pop(agent_id, None)
        if player_idx is not None:
            self._player_to_agent.pop(player_idx, None)

    def set_buffer(self, buffer: IStateBuffer) -> None:
        self._buffer = buffer
        self._notify_buffer()

    def _notify_buffer(self):
        if self._buffer:
            self._buffer.update(self._get_global_state())

    def _get_global_state(self) -> dict:
        valid = self._get_valid_actions(self._current_player)
        return {
            "num_players": self._num_players,
            "current_player": self._current_player,
            "round": self._round,
            "deck_size": len(self._deck),
            "game_over": self._game_over,
            "table": [c.to_dict() for c in self._table],
            "hands": {pid: [c.to_dict() for c in cards] for pid, cards in self._hands.items()},
            "casitas": {pid: [c.to_dict() for c in cards] for pid, cards in self._casitas.items()},
            "valid_actions": valid
        }

    def _get_state_for_agent(self, agent_id: int) -> dict:
        player_idx = self._get_player_index(agent_id)
        valid = self._get_valid_actions(player_idx)
        return {
            "num_players": self._num_players,
            "current_player": self._current_player,
            "agent_player_index": player_idx,
            "hand": [c.to_dict() for c in self._hands.get(player_idx, [])],
            "table": [c.to_dict() for c in self._table],
            "casitas": {pid: [c.to_dict() for c in cards] for pid, cards in self._casitas.items()},
            "deck_size": len(self._deck),
            "game_over": self._game_over,
            "last_taker": self._last_taker,
            "round": self._round,
            "valid_actions": valid
        }

    def _can_take_from_table(self, player_idx: int) -> list:
        hand = self._hands.get(player_idx, [])
        valid = []
        for i, card in enumerate(hand):
            matches = [j for j, tcard in enumerate(self._table) if card.matches_rank(tcard)]
            if matches:
                valid.append({"card_index": i, "matches": matches})
        return valid

    def _can_steal_casita(self, player_idx: int) -> list:
        hand = self._hands.get(player_idx, [])
        valid = []
        for i, card in enumerate(hand):
            for pid, casita in self._casitas.items():
                if pid != player_idx and casita:
                    top_card = casita[-1]
                    if card.matches_rank(top_card):
                        valid.append({"card_index": i, "target_player": pid})
        return valid

    def _get_valid_actions(self, player_idx: int) -> dict:
        take = self._can_take_from_table(player_idx)
        steal = self._can_steal_casita(player_idx)
        return {
            "take_from_table": take,
            "steal_casita": steal,
            "must_discard": len(take) == 0 and len(steal) == 0
        }

    def get_property(self, agent_id: int, property_name: str) -> dict:
        if agent_id not in self._agents:
            return {}
        state = self._get_state_for_agent(agent_id)
        if property_name in state:
            return {"agent": agent_id, property_name: state[property_name]}
        return {"agent": agent_id}

    def take_action(self, agent_id: int, action_name: str, params: dict = {}) -> None:
        if agent_id not in self._agents:
            return

        player_idx = self._get_player_index(agent_id)
        if player_idx != self._current_player:
            return

        if action_name == "play_card":
            self._handle_play_card(player_idx, params.get("card_index", 0), params.get("action_type", "discard"), params.get("target_player"))
            self._notify_buffer()

    def _handle_play_card(self, player_idx: int, card_index: int, action_type: str, target_player: int = None):
        hand = self._hands.get(player_idx, [])
        if card_index < 0 or card_index >= len(hand):
            return

        card = hand[card_index]

        if action_type == "take_from_table":
            matches = [j for j, tcard in enumerate(self._table) if card.matches_rank(tcard)]
            if matches:
                taken = [self._table.pop(j) for j in sorted(matches, reverse=True)]
                taken.append(card)
                hand.pop(card_index)
                self._casitas[player_idx].extend(taken)
                self._last_taker = player_idx
            else:
                return

        elif action_type == "steal_casita":
            if target_player is None:
                for pid, casita in self._casitas.items():
                    if pid != player_idx and casita and card.matches_rank(casita[-1]):
                        target_player = pid
                        break

            if target_player is not None and self._casitas[target_player]:
                top_card = self._casitas[target_player][-1]
                if card.matches_rank(top_card):
                    stolen = self._casitas[target_player]
                    self._casitas[target_player] = []
                    stolen.append(card)
                    hand.pop(card_index)
                    self._casitas[player_idx].extend(stolen)
                    self._last_taker = player_idx
                else:
                    return
            else:
                return

        elif action_type == "discard":
            hand.pop(card_index)
            self._table.append(card)

        self._next_turn()

    def _next_turn(self):
        if all(len(self._hands.get(pid, [])) == 0 for pid in range(self._num_players)):
            self._new_round()
        else:
            self._current_player = (self._current_player + 1) % self._num_players
            while len(self._hands.get(self._current_player, [])) == 0:
                self._current_player = (self._current_player + 1) % self._num_players

    def _new_round(self):
        if not self._deck:
            self._end_game()
            return

        self._round += 1
        for player_id in range(self._num_players):
            for _ in range(3):
                if self._deck:
                    self._hands[player_id].append(self._deck.pop())

        if not self._table and self._deck:
            for _ in range(6):
                if self._deck:
                    self._table.append(self._deck.pop())

        self._current_player = 0
        while len(self._hands.get(self._current_player, [])) == 0:
            self._current_player = (self._current_player + 1) % self._num_players

    def _end_game(self):
        if self._table and self._last_taker is not None:
            self._casitas[self._last_taker].extend(self._table)
            self._table = []
        self._game_over = True

    @property
    def current_player(self) -> int:
        return self._current_player

    @property
    def game_over(self) -> bool:
        return self._game_over

    @property
    def num_players(self) -> int:
        return self._num_players

    def get_winner(self):
        if not self._game_over:
            return None
        max_cards = -1
        winner_player_idx = None
        for pid, casita in self._casitas.items():
            if len(casita) > max_cards:
                max_cards = len(casita)
                winner_player_idx = pid
        if winner_player_idx is not None:
            return self._player_to_agent.get(winner_player_idx, winner_player_idx)
        return None

    def get_scores(self):
        scores = {}
        for pid, casita in self._casitas.items():
            agent_id = self._player_to_agent.get(pid, pid)
            scores[agent_id] = len(casita)
        return scores