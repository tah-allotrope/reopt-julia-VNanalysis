"""
Quality audit: count Vietnam-specific vs generic entries in staging file.
Also prints a summary by sub-question and tier.
"""
import json

STAGING = r"C:\Users\tukum\Downloads\reopt-pysam\research\sources\2026-06-20_vn-power-market-2026-2_academia.jsonl"

VN_KWS = ["vietnam", "viet nam", "vietnamese", "evn ", "evn,", "hanoi", "ho chi minh",
           "mekong", "pdp8", "dppa", "erav", "ipp", "duc hue"]

records = []
with open(STAGING, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            records.append(rec)
        except:
            pass

print(f"Total rows: {len(records)}")

vn_specific = []
generic = []
for r in records:
    combined = (r.get("title","") + " " + r.get("claim","") + " " + r.get("note","")).lower()
    if any(kw in combined for kw in VN_KWS):
        vn_specific.append(r)
    else:
        generic.append(r)

print(f"Vietnam-specific: {len(vn_specific)}")
print(f"Generic/tangential: {len(generic)}")

# By tier
tier_counts = {}
for r in vn_specific:
    t = r.get("tier", 5)
    tier_counts[t] = tier_counts.get(t, 0) + 1
print(f"\nVN-specific by tier:")
for t in sorted(tier_counts):
    print(f"  Tier {t}: {tier_counts[t]}")

# By sub-question
tag_map = {}
for r in vn_specific:
    tag = r.get("discovered_via","unknown").split("-")[0] + "-" + r.get("discovered_via","").split("-")[1] if "-" in r.get("discovered_via","") else r.get("discovered_via","")
    tag = "-".join(r.get("discovered_via","").split("-")[:2])
    tag_map[tag] = tag_map.get(tag, 0) + 1
print(f"\nVN-specific by source tag:")
for t, c in sorted(tag_map.items()):
    print(f"  {t}: {c}")

# Top VN-specific by citation
print(f"\nTop 15 VN-specific by citations:")
top = sorted(vn_specific, key=lambda x: -x["signal"]["citations"])[:15]
for r in top:
    print(f"  [{r['id']}] T{r['tier']} {r['signal']['year']} cites={r['signal']['citations']:4d} | {r['title'][:70]}")

# Sample generic for assessment
print(f"\nSample 5 generic entries:")
for r in generic[:5]:
    print(f"  [{r['id']}] T{r['tier']} {r['signal']['year']} cites={r['signal']['citations']:4d} | {r['title'][:70]}")
