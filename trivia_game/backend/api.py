# backend/api.py

import requests
import random
import html

class OpenTDBFetcher:
    """Fetches trivia questions from https://opentdb.com/"""
    BASE_URL = "https://opentdb.com/api.php"

    def __init__(self, session=None):
        # allow injecting a requests‐compatible session for testing
        self.session = session or requests

    def fetch(self, amount=10, category=None, difficulty=None, q_type="multiple"):
        """
        Returns a list of dicts: { 'text': str, 'options': [str,...], 'correct': str }
        or [] on any error / non-zero response_code.
        """
        params = {"amount": amount, "type": q_type}
        if category is not None:
            params["category"] = category
        if difficulty and difficulty.lower() != "any":
            params["difficulty"] = difficulty.lower()

        try:
            resp = self.session.get(self.BASE_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        if data.get("response_code") != 0:
            return []

        processed = []
        for item in data["results"]:
            q_text  = html.unescape(item["question"])
            correct = html.unescape(item["correct_answer"])
            opts    = [html.unescape(ans) for ans in item["incorrect_answers"]] + [correct]
            random.shuffle(opts)
            processed.append({
                "text":    q_text,
                "options": opts,
                "correct": correct,
            })
        return processed
