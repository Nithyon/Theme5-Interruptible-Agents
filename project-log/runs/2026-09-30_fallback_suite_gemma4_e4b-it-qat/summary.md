# Local fallback suite: gemma4:e4b-it-qat

Machine: Intel(R) Core(TM) Ultra 7 258V, 32.4 GB RAM, 3.1 GB of the model on a GPU, Ollama 0.32.14, 27.5 tokens/s. Timeout 30 s, mode tools.

| Set | Run | Right tool | Fully correct | Stayed out when no tool fits | Self-corrections | No answer | Median time |
|---|---|---|---|---|---|---|---|
| own | 1 | 36/36 | 34/36 | 4/4 | 6/6 | 0 | 2.06 s |
| own | 2 | 36/36 | 34/36 | 4/4 | 6/6 | 0 | 1.95 s |
| own | 3 | 36/36 | 34/36 | 4/4 | 6/6 | 0 | 2.07 s |
| own | | commands whose outcome changed between runs: 0 | | | | | |
| slurp | 1 | 20/51 | 18/51 | 60/60 | 0/0 | 0 | 1.67 s |
| slurp | 2 | 20/51 | 18/51 | 60/60 | 0/0 | 0 | 1.67 s |
| slurp | 3 | 20/51 | 18/51 | 60/60 | 0/0 | 0 | 1.68 s |
| slurp | | commands whose outcome changed between runs: 0 | | | | | |

own = 40 commands we wrote. slurp = 111 real requests from the SLURP test set (51 light control, 60 that none of our tools can serve); the mapping from SLURP intent to our tool is ours. Typed text, no audio.
