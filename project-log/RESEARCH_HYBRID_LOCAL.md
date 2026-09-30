# Evidence: hybrid local + cloud models (fallback, routing, offline)

Collected 2026-09-29 for the "Gemma local fallback" idea (brownie points for user experience / cost / latency savings, organizer briefing). ✅ = quote checked on the primary page; ◐ = from a search summary of the primary source.

## Research papers

1. ✅ **Hybrid LLM: Cost-Efficient and Quality-Aware Query Routing**, Ding et al., **ICLR 2024** (Microsoft Research / UBC). https://arxiv.org/abs/2404.14618
   - Problem: large LLMs "require expensive cloud servers", while "smaller models that can be deployed on lower cost (e.g., edge) devices, tend to lag behind in terms of response quality."
   - Method: "a router that assigns queries to the small or large model based on the predicted query difficulty and the desired quality level."
   - Result: "up to 40% fewer calls to the large model, with no drop in response quality."
2. ◐ **RouteLLM: Learning to Route LLMs with Preference Data**, Ong et al. (LMSYS / UC Berkeley), ICLR 2025. https://arxiv.org/abs/2406.18665 · blog https://www.lmsys.org/blog/2024-07-01-routellm/
   - Routes between a strong and a weak model; reported cost reductions of over 2× without sacrificing response quality (e.g. >85% on MT Bench vs GPT-4 only, at 95% of GPT-4's performance).

## Industry use

3. ✅ **Google FunctionGemma** (Gemma 3 270M specialized for function calling). https://deepmind.google/models/gemma/functiongemma/
   - "An open model specialized for function calling at the edge."
   - "Enables inference on mobile and IoT devices so data is processed locally, protecting user privacy."
   - "Process common commands on-device or route to larger models for more complex tasks."
   - Mobile Actions: fine-tuning raised accuracy from 58% to 85%, i.e. small local models need task-specific tuning to be reliable.
4. ✅ **Cerence xUI** (automotive voice assistant platform). https://www.cerence.com/cerence-products/conversational-generative-ai
   - "seamlessly integrates cloud and edge AI to power advanced conversational UX"; "uninterrupted access even when the vehicle is offline."
   - ◐ Search summaries (not on that page) describe its edge model CaLLM Edge as a 4-bit quantized Microsoft Phi-3.

## What this supports for us (honest reading)

- Hybrid "small local + large cloud" with routing or fallback is an established, published pattern (ICLR 2024/2025) and is shipped in production for cars (Cerence) and phones (Google's on-device Gemma models).
- The same sources say small local models are **less accurate** (Hybrid LLM: "lag behind in terms of response quality"; FunctionGemma: 58% base accuracy), so the cloud model stays primary for the benchmark; local Gemma is for **availability (offline/outage), cost routing and privacy**, which is the in-car extension's case.

## Voice-specific routing: "one model talks, a stronger model thinks" (added 2026-09-30)

5. ✅ **OpenAI Realtime Agents, "Chat-Supervisor" pattern** (official demo repo). https://github.com/openai/openai-realtime-agents
   - A realtime chat agent handles greeting, small talk and collecting information; "a more intelligent, text-based supervisor model (e.g. gpt-4.1) is used extensively to handle tool calls and more challenging responses." Trade-off stated: high-quality answers "with a small increase in latency."
6. ✅ **LiveKit, "Supervisor pattern for voice agents"** (blog, 2026-03-23). https://livekit.com/blog/supervisor-pattern-voice-agents
   - One agent keeps the session; specialist Tasks run "inside the same session, share the voice pipeline", so turn detection and interruption handling are preserved. No latency/accuracy numbers given.
7. ◐ **LTS-VoiceAgent: Listen-Think-Speak** (Zou et al., arXiv 2601.19952, Jan 2026). https://arxiv.org/abs/2601.19952
   - Abstract: "End-to-end models often lack deep reasoning, while cascaded pipelines incur high latency"; a semantic trigger decides when to think, a dual-role orchestrator runs background thinking and foreground speech in parallel. Introduces a **Pause-and-Repair** benchmark (relevant to self-corrections). Numbers not checked yet.
8. ◐ **Can Speech LLMs Think while Listening?** (arXiv 2510.07497, ICLR 2026 poster). Starts reasoning before the question ends using a "question completeness" signal; search summary reports ~70% lower reasoning latency without accuracy loss. Not checked on the paper.
9. ✅ (already in INDUSTRY_BENCHMARKS.md) Artificial Analysis: Gemini 3.8 Live Tau3 Voice 30.1 vs its Extended Thinking variant 68.6 — the voice model is fluent but much weaker on multi-step tool tasks, which is the gap a supervisor/escalation route targets.

**Reading for us:** the published and shipped pattern is: the realtime model keeps talking; hard turns go to a stronger text model. Our gate already holds every tool call before it runs, so the "thinking" step (verify/repair the held call's arguments with a stronger model) can happen inside the hold, only for turns our router flags as complex. It targets wrong arguments (our largest failure class), not late changes after execution.
