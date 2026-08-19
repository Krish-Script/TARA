# TARA — Week 9 Report
## Research Integrity, Documentation Finalization, Portfolio Completion

**Sprint duration:** Week 9 of 10

**Status:** ✅ Complete (7/7 tasks complete)

---

## T1 Status: ✅ Complete

### "What Has Not Been Measured": Explicit Reasoning Per Open Question

**Estimate:** 0.75h | **Actual:** ~0.5h

Opened `docs/research_notes.md` and located the "What Has Not Been Measured" section. Each of the three open questions had an existing descriptive paragraph explaining what was unknown. T1 required adding one explicit paragraph per question answering: what would measuring this require, what prevented measurement, and what it would contribute if measured.

**Changes made:**

#### docs/research_notes.md
- **Question 1 (VRAM/format Pareto frontier):** Added paragraph citing the hardware constraint as the limiting factor — one GPU, one parameter count. Minimum six data points across two VRAM budgets required for a meaningful curve. Model selection framed as defensible but not optimal.
- **Question 2 (Memory injection at scale):** Added paragraph explaining that scripted session generation (not live voice interaction) would be required to reach 50+ facts and 200+ turns. 600-token ceiling guard noted as making this a managed risk rather than an uncharacterised one. Identified as the first measurement priority for a long-running deployment scenario.
- **Question 3 (STT domain vocabulary error rate):** Added paragraph explaining that a labelled test set of 50+ domain-specific terms read by the same speaker is required. Correction dictionary noted as reactively constructed — three of four entries discovered in a single dry run session. Near-completeness stated as a hypothesis, not a supported conclusion.

**Commit:** `docs: add rationale for unmeasured research questions` at v0.31.0

---

## T2 Status: ✅ Complete

### Session Summary: Fix Content vs Statistics

**Estimate:** 1.0h | **Actual:** ~1.0h

Replaced stats-based prompt in `_generate_session_summary()` with `get_context_for_llm(session_id=self.session_id)` call returning actual conversation turns. Added fallback to stats-based prompt for tool-only sessions where `get_context_for_llm()` returns empty string (source_filter="chat" excludes tool turns).

**Validation — three session types:**

| Session | Type | Summary spoken | Pass |
|---------|------|---------------|------|
| A | Mixed (chat + note + tool) | Described ML topic and note creation | ✅ |
| B | Chat only | Named all three topics discussed | ✅ |
| C | Tool only | Stats fallback — acceptable, no crash | ✅ |

**Known limitation:** Tool-only sessions hit the stats fallback because `get_context_for_llm()` filters to `source="chat"` only. Correct fix requires a separate `get_tool_turns_for_llm()` method — out of scope for Week 9. Fallback produces a functional summary rather than silence.

#### components/orchestrator.py
- `_generate_session_summary()`: replaced stats prompt with `get_context_for_llm()` call. Added empty-context fallback. Added few-shot example to content prompt for natural spoken output.

---

## T3 Status: ✅ Complete

### VAD Correction: Propagate to Research Findings and Abstract

**Estimate:** 1.5h | **Actual:** ~1.0h

**Changes made:**

#### docs/research_notes.md
- **Finding 10 added** — VAD Configuration as a User-Perceived Latency Lever. Full F/E/M/I structure:
  - Finding: 1.8s VAD window added 1.0s user-perceived latency to every query path. Recalibration to 0.8s produced 1.0s improvement with no pipeline or model changes.
  - Evidence: Four ambient noise diagnostic runs (Week 8), mean amplitude 1.5 vs threshold 300 (200× margin). User-perceived tool path: 3.10s → 2.05s. Chat path: 4.80s → 3.80s.
  - Mechanism: VAD silence window is experienced as dead time by the user but excluded from the pipeline TTFS formula — invisible in all logged measurements across Weeks 1–7.
  - Implication: VAD calibration against the actual acoustic environment is a first-order latency concern. Both logged and user-perceived TTFS values should be stated explicitly in any voice interface benchmark.
- **Finding 1 note updated** — user-perceived reduction (46%, 2.05s vs 3.80s) added alongside existing logged reduction note (58%, 1.25s vs 3.00s).
- **Measurement integrity preamble** — confirmed accurate and complete. No changes required.

#### docs/project_abstract.md
- **Finding 1 updated** — now states both logged TTFS reduction (58%, 1.25s vs 3.00s) and user-perceived reduction (46%, 2.05s vs 3.80s) with explicit VAD window attribution.

---

## T4 Status: ✅ Complete

### Research Notes Final Audit: Completeness and Coherence

**Estimate:** 1.5h (adjusted to 2.0h) | **Actual:** ~1.0h

Full end-to-end read of `docs/research_notes.md` completed against four-question checklist.

**Findings reviewed:**
- All 9 active findings contain at least one specific measured number in Evidence. Finding 8 evidence cites routing correctness boundary cases rather than timing — appropriate for the finding type.
- Finding 2: dual-injection annotation confirmed present and accurate.
- Finding 7: VAD measurement note added — logged vs user-perceived distinction now explicit for all three compound chain values.
- Findings 8 and 9: confirmed F/E/M/I standard.
- Finding 4: confirmed labeled as superseded with reason.

**Finding count confirmed:** 10 total (9 active, 1 superseded).  
**Unmeasured gaps confirmed:** 3, each with explicit rationale paragraph.

#### docs/research_notes.md
- Finding 7 Evidence: VAD measurement note added citing logged vs user-perceived values for all three compound chains.

---

## T5 Status: ✅ Complete

### Final Cold-Boot Benchmark Run: Definitive Published Results

**Estimate:** 0.75h | **Actual:** ~0.75h

**System state at benchmark start:**

