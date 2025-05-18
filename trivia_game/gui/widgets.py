# gui/widgets.py

import tkinter as tk
from tkinter import ttk
import config

class TimerLabel(tk.Label):
    """A countdown label with padding, border, and high-contrast colours."""
    def __init__(self, master=None, **kwargs):
        super().__init__(
            master,
            font=config.META_FONT,
            bg=config.COLOR_SECONDARY,
            fg=config.COLOR_TEXT_LIGHT,
            relief=tk.RIDGE,
            bd=2,
            padx=12,
            pady=6,
            **kwargs
        )

    def set_time(self, seconds: int):
        """Update the displayed time."""
        self.config(text=f"⏱ {seconds:2d}s")


class OptionButton(ttk.Button):
    """A styled option button using ttk so background/foreground are obeyed."""
    def __init__(self, master=None, command=None, **kwargs):
        # Ensure our styles exist (harmless to re-run multiple times)
        style = ttk.Style(master)

        # --- Default option style ---
        style.configure(
            "Option.TButton",
            font=config.OPTION_FONT,
            background=config.COLOR_BUTTON_DEFAULT_BG,
            foreground=config.COLOR_TEXT_LIGHT,
            padding=(8, 6),
            wraplength=240,
            justify="center",
            relief="raised",
            borderwidth=2,
        )
        style.map(
            "Option.TButton",
            background=[
                ("!disabled", config.COLOR_BUTTON_DEFAULT_BG),
                ("active",    config.COLOR_PRIMARY),
                ("disabled",  config.COLOR_BUTTON_DEFAULT_BG),
            ],
            foreground=[
                ("!disabled", config.COLOR_TEXT_LIGHT),
                ("disabled",  config.COLOR_DISABLED_BUTTON_TEXT),
            ],
        )

        # --- Correct / Incorrect result styles ---
        style.configure(
            "Correct.TButton",
            font=config.OPTION_FONT,
            background=config.COLOR_CORRECT,
            foreground=config.COLOR_TEXT_LIGHT,
            padding=(8, 6),
            wraplength=240,
            justify="center",
            relief="raised",
            borderwidth=2,
        )
        style.configure(
            "Incorrect.TButton",
            font=config.OPTION_FONT,
            background=config.COLOR_INCORRECT,
            foreground=config.COLOR_TEXT_LIGHT,
            padding=(8, 6),
            wraplength=240,
            justify="center",
            relief="raised",
            borderwidth=2,
        )

        super().__init__(
            master,
            style="Option.TButton",
            command=command,
            **kwargs
        )

    def mark_correct(self):
        """Switch to the green 'correct' style and disable."""
        self.state(["disabled"])
        self.config(style="Correct.TButton")

    def mark_incorrect(self):
        """Switch to the red 'incorrect' style and disable."""
        self.state(["disabled"])
        self.config(style="Incorrect.TButton")

    def reset(self, text: str):
        """Back to the default look and re-enable."""
        self.config(text=text,
                    style="Option.TButton")
        self.state(["!disabled"])
