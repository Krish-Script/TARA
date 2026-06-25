# TARA — Week 4 Report
## Agentic Tools Sprint

**Sprint duration:** Week 4 of 10  
**Primary goal:** Integrate intent detection and tool execution — TARA moves from answering questions to taking actions  
**Status:** ✅ Completed

---

## Sprint Summary

Week 4 introduced the agentic layer. The Orchestrator's Stage 2 (Intent Detection) and Stage 3 (Tool Execution) placeholders from Week 3's refactor are now fully active. TARA routes hardware queries directly to purpose-built tools, bypassing the LLM entirely for deterministic responses.

The critical finding of this week: **the LLM hallucinates plausible but completely wrong hardware values** when asked system metrics without tool routing. When "What's the GPU temperature?" fell through to the LLM before patterns were fixed, it responded with fabricated temperatures — 85°C CPU, 78°C GPU — neither of which bore any relation to actual sensor data. This confirmed the tool architecture is not optional for hardware queries; it is the only correct path.

Final benchmark: 19/19 intent accuracy (100%), 7/7 tool success (100%), TTFS estimate 1.37s.

---

## Final Performance Baseline

| Metric | Week 3 | Week 4 | Change |
|--------|--------|--------|--------|
| STT avg | 0.58s | 0.69s | +0.11s (session variance) |
| LLM avg (chat path) | 1.21s | 0.94s | stable |
| Tool execution avg | — | 25.3ms | new |
| Intent classification | — | 0.00ms | new |
| TTS synthesis avg | 0.65s | 0.72s | stable |
| TTFS (chat path) | 2.46s | 2.50s | stable |
| **TTFS (tool path)** | — | **1.37s** | **beats ≤1.50s target** |
| Tool queries supported | 0 | 8 | +8 |

---

## What Was Built

### T1 — Intent Detector + Tool Registry + Time Tool + Formatter

**`components/intent.py`** — keyword-pattern router returning Intent enum values. Five intents: CHAT, TIME_QUERY, SYSTEM_QUERY, CALCULATION, MEMORY. Specific multi-word phrases only — bare keywords cause false positives.

**`components/tools/registry.py`** — central dispatcher mapping `Intent → handler` with full error isolation. `ToolResult` dataclass standardises all tool output.

**`components/tools/time_tool.py`** — datetime tool, chosen first to prove full pipeline plumbing with zero risk of wrong answer before debugging complex psutil values.

**`components/tools/formatter.py`** — translates raw dicts to TTS-ready spoken language. No markdown, spells out "gigabytes"/"percent"/"degrees Celsius", max two sentences.

**Plumbing validated:** "What time is it?" → TIME_QUERY → TimeTool → spoken result. TTFS: 1.17s.

---

### T2 — System Monitor (7 metrics + thermal-aware operation)

**`components/tools/system_monitor.py`** — psutil + pynvml hardware monitor.

| Metric | Method | Latency | Notes |
|--------|--------|---------|-------|
| CPU usage | `psutil.cpu_percent(interval=0.1)` | ~100ms | Warm-up in `__init__` discards always-zero first reading |
| RAM | `psutil.virtual_memory()` | 0.3ms | |
| Disk | `psutil.disk_usage('C:\\')` | 0.0ms | |
| Battery | `psutil.sensors_battery()` | 0.0ms | None guard for devices without sensor |
| VRAM | `pynvml.nvmlDeviceGetMemoryInfo()` | 0.1ms | 0.13GB idle, 2.37GB with Ollama loaded |
| GPU temperature | `pynvml.nvmlDeviceGetTemperature()` | 0.1ms | 44–53°C at idle — healthy for RTX 3050 |
| CPU temperature | `psutil.sensors_temperatures()` | 0.0ms | Unavailable on Windows — graceful fallback |
| Uptime | `time.time() - psutil.boot_time()` | 0.0ms | |

**Thermal-aware operation:** GPU temperature monitoring confirmed working via pynvml. CPU temperature unavailable on Windows without third-party sensor drivers — `hasattr` guard handles this correctly. The project objective's "thermal-aware operation" claim is honest: GPU thermal state is monitored; CPU thermal state reports "unavailable" rather than guessing or crashing.

---

### T3 — Benchmark & Validation

**`tests/test_benchmark.py`** — 19-query test suite covering intent classification accuracy, tool pipeline correctness, and latency measurement.

**Final results:**

