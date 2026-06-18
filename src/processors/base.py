import pygame

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final


FRAMERATE = 30


class DefrostingOrder(Enum):
    left_to_right = 'left_to_right'
    order_by_time = 'order_by_time'


@dataclass
class SettingsStorage:
    log_file_path: Path | None = None
    freeze_duration_seconds: int | None = None
    contest_name: str | None = None
    defrosting_order: DefrostingOrder = DefrostingOrder.left_to_right


settings_storage: Final[SettingsStorage] = SettingsStorage()


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
