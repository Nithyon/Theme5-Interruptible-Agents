# Local fallback suite: gemma4:26b-a4b-it-qat

Machine: Intel(R) Core(TM) Ultra 7 258V, 32.4 GB RAM, 8.4 GB of the model on a GPU, Ollama 0.32.14, 16.9 tokens/s. Timeout 30 s, mode tools.

| Set | Run | Right tool | Fully correct | Stayed out when no tool fits | Self-corrections | No answer | Median time |
|---|---|---|---|---|---|---|---|
| interrupt | 1 | 29/29 | 28/29 | 8/8 | 16/16 | 0 | 5.86 s |
| interrupt | | commands whose outcome changed between runs: 0 | | | | | |

interrupt, run 1, fully correct by kind: correct_value 6/6, correct_place 4/4, change_action 4/4, cancel 6/6, hesitation 4/5, not_a_correction 5/5, double_correction 3/3, correction_then_cancel 2/2, cancel_then_new 2/2

own = 40 commands we wrote. slurp = 111 real requests from the SLURP test set (51 light control, 60 that none of our tools can serve); the mapping from SLURP intent to our tool is ours. interrupt = 37 commands we wrote with mid-sentence corrections, cancellations, hesitations and false alarms. Typed text, no audio.
