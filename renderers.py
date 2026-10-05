from abc import ABC, abstractmethod

class IRenderer(ABC):
    @abstractmethod
    def render(self):
        pass

    @abstractmethod
    def observe(self, statebuffer):
        pass

class NullRenderer(IRenderer):
    def render(self):
        pass

    def observe(self, statebuffer):
        pass