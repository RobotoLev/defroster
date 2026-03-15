import pygame
import pygame_gui

import threading
import tkinter
import tkinter.filedialog

from .base import BaseProcessor, AppState, FRAMERATE


class SettingsProcessor(BaseProcessor):
    calculate_processor = None

    def __init__(self):
        super().__init__()
        self.manager = pygame_gui.UIManager(pygame.display.get_window_size())
        self.openfile_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(25, 50, 150, 100),
            text="Open log file",
            manager=self.manager,
        )

    def process(self) -> AppState:
        if self.calculate_processor is None:
            raise NotImplementedError()
        from .calculate import CalculateProcessor
        self.calculate_processor: CalculateProcessor

        time_delta = self.clock.tick(FRAMERATE) / 1000.
        screen = pygame.display.get_surface()

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return AppState.QUIT
            if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.openfile_button:
                top = tkinter.Tk()
                top.withdraw()
                log_file_path = tkinter.filedialog.askopenfilename(
                    parent=top,
                    filetypes=(
                        ("Yandex.Contest submission log", "*.xml"),
                    )
                )
                top.destroy()
                if log_file_path != "":
                    thread = threading.Thread(
                        target=self.calculate_processor.prepare_defrost_data,
                        args=(log_file_path,)
                    )
                    thread.start()
                    self.calculate_processor.preparer_thread = thread
                    return AppState.CALCULATE
            self.manager.process_events(event)

        self.manager.update(time_delta)

        screen.fill('white')
        self.manager.draw_ui(screen)
        pygame.display.flip()

        return AppState.SETTINGS
