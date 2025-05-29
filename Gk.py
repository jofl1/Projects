import tkinter as tk
from tkinter import ttk, messagebox
import requests
import random
import html

"""
Tricky Trivia Quiz – polished GUI version
----------------------------------------
A two‑player general‑knowledge quiz that pulls questions from the Open
Trivia Database (https://opentdb.com/).  Players take turns answering
multiple‑choice questions, racing against a per‑question timer.  Scores
are tallied, and the winner is announced at the end with the option to
play again immediately.

Key GUI extras
~~~~~~~~~~~~~~
* Category and difficulty pickers (ttk.Combobox)
* 20‑second countdown timer with auto‑lock on timeout
* Coloured answer feedback (green = correct, red = wrong)
* Window pops to the front when a new game starts
* Wider, cleaner layout with modern fonts
"""

# ────────────────────────────────────────────────────────────────────
# Constants & configuration
# ────────────────────────────────────────────────────────────────────

QUESTION_TIME_LIMIT = 20          # seconds allowed per question
TOTAL_QUESTIONS_PER_GAME = 10

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

COLOR_BACKGROUND = "#0F172A"      # Deep space blue background
COLOR_FRAME_BG = "#1E293B"        # Slate blue for frames/question areas
COLOR_TEXT_DARK = "#E2E8F0"       # Soft silver for text on dark backgrounds
COLOR_TEXT_LIGHT = "#FFFFFF"      # Bright white for high contrast on buttons

# Super Cool Button Colors
COLOR_PRIMARY = "#06B6D4"         # Cyan for primary actions
COLOR_SECONDARY = "#8B5CF6"       # Vibrant purple for secondary actions
COLOR_CORRECT = "#10B981"         # Emerald green for correct answers
COLOR_INCORRECT = "#F43F5E"       # Rose red for incorrect answers
COLOR_BUTTON_DEFAULT_BG = "#3B82F6" # Bright blue for option buttons
COLOR_BUTTON_TEXT = "#FFFFFF"     # White text on buttons for readability
COLOR_DISABLED_BUTTON_TEXT = "#94A3B8" # Slate gray for disabled text

# ────────────────────────────────────────────────────────────────────
# Global game state (mutated in‑place; simple for a single‑window app)
# ────────────────────────────────────────────────────────────────────

questions_data = []
current_question_index = 0
score_player1 = 0
score_player2 = 0
current_player = 1
remaining_time = QUESTION_TIME_LIMIT
_timer_job = None  # after() job id so we can cancel the countdown

# ────────────────────────────────────────────────────────────────────
# Trivia API helper
# ────────────────────────────────────────────────────────────────────

def fetch_questions_from_opentdb(amount=10, category=None, difficulty=None, q_type="multiple"):
    """Return a *list* of processed question dicts or [] on failure."""
    url = "https://opentdb.com/api.php"
    params = {"amount": amount}
    if category:
        params["category"] = category
    if difficulty and difficulty.lower() != "any":
        params["difficulty"] = difficulty.lower()
    params["type"] = q_type

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        messagebox.showerror("Network Error", f"Could not contact OpenTDB: {e}")
        return []

    if data.get("response_code") != 0:
        messagebox.showerror("API Error", f"OpenTDB error code {data.get('response_code')}")
        return []

    processed = []
    for item in data["results"]:
        q_text = html.unescape(item["question"])
        correct = html.unescape(item["correct_answer"])
        options = [html.unescape(ans) for ans in item["incorrect_answers"]] + [correct]
        random.shuffle(options)
        processed.append({
            "question": q_text,
            "options": options,
            "correct": correct,
        })
    return processed

# ────────────────────────────────────────────────────────────────────
# Game‑flow helpers
# ────────────────────────────────────────────────────────────────────

