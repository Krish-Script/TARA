# TARA — Week 4 Report
## Agentic Tools Sprint

**Sprint duration:** Week 4 of 10  
**Primary goal:** Integrate intent detection and tool execution — TARA moves from answering questions to taking actions  
**Status:** 🔄 In Progress (T1–T2 complete, T3 pending)

---

## Sprint Summary

Week 4 introduces the agentic layer. The Orchestrator's Stage 2 (Intent Detection) and Stage 3 (Tool Execution) placeholders from Week 3's refactor are now active. TARA routes hardware queries directly to purpose-built tools, bypassing the LLM entirely for deterministic responses.

Two tool sessions this week established the critical finding: **the LLM hallucinates plausible but completely wrong hardware values** when asked system metrics. When asked "What's the GPU temperature?" before tool routing was configured, the LLM responded with fabricated temperatures (85°C CPU, 78°C GPU) that bore no relation to actual sensor data. This validates the entire tool architecture decision — hardware queries must never go to the LLM.

---

## Performance Baseline

| Metric | Week 3 | Week 4 T1 | Week 4 T2 | Change |
|--------|--------|-----------|-----------|--------|
| STT avg | 0.58s | 0.59s | 0.69s | +0.11s (session variance) |
| LLM avg (chat) | 1.21s | 1.14s | 0.94s | stable |
| Tool execution avg | — | 0.000s | 0.102s | new |
| TTS synthesis avg | 0.65s | 0.67s | 0.72s | stable |
| TTFS (chat path) | 2.46s | 2.52s | 2.50s | stable |
| **TTFS (tool path)** | — | **1.17s** | **1.34–1.42s** | **beats ≤1.50s target** |
| Tool queries supported | 0 | 1 | 7 | +6 |

CPU tool latency (0.509s on first call) is explained by `cpu_percent(interval=0.1)` — psutil requires two samples 0.1s apart to calculate delta usage. Subsequent calls return immediately from cached state.

---

## What Was Built

### T1 — Intent Detector + Tool Registry + Time Tool + Formatter

`components/intent.py` — keyword-pattern router returning Intent enum values. Five intents: CHAT, TIME_QUERY, SYSTEM_QUERY, CALCULATION, MEMORY. Specific multi-word phrases only — bare keywords ("ram", "temperature") cause false positives on conversational queries.

`components/tools/registry.py` — central dispatcher mapping `Intent → handler`. `ToolResult` dataclass standardises all output. Tool failures return graceful fallback — never crash pipeline.

`components/tools/time_tool.py` — datetime tool, proved full pipeline plumbing with zero risk of wrong answer.

`components/tools/formatter.py` — translates raw dicts to TTS-ready spoken language. Rules: no markdown, spell out "gigabytes"/"percent"/"degrees Celsius", max two sentences.

**Validated:** "What time is it?" → TIME_QUERY → TimeTool → "It's 04:05 PM on Tuesday, June 23, 2026." TTFS: 1.17s.

### T2 — System Monitor (7 metrics + thermal-aware operation)

`components/tools/system_monitor.py` — psutil + pynvml hardware monitor.

| Query | Method | Latency | Notes |
|-------|--------|---------|-------|
| CPU usage | `psutil.cpu_percent(interval=0.1)` | ~0.1s | Warm-up call in `__init__` discards always-zero first reading |
| RAM | `psutil.virtual_memory()` | 0.000s | |
| Disk | `psutil.disk_usage('C:\\')` | 0.000s | |
| Battery | `psutil.sensors_battery()` | 0.000s | Guards for `None` on devices without sensor |
| VRAM | `pynvml.nvmlDeviceGetMemoryInfo()` | 0.000s | 2.37GB with Ollama loaded — confirms live readings |
| GPU temperature | `pynvml.nvmlDeviceGetTemperature()` | 0.000s | 48–53°C at idle — healthy for RTX 3050 |
| CPU temperature | `psutil.sensors_temperatures()` | 0.000s | Unavailable on Windows — graceful fallback, not an error |
| Uptime | `time.time() - psutil.boot_time()` | 0.000s | |

