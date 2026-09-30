"""One-off: update the documents to the extension's state after the end-to-end runs on audio
of 2026-09-30. Run from the repo root. Each replacement asserts its target exists once."""

E2E = (
    "Run end to end on audio on 2026-09-30: a recorded request clip (our own lines, synthetic voice) was "
    "streamed through LiveKit to the extension agent the way the benchmark streams its recordings, and the "
    "agent's spoken replies and the recovery log were saved. **In-car EV assistant (the headline scenario), "
    "`project-log/runs/2026-09-30_ext_car_e2e/`:** a corrected reroute (one call), a traffic check, a charger "
    "lookup that failed twice and succeeded on the third try, a booking, a repeated booking that was not "
    "re-executed, a change of time that cancelled the first booking before making the new one, and two failed "
    "roadside requests ending in a hand-off with a reference. The home pack was run the same way "
    "(`runs/2026-09-30_ext_home_e2e*/`). Each folder has `conversation.wav` (the whole exchange), the recovery "
    "log and the agent log. Limits: one run per scenario, no live human speaker, and the spoken progress notice "
    "for slow tools is switched off because the model read its instruction aloud (see `WORKLOG.md`)."
)


def fix(path, pairs):
    s = open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert s.count(a) == 1, (path, a[:70], s.count(a))
        s = s.replace(a, b)
    open(path, "w", encoding="utf-8", newline="\n").write(s)
    print("updated", path, len(pairs))


def fix_between(path, start, end, new):
    s = open(path, encoding="utf-8").read()
    assert s.count(start) == 1, (path, start[:60], s.count(start))
    i = s.index(start)
    j = s.index(end, i) + len(end)
    s = s[:i] + new + s[j:]
    open(path, "w", encoding="utf-8", newline="\n").write(s)
    print("updated", path, "(span)")


fix("README.md", [
    ("| offline tests; the agent starts, no spoken conversation held yet |",
     "| offline tests; run end to end on recorded request clips (in-car and home), see the Extension section |"),
    ("; the extension has not been run live.",
     "; the extension has been run end to end on recorded clips only, not with a live speaker."),
])
fix_between("README.md", "The LiveKit agent `extension/ext_agent.py` is written but had **not been run live**",
            "(see `project-log/VIDEO_SCRIPT.md`).", E2E)

fix("project-log/TEAM_HANDOFF.md", [
    ("The in-car extension agent (`extension/ext_agent.py`) has not been run live yet, so the extension segment "
     "cannot be shown live until someone runs it.",
     "The extension agent has been run end to end on recorded clips (`runs/2026-09-30_ext_car_e2e/`, "
     "`runs/2026-09-30_ext_home_e2e/`); `conversation.wav` in each folder is the whole exchange and can be "
     "played in the video."),
    ("but has not been run live.",
     "and was run end to end on recorded audio on 30 Sep (in-car: retries, duplicate blocked, rollback and "
     "hand-off are all in the recovery log)."),
    ("`ext_agent.py` never run live; mock tools only.",
     "`ext_agent.py` run end to end on a recorded clip (30 Sep); mock tools only."),
    ("extension not run live.", "extension run end to end on recorded clips."),
    ("not a Bixby integration, not run live.", "not a Bixby integration; run end to end on a recorded clip."),
])
fix_between("project-log/SLIDES_OUTLINE.md", "; the live LiveKit run is [", "]",
            "; both packs were run end to end on a recorded request clip through LiveKit (30 Sep), the in-car EV "
            "assistant as the headline scenario; no live human speaker")
fix("project-log/JUDGE_QA.md", [
    ("The device tools are mocks.",
     "The device tools are mocks. Both were run end to end on recorded request clips through LiveKit on 30 "
     "September; the in-car EV assistant is the headline scenario (`runs/2026-09-30_ext_car_e2e/`)."),
])
fix("project-log/PRESENTATION_SCRIPT.md", [
    ("We tested these behaviours with automated tests that drive the recovery layer, not yet in a live spoken "
     "conversation.",
     "We ran both end to end on recorded request clips, the same way the benchmark plays its recordings, and the "
     "recovery log shows each of these steps. We have not done it with a live speaker."),
])
s = open("extension/README.md", encoding="utf-8").read()
s = s.rstrip("\n") + (
    "\n\n## End-to-end runs on audio (2026-09-30)\n\n" + E2E + "\n\n"
    "To repeat: `python extension/e2e/make_clip_car.py` (in the text-to-speech environment) builds the request "
    "clip; `bash project-log/scripts/ext_e2e_car.sh` starts the agent, streams the clip with the benchmark's "
    "runner and saves the results (`ext_e2e.sh` and `make_clip.py` do the same for the home pack). Do not run "
    "it while a benchmark run is using the same LiveKit project.\n\n"
    "What the first attempts found and fixed: `session.say(text)` is not available on a speech-to-speech "
    "session (it crashed the tool on rollback); recovery events are now written as they happen; the model read "
    "callback instructions aloud, so hand-off and rollback are announced from the tool result and the progress "
    "notice is off; a prompt rule stops the model from claiming a transfer when a tool only failed. The first "
    "attempts are kept in `runs/*_attempt1` and `*_attempt2`.\n"
)
open("extension/README.md", "w", encoding="utf-8", newline="\n").write(s)
print("updated extension/README.md")
