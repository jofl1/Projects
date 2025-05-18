# backend/models.py

from dataclasses import dataclass, field
from typing import List

@dataclass
class Question:
    text: str
    options: List[str]
    correct: str

@dataclass
class Player:
    name: str
    score: int = 0

@dataclass
class GameState:
    questions: List[Question] = field(default_factory=list)
    current_index: int = 0
    players: List[Player] = field(default_factory=lambda: [Player("P1"), Player("P2")])
    active_player: int = 0   # index into `players`
    time_left: int = 0       # you can let GUI reset this each question
