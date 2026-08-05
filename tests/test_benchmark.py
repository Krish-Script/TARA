"""
Tests intent classification accuracy and tool pipeline correctness
without voice input. Text queries go directly to IntentDetector
and ToolRegistry.

Three sections:
  1. Intent Classification — 19 queries, expected vs actual, accuracy score
  2. Tool Pipeline         — every registered tool called and verified
  3. Latency Summary       — tool dispatch times, TTFS proxy (no STT)

Run with:
    cd D:\\TARA
    .venv\\Scripts\\activate
    python tests/test_benchmark.py

A result below 90% intent accuracy, any tool failure, or any
false positive on conversational queries should be fixed before
adding new tools or pipeline stages in Week 5.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.intent import IntentDetector, Intent
from components.tools.registry import ToolRegistry, ToolResult


# ── Test Cases ───────────────────────────────────────────────

# Format: (query, expected_intent, description)
INTENT_TEST_CASES = [

    # ── System queries — must route to SYSTEM_QUERY ──────────
    ("What's my CPU usage?",         Intent.SYSTEM_QUERY, "cpu usage"),
    ("How much RAM am I using?",     Intent.SYSTEM_QUERY, "ram usage"),
    ("What's my disk space?",        Intent.SYSTEM_QUERY, "disk space"),
    ("What's my battery level?",     Intent.SYSTEM_QUERY, "battery level"),
    ("How much VRAM am I using?",    Intent.SYSTEM_QUERY, "vram query"),
    ("What's the GPU temperature?",  Intent.SYSTEM_QUERY, "gpu temperature"),
    ("What's my system status?",     Intent.SYSTEM_QUERY, "system status"),
    ("What's the CPU utilization?",  Intent.SYSTEM_QUERY, "cpu utilization"),
    ("How much storage is left?",    Intent.SYSTEM_QUERY, "storage query"),
    ("What's the CPU used?",         Intent.SYSTEM_QUERY, "cpu used variant"),

    # ── Time queries — must route to TIME_QUERY ──────────────
    ("What time is it?",             Intent.TIME_QUERY,   "time query"),
    ("What day is it today?",        Intent.TIME_QUERY,   "day query"),
    ("What's today's date?",         Intent.TIME_QUERY,   "date query"),

    # ── Chat queries — must route to CHAT ────────────────────
    ("Tell me about black holes.",   Intent.CHAT,         "chat — science"),
    ("Tell me a joke.",              Intent.CHAT,         "chat — joke"),
    ("What is recursion?",           Intent.CHAT,         "chat — tech concept"),
    ("How are you today?",           Intent.CHAT,         "chat — greeting"),
    
    # ── Calculator ───────────────────────────────────────────
    ("Calculate 15 percent of 340.",      Intent.CALCULATION,   "calc — percent"),
    ("What is 847 divided by 7?",         Intent.CALCULATION,   "calc — division"),
    ("Compute 12 times 15.",              Intent.CALCULATION,   "calc — multiply"),

    # ── Notes ────────────────────────────────────────────────
    ("Take a note, buy milk tomorrow.",   Intent.NOTES_CREATE,  "notes — create"),
    ("What was my last note?",            Intent.NOTES_READ,    "notes — read"),
    ("List my notes.",                    Intent.NOTES_LIST,    "notes — list"),
    ("Find my note about milk.",          Intent.NOTES_SEARCH,  "notes — search"),

    # ── File ─────────────────────────────────────────────────
    ("Read the README file.",             Intent.FILE_READ,     "file — read"),
    ("List files in my documents.",       Intent.FILE_LIST,     "file — list"),

    # ── Local search ─────────────────────────────────────────
    ("Do you know anything about my chess games?", Intent.LOCAL_SEARCH, "search — local"),
    ("What do you know about my flight?", Intent.LOCAL_SEARCH,  "search — local"),

    # ── Edge cases — false positive detection ────────────────
    # These must NOT trigger tool routing despite containing
    # keywords that appear in SYSTEM_QUERY or TIME_QUERY patterns.
    ("Explain how RAM works.",         Intent.CHAT, "edge — explain RAM"),
    ("Tell me about CPUs in detail.",  Intent.CHAT, "edge — explain CPU"),
    ("What time do trains run?",       Intent.CHAT, "edge — time ambiguous"),
    ("How is temperature measured?",   Intent.CHAT, "edge — temperature concept"),
    ("Do you have a good memory?",     Intent.CHAT, "edge — memory concept"),
    ("What is a neural network?",      Intent.CHAT, "edge — calc false pos"),
    ("What's the history of Python?",  Intent.CHAT, "edge — calc false pos 2"),
    ("Remember that I like chess.",    Intent.MEMORY, "memory — not notes"),
    ("Remember to buy milk.",          Intent.NOTES_CREATE, "notes — not memory"),
    ("What's the weather like today?", Intent.CHAT, "edge — what's ambiguous"),
    ("What do you know about Einstein?",  Intent.CHAT, "edge — search false pos"),

    # ── Compound boundary — must NOT trigger CompoundRouter ──────
    # These reach IntentDetector normally and must route correctly.
    ("Take a note: buy milk",           Intent.NOTES_CREATE,  "compound neg — note no system data"),
    ("What's my CPU right now?",        Intent.SYSTEM_QUERY,  "compound neg — single metric not compound"),
    ("How is quantum computing done?",  Intent.CHAT,          "compound neg — how is not system"),
    ("List my notes",                   Intent.NOTES_LIST,    "compound neg — list not search chain"),

    # ── Week 8 adversarial findings — confirmed routing behaviour ─
    # These document routing decisions confirmed under adversarial
    # testing (T4) and demo dry run (T1). Do not remove.
    ("What's my memory?",                   Intent.CHAT,         "edge — memory gap (Finding 8, no 'usage' suffix)"),
    ("Show me what you know.",              Intent.CHAT,         "edge — local search false pos (no possessive+topic)"),
    ("What time does the file say?",        Intent.CHAT,         "edge — ambiguous time+file, falls to CHAT"),
    ("What's my memory usage?",             Intent.SYSTEM_QUERY, "system — memory usage variant (contrast with edge above)"),
    ("I need to check, what is my CPU usage right now?", Intent.SYSTEM_QUERY, "edge — buried trigger in long input"),
    ("Take a note: meeting at 3pm.",        Intent.NOTES_CREATE, "notes — create with colon separator"),
    ("Summarize the README file.",          Intent.FILE_READ,    "file — demo Q7 fixed phrase"),
    ("What do you know about my demonstration?", Intent.LOCAL_SEARCH, "search — demo Q8 fixed phrase"),
]

# ── Tool pipeline tests ──────────────────────────────────────
# Format: (intent, query, description, expected_key_in_raw_output)
TOOL_TEST_CASES = [
    (Intent.TIME_QUERY,   "What time is it?",          "time tool",    "time_12h"),
    (Intent.SYSTEM_QUERY, "What's my CPU usage?",      "cpu tool",     "cpu_percent"),
    (Intent.SYSTEM_QUERY, "How much RAM am I using?",  "ram tool",     "ram_used_gb"),
    (Intent.SYSTEM_QUERY, "What's my disk space?",     "disk tool",    "disk_free_gb"),
    (Intent.SYSTEM_QUERY, "What's my battery level?",  "battery tool", "battery_percent"),
    (Intent.SYSTEM_QUERY, "How much VRAM am I using?", "vram tool",    "vram_used_gb"),
    (Intent.SYSTEM_QUERY, "What's the GPU temperature?","temp tool",   "gpu_temp_c"),
]

# ── Compound router tests ────────────────────────────────────
# Format: (query, expected_chain_or_none, description)
# expected_chain_or_none = None means CompoundRouter should NOT match.
COMPOUND_TEST_CASES = [
    # Five that SHOULD match compound patterns
    ("How is my system doing?",              "system_status_snapshot",  "compound pos — system status"),
    ("How's my system doing?",               "system_status_snapshot",  "compound pos — system status contraction"),
    ("Give me a full system report",         "system_status_snapshot",  "compound pos — full report"),
    ("Take a note with my current CPU usage","note_with_system_data",   "compound pos — note with data"),
    ("Note the time right now",              "timestamped_note",        "compound pos — timestamped note"),

    # Five that should NOT match compound patterns
    ("Take a note: buy milk",               None, "compound neg — plain note"),
    ("What's my CPU right now?",            None, "compound neg — single metric"),
    ("How is quantum computing done?",      None, "compound neg — how is general"),
    ("List my notes",                       None, "compound neg — list intent"),
    ("What do you know about Einstein?",    None, "compound neg — search false pos"),

    ("Take a note with my current RAM usage", "note_with_system_data",  "compound pos — note with RAM variant"),
    ("System status report",                  "system_status_snapshot", "compound pos — short form trigger"),
]

# ── Helpers ──────────────────────────────────────────────────

def _pass(msg): print(f"  ✅ PASS  {msg}")
def _fail(msg): print(f"  ❌ FAIL  {msg}")
def _warn(msg): print(f"  ⚠️  WARN  {msg}")
def _sep():     print(f"  {'─' * 51}")


# ── Section 1: Intent Classification ─────────────────────────

def run_intent_tests(detector: IntentDetector) -> tuple[int, int, list[str]]:
    """
    Run all intent test cases.
    Returns (passes, total, list_of_failure_descriptions).
    """
    print("\n" + "=" * 55)
    print("  SECTION 1 — Intent Classification")
    print("=" * 55)

    passes       = 0
    false_positives: list[str] = []

    for query, expected, description in INTENT_TEST_CASES:
        actual, matched = detector.classify_with_confidence(query)
        matched_str     = f"matched: '{matched}'" if matched else "no match"

        if actual == expected:
            passes += 1
            _pass(f"{query:30s}  {actual.name}  ({matched_str})")
        else:
            failure = (
                f"{query:30s}  "
                f"got {actual.name}, expected {expected.name}  ({matched_str})"
            )
            _fail(failure)
            if expected == Intent.CHAT and actual != Intent.CHAT:
                false_positives.append(f"'{query}' → {actual.name} (should be CHAT)")

    total    = len(INTENT_TEST_CASES)
    accuracy = passes / total * 100

    _sep()
    print(f"  Score: {passes}/{total}  ({accuracy:.1f}%)")
    if false_positives:
        print(f"\n  False positives detected ({len(false_positives)}):")
        for fp in false_positives:
            print(f"    → {fp}")
        print("  Fix: remove bare trigger words from intent.py patterns")
    else:
        print("  No false positives ✅")

    return passes, total, false_positives


# ── Section 2: Tool Pipeline ──────────────────────────────────

def run_tool_tests(registry: ToolRegistry) -> tuple[int, int]:
    """
    Run all tool pipeline tests.
    Returns (passes, total).
    """
    print("\n" + "=" * 55)
    print("  SECTION 2 — Tool Pipeline")
    print("=" * 55)

    passes = 0

    for intent, query, description, expected_key in TOOL_TEST_CASES:
        result: ToolResult | None = registry.dispatch(intent, query)

        if result is None:
            _fail(f"{description:20s}  no tool registered for {intent.name}")
            continue

        if not result.success:
            _fail(f"{description:20s}  tool returned success=False: {result.error}")
            continue

        if expected_key not in result.raw_output:
            _fail(
                f"{description:20s}  "
                f"missing key '{expected_key}' in raw_output: {list(result.raw_output.keys())}"
            )
            continue

        if not result.formatted_output or result.formatted_output.startswith("Sorry"):
            _warn(f"{description:20s}  formatter returned fallback: '{result.formatted_output}'")
            continue

        passes += 1
        value = result.raw_output[expected_key]
        _pass(
            f"{description:20s}  "
            f"{expected_key}={value}  →  \"{result.formatted_output}\""
        )

    total = len(TOOL_TEST_CASES)
    _sep()
    print(f"  Score: {passes}/{total}  ({passes/total*100:.1f}%)")

    return passes, total

# ── Section 4: Compound Router ────────────────────────────────

def run_compound_tests(router) -> tuple[int, int]:
    """
    Test CompoundRouter.match() for correct positive and negative routing.
    Returns (passes, total).
    """
    print("\n" + "=" * 55)
    print("  SECTION 4 — Compound Router Boundary Tests")
    print("=" * 55)

    passes = 0
    false_positives: list[str] = []
    false_negatives: list[str] = []

    for query, expected_chain, description in COMPOUND_TEST_CASES:
        actual_chain = router.match(query)

        if actual_chain == expected_chain:
            passes += 1
            result_str = actual_chain if actual_chain else "no match"
            _pass(f"{query:42s}  → {result_str}")
        else:
            expected_str = expected_chain if expected_chain else "no match"
            actual_str   = actual_chain   if actual_chain   else "no match"
            _fail(f"{query:42s}  got '{actual_str}', expected '{expected_str}'")
            if expected_chain is None and actual_chain is not None:
                false_positives.append(f"'{query}' → {actual_chain} (should be no match)")
            elif expected_chain is not None and actual_chain is None:
                false_negatives.append(f"'{query}' → no match (should be {expected_chain})")

    total = len(COMPOUND_TEST_CASES)
    _sep()
    print(f"  Score: {passes}/{total}  ({passes/total*100:.1f}%)")

    if false_positives:
        print(f"\n  False positives ({len(false_positives)}) — compound router too broad:")
        for fp in false_positives:
            print(f"    → {fp}")
    if false_negatives:
        print(f"\n  False negatives ({len(false_negatives)}) — compound router missed:")
        for fn in false_negatives:
            print(f"    → {fn}")
    if not false_positives and not false_negatives:
        print("  No routing errors ✅")

    return passes, total

# ── Section 3: Latency Benchmark ─────────────────────────────

def run_latency_tests(
    detector: IntentDetector,
    registry: ToolRegistry,
) -> dict:
    """
    Measure tool dispatch latency across 10 repeated calls.
    Returns dict of timing stats.
    """
    print("\n" + "=" * 55)
    print("  SECTION 3 — Latency Benchmark")
    print("=" * 55)

    # Intent classification latency
    intent_times = []
    for _ in range(20):
        t0 = time.perf_counter()
        detector.classify("What's my CPU usage?")
        intent_times.append(time.perf_counter() - t0)

    intent_avg_ms = sum(intent_times) / len(intent_times) * 1000
    print(f"\n  Intent classification (20 calls):")
    print(f"    avg: {intent_avg_ms:.2f}ms  "
          f"min: {min(intent_times)*1000:.2f}ms  "
          f"max: {max(intent_times)*1000:.2f}ms")

    # Tool dispatch latency per tool
    print(f"\n  Tool dispatch latency:")
    tool_latencies = {}

    dispatch_cases = [
        (Intent.TIME_QUERY,   "What time is it?",          "time"),
        (Intent.SYSTEM_QUERY, "What's my CPU usage?",      "cpu"),
        (Intent.SYSTEM_QUERY, "How much RAM am I using?",  "ram"),
        (Intent.SYSTEM_QUERY, "What's the GPU temperature?","gpu_temp"),
    ]

    for intent, query, label in dispatch_cases:
        t0     = time.perf_counter()
        result = registry.dispatch(intent, query)
        elapsed = time.perf_counter() - t0
        tool_latencies[label] = elapsed

        status = "✅" if (result and result.success) else "❌"
        print(f"    {status} {label:12s}  {elapsed*1000:.1f}ms")

    # TTFS proxy — tool path without STT
    # (STT avg from Week 4: ~0.69s)
    STT_AVG = 0.69
    TTS_SYNTH_AVG = 0.65

    tool_dispatch_avg = sum(tool_latencies.values()) / len(tool_latencies)
    ttfs_proxy = STT_AVG + tool_dispatch_avg + TTS_SYNTH_AVG

    print(f"\n  TTFS proxy (STT {STT_AVG}s + dispatch + TTS synth {TTS_SYNTH_AVG}s):")
    print(f"    Tool dispatch avg: {tool_dispatch_avg*1000:.1f}ms")
    print(f"    TTFS estimate:     {ttfs_proxy:.2f}s")
    print(f"    Target:            ≤1.50s  "
          f"{'✅' if ttfs_proxy <= 1.50 else '❌'}")

    return {
        "intent_avg_ms":      intent_avg_ms,
        "tool_dispatch_avg_s": tool_dispatch_avg,
        "ttfs_proxy":         ttfs_proxy,
    }


# ── Summary ───────────────────────────────────────────────────

def print_summary(
    intent_passes:    int,
    intent_total:     int,
    tool_passes:      int,
    tool_total:       int,
    compound_passes:  int,
    compound_total:   int,
    false_positives:  list[str],
    latency:          dict,
):
    print("\n" + "=" * 55)
    print("  WEEK 8 BENCHMARK SUMMARY")
    print("=" * 55)

    intent_pct   = intent_passes   / intent_total   * 100
    tool_pct     = tool_passes     / tool_total     * 100
    compound_pct = compound_passes / compound_total * 100

    total_passes = intent_passes + tool_passes + compound_passes
    total_cases  = intent_total  + tool_total  + compound_total

    print(f"\n  Intent accuracy  : {intent_passes}/{intent_total}  ({intent_pct:.1f}%)")
    print(f"  Tool success     : {tool_passes}/{tool_total}  ({tool_pct:.1f}%)")
    print(f"  Compound routing : {compound_passes}/{compound_total}  ({compound_pct:.1f}%)")
    print(f"  ─────────────────────────────────────────")
    print(f"  Total            : {total_passes}/{total_cases}  ({total_passes/total_cases*100:.1f}%)")
    print(f"  False positives  : {len(false_positives)}")
    print(f"  Intent latency   : {latency['intent_avg_ms']:.2f}ms")
    print(f"  TTFS estimate    : {latency['ttfs_proxy']:.2f}s")

    print()
    if intent_pct == 100 and tool_pct == 100 and compound_pct == 100:
        print("  ✅ All tests passed. Pipeline routing is solid.")
    else:
        if compound_pct < 100:
            print("  ⚠️  Compound routing errors — review compound_router.py patterns.")
        if false_positives:
            print("  ⚠️  False positives — fix intent.py patterns.")
        if intent_pct < 90:
            print("  ⚠️  Intent accuracy below 90% — review pattern list.")
        if tool_pct < 100:
            print("  ⚠️  Tool failures — check tool output above.")

    print("=" * 55 + "\n")


# ── Entry Point ───────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  TARA — Intent & Tool Pipeline Benchmark Suite")
    print("=" * 55)
    print("  Initialising components...")

    detector = IntentDetector()
    registry = ToolRegistry()

    from components.compound_router import CompoundRouter
    router = CompoundRouter(registry)

    print("  Ready.\n")

    intent_passes,   intent_total,   false_positives = run_intent_tests(detector)
    tool_passes,     tool_total                      = run_tool_tests(registry)
    compound_passes, compound_total                  = run_compound_tests(router)
    latency                                          = run_latency_tests(detector, registry)

    print_summary(
        intent_passes,   intent_total,
        tool_passes,     tool_total,
        compound_passes, compound_total,
        false_positives,
        latency,
    )