"""
Academia pass 3: remaining queries 4-7 (BESS, TOU, price forecast, solar PV).
Only adds items not already in file. Target total >= 57 already met, but
we want thematic coverage of all 7 sub-questions.
"""
import urllib.request
import urllib.parse
import json
import time

STAGING = r"C:\Users\tukum\Downloads\reopt-pysam\research\sources\2026-06-20_vn-power-market-2026-2_academia.jsonl"

QUERIES = [
    ("Vietnam battery energy storage BESS grid integration economic dispatch",
     "q4-BESS"),
    ("Vietnam time-of-use electricity tariff demand response industrial",
     "q5-TOU"),
    ("Vietnam EVN electricity tariff escalation cost structure price projection",
     "q6-tariff-cost"),
    ("Vietnam rooftop solar photovoltaic net metering policy regulatory 2023 2024 2025",
     "q7-solar-rooftop"),
    ("Vietnam offshore wind power development cost LCOE investment 2024",
     "q8-offshore-wind"),
]

def load_existing_keys(path):
    keys = set()
    titles = set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    url = rec.get("url","")
                    if url:
                        keys.add(url[:120])
                    t = rec.get("title","")
                    if t:
                        titles.add(t[:80].lower())
                except:
                    pass
    except FileNotFoundError:
        pass
    return keys, titles

def count_existing(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for l in f if l.strip())
    except:
        return 0

def fetch_openalex(query, query_tag, seen_urls, seen_titles):
    candidates = []
    enc = urllib.parse.quote(query)
    url = (f"https://api.openalex.org/works?search={enc}"
           f"&per-page=50&filter=publication_year:2018-2026"
           f"&mailto=tah@allotropevc.com")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VN-Power-Research/1.0 tah@allotropevc.com"})
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.load(resp)
        results = data.get("results", [])
        print(f"  OA [{query_tag}]: {len(results)} raw")

        for r in results:
            doi = r.get("doi", "") or ""
            title = (r.get("title") or "").strip()
            if not title:
                continue
            title_key = title[:80].lower()

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

            url_key = item_url[:120]

            if url_key in seen_urls or title_key in seen_titles:
                continue

            combined = title.lower()
            relevant_kws = [
                "vietnam", "viet nam", "southeast asia", "asean",
                "energy", "power", "electric", "solar", "wind",
                "renewable", "grid", "tariff", "battery", "storage",
                "photovoltaic", "pv", "bess", "dppa", "ppa",
                "carbon", "emission", "transition", "hydrogen",
                "demand response", "time-of-use", "offshore", "lcoe"
            ]
            if not any(kw in combined for kw in relevant_kws):
                continue

            seen_urls.add(url_key)
            seen_titles.add(title_key)

            if cites >= 50:
                tier = 2
            elif cites >= 10 or year >= 2022:
                tier = 3
            elif year >= 2018:
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
        print(f"  OA [{query_tag}] ERROR: {e}")
    return candidates

def fetch_s2_with_retry(query, query_tag, seen_urls, seen_titles):
    candidates = []
    enc = urllib.parse.quote(query)
    url = (f"https://api.semanticscholar.org/graph/v1/paper/search"
           f"?query={enc}&limit=50"
           f"&fields=title,abstract,year,citationCount,openAccessPdf,url,externalIds,venue")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "VN-Power-Research/1.0 tah@allotropevc.com"})
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.load(resp)
            results = data.get("data", [])
            print(f"  S2 [{query_tag}]: {len(results)} raw")

            for r in results:
                title = (r.get("title") or "").strip()
                if not title:
                    continue
                title_key = title[:80].lower()
                year = r.get("year") or 0
                cites = r.get("citationCount") or 0
                oa_pdf = r.get("openAccessPdf") or {}
                oa = bool(oa_pdf.get("url"))
                oa_url = oa_pdf.get("url", "")
                venue = r.get("venue") or ""
                ext = r.get("externalIds") or {}
                doi = ext.get("DOI", "") or ""
                paper_url = oa_url or r.get("url") or (f"https://doi.org/{doi}" if doi else "")
                url_key = paper_url[:120]

                if url_key in seen_urls or title_key in seen_titles:
                    continue

                combined = title.lower() + " " + (r.get("abstract") or "").lower()
                relevant_kws = [
                    "vietnam", "viet nam", "southeast asia", "asean",
                    "energy", "power", "electric", "solar", "wind",
                    "renewable", "grid", "tariff", "battery", "storage",
                    "photovoltaic", "pv", "bess", "dppa", "ppa",
                    "carbon", "emission", "transition", "hydrogen",
                    "demand response", "time-of-use", "offshore", "lcoe"
                ]
                if not any(kw in combined for kw in relevant_kws):
                    continue

                seen_urls.add(url_key)
                seen_titles.add(title_key)

                if cites >= 50:
                    tier = 2
                elif cites >= 10 or year >= 2022:
                    tier = 3
                elif year >= 2018:
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
            time.sleep(1.5)
            break
        except Exception as e:
            print(f"  S2 [{query_tag}] attempt {attempt+1} ERROR: {e}")
            time.sleep(3)
    return candidates

def main():
    seen_urls, seen_titles = load_existing_keys(STAGING)
    existing_count = count_existing(STAGING)
    print(f"Existing: {existing_count} rows, {len(seen_urls)} URL keys, {len(seen_titles)} title keys")

    new_candidates = []

    for i, (query, tag) in enumerate(QUERIES):
        print(f"\nQuery {i+1}/{len(QUERIES)}: [{tag}]")
        prev = len(new_candidates)

        oa_res = fetch_openalex(query, tag+"-oa", seen_urls, seen_titles)
        new_candidates.extend(oa_res)
        time.sleep(0.5)

        s2_res = fetch_s2_with_retry(query, tag+"-s2", seen_urls, seen_titles)
        new_candidates.extend(s2_res)

        added = len(new_candidates) - prev
        print(f"  -> Added {added} new. Running total new: {len(new_candidates)}")

    # Append with sequential IDs
    next_id = existing_count + 1
    print(f"\nAppending {len(new_candidates)} new candidates...")
    with open(STAGING, "a", encoding="utf-8") as f:
        for rec in new_candidates:
            rec["id"] = f"aca-{next_id:03d}"
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            next_id += 1

    total = count_existing(STAGING)
    print(f"\nFINAL total rows in staging file: {total}")

    # Summary by query tag
    tag_counts = {}
    for r in new_candidates:
        tag = r["discovered_via"].rsplit("-", 1)[0]
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
    print("New candidates by sub-question:")
    for t, c in sorted(tag_counts.items()):
        print(f"  {t}: {c}")

    # Top by tier/citations
    top = sorted(new_candidates, key=lambda x: (x["tier"], -x["signal"]["citations"]))[:10]
    print("\nTop 10 new candidates by tier/citations:")
    for r in top:
        print(f"  T{r['tier']} {r['signal']['year']} cites={r['signal']['citations']:4d} | {r['title'][:75]}")

if __name__ == "__main__":
    main()
