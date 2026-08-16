# TARA — Week 9 Report
## Research Integrity, Documentation Finalization, Portfolio Completion

**Sprint duration:** Week 9 of 10

**Status:** 🔄 In Progress (3/7 tasks complete)

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

## T4 Status: 🔄 Pending

**Research Notes Final Audit: Completeness and Coherence**
*Estimate: 1.5h (adjusted mentally to 2.0h — T1 and T3 both modify docs/research_notes.md before this audit runs)*

Not started. Full end-to-end read of `docs/research_notes.md` against four-question checklist per finding. Targeted review of Findings 2, 7, 8, 9. Final finding count to be confirmed at 10 (9 active, 1 superseded).

---

## T5 Status: 🔄 Pending

**Final Cold-Boot Benchmark Run: Definitive Published Results**
*Estimate: 0.75h*

Not started. Full cold-boot procedure: kill all Ollama and Python processes, verify VRAM baseline via nvidia-smi, warm with throwaway chat query ("What is a large language model?"), run `python tests/test_benchmark.py`. Demo sequence Run 4 from cold boot. System state at benchmark start to be documented in this section on completion.

---

## T6 Status: 🔄 Pending

**Version 1.0.0 Release and Final CHANGELOG**
*Estimate: 0.75h*

Not started. CHANGELOG v1.0.0 entry to be written per sprint plan template. Git tag `v1.0.0` to be pushed to remote.

---

## T7 Status: 🔄 Pending

**Week 10 Preparation: Final Demo and Submission Materials**
*Estimate: 1.0h*

Not started. `docs/week10_checklist.md` to be created with pre-demo verification, final documentation checklist, and portfolio submission checklist. Week 10 deliverable confirmed: on-camera demo recording (~3 minutes), uploaded to LinkedIn and linked in README.

---

## Hours Summary (Week 9 — In Progress)

| Task | Estimated | Actual |
|------|-----------|--------|
| T1 — "What Has Not Been Measured" rationale | 0.75h | ~0.5h |
| T2 — Session summary fix | 1.0h | ~1.0h |
| T3 — VAD correction propagation | 1.5h | ~1.0h |
| T4 — Research notes final audit | 1.5h | — |
| T5 — Cold-boot benchmark | 0.75h | — |
| T6 — Version 1.0.0 release | 0.75h | — |
| T7 — Week 10 preparation | 1.0h | — |
| **Total** | **7.25h** | **~2.5h** |

---

## Notes

- T1 came in 0.25h under estimate. Existing paragraphs were well-formed; the addition required was one explanatory paragraph per question, not structural revision of the section.
- T4 estimate mentally adjusted to 2.0h: T1 and T3 both modify `docs/research_notes.md` before the audit runs. Auditing a document updated in two places requires more careful end-to-end verification than auditing a stable file.
- GitHub repository made public at the start of Week 9. `data/` confirmed gitignored before publishing.
- Week 10 deliverable confirmed: on-camera demo recording (~3 minutes), uploaded to LinkedIn and linked in README.