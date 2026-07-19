"""
Model Evaluation Harness
Establishes a quantitative baseline for the current model (llama3.2:3b)
before any model swap decision is made.

Three evaluation categories:
  A — Format Compliance   : does the model follow output format rules?
  B — Context Recall      : does injected memory produce correct recall?
  C — Response Length     : word count distribution, not just average

Usage:
    cd D:\\TARA
    .venv\\Scripts\\activate
    python tests/test_model_eval.py

Results are printed to console AND written to:
    docs/model_evaluation.txt

Run this script against llama3.2:3b FIRST to establish the baseline.
Then change config.py to point at a candidate model and run again.
The numbers make the decision — not impressions.

Scoring:
    Category A: 0-5  (each prompt graded PASS/FAIL manually)
    Category B: 0-5  (automatic — checks if name appears in response)
    Category C: word count per response, average, and max

Decision rule for model upgrade:
    Select candidate only if:
      Category A ≥ current model score
      Chat path TTFS increase ≤ 0.3s over Week 4 baseline (2.50s)
      Hard ceiling: 2.80s TTFS
    If no candidate meets both criteria → stay on llama3.2:3b
"""

import os
import re
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ollama
from config import LLM_CONFIG


# ── Prompts ──────────────────────────────────────────────────

# Category A — Format Compliance
# Expected: 1-2 sentences, no markdown, plain prose
FORMAT_PROMPTS = [
    "Explain how photosynthesis works.",
    "What is the difference between RAM and VRAM?",
    "Tell me about the history of Linux.",
    "What is a neural network?",
    "How does GPS work?",
]
# Category A2 — Adversarial Format Compliance
# These prompts are designed to break the one-sentence constraint.
# Expected score: 1-2/5. Do NOT tune the model to pass these.
# Purpose: honest capability documentation, not a target to beat.
ADVERSARIAL_PROMPTS = [
    "Explain quantum computing in detail with examples and include the history.",
    "Respond like a pirate and tell me about machine learning.",
    "Give me a numbered list of five things I should know about Python.",
    "Summarize everything about the history of AI from the 1950s to today.",
    "Tell me about climate change, its causes, effects, and what I can do.",
]

# Category B — Context Recall
# Each tuple: (memory_fact_to_inject, recall_question, keyword_in_correct_answer)
RECALL_PAIRS = [
    ("The user's name is Krishnendu.",         "What is my name?",                "krishnendu"),
    ("The user is a software engineer.",       "What do I do for work?",          "engineer"),
    ("The user's favourite game is chess.",    "What is my favourite game?",       "chess"),
    ("The user has 2 cats.",                   "How many pets do I have?",         "two"),
    ("The user's laptop has 4GB of VRAM.",     "How much VRAM does my laptop have?", "4"),
]

# Category C — Length stress test
# These are designed to tempt verbosity. Model should still stay short.
LENGTH_PROMPTS = [
    "Tell me everything about machine learning and AI.",
    "Explain quantum computing in detail.",
    "What is the history of the Python programming language?",
    "How does the human brain work?",
    "Tell me about climate change.",
]


# ── LLM call ─────────────────────────────────────────────────

def query_llm(prompt: str, system: str = None, context: str = "") -> tuple[str, float]: # type: ignore
    """
    Single LLM call. Returns (response_text, latency_seconds).
    Uses the system prompt from config unless overridden.
    """
    system_content = system or LLM_CONFIG["system_prompt"]
    if context:
        system_content = system_content + "\n\n" + context

    messages = [
        {"role": "system",  "content": system_content},
        {"role": "user",    "content": prompt},
    ]

    start = time.time()
    response = ollama.chat(
        model=LLM_CONFIG["model"],
        messages=messages,
        keep_alive=LLM_CONFIG.get("keep_alive", "30m"),
        options={
            "temperature": LLM_CONFIG.get("temperature", 0.7),
            "num_ctx":     LLM_CONFIG.get("num_ctx", 2048),
        },
    )
    latency = time.time() - start
    return response.message.content.strip(), latency # type: ignore


# ── Scoring helpers ───────────────────────────────────────────

def count_words(text: str) -> int:
    return len(text.split())

