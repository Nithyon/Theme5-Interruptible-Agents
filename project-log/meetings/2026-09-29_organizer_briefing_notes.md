# Organizer briefing notes (2026-09-29)

Source: `2026-09-29_organizer_briefing_transcript.md`, an auto-transcription (Otter.ai-style) of the PRISM organizer Q&A. Several proper nouns and numbers are almost certainly mis-heard by the transcription tool — flagged inline as **[uncertain]**. This is very likely the meeting `PLAN_VS_ACTUAL.md` listed as `MEETING_2026-09-29_FDBv3_switch.md`, which that file marked "unverified / not found" — it can now be considered found and analyzed here.

## Key facts (with quotes)

1. **Scoring is 60% benchmark / 20% extension / 20% docs**, confirmed directly: *"we will have 60% of the uh score... dedicated to the benchmark score"*; *"we will award uh 20% for that [extension]. And the rest of the documentation and architecture will fetch you... other 20%."*

2. **They re-run your code and check your run logs, not just your numbers.** *"we do not believe your numbers... we will check the logs, whatever run logs you provide, as well as we rerun your codes on the same benchmark."* Also: *"people might quote uh some numbers, but uh the run logs will suggest something else."*

3. **"One-command" is a goal, not a strict literal requirement.** *"Do not take one-command as very serious... if you can wrap all the script all the commands in a script file, that will be great."*

4. **The `--use-llm` judge is optional; report whichever numbers you get.** *"There are two options: you can either target locally, which will not involve an LLM, or you can use this use LLM flag... combining all those things, you will... report the numbers."*

5. **The 48GB VRAM limit only applies if you bring your own model/checkpoint**, not if you use hosted APIs. *"if you are using a uh own model of custom checkpoint, make sure that your model can run with a VRAM of 48GBs."* Separately, they clarified they don't supply a GPU to you: *"we are not providing GPU... I will rerun your code in a... environment that has 48GBs of VRAM. That is it."* (A separate mention of *"16,000 uh A6000 GPU"* **[uncertain — likely mis-transcribed, unclear what number/model was actually said]** appears earlier and isn't repeated or explained later; treat the 48GB figure as the reliable one since it's stated plainly twice.)

6. **Gemini/Gemma are preferred and need no key for reproduction; other providers might.** *"for Gemini and Gemma, uh we will not need the key, even for... the big large, we don't need the key. But however, if you're planning for some other lab, we might ask you to... reach out to you for... reproduction steps."* Earlier, on why Gemini is preferred: *"since we have a close integration with Gemini, you will find... we can easily reproduce."* — **but this is ambiguous for us specifically** (see Open Questions #1): it's unclear whether this covers our Vertex-AI-via-ADC path or assumes a plain AI Studio API key.

7. **FDB-v3 (the benchmark itself) has no video/vision input in Round 1; that may change in Round 2.** *"I don't think full duplex bench has any kind of vision inputs... that is not at least the case in the first round."* *"Full duplex is uh wave... you'll find only the wave files here, uh no video as such."* Round 2 possibility: *"there then will be three modalities: uh the tool call... the audio, and the video."* This is about the **benchmark's input data**, not about whether a demo video deliverable is required (that's still required, separately — see fact 12).

8. **The extension should extend the "dual-mind" idea** (one mind talking, one mind thinking), to new use cases, and user-experience/cost/latency savings earn points too. *"Use case extension is something that if you're able to extend the same uh dual dual-mind thing, where one mind is talking and one mind is thinking... we will award uh 20% for that."* Also: *"if you can provide certain kind of extension in terms of use case or... user experience or some kind of cost saving or latency saving... we will be happy to... award you extra brownie points."*

9. **Recovery from tool failures and variable latency should be showcased**, not hidden. *"There will be instances where the tasks will fail. You will have to manage that. There will be instances where the latency will be variable... those kind of things if you... can showcase, that will be very good... you should be able to recover cleanly... You can retry, you can close the session, you can move it to human in the loop... but... you should be able to recover."*

