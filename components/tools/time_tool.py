"""
Returns current time and date as a structured dict.

This tool is intentionally trivial. Its purpose in Week 4
is to prove the full tool pipeline end-to-end with zero
risk of a wrong answer — before debugging psutil values.

If "what time is it?" works voice-to-voice, the plumbing is right.
"""

from datetime import datetime


class TimeTool:

    def run(self, query: str) -> dict:
        """
        Return current time and date as a structured dict.
        The formatter (not this class) decides how to speak it.
        """
        now = datetime.now()

        return {
            "hour":        now.hour,
            "minute":      now.minute,
            "second":      now.second,
            "day_name":    now.strftime("%A"),          # "Monday"
            "month_name":  now.strftime("%B"),          # "January"
            "day":         now.day,                     # 14
            "year":        now.year,                    # 2026
            "time_12h":    now.strftime("%I:%M %p"),    # "02:35 PM"
            "date_full":   now.strftime("%A, %B %d, %Y"),  # "Monday, January 14, 2026"
        }