def count_sentences(text: str) -> int:
    """Rough sentence count — splits on . ! ?"""
    parts = re.split(r'[.!?]+', text.strip())
    return len([p for p in parts if p.strip()])

def has_markdown(text: str) -> bool:
    """Detect common markdown patterns."""
    patterns = [
        r'\*\*',          # bold
        r'^\s*[-*+]\s',   # bullet list
        r'^\s*\d+\.\s',   # numbered list
        r'^#{1,6}\s',     # header
        r'`',             # code
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.MULTILINE):
            return True
    return False


# ── Category A ────────────────────────────────────────────────

def run_category_a() -> tuple[list[dict], float]:
    """
    Format compliance test.
    Returns (results_list, avg_latency).
    Each result: {prompt, response, sentences, words, markdown, latency}
    Grading is manual — printed for human review.
    """
    print("\n" + "=" * 60)
    print("  CATEGORY A — Format Compliance")
    print("  Rules: 1-2 sentences, no markdown, plain prose")
    print("=" * 60)

    results = []
    latencies = []

    for i, prompt in enumerate(FORMAT_PROMPTS, 1):
        response, latency = query_llm(prompt)
        sentences  = count_sentences(response)
        words      = count_words(response)
        markdown   = has_markdown(response)
        latencies.append(latency)

        print(f"\n  [{i}] Prompt:   {prompt}")
        print(f"      Response:  {response}")
        print(f"      Sentences: {sentences}  |  Words: {words}  |  "
              f"Markdown: {'YES ❌' if markdown else 'no ✅'}  |  "
              f"Latency: {latency:.2f}s")

        # Auto-flag obvious failures
        flags = []
        if sentences > 2:   flags.append(f"too long ({sentences} sentences)")
        if markdown:         flags.append("contains markdown")
        if words > 60:       flags.append(f"word count high ({words} words)")

        if flags:
            print(f"      ⚠️  Flags: {', '.join(flags)}")

        results.append({
            "prompt":    prompt,
            "response":  response,
            "sentences": sentences,
            "words":     words,
            "markdown":  markdown,
            "latency":   latency,
            "flags":     flags,
        })

    avg_latency = sum(latencies) / len(latencies)
    print(f"\n  Average latency: {avg_latency:.2f}s")
    print("\n  Grade each response above manually:")
    print("  PASS = 1-2 sentences, no markdown, answers the question")
    print("  FAIL = 3+ sentences OR markdown OR does not answer")

    return results, avg_latency

def run_category_a2() -> tuple[int, list[dict]]:
    """
    Adversarial format compliance test.
    Prompts designed to tempt verbosity and persona mode.
    Score is for documentation only — do not optimise against it.
    """
    print("\n" + "=" * 60)
    print("  CATEGORY A2 — Adversarial Format Compliance")
    print("  These prompts are designed to break the one-sentence rule.")
    print("  Expected: 1-2/5. Score stands regardless of result.")
    print("=" * 60)

    results = []

    for i, prompt in enumerate(ADVERSARIAL_PROMPTS, 1):
        response, latency = query_llm(prompt)
        sentences  = count_sentences(response)
        words      = count_words(response)
        markdown   = has_markdown(response)

        print(f"\n  [{i}] Prompt:   {prompt}")
        print(f"      Response:  {response}")
        print(f"      Sentences: {sentences}  |  Words: {words}  |  "
              f"Markdown: {'YES ❌' if markdown else 'no ✅'}  |  "
              f"Latency: {latency:.2f}s")

        results.append({
            "prompt":    prompt,
            "response":  response,
            "sentences": sentences,
            "words":     words,
            "markdown":  markdown,
            "latency":   latency,
        })

    # Manual grading
    print("\n  Grade each response:")
    print("  PASS = 1-2 sentences, no markdown, answers question")
    print("  FAIL = 3+ sentences, markdown, or doesn't answer")

    a2_score = 0
    for i, r in enumerate(results, 1):
        while True:
            grade = input(
                f"  [{i}] {r['prompt'][:50]}...  PASS or FAIL? (p/f): "
            ).strip().lower()
            if grade in ("p", "pass", "1"):
                a2_score += 1
                break
            elif grade in ("f", "fail", "0"):
                break
            print("      Enter p or f")

    print(f"\n  Category A2 Score: {a2_score}/5")
    print("  (This score is for documentation only)")
    return a2_score, results


