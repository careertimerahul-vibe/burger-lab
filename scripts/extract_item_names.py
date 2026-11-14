#!/usr/bin/env python3
"""Extract menu item names from config.js so captions can be checked against them."""
import json
import re

src = open("/opt/data/projects/burger-lab/config.js").read()
names = sorted(set(re.findall(r'name:\s*"([^"]+)"', src)))
out = "/opt/data/projects/burger-lab/data/menu_item_names.json"
json.dump({"names": names}, open(out, "w"), indent=1)
print(len(names), "names ->", out)
print(names[:10])