10. **Text output is acceptable if voice generation is hard — state the assumption.** *"it is accepting a wave file and it is giving out a wave file or a text file... if you are finding difficulty in generating the voice, it is okay to put your responses in text... make those kind of assumptions, state those assumptions."*

11. **Artificial Analysis is a reference point, not a target to beat.** *"this is not a very hard... you have to beat these numbers, but these will act as a good reference point."*

12. **A demo video and a slide deck are still required deliverables** (separate from fact 7's "no video input" point). *"the demo videos that you will submit should... have all the things... what approach you have followed... what architecture."* Confirmed again later: *"we are expecting a GitHub repo, one slide... one PPT slide, and the demo."*

13. **Originality is checked; replicating published numbers honestly is fine, claiming someone else's model as your own work is not.** *"you cannot say that I am using GPT Realtime and then... claim that... that is my finding or that is my project."* *"we do have techniques to... understand whether it was taken from somewhere else... If we have any kind of doubt, you will surely reach out to us."*

14. **An AI-usage declaration form must be filled whenever AI is used** — no restriction on which AI. *"there are no restriction on what AI you can use. Uh the only thing is that we have already circulated one uh declaration form... whenever you are using an AI, please make sure that you are filling it out."*

15. **A Bixby-relevant use case is valued but subjective/bonus, not required.** *"if you are able to get us a use case which relates to Bixby, that is... wonderful for us."* (A number **"40%"** is mentioned right after this in the transcript — almost certainly a slip/mis-transcription, since the extension is stated as 20% everywhere else in the same conversation; don't treat "40%" as a real figure.) Framed as bonus, not core: *"even if you have... an average score in... the benchmark, but you are able to showcase good use cases, then also... it gives you a fair chance."*

16. **No restriction on architecture — voice-to-voice, cascaded text, or rule-based are all fine**, but tool-calling reliability is the real tradeoff. *"We have not put any kind of restrictions... you can use a text-based model. You can use a voice-to-voice model... rule-based... free to do that."* But: *"it will better if you can align your performance, because if you say voice-to-voice, whether it is able to make those tool calls or not, that becomes a bottleneck... when you are... scoring against these kind of benchmarks."* — this directly validates our commit-gate approach on a speech-to-speech model.

17. **Deadline — conflicting statements in this transcript itself:**
    - Initially raised as possibly moving: *"I guess it is 30th September right now, but I guess we can move it to 4th of October or something. But uh PRISM team will communicate to you about this."*
    - Later, when asked directly: *"it is already extended to 30th"* / *"Yes, extended 30th"* / *"take 30th as the deadline for now."*
    - Still later, a single line says: *"the deadline submission has been extended to 30th of November."* **[uncertain — almost certainly a transcription or speaker error; contradicts every other statement in the same meeting, including ones said minutes earlier, and is never confirmed or repeated]**
    - **Conclusion: plan for 30 Sep 2026, 11:59 PM IST**, consistent with `STATUS.md`'s existing Deadline section. Treat "4 Oct" as a possible-but-unconfirmed extension and "30 Nov" as noise, not signal.

18. **Other transcription uncertainties, flagged, not used as fact:** the paper is attributed in the transcript to *"Gaoxuan"* **[uncertain — the actual first author, verified independently via arXiv in this session's earlier research, is Guan-Ting Lin; "Gaoxuan" is very likely a mishearing]**; the paper is also described as *"from NTU and NVIDIA"* **[unverified by us independently — our own earlier check of the arXiv page confirmed NTU-affiliated authors (Guan-Ting Lin, Chen Chen, Zhehuai Chen, Hung-yi Lee) but did not confirm an NVIDIA affiliation]**; the organizer contact email appears as *"prism@campaign.com"* **[uncertain — likely mis-transcribed; conflicts with `BUILD_PLAN_FDB_V3.md`'s assumed "prism@samsung.com"]**.

## What changes for us

| Point | Our current state | Action | Owner suggestion |
|---|---|---|---|
| Judge (`--use-llm`) | `STATUS.md`: blocked on an OpenAI/Azure key, "until then scoring is exact-match" | **Keep pursuing, but de-prioritize as a blocker** — organizers explicitly accept either scoring mode ("report the numbers"). Exact-match-only is a valid submission if the Azure key doesn't land in time. | Infra (the teammate wiring the Azure GPT-4o judge, per the earlier upgrade-pack review) |
| Vertex AI + ADC reproduction | `STATUS.md` open risk: *"organizers would need their own Google Cloud login to re-run a Vertex agent"* | **Still open — email them (see Open Questions #1).** The transcript's "we will not need the key" doesn't clearly resolve whether this covers our Vertex/ADC setup specifically, or assumes a plain API key. | Saini (sends the email; only he can authorize contacting PRISM) |
| `reproduce.sh` / one-command script | Drafted in S4, a bash script wrapping multiple steps | **No change needed** — organizer explicitly said not to take "one command" too literally; a wrapper script is exactly what they asked for. | Infra/Agent-core owner (per `BUILD_PLAN_FDB_V3.md`'s workstream split) |
| Run logs in the submission | `STATUS.md`: "push the full baseline run folder... before submission" already planned | **Reinforce priority** — this is the single most emphasized reproducibility point in the whole transcript ("we will check the logs... run logs will suggest something else"). | Whoever does Phase 5 packaging |
| 48GB VRAM limit | `BUILD_PLAN_FDB_V3.md` already scopes this to "our own checkpoints," correctly | **No change** — confirmed correct; hosted-API reproduction isn't VRAM-constrained on their side. | — |
| Extension design | `PLAN_VS_ACTUAL.md` flagged two competing, unbuilt ideas: kit-harness Bixby pack (PDF) vs. LiveKit-native camera troubleshooting (`BUILD_PLAN_FDB_V3.md`) | **Reprioritize toward the BUILD_PLAN version, and treat the camera/video part as optional, not core** — the "dual-mind" framing organizers want is exactly BUILD_PLAN's "same coordinator, new adapter" idea, and video is explicitly a Round 2 concept, not evaluated in Round 1. A cheaper, camera-free extension scenario (still using the same talker/reasoner/gate) may be more time-efficient than building camera ingestion under this deadline. | Extension workstream owner (Phase 4a, per `BUILD_PLAN_FDB_V3.md`) |
| Deadline | `STATUS.md` already states 30 Sep 2026, 11:59 PM IST | **No change** — this transcript's contradictions resolve to the same date `STATUS.md` already uses; worth still getting written confirmation per the open question below. | Saini (email) |
| AI-usage declaration form | Not currently tracked as an explicit checklist item in `STATUS.md` | **Add it** to the submission checklist — organizer stressed it twice. | Docs/deck owner (Phase 4b/5) |
| Bixby-style use case | Treated in `PLAN_VS_ACTUAL.md` as one of two candidate extension directions | **Keep as a bonus framing, not the core deliverable** — organizer called it subjective/"cherry on the cake," not a scored requirement on its own. | Extension workstream owner |

## Open questions to email the organizers

1. Does *"for Gemini and Gemma we will not need the key"* cover our specific setup — Vertex AI via Application Default Credentials (needing your own Google Cloud project login to re-run) — or does it assume a plain Gemini API key? If it's the latter, do you have a way to run a Vertex/ADC-based agent, or should we switch back to a plain API key for the submission?
2. Given this session's own contradictory statements on the deadline (30 Sep, a possible 4 Oct, and a later "30 Nov" that seems inconsistent with everything else said), can you confirm the final submission deadline in writing?
3. Is the camera/video extension idea purely a Round 2 preview, or would including it (even partially) in a Round 1 submission earn any credit toward the 20% extension score — should we deprioritize it in favor of an audio/text-only extension given the time we have left?
4. Which exact contact email should we use — the transcript shows what sounds like "prism@campaign.com," but we had assumed "prism@samsung.com" from an earlier document?
5. (Carried over from `BUILD_PLAN_FDB_V3.md`'s own open list, still unanswered) Exactly which FDB-v3 numbers make up the 60%: strict Pass@1 alone, or combined with Tool-F1/latency — and should the headline number use `--use-llm` or exact-match?
