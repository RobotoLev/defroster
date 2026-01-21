import threading

import pygame
import pygame.freetype

from dataclasses import dataclass
from typing import Generator
import xml.etree.ElementTree as ET

from .base import BaseProcessor, AppState


FONT = pygame.freetype.SysFont(None, 20)


def fade_color(color1: pygame.Color, color2: pygame.Color, power: float) -> pygame.Color:
    if power < 0:
        power = 0
    if power > 1:
        power = 1
    return pygame.Color([round(x + ((y - x) * power)) for x, y in zip(color1, color2)])


def render_text_to_center(
        text: str,
        color: pygame.Color,
        surface: pygame.Surface,
        rect: pygame.Rect,
        font: pygame.freetype.Font = FONT,
):
    text_surface, text_rect = font.render(text, color)
    text_rect.center = rect.center
    surface.blit(text_surface, text_rect)


class DetailedScoreboard:
    @dataclass
    class User:
        id: str
        displayed_name: str

    @dataclass
    class Problem:
        id: str

    @dataclass
    class Submission:
        contest_time_ms: int
        ok: bool

    class Cell:
        BLINK_COLORS = [pygame.Color("gold1"), pygame.Color("white")]
        BLINK_INTERVAL_MS = 250
        PADDING_X = 15
        PADDING_Y = 10

        def __init__(self, problem_id: str):
            self.submissions_warm: list['DetailedScoreboard.Submission'] = []
            self.submissions_frozen: list['DetailedScoreboard.Submission'] = []
            self.problem_id = problem_id
            self.text = "."
            self.background_color = pygame.Color("white")
            self.text_color = pygame.Color("black")
            self.is_blinking = False
            self.blink_phase = 0
            self.last_blink_time = 0

        def solved(self) -> bool:
            return any(sub.ok for sub in self.submissions_warm)

        def first_known_ok(self) -> tuple[int, 'DetailedScoreboard.Submission'] | None:
            return next(filter(lambda tp: tp[1].ok, enumerate(self.submissions_warm)), None)

        def penalty(self) -> int:
            # in seconds
            first_known_ok = self.first_known_ok()
            if first_known_ok is None:
                return 0
            index, submission = first_known_ok
            return index * 20 * 60 + submission.contest_time_ms // 1000

        def refresh_text_and_background(self):
            first_known_ok = self.first_known_ok()
            if first_known_ok is not None:
                index, submission = first_known_ok
                self.text = f"+ {index}" if index > 0 else "+"
                self.background_color = pygame.Color("green")
            else:
                if len(self.submissions_frozen) > 0:
                    self.text = f"? {len(self.submissions_warm) + len(self.submissions_frozen)}"
                    self.background_color = pygame.Color("gold1")
                else:
                    if len(self.submissions_warm) > 0:
                        self.text = f"- {len(self.submissions_warm)}"
                        self.background_color = pygame.Color("red")
                    else:
                        pass

        def draw(self, surface: pygame.Surface, rect: pygame.Rect):
            label_rect = pygame.Rect(rect.x, rect.y, rect.width, rect.height // 3)
            rect.y += rect.height // 3
            rect.height -= rect.height // 3
            if self.is_blinking:
                self.background_color = fade_color(
                    self.BLINK_COLORS[self.blink_phase],
                    self.BLINK_COLORS[(self.blink_phase + 1) % 2],
                    (pygame.time.get_ticks() - self.last_blink_time) / self.BLINK_INTERVAL_MS,
                )
            render_text_to_center(self.problem_id, self.text_color, surface, label_rect)
            rect.x += self.PADDING_X
            rect.y += self.PADDING_Y
            rect.width -= 2 * self.PADDING_X
            rect.height -= 2 * self.PADDING_Y
            pygame.draw.rect(surface, self.background_color, rect)
            render_text_to_center(self.text, self.text_color, surface, rect)

        def update(self):
            if self.is_blinking:
                current_time = pygame.time.get_ticks()
                if current_time - self.last_blink_time > self.BLINK_INTERVAL_MS:
                    self.blink_phase = (self.blink_phase + 1) % 2
                    self.last_blink_time = current_time

        def start_blinking(self):
            self.is_blinking = True
            self.blink_phase = 0
            self.last_blink_time = pygame.time.get_ticks()

        def stop_blinking(self):
            self.is_blinking = False

    class Row:
        BACKGROUND_COLOR_NORMAL = pygame.Color("deepskyblue")
        BACKGROUND_COLOR_SELECTED = pygame.Color("plum")
        HEIGHT = 120
        NAME_HEIGHT = 40
        PADDING = 5
        CELL_WIDTH = 90
        CELL_HEIGHT = HEIGHT - NAME_HEIGHT - PADDING * 2
        TEXT_COLOR = pygame.Color("black")

        def __init__(self, user: 'DetailedScoreboard.User', cells: list['DetailedScoreboard.Cell']):
            self.user = user
            self.cells = cells
            self.last_submission_time_ms = float('inf')
            self.selected = False
            self.animating = False
            self.current_index: int | None = None
            self.target_index: int | None = None
            self.current_rect: pygame.Rect | None = None
            self.target_rect: pygame.Rect | None = None

        def score(self) -> int:
            return sum(int(cell.solved()) for cell in self.cells)

        def penalty(self) -> int:
            # in minutes
            return sum(cell.penalty() for cell in self.cells) // 60

        def draw(self, surface: pygame.Surface):
            if self.current_rect is None:
                raise NotImplementedError
            pygame.draw.rect(
                surface,
                self.BACKGROUND_COLOR_SELECTED if self.selected else self.BACKGROUND_COLOR_NORMAL,
                self.current_rect,
                width=0,
                border_radius=10,
            )
            name_rect = self.current_rect.copy()
            name_rect.height = self.NAME_HEIGHT
            render_text_to_center(self.user.displayed_name, self.TEXT_COLOR, surface, name_rect)
            place_rect = pygame.Rect(0, self.current_rect.y, self.CELL_WIDTH, self.HEIGHT)
            render_text_to_center(f"{self.current_index + 1}", self.TEXT_COLOR, surface, place_rect)
            for i in range(len(self.cells)):
                rect = pygame.Rect(
                    self.CELL_WIDTH * (i + 1), self.current_rect.y + self.NAME_HEIGHT,
                    self.CELL_WIDTH, self.CELL_HEIGHT
                )
                self.cells[i].draw(surface, rect)
            score_rect = pygame.Rect(
                self.CELL_WIDTH * (len(self.cells) + 1), self.current_rect.y,
                self.CELL_WIDTH, self.HEIGHT,
            )
            render_text_to_center(f"{self.score()}", self.TEXT_COLOR, surface, score_rect)
            penalty_rect = pygame.Rect(
                self.CELL_WIDTH * (len(self.cells) + 2), self.current_rect.y,
                self.CELL_WIDTH, self.HEIGHT,
            )
            render_text_to_center(f"{self.penalty()}", self.TEXT_COLOR, surface, penalty_rect)

        def update(self):
            for cell in self.cells:
                cell.update()

            if self.animating:
                diff = self.target_rect.y - self.current_rect.y
                if abs(diff) < 1:
                    self.current_rect = self.target_rect
                    self.animating = False
                else:
                    if diff > 0:
                        self.current_rect.y += max(1., diff * 0.1)
                    else:
                        self.current_rect.y += min(-1., diff * 0.1)

        def set_index(self, index: int):
            self.current_index = self.target_index = index
            self.current_rect = self.target_rect = self.calc_rect(index)

        def calc_rect(self, index: int) -> pygame.Rect:
            return pygame.Rect(
                0, self.HEIGHT * index + self.PADDING,
                self.CELL_WIDTH * (len(self.cells) + 3), self.HEIGHT - self.PADDING * 2,
            )

        def start_animation(self, target_index):
            self.animating = True
            self.current_index = target_index
            self.target_index = target_index
            self.target_rect = self.calc_rect(target_index)

        def __lt__(self, other: 'DetailedScoreboard.Row') -> bool:
            self_score = self.score()
            other_score = other.score()
            if self_score != other_score:
                return self_score > other_score
            self_penalty = self.penalty()
            other_penalty = other.penalty()
            if self_penalty != other_penalty:
                return self.penalty() < other.penalty()
            return self.last_submission_time_ms < other.last_submission_time_ms

    contest_name: str
    contest_duration_seconds: int
    warm_duration_seconds: int
    problems: list['DetailedScoreboard.Problem'] = []
    problem_lookup: dict[str, int] = {}
    rows: list['DetailedScoreboard.Row'] = []
    _user_lookup: dict[str, int] = {}

    def __init__(self, contest_name: str, contest_duration_seconds: int, warm_duration_seconds: int):
        self.contest_name = contest_name
        self.contest_duration_seconds = contest_duration_seconds
        self.warm_duration_seconds = warm_duration_seconds
        self.defrosting_index: int | None = None

    def add_problem(self, problem: 'DetailedScoreboard.Problem'):
        if problem.id in self.problem_lookup:
            return
        self.problems.append(problem)
        self.problem_lookup[problem.id] = len(self.problems) - 1

    def add_user(self, user: 'DetailedScoreboard.User'):
        if user.id in self._user_lookup:
            return
        self.rows.append(self.Row(
            user=user,
            cells=[self.Cell(problem.id) for problem in self.problems],
        ))
        self._user_lookup[user.id] = len(self.rows) - 1

    def add_submission(
            self,
            user_id: str,
            problem_id: str,
            submission: 'DetailedScoreboard.Submission'
    ):
        if not (0 <= submission.contest_time_ms < self.contest_duration_seconds * 1000) \
                or user_id not in self._user_lookup \
                or problem_id not in self.problem_lookup:
            return
        line = self.rows[self._user_lookup[user_id]]
        problem_index = self.problem_lookup[problem_id]
        if submission.contest_time_ms < self.warm_duration_seconds * 1000:
            line.cells[problem_index].submissions_warm.append(submission)
        else:
            line.cells[problem_index].submissions_frozen.append(submission)
        if line.last_submission_time_ms == float('inf'):
            line.last_submission_time_ms = submission.contest_time_ms
        else:
            line.last_submission_time_ms = max(line.last_submission_time_ms, submission.contest_time_ms)

    @staticmethod
    def from_yandex_contest_xml(log_file_path: str) -> 'DetailedScoreboard':
        tree = ET.parse(log_file_path)
        root = tree.getroot()

        contest_name = root.find('settings').find('contestName').text
        contest_duration_str = root.find('settings').find('duration').text
        h, m, s = contest_duration_str.split(':')
        contest_duration_seconds = int(h) * 60 * 60 + int(m) * 60 + int(s)
        warm_duration_seconds = contest_duration_seconds - 60 * 60

        scoreboard = DetailedScoreboard(contest_name, contest_duration_seconds, warm_duration_seconds)

        for problem in root.find('problems').iter('problem'):
            scoreboard.add_problem(scoreboard.Problem(id=problem.attrib['title']))

        for user in root.find('users').iter('user'):
            scoreboard.add_user(scoreboard.User(id=user.attrib['id'], displayed_name=user.attrib['displayedName']))

        for submission in root.find('events').iter('submit'):
            if 'problemTitle' not in submission.attrib:
                continue
            scoreboard.add_submission(
                user_id=submission.attrib['userId'],
                problem_id=submission.attrib['problemTitle'],
                submission=scoreboard.Submission(
                    contest_time_ms=int(submission.attrib['contestTime']),
                    ok=(submission.attrib['verdict'] == "OK"),
                ),
            )

        scoreboard.rows.sort()
        for index, row in enumerate(scoreboard.rows):
            row.set_index(index)
            for cell in row.cells:
                cell.refresh_text_and_background()

        while len(scoreboard.rows) > 0 and \
                not any(
                    len(cell.submissions_warm) > 0 or len(cell.submissions_frozen) > 0 \
                    for cell in scoreboard.rows[-1].cells
                ):
            scoreboard.rows.pop()

        return scoreboard

    def draw(self, surface: pygame.Surface):
        for row in self.rows:
            row.draw(surface)

    def update(self):
        for row in self.rows:
            row.update()

    def width(self) -> int:
        return self.rows[0].CELL_WIDTH * (len(self.problems) + 3)

    def height(self) -> int:
        return self.Row.HEIGHT * len(self.rows)

    def defrost(self) -> Generator[int]:
        if self.defrosting_index is None:
            self.defrosting_index = len(self.rows) - 1
            self.rows[self.defrosting_index].selected = True
            yield self.defrosting_index
        row = self.rows[self.defrosting_index]
        blinking_cell: 'DetailedScoreboard.Cell | None' = next(filter(lambda cell: cell.is_blinking, row.cells), None)
        if blinking_cell is None:
            freezing_cell = next(filter(lambda cell: len(cell.submissions_frozen) > 0, row.cells), None)
            if freezing_cell is None:
                if self.defrosting_index > 0:
                    row.selected = False
                    self.defrosting_index -= 1
                    self.rows[self.defrosting_index].selected = True
            else:
                freezing_cell.start_blinking()
            yield self.defrosting_index
        else:
            blinking_cell.submissions_warm += blinking_cell.submissions_frozen
            blinking_cell.submissions_frozen.clear()
            blinking_cell.stop_blinking()
            blinking_cell.refresh_text_and_background()
            if blinking_cell.solved():
                new_rows = self.rows[::]
                new_rows.sort()
                new_index = new_rows.index(row)
                print(self.defrosting_index, new_index)
                row.start_animation(target_index=new_index)
                for i in range(new_index, self.defrosting_index):
                    self.rows[i].start_animation(target_index=i+1)
                row.selected = False
                new_rows[self.defrosting_index].selected = True
                self.rows = new_rows[::]
                yield self.defrosting_index
            else:
                yield self.defrosting_index


class CalculateProcessor(BaseProcessor):
    defrost_processor = None

    def __init__(self):
        super().__init__()
        self.detailed_scoreboard: DetailedScoreboard | None = None
        self.preparer_thread: threading.Thread | None = None

    def prepare_defrost_data(self, log_file_path: str):
        self.detailed_scoreboard = DetailedScoreboard.from_yandex_contest_xml(log_file_path)

    def process(self) -> AppState:
        screen = pygame.display.get_surface()
        screen.fill((128, 128, 128))

        if self.preparer_thread is None:
            raise NotImplementedError
        if not self.preparer_thread.is_alive():
            if self.defrost_processor is None:
                raise NotImplementedError
            self.defrost_processor.detailed_scoreboard = self.detailed_scoreboard
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            return AppState.DEFROST

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return AppState.QUIT

        pygame.display.flip()
        self.clock.tick(60)
        return AppState.CALCULATE


class DefrostProcessor(BaseProcessor):
    detailed_scoreboard: DetailedScoreboard | None = None
    BACKGROUND_COLOR = pygame.Color("palegreen")

    def __init__(self):
        super().__init__()
        self.defrost_started = False
        self.fullscreen = True
        self.defrosting_index: int | None = None

        self.animating = False
        self.current_y: int | None = None
        self.target_y: int | None = None

    def toggle_fullscreen(self):
        if self.fullscreen:
            pygame.display.toggle_fullscreen()
        else:
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.fullscreen = not self.fullscreen

    def process(self) -> AppState:
        if self.detailed_scoreboard is None:
            raise NotImplementedError

        if self.defrosting_index is None:
            self.defrosting_index = next(self.detailed_scoreboard.defrost(), None)
            self.current_y = self.target_y = self.detailed_scoreboard.Row.HEIGHT * (2 - self.defrosting_index)

        screen = pygame.display.get_surface()
        screen.fill(self.BACKGROUND_COLOR)

        scoreboard_surface = pygame.Surface(
            (self.detailed_scoreboard.width(), self.detailed_scoreboard.height())
        )
        scoreboard_surface.fill(self.BACKGROUND_COLOR)
        self.detailed_scoreboard.draw(scoreboard_surface)
        screen.blit(
            scoreboard_surface,
            (
                (screen.width - scoreboard_surface.width) // 2,
                self.current_y,
            ),
        )

        name_surface = pygame.Surface((screen.width, self.detailed_scoreboard.Row.HEIGHT))
        name_surface.fill(self.BACKGROUND_COLOR)
        render_text_to_center(
            self.detailed_scoreboard.contest_name,
            pygame.Color("black"),
            name_surface,
            name_surface.get_rect(),
            pygame.freetype.SysFont(None, 32)
        )
        screen.blit(name_surface, (0, 0))

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return AppState.QUIT
            if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                self.toggle_fullscreen()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
                new_defrosting_index = next(self.detailed_scoreboard.defrost())
                if new_defrosting_index != self.defrosting_index:
                    self.target_y += self.detailed_scoreboard.Row.HEIGHT
                    self.animating = True
                    self.defrosting_index = new_defrosting_index

        self.detailed_scoreboard.update()
        if self.animating:
            diff = self.target_y - self.current_y
            if abs(diff) < 1:
                self.current_y = self.target_y
                self.animating = False
            else:
                self.current_y += max(1., diff * 0.1)


        pygame.display.flip()
        self.clock.tick(30)
        return AppState.DEFROST
