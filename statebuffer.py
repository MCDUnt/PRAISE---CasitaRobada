from abc import ABC, abstractmethod


class IStateBuffer(ABC):
    @abstractmethod
    def update(self, state: dict) -> None:
        pass

    @abstractmethod
    def get_state(self) -> dict | None:
        pass


class GlobalStateBuffer(IStateBuffer):
    def __init__(self):
        self._state = None
        self._changed = False

    def update(self, state: dict) -> None:
        self._state = state
        self._changed = True

    def get_state(self) -> dict | None:
        if self._changed:
            self._changed = False
            return self._state
        return None