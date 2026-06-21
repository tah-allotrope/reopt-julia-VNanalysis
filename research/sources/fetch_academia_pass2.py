"""
Academia wide-pass (pass 2): queries 3-7 on remaining sub-questions.
Reads existing JSONL to avoid duplicates, then appends new ones.
"""
import urllib.request
import urllib.parse
import json
import time

STAGING = r"C:\Users\tukum\Downloads\reopt-pysam\research\sources\2026-06-20_vn-power-market-2026-2_academia.jsonl"

QUERIES = [
    ("Vietnam direct power purchase agreement DPPA corporate renewable energy",
     "q3-DPPA"),
    ("Vietnam battery energy storage BESS economic analysis tariff grid stability",
     "q4-BESS"),
    ("Vietnam time-of-use tariff industrial electricity price reform demand response",
     "q5-TOU-tariff"),
    ("Vietnam electricity price forecasting EVN tariff escalation cost",
     "q6-price-forecast"),
    ("Vietnam solar photovoltaic policy rooftop net metering self-consumption",
     "q7-solar-PV-policy"),
]

def load_existing_keys(path):
    keys = set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                keys.add(rec.get("url","")[:100])
                keys.add(rec.get("title","")[:80])
    except FileNotFoundError:
        pass
    return keys

def count_existing(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for l in f if l.strip())
    except:
        return 0

def fetch_openalex(query, query_tag, seen_keys):
    candidates = []
    enc = urllib.parse.quote(query)
    url = (f"https://api.openalex.org/works?search={enc}"
           f"&per-page=50&filter=publication_year:2019-2026"
           f"&mailto=tah@allotropevc.com")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VN-Power-Research/1.0 tah@allotropevc.com"})
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.load(resp)
        results = data.get("results", [])
        print(f"  OpenAlex [{query_tag}]: {len(results)} raw results")

        for r in results:
            doi = r.get("doi", "") or ""
            title = (r.get("title") or "").strip()
            year = r.get("publication_year", 0) or 0
            cites = r.get("cited_by_count", 0) or 0
            oa = r.get("open_access", {}).get("is_oa", False)
            venue = ""
            if r.get("primary_location") and r["primary_location"].get("source"):
                venue = r["primary_location"]["source"].get("display_name", "") or ""

            if doi and doi.startswith("http"):
                item_url = doi
            elif doi:
                item_url = f"https://doi.org/{doi}"
            else:
                item_url = r.get("id", "")

            # Dedup checks
            url_key = item_url[:100]
            title_key = title[:80]
            if url_key in seen_keys or title_key in seen_keys or not title:
                continue

            combined = title.lower()
            # Must be somewhat relevant to energy/power/Vietnam topic
            if not any(kw in combined for kw in [
                "vietnam", "viet nam", "southeast asia", "asean",
                "energy", "power", "electric", "solar", "wind",
                "renewable", "grid", "tariff", "battery", "storage",
                "photovoltaic", "demand response", "dppa", "ppa",
                "carbon", "emission", "transition", "hydrogen"
            ]):
                continue

            seen_keys.add(url_key)
            seen_keys.add(title_key)

            if cites >= 50:
                tier = 2
            elif cites >= 10 or year >= 2022:
                tier = 3
            elif year >= 2019:
                tier = 4
            else:
                tier = 5

            rec = {
                "id": "PENDING",
                "bucket": "academia",
                "url": item_url,
                "title": title,
                "tier": tier,
                "status": "candidate",
                "pass": "wide",
                "discovered_via": query_tag,
                "signal": {"year": year, "citations": cites, "oa": bool(oa)},
                "claim": f"Academic source on: {query[:80]}",
                "note": f"{venue}; {'OA' if oa else 'closed'}"
            }
            candidates.append(rec)
    except Exception as e:
        print(f"  OpenAlex [{query_tag}] ERROR: {e}")
    return candidates

