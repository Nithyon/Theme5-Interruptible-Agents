import sys
sys.path.insert(0, "/mnt/d/Theme5-Interruptible-Agents/project-log/scripts")
import judge_vertex as jv
j = jv.VertexJudge()
r = j.chat.completions.create(model="gpt-4o", temperature=0, max_tokens=200, messages=[{"role": "user", "content":
    'Is "NYC" the same destination as "New York"? Respond with ONLY a JSON object: {"correct": true/false, "explanation": "brief reason"}'}])
print(jv.MODEL, "->", r.choices[0].message.content.strip()[:200])
print(jv.stats)