**Thermal-aware operation implementation:**
The project objective states "thermal-aware operation" as a design emphasis. GPU temperature monitoring via pynvml is implemented and confirmed working. CPU temperature is unavailable on Windows without third-party driver support — `sensors_temperatures()` is Linux/macOS only. `hasattr` guard prevents Pylance warning and handles Windows correctly. This makes the thermal-aware claim honest within platform constraints: GPU thermal state is monitored; CPU thermal state reports "unavailable" rather than guessing.

---

## Challenges Encountered

**1. Temperature queries routing to LLM**
"What's the GPU temperature?" fell through to the LLM because "temperature" was absent from SYSTEM_QUERY patterns. The LLM fabricated both CPU (85°C) and GPU (78°C) temperatures — completely hallucinated. Fixed by adding "temperature", "gpu temp", "cpu temp", "thermal", "how hot" to the pattern list.

**This is the most important finding of Week 4:** the LLM invents plausible hardware values rather than admitting it doesn't know. Any query that has a deterministic correct answer must be handled by a tool.

**2. "VRAM usage" matching `ram usage` pattern**
"What's the VRAM usage?" was correctly classified as SYSTEM_QUERY (matched phrase logged as `ram usage`) because "vram usage" contains "ram usage" as a substring. Intent classification was correct; SystemMonitor.run() correctly dispatched to `_get_vram()` by checking for "vram" in the full query. The logged matched phrase is misleading but behaviour is correct. Documented as a known pattern ordering quirk — not a bug.

**3. Pylance `sensors_temperatures` warning**
`psutil.sensors_temperatures()` is not declared in psutil's Windows type stubs, causing a Pylance false positive. Fixed with `hasattr(psutil, "sensors_temperatures")` guard before calling — correct for both runtime behaviour and static analysis.

---

## Architecture: Active Pipeline Stages

```
Stage 1: Memory Context Retrieval     ← active
Stage 2: Intent Detection             ← active (keyword routing, <5ms)
Stage 3: Tool Execution               ← active (7 queries, 2 tools)
    ├── TIME_QUERY   → TimeTool
    └── SYSTEM_QUERY → SystemMonitor
Stage 4: RAG Retrieval                [FUTURE — Week 5]
Stage 5: LLM Generation               ← active (CHAT intent only)
Stage 6: Response Delivery            ← active (chunked TTS)
Stage 7: Persistence                  ← active (tool responses tagged source='tool')
```

---

## Lessons Learned

- **LLMs hallucinate hardware data convincingly.** The LLM gave wrong-but-plausible CPU and GPU temperatures without any hesitation. Tools are not optional for system queries — they are the only correct path.
- **Pattern specificity over coverage.** The temperature routing failure happened because the pattern list wasn't comprehensive enough. Every new tool query type needs its trigger phrases tested against conversational edge cases before deployment.
- **The Week 3 refactor paid off immediately.** T1 wiring took under 30 minutes due to the staged pipeline architecture. Without it, adding intent detection and tool routing would have required structural changes to `main.py`.
- **Live hardware readings confirm the tool is working correctly.** VRAM showing 0.13GB at idle and 2.37GB with Ollama loaded — not a static value, not a cached value. The tool reads real state.

---

## Pending — T3

| Task | Description |
|------|-------------|
| T3 — Benchmark & Validation | 15-query test set, intent accuracy measurement, final TTFS numbers per path |

---

## Week 4 Final Targets

| Metric | Current | Target |
|--------|---------|--------|
| Tool path TTFS | 1.34–1.42s | ≤1.50s ✅ |
| Chat path TTFS | 2.50s | ≤2.60s ✅ |
| Tool queries | 7 | ≥6 ✅ |
| Intent accuracy | untested | 100% on 15-query set |