def fetch_s2(query, query_tag, seen_keys):
    candidates = []
    enc = urllib.parse.quote(query)
    url = (f"https://api.semanticscholar.org/graph/v1/paper/search"
           f"?query={enc}&limit=50"
           f"&fields=title,abstract,year,citationCount,openAccessPdf,url,externalIds,venue")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VN-Power-Research/1.0 tah@allotropevc.com"})
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.load(resp)
        results = data.get("data", [])
        print(f"  S2 [{query_tag}]: {len(results)} raw results")

        for r in results:
            title = (r.get("title") or "").strip()
            year = r.get("year") or 0
            cites = r.get("citationCount") or 0
            oa_pdf = r.get("openAccessPdf") or {}
            oa = bool(oa_pdf.get("url"))
            oa_url = oa_pdf.get("url", "")
            venue = r.get("venue") or ""
            ext = r.get("externalIds") or {}
            doi = ext.get("DOI", "") or ""
            paper_url = oa_url or r.get("url") or (f"https://doi.org/{doi}" if doi else "")

            url_key = paper_url[:100]
            title_key = title[:80]
            if url_key in seen_keys or title_key in seen_keys or not title:
                continue

            combined = title.lower() + " " + (r.get("abstract") or "").lower()
            if not any(kw in combined for kw in [
                "vietnam", "viet nam", "southeast asia", "asean",
                "energy", "power", "electric", "solar", "wind",
                "renewable", "grid", "tariff", "battery", "storage",
                "photovoltaic", "dppa", "ppa", "carbon", "emission",
                "transition", "hydrogen", "demand response"
            ]):
                continue

            seen_keys.add(url_key)
            seen_keys.add(title_key)

            if cites >= 50:
                tier = 2
            elif cites >= 10 or year >= 2022:
                tier = 3
            elif year >= 2019:
                tier = 4
            else:
                tier = 5

            rec = {
                "id": "PENDING",
                "bucket": "academia",
                "url": paper_url,
                "title": title,
                "tier": tier,
                "status": "candidate",
                "pass": "wide",
                "discovered_via": query_tag,
                "signal": {"year": year, "citations": cites, "oa": oa},
                "claim": f"Academic source on: {query[:80]}",
                "note": f"{venue}; {'OA' if oa else 'closed'}"
            }
            candidates.append(rec)
        time.sleep(1.2)
    except Exception as e:
        print(f"  S2 [{query_tag}] ERROR: {e}")
    return candidates

def main():
    # Load existing keys to avoid duplicates
    seen_keys = load_existing_keys(STAGING)
    existing_count = count_existing(STAGING)
    print(f"Existing records: {existing_count}")
    print(f"Existing dedup keys: {len(seen_keys)}")

    new_candidates = []

    for i, (query, tag) in enumerate(QUERIES):
        print(f"\nQuery {i+1}/{len(QUERIES)}: [{tag}]")
        prev = len(new_candidates)

        oa_res = fetch_openalex(query, f"{tag}-oa", seen_keys)
        new_candidates.extend(oa_res)
        time.sleep(0.4)

        s2_res = fetch_s2(query, f"{tag}-s2", seen_keys)
        new_candidates.extend(s2_res)

        added = len(new_candidates) - prev
        novelty = added / max(prev + existing_count, 1) * 100
        print(f"  Added {added} new (novelty {novelty:.1f}%). Running total new: {len(new_candidates)}")

        if len(new_candidates) + existing_count >= 80:
            print("Reached 80 total, stopping early")
            break

    # Assign IDs and append
    next_id = existing_count + 1
    print(f"\nAppending {len(new_candidates)} new candidates (starting at aca-{next_id:03d})...")
    with open(STAGING, "a", encoding="utf-8") as f:
        for rec in new_candidates:
            rec["id"] = f"aca-{next_id:03d}"
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            next_id += 1

    total = count_existing(STAGING)
    print(f"\nDONE. Total rows in file: {total}")

    # Print top by tier
    top = sorted(new_candidates, key=lambda x: (x["tier"], -x["signal"]["citations"]))[:8]
    print("\nTop new candidates:")
    for r in top:
        print(f"  T{r['tier']} {r['signal']['year']} cites={r['signal']['citations']:4d} | {r['title'][:75]}")

if __name__ == "__main__":
    main()
