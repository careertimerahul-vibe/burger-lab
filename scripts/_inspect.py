import json, csv
from collections import Counter

d = json.load(open('/opt/data/projects/burger-lab/data/wa_burgerlab_full.json'))
noin = [c for c in d if not c.get('is_group') and not any(not m.get('me') for m in c.get('messages', []))]
print("no_inbound dms:", len(noin))
print("  zero messages:", sum(1 for c in noin if not c.get('messages')))
print("  only outbound:", sum(1 for c in noin if c.get('messages')))
print("  msg_count buckets:", Counter(min(c.get('msg_count', 0), 5) for c in noin).most_common())
print("  sample outbound-only:", [c['messages'][-1]['x'][:60] for c in noin if c.get('messages')][:5])

rows = list(csv.DictReader(open('/opt/data/projects/burger-lab/data/wa_customers.csv')))
cust = [r for r in rows if r['verdict'] == 'customer']
print("\ncustomers:", len(cust))
for r in cust[:15]:
    print(f"  {r['phone']:>14} | {r['confidence']:6} | {r['last_activity'][:18]:18} | {r['evidence'][:70]}")
