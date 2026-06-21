"""
Final cleanup: remove clearly off-topic records and fix a few claims.
"""
import json

STAGING = r"C:\Users\tukum\Downloads\reopt-pysam\research\sources\2026-06-20_vn-power-market-2026-2_academia.jsonl"

# Titles that are clearly off-topic despite Vietnam mention
EXCLUDE_FRAGMENTS = [
    "port service quality",
    "customer satisfaction",
    "productivity spillovers",
    "firm-level anal",
    "polylactic acid",
    "echolocating bat",
    "bat activity",
    "russia–vietnam ties",  # geopolitics not power
    "pandemic",                 # COVID economic recovery - tangential
    "rivers: the past",        # hydropower history essay
    "foreign direct investment and productivity",
    "essays on the economics of energy",  # dissertation - keep
]

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

print(f"Input: {len(records)}")

filtered = []
removed = []
for rec in records:
    title_lower = rec.get("title","").lower()
    skip = False
    for frag in EXCLUDE_FRAGMENTS:
        if frag.lower() in title_lower:
            skip = True
            removed.append(rec["title"][:70])
            break
    if not skip:
        filtered.append(rec)

print(f"Removed {len(removed)} off-topic records:")
for t in removed:
    print(f"  - {t}")
print(f"Remaining: {len(filtered)}")

# Renumber and fix a few claims
CLAIM_MAP = {
    "q4-BESS": "Battery energy storage system (BESS) integration economics for Vietnam grid",
    "q5-TOU": "Vietnam electricity tariff structure, TOU pricing, and demand response",
    "q6-tariff": "Vietnam EVN tariff cost structure, escalation trajectory, and price reform",
    "q7-solar": "Vietnam solar PV policy, rooftop net metering, and regulatory framework",
    "q8-offshore": "Vietnam offshore wind development economics and investment framework",
}

final = []
for i, rec in enumerate(filtered, 1):
    rec["id"] = f"aca-{i:03d}"
    via_base = "-".join(rec.get("discovered_via","").split("-")[:2])
    if via_base in CLAIM_MAP and "manual" not in rec.get("discovered_via",""):
        rec["claim"] = CLAIM_MAP[via_base]
    final.append(rec)

with open(STAGING, "w", encoding="utf-8") as f:
    for rec in final:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"\nFinal file: {len(final)} rows")

tier_c = {}
for r in final:
    t = r["tier"]
    tier_c[t] = tier_c.get(t, 0) + 1
print(f"Tier distribution: {tier_c}")

oa_count = sum(1 for r in final if r["signal"]["oa"])
print(f"Open access: {oa_count}/{len(final)}")

year_recent = sum(1 for r in final if r["signal"]["year"] >= 2022)
print(f"Published 2022-2026: {year_recent}/{len(final)}")

print(f"\nSATURATION CHECK: {len(final)} >= 57 target: {'YES' if len(final) >= 57 else 'NO'}")