def start_new_game():
    """Reset state, fetch questions, and show the first one."""
    global questions_data, current_question_index, score_player1, score_player2, current_player, remaining_time

    cat_name = category_var.get()
    diff = difficulty_var.get()
    cat_id = CATEGORY_MAP.get(cat_name)

    start_button.config(state=tk.DISABLED, text="Loading…", bg="#B0BEC5", fg=COLOR_TEXT_DARK) # Neutral loading
    root.update_idletasks()

    questions_data = fetch_questions_from_opentdb(TOTAL_QUESTIONS_PER_GAME, cat_id, diff)
    start_button.config(state=tk.NORMAL, text="Start New Game", bg=COLOR_PRIMARY, fg=COLOR_TEXT_LIGHT)

    if not questions_data:
        question_label.config(text="Could not load questions — try again.")
        return

    # Reset scores & pointers
    current_question_index = 0
    score_player1 = score_player2 = 0
    current_player = 1
    remaining_time = QUESTION_TIME_LIMIT

    update_score_display()
    display_question()
    root.lift()
    root.after(100, lambda: root.focus_force())


def display_question():
    """Populate the UI with the current question."""
    global remaining_time, _timer_job

    if _timer_job is not None:
        root.after_cancel(_timer_job)
        _timer_job = None

    if current_question_index >= len(questions_data):
        return end_game()

    q = questions_data[current_question_index]
    question_label.config(text=q["question"])

    for i, text in enumerate(q["options"]):
        b = option_buttons[i]
        b.config(text=text, state=tk.NORMAL, bg=COLOR_BUTTON_DEFAULT_BG, fg=COLOR_BUTTON_TEXT, activebackground="#C5CAE9", activeforeground=COLOR_BUTTON_TEXT)
    for i in range(len(q["options"]), 4):
        option_buttons[i].config(text="", state=tk.DISABLED, bg=COLOR_BACKGROUND, fg=COLOR_DISABLED_BUTTON_TEXT)


    player_turn_label.config(text=f"Player {current_player}'s turn")
    remaining_time = QUESTION_TIME_LIMIT
    timer_label.config(text=f"⏱ {remaining_time}s")
    count_down()


def count_down():
    """Update the timer each second; auto‑lock when it hits 0."""
    global remaining_time, _timer_job

    timer_label.config(text=f"⏱ {remaining_time}s")
    if remaining_time > 0:
        remaining_time -= 1
        _timer_job = root.after(1000, count_down)
    else:
        _timer_job = None
        lock_buttons(None)


def lock_buttons(selected_text):
    """Colour the options; update scores if needed; enable Next."""
    global score_player1, score_player2

    q = questions_data[current_question_index]
    correct = q["correct"]

    for btn in option_buttons:
        txt = btn.cget("text")
        if not txt:
            btn.config(bg=COLOR_BACKGROUND) # Ensure disabled buttons match background
            continue
        if txt == correct:
            btn.config(bg=COLOR_CORRECT, fg=COLOR_TEXT_LIGHT, activebackground=COLOR_CORRECT, activeforeground=COLOR_TEXT_LIGHT)
        elif txt == selected_text:
            btn.config(bg=COLOR_INCORRECT, fg=COLOR_TEXT_LIGHT, activebackground=COLOR_INCORRECT, activeforeground=COLOR_TEXT_LIGHT)
        else: # Other incorrect options, not selected
            btn.config(bg=COLOR_BUTTON_DEFAULT_BG, fg=COLOR_DISABLED_BUTTON_TEXT, activebackground=COLOR_BUTTON_DEFAULT_BG, activeforeground=COLOR_DISABLED_BUTTON_TEXT)

        btn.config(state=tk.DISABLED)


    if selected_text and selected_text == correct:
        if current_player == 1:
            score_player1 += 1
        else:
            score_player2 += 1

    update_score_display()
    next_button.config(state=tk.NORMAL, bg=COLOR_SECONDARY, fg=COLOR_TEXT_LIGHT)


def check_answer(btn):
    """Button callback — stop timer and lock buttons."""
    if _timer_job is not None:
        root.after_cancel(_timer_job)
    selected = btn.cget("text")
    lock_buttons(selected)


def next_question():
    """Advance to the next question, toggling player turn."""
    global current_question_index, current_player
    current_question_index += 1
    current_player = 2 if current_player == 1 else 1
    next_button.config(state=tk.DISABLED, bg="#B0BEC5", fg=COLOR_TEXT_DARK) # Neutral disabled
    display_question()


def update_score_display():
    score_label.config(text=f"P1: {score_player1}   |   P2: {score_player2}")


