import sys; sys.path.insert(0, "/mnt/d/Theme5-Interruptible-Agents/fdb_agent")
import responsive as r
f = r._load_frames(r.ACK_PATH)
print("ack frames:", len(f), "| rate", f[0].sample_rate, "| seconds", round(len(f) * 0.02, 2))
