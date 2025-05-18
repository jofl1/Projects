# config.py
# ────────────────────────────────────────────────────────────────────
# Game settings
# ────────────────────────────────────────────────────────────────────

QUESTION_TIME_LIMIT       = 20
TOTAL_QUESTIONS_PER_GAME  = 10

CATEGORY_MAP = {
    "Any": None,
    "General Knowledge": 9,
    "Books": 10,
    "Film": 11,
    "Music": 12,
    "Science & Nature": 17,
    "Sports": 21,
    "Geography": 22,
    "History": 23,
    "Politics": 24,
    "Art": 25,
    "Celebrities": 26,
}

DIFFICULTIES = ["Any", "easy", "medium", "hard"]


# ────────────────────────────────────────────────────────────────────
# Colour palette
# ────────────────────────────────────────────────────────────────────

COLOR_BACKGROUND           = "#0F172A"
COLOR_FRAME_BG             = "#1E293B"
COLOR_TEXT_DARK            = "#E2E8F0"
COLOR_TEXT_LIGHT           = "#FFFFFF"

COLOR_PRIMARY              = "#06B6D4"
COLOR_SECONDARY            = "#8B5CF6"
COLOR_CORRECT              = "#10B981"
COLOR_INCORRECT            = "#F43F5E"

COLOR_BUTTON_DEFAULT_BG    = "#3B82F6"
COLOR_DISABLED_BUTTON_TEXT = "#94A3B8"


# ────────────────────────────────────────────────────────────────────
# Fonts (needed by gui/widgets.py)
# ────────────────────────────────────────────────────────────────────

TITLE_FONT    = ("Helvetica", 22, "bold")
QUESTION_FONT = ("Helvetica", 16)
OPTION_FONT   = ("Helvetica", 12)
BUTTON_FONT   = ("Helvetica", 12, "bold")
META_FONT     = ("Helvetica", 12, "bold")

