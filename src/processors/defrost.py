import pygame

from .base import BaseProcessor, AppState


class DefrostProcessor(BaseProcessor):
    def process(self) -> AppState:
        screen = pygame.display.get_surface()
        screen.fill((0, 0, 0))

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return AppState.QUIT

        pygame.display.flip()
        self.clock.tick(60)
        return AppState.DEFROST
