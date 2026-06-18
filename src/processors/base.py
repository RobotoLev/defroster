import pygame

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final


FRAMERATE = 30


@dataclass
class SettingsStorage:
    log_file_path: Path | None = None
    freeze_duration_seconds: int | None = None
    contest_name: str | None = None


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
