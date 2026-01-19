from .base import AppState
from .calculate import CalculateProcessor
from .defrost import DefrostProcessor
from .settings import SettingsProcessor

settings_processor = SettingsProcessor()
calculate_processor = CalculateProcessor()
defrost_processor = DefrostProcessor()

settings_processor.calculate_processor = calculate_processor

__all__ = [
    'settings_processor',
    'calculate_processor',
    'defrost_processor',
    'AppState',
]
