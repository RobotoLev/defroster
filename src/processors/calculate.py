import pygame

from dataclasses import dataclass
import xml.etree.ElementTree as ET

from .base import BaseProcessor, AppState


class DetailedScoreboard:
    @dataclass
    class User:
        id: str
        displayed_name: str

    @dataclass
    class Submission:
        contest_time_ms: int
        ok: bool

    @dataclass
    class Cell:
        submissions_warm: list['DetailedScoreboard.Submission']
        submissions_frozen: list['DetailedScoreboard.Submission']

        def solved(self) -> bool:
            return any(sub.ok for sub in self.submissions_warm)

        def penalty(self) -> int:
            # in seconds
            first_known_ok = next(filter(lambda tp: tp[1].ok, enumerate(self.submissions_warm)), None)
            if first_known_ok is None:
                return 0
            index, submission = first_known_ok
            return index * 20 * 60 + submission.contest_time_ms // 1000

    @dataclass
    class Line:
        user: 'DetailedScoreboard.User'
        cells: list['DetailedScoreboard.Cell']

        def score(self) -> int:
            return sum(int(cell.solved()) for cell in self.cells)

        def penalty(self) -> int:
            # in minutes
            return sum(cell.penalty() for cell in self.cells) // 60

    @dataclass
    class Problem:
        id: str

    contest_duration_seconds: int
    warm_duration_seconds: int
    problems: list['DetailedScoreboard.Problem'] = []
    problem_lookup: dict[str, int] = {}
    lines: list['DetailedScoreboard.Line'] = []
    _user_lookup: dict[str, int] = {}

    def __init__(self, contest_duration_seconds: int, warm_duration_seconds: int):
        self.contest_duration_seconds = contest_duration_seconds
        self.warm_duration_seconds = warm_duration_seconds

    def add_user(self, user: 'DetailedScoreboard.User'):
        if user.id in self._user_lookup:
            return
        self.lines.append(self.Line(user=user, cells=[self.Cell([], []) for _ in range(len(self.problems))]))
        self._user_lookup[user.id] = len(self.lines) - 1

    def add_problem(self, problem: 'DetailedScoreboard.Problem'):
        if problem.id in self.problem_lookup:
            return
        self.problems.append(problem)
        self.problem_lookup[problem.id] = len(self.problems) - 1

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
        line = self.lines[self._user_lookup[user_id]]
        problem_index = self.problem_lookup[problem_id]
        if submission.contest_time_ms < self.warm_duration_seconds * 1000:
            line.cells[problem_index].submissions_warm.append(submission)
        else:
            line.cells[problem_index].submissions_frozen.append(submission)

    @staticmethod
    def from_yandex_contest_xml(log_file_path: str) -> 'DetailedScoreboard':
        tree = ET.parse(log_file_path)
        root = tree.getroot()

        contest_duration_str = root.find('settings').find('duration').text
        h, m, s = contest_duration_str.split(':')
        contest_duration_seconds = int(h) * 3600 + int(m) * 60 + int(s)
        warm_duration_seconds = contest_duration_seconds - 60 * 60

        scoreboard = DetailedScoreboard(contest_duration_seconds, warm_duration_seconds)

        for problem in root.find('problems').iter('problem'):
            scoreboard.add_problem(scoreboard.Problem(id=problem.attrib['title']))

        for user in root.find('users').iter('user'):
            scoreboard.add_user(scoreboard.User(id=user.attrib['id'], displayed_name=user.attrib['displayedName']))

        for submission in root.find('events').iter('submit'):
            print(submission, submission.attrib)
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

        return scoreboard


class CalculateProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()
        self.detailed_scoreboard: DetailedScoreboard | None = None

    def prepare_defrost_data(self, log_file_path: str):
        self.detailed_scoreboard = DetailedScoreboard.from_yandex_contest_xml(log_file_path)
        print(self.detailed_scoreboard)

    def process(self) -> AppState:
        screen = pygame.display.get_surface()
        screen.fill((128, 128, 128))

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return AppState.QUIT

        pygame.display.flip()
        self.clock.tick(60)
        return AppState.CALCULATE
