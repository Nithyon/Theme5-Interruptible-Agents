"""Show the columns of the SLURP test shard and how many light-control recordings it holds."""
import collections, sys
import pyarrow.parquet as pq

p = sys.argv[1]
f = pq.ParquetFile(p)
print(f.schema_arrow)
cols = [c for c in f.schema_arrow.names if c != "audio"]
t = f.read(columns=cols).to_pandas()
print(len(t), "rows")
print(t.head(3).to_string())
for c in cols:
    if t[c].dtype == object and t[c].map(lambda v: isinstance(v, str)).all() and t[c].nunique() < 120:
        print(c, dict(collections.Counter(t[c]).most_common(100)))