def end_game():
    """Final scores & replay prompt."""
    if _timer_job is not None:
        root.after_cancel(_timer_job)

    if score_player1 > score_player2:
        result = "Player 1 wins!"
    elif score_player2 > score_player1:
        result = "Player 2 wins!"
    else:
        result = "It's a tie!"

    # Style the messagebox (though this is limited for system dialogs)
    # We can't directly style messagebox, but the app's theme might influence it slightly.
    again = messagebox.askyesno(
        "Game Over",
        f"Final scores:\n\nP1: {score_player1}\nP2: {score_player2}\n\n{result}\n\nPlay again?",
        parent=root # ensures it's on top of the root window
    )
    if again:
        start_new_game()
    else:
        question_label.config(text="Thanks for playing — see you next time!")
        for b in option_buttons:
            b.config(text="", state=tk.DISABLED, bg=COLOR_BACKGROUND)
        next_button.config(state=tk.DISABLED, bg="#B0BEC5", fg=COLOR_TEXT_DARK)
        timer_label.config(text="")

# ────────────────────────────────────────────────────────────────────
# GUI construction
# ────────────────────────────────────────────────────────────────────

root = tk.Tk()
root.title("Tricky Trivia Quiz!")
root.geometry("680x650") # Slightly adjusted for padding
root.configure(bg=COLOR_BACKGROUND)
root.minsize(650, 600)

# Fonts
TITLE_FONT = ("Helvetica", 22, "bold")
QUESTION_FONT = ("Helvetica", 16) # Slightly larger question
OPTION_FONT = ("Helvetica", 12)
BUTTON_FONT = ("Helvetica", 12, "bold") # Bolder for main control buttons
META_FONT = ("Helvetica", 12, "bold")

# --- Style ttk widgets ---
style = ttk.Style(root)
# Available themes: style.theme_names() -> ('winnative', 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative')
# 'clam' or 'alt' can look more modern than 'vista' or 'default' on some systems.
# If you have custom themes or want more control, you'd need to define elements.
# For now, let's pick one that's often available and looks decent.
current_themes = style.theme_names()
if "clam" in current_themes:
    style.theme_use("clam")
elif "alt" in current_themes:
    style.theme_use("alt")
elif "vista" in current_themes: # Fallback
    style.theme_use("vista")

style.configure("TCombobox", fieldbackground=COLOR_FRAME_BG, background=COLOR_BUTTON_DEFAULT_BG, foreground=COLOR_TEXT_DARK, selectbackground=COLOR_BUTTON_DEFAULT_BG, padding=5)
style.map("TCombobox",
    fieldbackground=[("readonly", COLOR_FRAME_BG)],
    selectbackground=[("readonly", COLOR_BACKGROUND)], # Background of the dropdown list items
    selectforeground=[("readonly", COLOR_TEXT_DARK)],  # Text color of the dropdown list items
    foreground=[("readonly", COLOR_TEXT_DARK)]
)
style.configure("TButton", background=COLOR_PRIMARY, foreground=COLOR_TEXT_LIGHT, font=BUTTON_FONT, padding=5)
style.map("TButton",
    background=[("active", "#3C78D8"), ("disabled", "#B0BEC5")], # Darker blue on active, grey disabled
    foreground=[("disabled", COLOR_DISABLED_BUTTON_TEXT)]
)


# Frames
header_frame = tk.Frame(root, bg=COLOR_BACKGROUND)
header_frame.pack(pady=(15, 10)) # More top padding

meta_frame = tk.Frame(root, bg=COLOR_BACKGROUND)
meta_frame.pack(pady=10)

question_frame = tk.Frame(root, bg=COLOR_FRAME_BG, bd=1, relief=tk.SOLID, padx=15, pady=15)
question_frame.pack(fill="x", padx=20, pady=(5, 15), ipady=10) # Added internal padding

options_frame = tk.Frame(root, bg=COLOR_BACKGROUND)
options_frame.pack(pady=10)

control_frame = tk.Frame(root, bg=COLOR_BACKGROUND)
control_frame.pack(pady=(15,20)) # More bottom padding

# Header
tk.Label(header_frame, text="Tricky Trivia Quiz", font=TITLE_FONT, bg=COLOR_BACKGROUND, fg=COLOR_TEXT_DARK).pack()

# Meta labels
player_turn_label = tk.Label(meta_frame, text="Player 1's turn", font=META_FONT, bg=COLOR_BACKGROUND, fg=COLOR_TEXT_DARK)
player_turn_label.grid(row=0, column=0, padx=15)