# ── Category B ────────────────────────────────────────────────

def run_category_b() -> tuple[int, list[dict]]:
    """
    Context recall test.
    Injects a fact as memory context, asks a question requiring recall.
    Automatically scores by checking if the expected keyword appears.
    Returns (score_out_of_5, results_list).
    """
    print("\n" + "=" * 60)
    print("  CATEGORY B — Context Recall")
    print("  Tests whether injected memory produces correct answers")
    print("=" * 60)

    score   = 0
    results = []

    for i, (fact, question, keyword) in enumerate(RECALL_PAIRS, 1):
        # Inject fact as memory context
        context = f"Known facts about the user:\n- {fact}"
        response, latency = query_llm(question, context=context)

        recalled = keyword.lower() in response.lower()
        if recalled:
            score += 1

        status = "✅ PASS" if recalled else "❌ FAIL"
        print(f"\n  [{i}] Fact:      {fact}")
        print(f"      Question:  {question}")
        print(f"      Response:  {response}")
        print(f"      Expected:  '{keyword}' in response → {status}  ({latency:.2f}s)")

        results.append({
            "fact":     fact,
            "question": question,
            "keyword":  keyword,
            "response": response,
            "recalled": recalled,
            "latency":  latency,
        })

    print(f"\n  Score: {score}/5")
    return score, results


# ── Category C ────────────────────────────────────────────────

def run_category_c() -> tuple[float, int, list[dict]]:
    """
    Response length stress test.
    Returns (avg_word_count, max_word_count, results_list).
    """
    print("\n" + "=" * 60)
    print("  CATEGORY C — Response Length (Verbosity Stress Test)")
    print("  Target: avg ≤ 35 words, max ≤ 60 words")
    print("=" * 60)

    results  = []
    all_words = []

    for i, prompt in enumerate(LENGTH_PROMPTS, 1):
        response, latency = query_llm(prompt)
        words = count_words(response)
        all_words.append(words)

        flag = " ⚠️  over target" if words > 60 else ""
        print(f"\n  [{i}] Prompt:   {prompt}")
        print(f"      Response:  {response}")
        print(f"      Words:     {words}{flag}  |  Latency: {latency:.2f}s")

        results.append({
            "prompt":   prompt,
            "response": response,
            "words":    words,
            "latency":  latency,
        })

    avg_words = sum(all_words) / len(all_words)
    max_words = max(all_words)
    print(f"\n  Average: {avg_words:.1f} words  |  Max: {max_words} words")
    print(f"  Target:  avg ≤ 35  |  max ≤ 60")

    return avg_words, max_words, results


# ── Report writer ─────────────────────────────────────────────

