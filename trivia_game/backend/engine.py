# backend/engine.py

from backend.models import Question, Player, GameState

class TriviaEngine:
    """
    Manages a two‐player trivia game:
      - Fetch questions via the provided fetcher
      - Keep track of whose turn it is, scores, and current index
      - Check answers and advance turns
    """

    def __init__(self, fetcher, num_questions=10):
        """
        fetcher: instance of OpenTDBFetcher (or any .fetch(amount,cat,diff))
        num_questions: how many to pull each game
        """
        self.fetcher      = fetcher
        self.num_questions = num_questions
        self.state        = GameState()

    def start(self, category=None, difficulty=None):
        """
        Fetches a fresh batch of questions and resets all counters.
        """
        raw = self.fetcher.fetch(self.num_questions, category, difficulty)
        # build Question objects
        self.state.questions = [
            Question(text=item["text"], options=item["options"], correct=item["correct"])
            for item in raw
        ]
        self.state.current_index = 0
        # reset players
        self.state.players = [Player("P1"), Player("P2")]
        self.state.active_player = 0
        self.state.time_left = 0

    def answer(self, choice: str) -> bool:
        """
        Submit a choice for the current question.
        Returns True if correct, False otherwise.
        Updates the active player's score on a correct answer.
        """
        idx = self.state.current_index
        if idx >= len(self.state.questions):
            return False

        q = self.state.questions[idx]
        correct = (choice == q.correct)
        if correct:
            self.state.players[self.state.active_player].score += 1
        return correct

    def next_turn(self):
        """
        Advance to the next question and toggle active player.
        """
        self.state.current_index += 1
        # flip between 0 and 1
        self.state.active_player = 1 - self.state.active_player

    def is_over(self) -> bool:
        """
        True once we've stepped past the last question.
        """
        return self.state.current_index >= len(self.state.questions)