score_label = tk.Label(meta_frame, text="P1: 0   |   P2: 0", font=META_FONT, bg=COLOR_BACKGROUND, fg=COLOR_TEXT_DARK)
score_label.grid(row=0, column=1, padx=15)

timer_label = tk.Label(meta_frame, text="", font=META_FONT, bg=COLOR_BACKGROUND, fg=COLOR_TEXT_DARK, width=10)
timer_label.grid(row=0, column=2, padx=15)

# Question display
question_label = tk.Label(
    question_frame,
    text="Click 'Start New Game' to begin!",
    font=QUESTION_FONT,
    wraplength=580, # Adjusted for padding
    justify="center",
    bg=COLOR_FRAME_BG,
    fg=COLOR_TEXT_DARK,
    pady=10,
)
question_label.pack(padx=10, pady=10)

# Option buttons
option_buttons = []
for i in range(4):
    btn = tk.Button(
        options_frame,
        text="",
        font=OPTION_FONT,
        width=30, # Slightly wider
        height=2,
        state=tk.DISABLED,
        relief=tk.FLAT, # Flatter button look
        bg=COLOR_BUTTON_DEFAULT_BG,
        fg=COLOR_DISABLED_BUTTON_TEXT, # Start as disabled looking
        activebackground="#C5CAE9", # Light indigo for active (pressed)
        activeforeground=COLOR_BUTTON_TEXT,
        bd=1, # border width
    )
    # Add some padding inside the button if possible (relief and bd affect this)
    btn.grid(row=i // 2, column=i % 2, padx=10, pady=8)
    btn.config(command=lambda b=btn: check_answer(b))
    option_buttons.append(btn)

# Controls — category, difficulty, start, next
category_var = tk.StringVar(value="Any")
difficulty_var = tk.StringVar(value="Any")


cat_label = tk.Label(control_frame, text="Category:", font=OPTION_FONT, bg=COLOR_BACKGROUND, fg=COLOR_TEXT_DARK)
cat_label.grid(row=0, column=0, sticky="e", padx=(0, 5), pady=5)

cat_combo = ttk.Combobox(control_frame, width=20, textvariable=category_var, state="readonly",
                         values=list(CATEGORY_MAP.keys()), font=OPTION_FONT)
cat_combo.grid(row=0, column=1, padx=(0, 20), pady=5)


diff_label = tk.Label(control_frame, text="Difficulty:", font=OPTION_FONT, bg=COLOR_BACKGROUND, fg=COLOR_TEXT_DARK)
diff_label.grid(row=0, column=2, sticky="e", padx=(0, 5), pady=5)

diff_combo = ttk.Combobox(control_frame, width=12, textvariable=difficulty_var, state="readonly",
                          values=DIFFICULTIES, font=OPTION_FONT)
diff_combo.grid(row=0, column=3, padx=(0, 20), pady=5)

start_button = tk.Button(control_frame, text="Start New Game", font=BUTTON_FONT,
                         command=start_new_game, bg=COLOR_PRIMARY, fg=COLOR_TEXT_LIGHT,
                         relief=tk.FLAT, bd=0, activebackground="#3C78D8", activeforeground=COLOR_TEXT_LIGHT,
                         width=16, height=1, padx=10, pady=5) # Added padding
start_button.grid(row=1, column=0, columnspan=2, pady=(15,5), padx=5) # Moved to new row, centered a bit

next_button = tk.Button(control_frame, text="Next", font=BUTTON_FONT, command=next_question,
                        bg="#B0BEC5", fg=COLOR_TEXT_DARK, # Start disabled
                        relief=tk.FLAT, bd=0, activebackground="#64B5F6", activeforeground=COLOR_TEXT_LIGHT,
                        width=12, height=1, padx=10, pady=5, state=tk.DISABLED) # Added padding
next_button.grid(row=1, column=2, columnspan=2, pady=(15,5), padx=5) # Moved to new row

# Keyboard shortcuts
root.bind("<Return>", lambda e: start_button.invoke() if start_button["state"] == tk.NORMAL else None)
root.bind("<space>", lambda e: next_button.invoke() if next_button["state"] == tk.NORMAL else None)

# Run the Tkinter main loop
if __name__ == "__main__":
    root.mainloop()
