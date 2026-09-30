# Local fallback suite: gemma4:26b-a4b-it-qat

Machine: Intel(R) Core(TM) Ultra 7 258V, 32.4 GB RAM, 8.3 GB of the model on a GPU, Ollama 0.32.14, 16.4 tokens/s. Timeout 30 s, mode tools.

| Set | Run | Right tool | Fully correct | Stayed out when no tool fits | Self-corrections | No answer | Median time |
|---|---|---|---|---|---|---|---|
| own | 1 | 36/36 | 34/36 | 4/4 | 6/6 | 0 | 5.56 s |
| own | | commands whose outcome changed between runs: 0 | | | | | |
| slurp | 1 | 46/51 | 45/51 | 60/60 | 0/0 | 0 | 5.99 s |
| slurp | | commands whose outcome changed between runs: 0 | | | | | |

own = 40 commands we wrote. slurp = 111 real requests from the SLURP test set (51 light control, 60 that none of our tools can serve); the mapping from SLURP intent to our tool is ours. Typed text, no audio.