| Section | Score | Notes |
|---------|-------|-------|
| Intent classification | 19/19 (100%) | After fixing 2 false positives |
| Tool pipeline | 7/7 (100%) | All tools return correct data |
| Intent latency | 0.00ms | Keyword matching, not LLM |
| Tool TTFS estimate | 1.37s | Under ≤1.50s target |

**False positives found and fixed:**

| Query | Before fix | After fix |
|-------|-----------|-----------|
| "What time do trains run?" | TIME_QUERY (false positive) | CHAT ✅ |
| "How is temperature measured?" | SYSTEM_QUERY (false positive) | CHAT ✅ |

Root cause: bare trigger words `"what time"` and `"temperature"` matched as substrings of conversational queries. Fixed by removing bare words — specific phrases (`"what time is it"`, `"gpu temperature"`) still match correctly.

---

## Challenges Encountered

**1. Temperature queries routing to LLM**
Before temperature patterns were added, "What's the GPU temperature?" fell through to the LLM. The LLM fabricated CPU (85°C) and GPU (78°C) temperatures with no hesitation. Adding patterns fixed routing; the benchmark then caught the resulting false positive on "How is temperature measured?" — a reminder that adding patterns requires testing both the target query and its conversational neighbours.

**2. "VRAM usage" matched `ram usage` pattern**
"What's the VRAM usage?" was correctly classified as SYSTEM_QUERY (matched phrase logged as `ram usage` because "vram usage" contains "ram usage" as a substring). `SystemMonitor.run()` correctly dispatched to `_get_vram()` via full query inspection. Correct behaviour, misleading log — documented as known quirk.

**3. CPU tool latency 100ms**
`cpu_percent(interval=0.1)` blocks for 0.1s — psutil requires two samples to calculate delta usage. This is working correctly and expected. Acceptable for voice interaction. Could be reduced by pre-computing CPU usage on a background thread in a future sprint.

---

## Architecture: Active Pipeline

```
Stage 1: Memory Context Retrieval     ← active
Stage 2: Intent Detection             ← active  (0.00ms, keyword routing)
Stage 3: Tool Execution               ← active  (8 query types, 2 tools)
    ├── TIME_QUERY   → TimeTool       (0.1ms)
    └── SYSTEM_QUERY → SystemMonitor  (0.1–100ms depending on query)
Stage 4: RAG Retrieval                [FUTURE — Week 5]
Stage 5: LLM Generation               ← active  (CHAT intent only)
Stage 6: Response Delivery            ← active  (chunked TTS)
Stage 7: Persistence                  ← active  (tool responses tagged source='tool')
```

---

## Lessons Learned

- **LLMs hallucinate hardware data convincingly.** The LLM gave wrong-but-plausible temperature values without hesitation. Hardware queries must route to tools — always.
- **Test both the intended query and its conversational neighbours.** Adding "temperature" to fix temperature routing immediately created a false positive on "How is temperature measured?" Specific phrases are always safer than bare keywords.
- **Benchmark before shipping.** The two false positives were caught by the test suite, not by voice testing. Voice testing would have caught the obvious case ("What's the GPU temperature?") but not the edge case ("How is temperature measured?").
- **The Week 3 refactor paid off.** T1 wiring took under 30 minutes. The staged pipeline architecture made adding two new components a matter of filling in documented placeholders.
- **Tool path TTFS (1.37s) vs chat path TTFS (2.50s).** The 1.13s difference demonstrates the value of bypassing LLM generation for deterministic queries. Users feel this difference.

---

## Sprint Outcome

✅ IntentDetector with keyword routing (<1ms classification)  
✅ ToolRegistry with ToolResult dataclass and error isolation  
✅ TimeTool — full pipeline plumbing validated  
✅ SystemMonitor — 7 metrics (CPU, RAM, disk, battery, VRAM, temperature, uptime)  
✅ Thermal-aware GPU temperature monitoring (pynvml, RTX 3050 confirmed)  
✅ ToolFormatter — TTS-ready output for all tools  
✅ 19/19 benchmark accuracy after false positive fixes  
✅ Tool path TTFS 1.37s — beats ≤1.50s target  
✅ Stage 2 and Stage 3 fully active in Orchestrator  

---

## Week 5 Preview

**Theme: Context Window Optimisation + First Stretch Goals**  
Memory context is currently injected on every LLM turn — including tool turns where it adds latency with no benefit. Week 5 will optimise context injection (skip for tool path, trim for chat path) and begin exploring model upgrade (llama3.2:5b) if VRAM headroom permits.