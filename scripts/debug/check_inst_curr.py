from scripts.shared.db import execute_query
import pandas as pd

results = execute_query("SELECT * FROM instruments WHERE symbol = '2318.HK'")
if results:
    print(dict(results[0]))
else:
    print("Not found")