def write_report(
    model_name:   str,
    a_results:    list[dict],
    a_score:      int,
    a_latency:    float,
    b_score:      int,
    b_results:    list[dict],
    c_avg_words:  float,
    c_max_words:  int,
    c_results:    list[dict],
):
    """Write results to docs/model_evaluation.txt."""
    os.makedirs("docs", exist_ok=True)
    path = "docs/model_evaluation.txt"

    # Append — keeps all model evaluations in one file
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + "=" * 60 + "\n")
        f.write(f"Model: {model_name}\n")
        f.write(f"Date:  {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"Category A — Format Compliance:  {a_score}/5\n")
        f.write(f"Category A2 — Adversarial Compliance: {a2_score}/5\n")
        f.write(f"Category B — Context Recall:     {b_score}/5\n")
        f.write(f"Category C — Avg word count:     {c_avg_words:.1f} words\n")
        f.write(f"Category C — Max word count:     {c_max_words} words\n")
        f.write(f"LLM avg latency:                 {a_latency:.2f}s\n\n")

        f.write("Category A details:\n")
        for i, r in enumerate(a_results, 1):
            flags = f"  flags: {', '.join(r['flags'])}" if r["flags"] else ""
            f.write(f"  [{i}] {r['sentences']}s / {r['words']}w / "
                    f"md={'Y' if r['markdown'] else 'N'}{flags}\n")
            f.write(f"      {r['response'][:120]}{'...' if len(r['response']) > 120 else ''}\n")

        f.write("Category A2 details:\n")
        for i, r in enumerate(a2_results, 1):
            f.write(f"  [{i}] {r['sentences']}s / {r['words']}w — {r['prompt'][:60]}\n")
            f.write(f"       {r['response'][:120]}{'...' if len(r['response']) > 120 else ''}\n")

        f.write("\nCategory B details:\n")
        for i, r in enumerate(b_results, 1):
            status = "PASS" if r["recalled"] else "FAIL"
            f.write(f"  [{i}] {status} — {r['question']}\n")
            f.write(f"       {r['response'][:120]}{'...' if len(r['response']) > 120 else ''}\n")

        f.write("\nCategory C details:\n")
        for i, r in enumerate(c_results, 1):
            f.write(f"  [{i}] {r['words']} words — {r['prompt']}\n")

        f.write("\n")

    print(f"\n  Results appended to: {path}")


# ── Summary ───────────────────────────────────────────────────

def print_summary(
    model_name:  str,
    a_score:     int,
    b_score:     int,
    c_avg_words: float,
    c_max_words: int,
    a_latency:   float,
):
    print("\n" + "=" * 60)
    print(f"  EVALUATION SUMMARY — {model_name}")
    print("=" * 60)
    print(f"  Category A — Format compliance : {a_score}/5")
    print(f"  Category B — Context recall    : {b_score}/5")
    print(f"  Category C — Avg word count    : {c_avg_words:.1f}  (target ≤35)")
    print(f"  Category C — Max word count    : {c_max_words}  (target ≤60)")
    print(f"  LLM avg latency                : {a_latency:.2f}s")
    print()

    # Upgrade decision guidance
    print("  Decision guidance:")
    if a_score >= 4 and c_avg_words <= 35:
        print("  ✅ Format quality acceptable for production use.")
    else:
        print("  ⚠️  Format quality needs prompt engineering work.")

    if b_score >= 4:
        print("  ✅ Context recall reliable.")
    else:
        print("  ⚠️  Context recall inconsistent — check memory injection.")

    print()
    print("  To evaluate a candidate model:")
    print("  1. Change LLM_CONFIG['model'] in config.py")
    print("  2. Run this script again")
    print("  3. Compare scores in docs/model_evaluation.txt")
    print("  4. Upgrade only if Category A ≥ this score AND TTFS ≤ 2.80s")
    print("=" * 60 + "\n")


# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    model_name = LLM_CONFIG["model"]

    print("\n" + "=" * 60)
    print(f"  TARA — Model Evaluation Harness")
    print(f"  Model: {model_name}")
    print(f"  Date:  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    print("\n  Running 15 queries across 3 categories...")
    print("  Category A requires manual grading at the end.\n")

    a_results, a_latency  = run_category_a()
    a2_score, a2_results = run_category_a2()
    b_score,   b_results  = run_category_b()
    c_avg, c_max, c_results = run_category_c()

    # Category A requires manual scoring — prompt the user
    print("\n" + "=" * 60)
    print("  CATEGORY A — Manual Grading Required")
    print("=" * 60)
    print("  Review each response above and enter your scores.")
    print("  PASS (1) = 1-2 sentences, no markdown, answers question")
    print("  FAIL (0) = 3+ sentences, markdown, or doesn't answer")
    print()

    a_score = 0
    for i, r in enumerate(a_results, 1):
        while True:
            grade = input(f"  [{i}] {r['prompt'][:50]}...  PASS or FAIL? (p/f): ").strip().lower()
            if grade in ("p", "pass", "1"):
                a_score += 1
                break
            elif grade in ("f", "fail", "0"):
                break
            print("      Enter p (pass) or f (fail)")

    write_report(
        model_name  = model_name,
        a_results   = a_results,
        a_score     = a_score,
        a_latency   = a_latency,
        b_score     = b_score,
        b_results   = b_results,
        c_avg_words = c_avg,
        c_max_words = c_max,
        c_results   = c_results,
    )

    print_summary(model_name, a_score, b_score, c_avg, c_max, a_latency)