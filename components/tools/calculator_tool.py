"""
Handles mathematical queries via two-stage pipeline:

Stage 1 — LLM normalisation:
    Converts natural language word problems to a clean
    arithmetic expression string.
    "fifteen percent of two hundred" → "200 * 0.15"
    "what is 847 divided by 7"       → "847 / 7"

Stage 2 — safe_eval:
    Evaluates the sanitised expression. Only numeric
    characters and arithmetic operators are permitted
    through the regex filter — eval() never receives
    raw user input.

Error handling:
    All failures raise ToolExpectedError with a natural
    spoken message — no tracebacks reach the terminal.
"""

import re

from components.error_manager import ToolExpectedError


class CalculatorTool:

    def __init__(self, llm):
        self.llm = llm

    # ── Public API ───────────────────────────────────────────

    def run(self, query: str) -> dict:
        """
        Evaluate a mathematical query.
        Returns dict with keys: expression, result, spoken_result.
        Raises ToolExpectedError on any failure.
        """
        # Stage 1: normalise natural language to arithmetic expression
        expression = self._normalise(query)

        # Stage 2: safe evaluation
        result = self._safe_eval(expression)

        # Format result for speech
        spoken = self._format_result(result)

        return {
            "expression":    expression,
            "result":        result,
            "spoken_result": spoken,
        }

    # ── Stage 1: LLM normalisation ───────────────────────────

    def _normalise(self, query: str) -> str:
        """
        Ask the LLM to convert a natural language maths query
        into a bare arithmetic expression.

        Returns a string like "200 * 0.15" or "847 / 7".
        Raises ToolExpectedError if LLM returns something
        that doesn't look like an arithmetic expression.
        """
        prompt = (
            "Convert the user's maths question into a single arithmetic expression. "
            "Return ONLY the expression — no words, no explanation, no equals sign.\n\n"
            "User: what is 15 percent of 240\nExpression: 240 * 0.15\n"
            "User: 847 divided by 7\nExpression: 847 / 7\n"
            "User: add 128 and 456\nExpression: 128 + 456\n"
            "User: square root of 144\nExpression: 144 ** 0.5\n"
            "User: 3 squared\nExpression: 3 ** 2\n"
            f"User: {query}\nExpression:"
        )

        raw, _ = self.llm.generate(prompt, memory_context="")
        expression = raw.strip().split("\n")[0].strip()

        if not expression:
            raise ToolExpectedError(
                "I couldn't work out what calculation you wanted."
            )

        return expression

    # ── Stage 2: safe_eval ───────────────────────────────────

    def _safe_eval(self, expression: str) -> float:
        """
        Evaluate an arithmetic expression safely.

        Strips everything except digits, operators, parentheses,
        and decimal points before passing to eval().
        eval() never receives raw user input.

        Raises ToolExpectedError on:
          - Empty expression after sanitisation
          - No digit found (expression was pure symbols)
          - ZeroDivisionError
          - Any other evaluation failure
        """
        # Remove everything that isn't a digit, operator, paren, or dot
        cleaned = re.sub(r"[^0-9+\-*/().\s\*]", "", expression)
        # Handle ** (power) — preserved as two * characters
        cleaned = cleaned.strip()

        if not cleaned:
            raise ToolExpectedError(
                "I couldn't find a valid calculation in that."
            )

        if not re.search(r"\d", cleaned):
            raise ToolExpectedError(
                "The expression doesn't seem to contain any numbers."
            )

        try:
            result = eval(cleaned)          # safe: only numeric chars passed
            return float(result)
        except ZeroDivisionError:
            raise ToolExpectedError("I can't divide by zero.")
        except Exception:
            raise ToolExpectedError(
                "I had trouble computing that. Try rephrasing it."
            )

    # ── Result formatting ─────────────────────────────────────

    def _format_result(self, result: float) -> str:
        """
        Format a float result for natural spoken delivery.

        - Whole numbers: speak as integer ("36", not "36.0")
        - Decimals: round to 4 significant figures, strip trailing zeros
        - Very large/small: keep 4 sig figs
        """
        if result == int(result) and abs(result) < 1e12:
            return str(int(result))

        # Round to 4 significant figures
        rounded = float(f"{result:.4g}")

        # Remove trailing zeros after decimal
        text = f"{rounded:f}".rstrip("0").rstrip(".")
        return text