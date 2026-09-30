# Local fallback suite: gemma4:e4b-it-qat

Machine: Intel(R) Core(TM) Ultra 7 258V, 32.4 GB RAM, 3.1 GB of the model on a GPU, Ollama 0.32.14, 27.8 tokens/s. Timeout 30 s, mode tools.

| Set | Run | Right tool | Fully correct | Stayed out when no tool fits | Self-corrections | No answer | Median time |
|---|---|---|---|---|---|---|---|
| interrupt | 1 | 29/29 | 29/29 | 6/8 | 14/16 | 0 | 2.24 s |
| interrupt | 2 | 29/29 | 29/29 | 6/8 | 14/16 | 0 | 2.27 s |
| interrupt | 3 | 29/29 | 29/29 | 6/8 | 14/16 | 0 | 2.12 s |
| interrupt | | commands whose outcome changed between runs: 0 | | | | | |

interrupt, run 1, fully correct by kind: correct_value 6/6, correct_place 4/4, change_action 4/4, cancel 5/6, hesitation 5/5, not_a_correction 5/5, double_correction 3/3, correction_then_cancel 1/2, cancel_then_new 2/2

interrupt, run 2, fully correct by kind: correct_value 6/6, correct_place 4/4, change_action 4/4, cancel 5/6, hesitation 5/5, not_a_correction 5/5, double_correction 3/3, correction_then_cancel 1/2, cancel_then_new 2/2

interrupt, run 3, fully correct by kind: correct_value 6/6, correct_place 4/4, change_action 4/4, cancel 5/6, hesitation 5/5, not_a_correction 5/5, double_correction 3/3, correction_then_cancel 1/2, cancel_then_new 2/2

own = 40 commands we wrote. slurp = 111 real requests from the SLURP test set (51 light control, 60 that none of our tools can serve); the mapping from SLURP intent to our tool is ours. interrupt = 37 commands we wrote with mid-sentence corrections, cancellations, hesitations and false alarms. Typed text, no audio.
