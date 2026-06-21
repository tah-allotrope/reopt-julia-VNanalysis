"""
Stricter audit: check title/note for Vietnam-specific keywords only.
Also produces a clean count summary.
"""
import json

STAGING = r"C:\Users\tukum\Downloads\reopt-pysam\research\sources\2026-06-20_vn-power-market-2026-2_academia.jsonl"

# Strict Vietnam keywords - must appear in title or note
VN_STRICT = ["vietnam", "viet nam", "vietnamese", "evn", "hanoi", "ho chi minh",
              "mekong", "pdp8", "dppa", "erav", "duc hue", "southeast asia", "asean",
              "indochina", "haiphong", "da nang"]

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
    # Check title AND note (venue) only — not the generic "claim" field
    title_lower = r.get("title","").lower()
    note_lower = r.get("note","").lower()
    via_lower = r.get("discovered_via","").lower()

    # Manual entries are all Vietnam-relevant by design
    if "manual" in via_lower:
        vn_specific.append(r)
        continue

    if any(kw in title_lower or kw in note_lower for kw in VN_STRICT):
        vn_specific.append(r)
    else:
        generic.append(r)

print(f"Vietnam-specific (strict): {len(vn_specific)}")
print(f"Generic/tangential (excluded): {len(generic)}")

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
    tag = "-".join(r.get("discovered_via","unknown").split("-")[:2])
    tag_map[tag] = tag_map.get(tag, 0) + 1
print(f"\nVN-specific by source tag:")
for t, c in sorted(tag_map.items()):
    print(f"  {t}: {c}")

# Top VN-specific by citation
print(f"\nTop 20 VN-specific by citations:")
top = sorted(vn_specific, key=lambda x: -x["signal"]["citations"])[:20]
for r in top:
    print(f"  [{r['id']}] T{r['tier']} {r['signal']['year']} cites={r['signal']['citations']:4d} | {r['title'][:75]}")

print(f"\nRecent (2024-2026) VN-specific papers:")
recent = [r for r in vn_specific if r["signal"]["year"] >= 2024]
recent.sort(key=lambda x: -x["signal"]["citations"])
for r in recent[:15]:
    print(f"  [{r['id']}] T{r['tier']} {r['signal']['year']} cites={r['signal']['citations']:4d} | {r['title'][:75]}")

# Show generic sample to understand what's being excluded
print(f"\nSample 10 generic (excluded) titles:")
for r in generic[:10]:
    print(f"  T{r['tier']} {r['signal']['year']} cites={r['signal']['citations']:4d} | {r['title'][:75]}")
