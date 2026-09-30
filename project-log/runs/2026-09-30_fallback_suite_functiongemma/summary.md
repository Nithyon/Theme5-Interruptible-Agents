# Local fallback suite: functiongemma

Machine: Intel(R) Core(TM) Ultra 9 275HX, 16.1 GB RAM, 0.0 GB of the model on a GPU, Ollama 0.35.0, 68.1 tokens/s. Timeout 15 s, mode tools.

| Set | Run | Right tool | Fully correct | Stayed out when no tool fits | Self-corrections | No answer | Median time |
|---|---|---|---|---|---|---|---|
| interrupt | 1 | 18/29 | 13/29 | 0/8 | 6/16 | 5 | 0.74 s |
| interrupt | | commands whose outcome changed between runs: 0 | | | | | |

interrupt, run 1, fully correct by kind: correct_value 2/6, correct_place 1/4, change_action 1/4, cancel 0/6, hesitation 3/5, not_a_correction 4/5, double_correction 1/3, correction_then_cancel 0/2, cancel_then_new 1/2

own = 40 commands we wrote. slurp = 111 real requests from the SLURP test set (51 light control, 60 that none of our tools can serve); the mapping from SLURP intent to our tool is ours. interrupt = 37 commands we wrote with mid-sentence corrections, cancellations, hesitations and false alarms. Typed text, no audio.
