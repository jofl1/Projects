# gui/app.py

import tkinter as tk
from tkinter import ttk, messagebox

from backend.api import OpenTDBFetcher
from backend.engine import TriviaEngine
import config

from gui.widgets import TimerLabel, OptionButton


# ────────────────────────────────────────────────────────────────────
# Fonts
# ────────────────────────────────────────────────────────────────────
TITLE_FONT    = ("Helvetica", 22, "bold")
QUESTION_FONT = ("Helvetica", 16)
OPTION_FONT   = ("Helvetica", 12)
BUTTON_FONT   = ("Helvetica", 12, "bold")
META_FONT     = ("Helvetica", 12, "bold")


class TriviaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tricky Trivia Quiz")
        self.geometry("680x650")
        self.minsize(650, 600)
        self.configure(bg=config.COLOR_BACKGROUND)

        # Backend engine
        self.engine = TriviaEngine(
            fetcher=OpenTDBFetcher(),
            num_questions=config.TOTAL_QUESTIONS_PER_GAME
        )

        self._build_styles()
        self._build_widgets()
        self._layout_widgets()
        self._bind_keys()

    def _build_styles(self):
        style = ttk.Style(self)
        for theme in ("clam", "alt", "vista"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break

        style.configure("TCombobox",
                        fieldbackground=config.COLOR_FRAME_BG,
                        background=config.COLOR_BUTTON_DEFAULT_BG,
                        foreground=config.COLOR_TEXT_DARK,
                        padding=5)
        style.map("TCombobox",
                  fieldbackground=[("readonly", config.COLOR_FRAME_BG)],
                  selectbackground=[("readonly", config.COLOR_BACKGROUND)],
                  selectforeground=[("readonly", config.COLOR_TEXT_DARK)])

        style.configure("TButton",
                        background=config.COLOR_PRIMARY,
                        foreground=config.COLOR_TEXT_LIGHT,
                        font=BUTTON_FONT,
                        padding=5)
        style.map("TButton",
                  background=[("active", "#3C78D8"), ("disabled", "#B0BEC5")],
                  foreground=[("disabled", config.COLOR_DISABLED_BUTTON_TEXT)])
        
        style.configure(
            "Option.TButton",
            font=config.OPTION_FONT,
            background=config.COLOR_BUTTON_DEFAULT_BG,
            foreground=config.COLOR_TEXT_LIGHT,
            padding=(8,6),
            wraplength=240,
            justify="center",
            relief="raised",
            borderwidth=2,
        )
        style.map(
            "Option.TButton",
            background=[
                ("!disabled", config.COLOR_BUTTON_DEFAULT_BG),
                ("active",   config.COLOR_PRIMARY),
                ("disabled", config.COLOR_BUTTON_DEFAULT_BG),
            ],
            foreground=[
                ("!disabled", config.COLOR_TEXT_LIGHT),
                ("disabled",  config.COLOR_DISABLED_BUTTON_TEXT),
            ],
        )


    def _build_widgets(self):
        # Category & difficulty
        self.category_var   = tk.StringVar(value="Any")
        self.difficulty_var = tk.StringVar(value="Any")

        # Header
        self.header_frame = tk.Frame(self, bg=config.COLOR_BACKGROUND)
        self.title_lbl    = tk.Label(
            self.header_frame,
            text="Tricky Trivia Quiz",
            font=TITLE_FONT,
            bg=config.COLOR_BACKGROUND,
            fg=config.COLOR_TEXT_DARK
        )

        # Meta info
        self.meta_frame        = tk.Frame(self, bg=config.COLOR_BACKGROUND)
        self.player_turn_label = tk.Label(
            self.meta_frame,
            text="Player 1's turn",
            font=META_FONT,
            bg=config.COLOR_BACKGROUND,
            fg=config.COLOR_TEXT_DARK
        )
        self.score_label       = tk.Label(
            self.meta_frame,
            text="P1: 0   |   P2: 0",
            font=META_FONT,
            bg=config.COLOR_BACKGROUND,
            fg=config.COLOR_TEXT_DARK
        )
        self.timer_label       = TimerLabel(self.meta_frame)

        # Question area
        self.question_frame = tk.Frame(
            self,
            bg=config.COLOR_FRAME_BG,
            bd=1, relief=tk.SOLID,
            padx=15, pady=15
        )
        self.question_lbl   = tk.Label(
            self.question_frame,
            text="Click 'Start New Game' to begin!",
            font=QUESTION_FONT,
            wraplength=580,
            justify="center",
            bg=config.COLOR_FRAME_BG,
            fg=config.COLOR_TEXT_DARK
        )

        # Option buttons
        self.options_frame  = tk.Frame(self, bg=config.COLOR_BACKGROUND)
        self.option_buttons = []
        for i in range(4):
            btn = OptionButton(
                self.options_frame,
                command=lambda idx=i: self._on_answer(idx)
            )
            btn.grid(row=i//2, column=i%2, padx=10, pady=8)
            self.option_buttons.append(btn)

        # Controls (category/difficulty, start, next)
        self.control_frame = tk.Frame(self, bg=config.COLOR_BACKGROUND)
        self.cat_label     = tk.Label(
            self.control_frame,
            text="Category:",
            font=OPTION_FONT,
            bg=config.COLOR_BACKGROUND,
            fg=config.COLOR_TEXT_DARK
        )
        self.cat_combo     = ttk.Combobox(
            self.control_frame,
            width=20,
            textvariable=self.category_var,
            state="readonly",
            values=list(config.CATEGORY_MAP.keys()),
            font=OPTION_FONT
        )
        self.diff_label    = tk.Label(
            self.control_frame,
            text="Difficulty:",
            font=OPTION_FONT,
            bg=config.COLOR_BACKGROUND,
            fg=config.COLOR_TEXT_DARK
        )
        self.diff_combo    = ttk.Combobox(
            self.control_frame,
            width=12,
            textvariable=self.difficulty_var,
            state="readonly",
            values=config.DIFFICULTIES,
            font=OPTION_FONT
        )
        self.start_btn     = tk.Button(
            self.control_frame,
            text="Start New Game",
            font=BUTTON_FONT,
            command=self._on_start,
            bg=config.COLOR_PRIMARY,
            fg=config.COLOR_TEXT_LIGHT,
            relief=tk.FLAT, bd=0,
            width=16, height=1
        )
        self.next_btn      = tk.Button(
            self.control_frame,
            text="Next",
            font=BUTTON_FONT,
            command=self._on_next,
            bg="#B0BEC5",
            fg=config.COLOR_TEXT_DARK,
            relief=tk.FLAT, bd=0,
            width=12, height=1,
            state=tk.DISABLED
        )

    def _layout_widgets(self):
        # Header
        self.header_frame.pack(pady=(15,10))
        self.title_lbl.pack()

        # Meta
        self.meta_frame.pack(pady=10)
        self.player_turn_label.grid(row=0, column=0, padx=15)
        self.score_label.grid(row=0, column=1, padx=15)
        self.timer_label.grid(row=0, column=2, padx=15)

        # Question
        self.question_frame.pack(fill="x", padx=20, pady=(5,15), ipady=10)
        self.question_lbl.pack()

        # Options
        self.options_frame.pack(pady=10)

        # Controls
        self.control_frame.pack(pady=(15,20))
        self.cat_label.grid(row=0, column=0, sticky="e", padx=(0,5), pady=5)
        self.cat_combo.grid(row=0, column=1, padx=(0,20), pady=5)
        self.diff_label.grid(row=0, column=2, sticky="e", padx=(0,5), pady=5)
        self.diff_combo.grid(row=0, column=3, padx=(0,20), pady=5)
        self.start_btn.grid(row=1, column=0, columnspan=2, pady=(15,5), padx=5)
        self.next_btn.grid(row=1, column=2, columnspan=2, pady=(15,5), padx=5)

    def _bind_keys(self):
        self.bind("<Return>", lambda e: self.start_btn.invoke()
                  if self.start_btn["state"] == tk.NORMAL else None)
        self.bind("<space>", lambda e: self.next_btn.invoke()
                  if self.next_btn["state"] == tk.NORMAL else None)

    # ────────────────────────────────────────────────────────────────────
    # Game-flow callbacks
    # ────────────────────────────────────────────────────────────────────
    def _on_start(self):
        cat_name = self.category_var.get()
        diff     = self.difficulty_var.get()
        cat_id   = config.CATEGORY_MAP.get(cat_name)

        # disable while loading
        self.start_btn.config(state=tk.DISABLED, text="Loading…")
        self.update_idletasks()

        self.engine.start(category=cat_id, difficulty=diff)

        # restore start button
        self.start_btn.config(state=tk.NORMAL, text="Start New Game")
        if not self.engine.state.questions:
            self.question_lbl.config(
                text="Could not load questions — try again."
            )
            return

        self._update_score_display()
        self._show_question()
        self.lift()
        self.after(100, lambda: self.focus_force())

    def _show_question(self):
        gs = self.engine.state
        q  = gs.questions[gs.current_index]

        # reset timer
        gs.time_left = config.QUESTION_TIME_LIMIT

        # question text
        self.question_lbl.config(text=q.text)

        # reset & show only available options
        for i, opt in enumerate(q.options):
            self.option_buttons[i].reset(opt)
        for i in range(len(q.options), 4):
            self.option_buttons[i].config(
                text="", state=tk.DISABLED
            )

        # update meta labels
        self.player_turn_label.config(
            text=f"Player {gs.active_player+1}'s turn"
        )
        self.next_btn.config(state=tk.DISABLED)

        # start countdown
        self._countdown()

    def _countdown(self):
        gs = self.engine.state
        self.timer_label.set_time(gs.time_left)
        if gs.time_left > 0:
            gs.time_left -= 1
            self.after(1000, self._countdown)
        else:
            self._lock_options(selected_idx=None)

    def _on_answer(self, idx):
        # stop any pending countdown
        self.after_cancel(self._countdown)

        btn     = self.option_buttons[idx]
        choice  = btn.cget("text")
        correct = self.engine.answer(choice)

        self._lock_options(selected_idx=idx)

    def _lock_options(self, selected_idx):
        gs = self.engine.state
        q  = gs.questions[gs.current_index]

        for i, btn in enumerate(self.option_buttons):
            text = btn.cget("text")
            if not text:
                continue
            # disable every button
            btn.config(state=tk.DISABLED)

            # colour it
            if text == q.correct:
                btn.mark_correct()
            elif i == selected_idx:
                btn.mark_incorrect()

        self._update_score_display()
        self.next_btn.config(state=tk.NORMAL)

    def _on_next(self):
        self.engine.next_turn()
        if self.engine.is_over():
            self._end_game()
        else:
            self._show_question()

    def _update_score_display(self):
        p1, p2 = self.engine.state.players
        self.score_label.config(
            text=f"P1: {p1.score}   |   P2: {p2.score}"
        )

    def _end_game(self):
        p1, p2 = self.engine.state.players
        if p1.score > p2.score:
            result = "Player 1 wins!"
        elif p2.score > p1.score:
            result = "Player 2 wins!"
        else:
            result = "It's a tie!"

        again = messagebox.askyesno(
            "Game Over",
            f"P1: {p1.score}\nP2: {p2.score}\n\n"
            f"{result}\n\nPlay again?",
            parent=self
        )
        if again:
            self._on_start()
        else:
            self.question_lbl.config(
                text="Thanks for playing — see you next time!"
            )
            for b in self.option_buttons:
                b.config(text="", state=tk.DISABLED)
            self.next_btn.config(state=tk.DISABLED)
            self.timer_label.set_time(0)


if __name__ == "__main__":
    app = TriviaApp()
    app.mainloop()

