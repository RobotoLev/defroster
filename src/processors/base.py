import pygame

from abc import ABC, abstractmethod
from enum import Enum


class AppState(Enum):
    SETTINGS = 1
    CALCULATE = 2
    DEFROST = 3
    QUIT = 4


class BaseProcessor(ABC):
    def __init__(self):
        self.clock = pygame.time.Clock()

    @abstractmethod
    def process(self) -> AppState:
        raise NotImplementedError
