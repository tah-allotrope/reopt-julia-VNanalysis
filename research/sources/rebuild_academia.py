"""
Rebuild staging file: keep only Vietnam-specific records, renumber, improve tiers.
Overwrites the staging file with clean, relevant content only.
"""
import json

STAGING = r"C:\Users\tukum\Downloads\reopt-pysam\research\sources\2026-06-20_vn-power-market-2026-2_academia.jsonl"

# Strict Vietnam keywords in title/note
VN_STRICT = ["vietnam", "viet nam", "vietnamese", "evn", "hanoi", "ho chi minh",
              "mekong", "pdp8", "dppa", "erav", "duc hue", "southeast asia", "asean",
              "indochina", "haiphong", "da nang"]

# High-value venues that warrant tier 2
TIER2_VENUES = ["nature", "science", "energy policy", "applied energy", "renewable energy",
                "energy research", "world bank", "adb", "iea", "irena", "world development",
                "nature energy", "joule", "one earth", "energy", "pnas"]

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

print(f"Input: {len(records)} rows")

# Filter to Vietnam-specific
vn_records = []
for r in records:
    via_lower = r.get("discovered_via","").lower()
    title_lower = r.get("title","").lower()
    note_lower = r.get("note","").lower()

    if "manual" in via_lower:
        vn_records.append(r)
        continue

    if any(kw in title_lower or kw in note_lower for kw in VN_STRICT):
        vn_records.append(r)

print(f"Vietnam-specific: {len(vn_records)}")

# Deduplicate by title (case-insensitive)
seen_titles = set()
deduped = []
for r in vn_records:
    tk = r.get("title","").lower().strip()[:80]
    if tk in seen_titles:
        continue
    seen_titles.add(tk)
    deduped.append(r)

print(f"After dedup: {len(deduped)}")

# Re-tier based on venue and citations
def assign_tier(rec):
    via = rec.get("discovered_via","")
    if "manual" in via:
        return 2  # ADB/WB/IEA manual entries
    cites = rec["signal"]["citations"]
    venue = rec.get("note","").lower()
    year = rec["signal"]["year"]

    if cites >= 100 or any(v in venue for v in ["nature energy", "joule", "one earth", "science"]):
        return 2
    if cites >= 30 or any(v in venue for v in TIER2_VENUES):
        return 2
    if cites >= 5 or year >= 2022:
        return 3
    if year >= 2018:
        return 4
    return 5

# Improve claims based on title content
def make_claim(title, via):
    t = title.lower()
    if "pdp8" in t or "power development plan" in t:
        return "Vietnam PDP8 power development plan targets and renewable energy pathway"
    elif "dppa" in t or "direct power purchase" in t or "corporate" in t and "renewable" in t:
        return "Vietnam DPPA/corporate PPA mechanism for renewable energy procurement"
    elif "market reform" in t or "liberaliz" in t or "wholesale" in t or "retail" in t:
        return "Vietnam electricity market reform and liberalization trajectory"
    elif "battery" in t or "bess" in t or "storage" in t:
        return "Battery/energy storage in Vietnam grid context"
    elif "time-of-use" in t or "tariff" in t or "price" in t:
        return "Vietnam electricity tariff structure, TOU pricing, or price reform"
    elif "solar" in t or "photovoltaic" in t or "rooftop" in t:
        return "Vietnam solar PV policy, rooftop installations, or regulatory framework"
    elif "offshore wind" in t or "wind power" in t:
        return "Vietnam offshore/onshore wind power development and policy"
    elif "coal" in t or "phase" in t:
        return "Vietnam coal phase-out and clean energy transition"
    elif "hydrogen" in t:
        return "Vietnam hydrogen economy or gas/power sector decarbonization"
    elif "transition" in t or "net zero" in t or "decarboni" in t:
        return "Vietnam energy transition pathway and net-zero strategy"
    elif "asean" in t or "southeast asia" in t:
        return "Regional ASEAN energy context relevant to Vietnam power market"
    else:
        return "Academic source on Vietnam power market or energy sector"

# Rebuild with clean IDs and improved metadata
final = []
for i, rec in enumerate(sorted(deduped, key=lambda x: (
    0 if "manual" in x.get("discovered_via","") else 1,
    x["signal"]["tier"] if "tier" in x["signal"] else assign_tier(x),
    -x["signal"]["citations"],
    -x["signal"]["year"]
)), 1):
    rec["id"] = f"aca-{i:03d}"
    rec["tier"] = assign_tier(rec)
    if "manual" not in rec.get("discovered_via",""):
        rec["claim"] = make_claim(rec.get("title",""), rec.get("discovered_via",""))
    final.append(rec)

# Write clean file (overwrite)
with open(STAGING, "w", encoding="utf-8") as f:
    for rec in final:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"Wrote {len(final)} rows to staging file")

# Summary
tier_c = {}
for r in final:
    t = r["tier"]
    tier_c[t] = tier_c.get(t, 0) + 1
print(f"\nBy tier: {tier_c}")

tag_c = {}
for r in final:
    tag = "-".join(r.get("discovered_via","").split("-")[:2])
    tag_c[tag] = tag_c.get(tag, 0) + 1
print(f"\nBy sub-question tag:")
for t, c in sorted(tag_c.items()):
    print(f"  {t}: {c}")

print(f"\nAll {len(final)} records:")
for r in final:
    print(f"  [{r['id']}] T{r['tier']} {r['signal']['year']} cites={r['signal']['citations']:4d} OA={str(r['signal']['oa']):<5} | {r['title'][:72]}")
