import pygame
import pygame_gui

from pathlib import Path
import threading
import tkinter
import tkinter.filedialog

from .base import BaseProcessor, AppState, FRAMERATE, settings_storage, DefrostingOrder


class SettingsProcessor(BaseProcessor):
    calculate_processor = None
    WINDOW_SIZE = (500, 525)

    def __init__(self):
        super().__init__()
        pygame.display.set_mode(self.WINDOW_SIZE)
        self.manager = pygame_gui.UIManager(
            pygame.display.get_window_size(),
            Path(__file__).resolve().parent.parent.parent / "res" / "theme.json"
        )
        self.openfile_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(25, 25, 150, 50),
            text="Open log file",
            manager=self.manager,
        )
        self.chosen_file_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(25, 10, -1, -1),
            manager=self.manager,
            text="Выберите файл",
            anchors={
                'top_target': self.openfile_button,
            }
        )
        self.freeze_duration_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(25, 10, -1, -1),
            text="Длительность разморозки в секундах:",
            manager=self.manager,
            anchors={
                'top_target': self.chosen_file_label,
            }
        )
        self.freeze_duration_entry_line = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(25, 10, 60, 30),
            manager=self.manager,
            initial_text="3600",
            anchors={
                'top_target': self.freeze_duration_label,
            }
        )
        self.contest_name_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(25, 10, -1, -1),
            text="Название соревнования (по умолчанию - как в системе):",
            manager=self.manager,
            anchors={
                'top_target': self.freeze_duration_entry_line,
            }
        )
        self.contest_name_entry_line = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(25, 10, 400, 30),
            manager=self.manager,
            anchors={
                'top_target': self.contest_name_label,
            }
        )
        self.defrosting_mode_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(25, 10, -1, -1),
            manager=self.manager,
            text="Режим разморозки:",
            anchors={
                'top_target': self.contest_name_entry_line,
            }
        )
        defrosting_mode_options = [('Слева направо', DefrostingOrder.left_to_right.value), ('По порядку отправки', DefrostingOrder.order_by_time.value)]
        self.defrosting_mode = pygame_gui.elements.UIDropDownMenu(
            relative_rect=pygame.Rect(25, 10, 200, 30),
            options_list=defrosting_mode_options,
            starting_option=defrosting_mode_options[0],
            manager=self.manager,
            anchors={
                'top_target': self.defrosting_mode_label,
            }
        )
        self.start_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(25, 10, 150, 50),
            text="Запустить!",
            manager=self.manager,
            anchors={
                'top_target': self.defrosting_mode,
            }
        )

        self.help_text = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(25, 25, 500, 300),
            html_text="Справка по управлению:\n"
                      "Стрелка \"вправо\" или клик ЛКМ - следующий шаг разморозки\n"
                      "Кнопка F - переключение полноэкранного/оконного режимов\n"
                      "Кнопка Esc - завершение работы программы",
            manager=self.manager,
            anchors={
                'top_target': self.start_button,
            }
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
                    settings_storage.log_file_path = Path(log_file_path)
                    self.chosen_file_label.text = f"Выбран файл: {settings_storage.log_file_path.name}"
                    self.chosen_file_label.rebuild()
            if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.start_button:
                if settings_storage.log_file_path is not None and self.freeze_duration_entry_line.text.isdigit():
                    settings_storage.freeze_duration_seconds = int(self.freeze_duration_entry_line.text)
                    if self.contest_name_entry_line.text:
                        settings_storage.contest_name = self.contest_name_entry_line.text
                    settings_storage.defrosting_order = DefrostingOrder(self.defrosting_mode.selected_option[1])
                    print(settings_storage.defrosting_order)
                    thread = threading.Thread(
                        target=self.calculate_processor.prepare_defrost_data,
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