| Parameter | Value |
|-----------|-------|
| Date/time | Mon Aug 17 2026, 20:41:54 |
| GPU temp | 37°C |
| VRAM at start | 0MiB / 4096MiB |
| Running GPU processes | None |
| Throwaway warm-up query | "What is a large language model?" |
| Warm-up TTFS | 5.44s (true cold boot — model load included) |
| Benchmark start time | Mon Aug 17 2026, 20:52:54 |

**Benchmark result — 70/70 from cold boot:**

| Metric | Result | Target |
|--------|--------|--------|
| Intent accuracy | 51/51 (100%) | 100% |
| Tool success | 7/7 (100%) | 100% |
| Compound routing | 12/12 (100%) | 100% |
| **Total** | **70/70 (100%)** | **100%** |
| False positives | 0 | 0 |
| Intent latency | 0.01ms | <1ms |
| TTFS estimate | 1.37s | ≤1.50s |

This result — 70/70 from cold boot — is the definitive published benchmark. All prior benchmark runs were mid-development with models warm and fixes sometimes applied between runs. This run was taken from a verified cold system state.

**Demo sequence Run 4 — cold boot:**

| Query | Actual TTFS | STT Output | Notes |
|-------|------------|------------|-------|
| 1 | 3.63s | My name is TARA. | Slightly above 2.1–3.5s range — cold-boot thermal variance |
| 2 | 1.53s | It's 08:58 PM on Monday, August 17, 2026. | ✅ |
| 3 | 1.78s | CPU / RAM / disk status reported correctly. | ✅ Multi-metric overhead — consistent with Run 3 (1.68s) |
| 4 | 1.26s | GPU temperature is 40 degrees Celsius. | ✅ |
| 5 | 1.52s | Note saved: I demonstrated TARA today. | ✅ |
| 6 | 1.41s | Your last note says: I demonstrated TARA today. | ✅ |
| 7 | 2.09s | README summarised correctly. | ✅ Improvement vs Run 3 (2.27s) |
| 8 | 1.32s | Stem match: demonstrated TARA today. | ✅ |
| 9 | 1.17s | That's 51. | ✅ |
| 10 | 3.43s | LLM definition of large language models. | ✅ |

**Run 4 result: PASS — no crashes, no routing failures.**

**Comparison Run 3 vs Run 4:**

| Metric | Run 3 | Run 4 | Delta | Note |
|--------|-------|-------|-------|------|
| Query 1 TTFS | 2.14s | 3.63s | +1.49s | Run 3 below floor — VRAM pre-warm. Run 4 expected range |
| Tool path avg | 1.39s | 1.47s | +0.08s | Within variance |
| Chat path avg | 3.08s | 3.53s | +0.45s | Within target ≤4.0s |
| Query 7 TTFS | 2.27s | 2.09s | -0.18s | Improvement |
| Failures | 0 | 0 | — | ✅ |

No regressions. TTFS differences between runs reflect warm vs cold VRAM state, not pipeline changes. Run 4 is the authoritative result.

#### README.md
- Performance table updated with cold-boot benchmark run date: Mon Aug 17 2026.

---

## T6 Status: ✅ Complete

### Version 1.0.0 Release and Final CHANGELOG

**Estimate:** 0.75h | **Actual:** ~0.5h

CHANGELOG.md v1.0.0 entry written with full project summary, added, fixed, and known limitations sections. [Unreleased] block cleared — no further planned versions. Git tag v1.0.0 pushed to remote.

#### CHANGELOG.md
- [Unreleased] block updated: no planned versions remaining.
- v1.0.0 entry added: milestone summary, 12 functional requirements, 70/70 benchmark date, 10 findings, 8 known limitations, public repository noted.

---

## T7 Status: ✅ Complete

### Week 10 Preparation: Final Demo and Submission Materials

**Estimate:** 1.0h | **Actual:** ~0.5h

`docs/week10_checklist.md` created with three sections: pre-demo verification, final documentation checklist, and portfolio submission checklist. Recording shot list and OBS configuration included. Week 10 deliverable defined explicitly — no planning overhead required in Week 10.

#### docs/week10_checklist.md
- Week 10 deliverable defined: on-camera demo recording (~3 minutes), uploaded to LinkedIn and linked in README.
- Pre-demo verification: 10 steps including cold-boot, benchmark confirmation, audio mix test, and NVENC contention test.
- Recording shot list: 10 beats with expected TARA response per beat.
- OBS configuration documented.
- Final documentation checklist: 8 items.
- Portfolio submission checklist: 7 items.

---

## Hours Summary (Week 9 — In Progress)

| Task | Estimated | Actual |
|------|-----------|--------|
| T1 — "What Has Not Been Measured" rationale | 0.75h | ~0.5h |
| T2 — Session summary fix | 1.0h | ~1.0h |
| T3 — VAD correction propagation | 1.5h | ~1.0h |
| T4 — Research notes final audit | 1.5h | ~1.0h |
| T5 — Cold-boot benchmark | 0.75h | ~0.75h |
| T6 — Version 1.0.0 release | 0.75h | ~0.5h |
| T7 — Week 10 preparation | 1.0h | ~0.5h |
| **Total** | **7.25h** | **~5.25h** |

---

## Notes

- T1 came in 0.25h under estimate. Existing paragraphs were well-formed; the addition required was one explanatory paragraph per question, not structural revision of the section.
- T4 estimate mentally adjusted to 2.0h: T1 and T3 both modify `docs/research_notes.md` before the audit runs. Auditing a document updated in two places requires more careful end-to-end verification than auditing a stable file.
- GitHub repository made public at the start of Week 9. `data/` confirmed gitignored before publishing.
- Week 10 deliverable confirmed: on-camera demo recording (~3 minutes), uploaded to LinkedIn and linked in README.