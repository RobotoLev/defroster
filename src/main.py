import pygame


pygame.init()

BASIC_WINDOW_SIZE = (200, 200)
screen = pygame.display.set_mode(BASIC_WINDOW_SIZE)
pygame.display.set_caption("defroster")

from src.processors import *


running = True
state = AppState.SETTINGS

while running:
    if state == AppState.SETTINGS:
        state = settings_processor.process()
    elif state == AppState.DEFROST:
        state = defrost_processor.process()
    elif state == AppState.CALCULATE:
        state = calculate_processor.process()
    elif state == AppState.QUIT:
        running = False
    else:
        raise NotImplementedError(f"Unknown {state=}")

pygame.quit()
