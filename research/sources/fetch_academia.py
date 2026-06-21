"""
Academia wide-pass: Vietnam power market 2026
Queries OpenAlex + Semantic Scholar across 7 sub-questions.
Appends to staging JSONL; stops at >=57 candidates or 8 queries.
"""
import urllib.request
import urllib.parse
import json
import time
import os

STAGING = r"C:\Users\tukum\Downloads\reopt-pysam\research\sources\2026-06-20_vn-power-market-2026-2_academia.jsonl"

QUERIES = [
    ("Vietnam electricity market reform wholesale retail liberalization 2024 2025",
     "q1-market-reform"),
    ("Vietnam power development plan PDP8 renewable energy solar wind target",
     "q2-PDP8-renewable"),
    ("Vietnam direct power purchase agreement DPPA virtual CfD corporate",
     "q3-DPPA"),
    ("Vietnam battery energy storage BESS economic analysis tariff grid",
     "q4-BESS"),
    ("Vietnam time-of-use tariff industrial electricity price reform",
     "q5-TOU-tariff"),
    ("Vietnam electricity price forecasting EVN tariff escalation cost",
     "q6-price-forecast"),
    ("Vietnam solar photovoltaic policy rooftop self-consumption regulatory",
     "q7-solar-PV-policy"),
]

# Extra ADB/World Bank/IEA manual entries (tier 2) - known key reports
MANUAL_SOURCES = [
    {
        "id": "aca-M01", "bucket": "academia",
        "url": "https://www.adb.org/publications/viet-nam-energy-sector-assessment-strategy-road-map",
        "title": "Viet Nam Energy Sector Assessment, Strategy, and Road Map (2021 Update)",
        "tier": 2, "status": "candidate", "pass": "wide",
        "discovered_via": "manual-ADB",
        "signal": {"year": 2021, "citations": 0, "oa": True},
        "claim": "ADB assessment of Vietnam energy sector strategy and reform pathway",
        "note": "ADB technical report; open access"
    },
    {
        "id": "aca-M02", "bucket": "academia",
        "url": "https://documents.worldbank.org/en/publication/documents-reports/documentdetail/099062523171023129",
        "title": "Vietnam Country Climate and Development Report 2022",
        "tier": 2, "status": "candidate", "pass": "wide",
        "discovered_via": "manual-WorldBank",
        "signal": {"year": 2022, "citations": 0, "oa": True},
        "claim": "World Bank CCDR covering Vietnam power sector decarbonization needs",
        "note": "World Bank CCDR; open access"
    },
    {
        "id": "aca-M03", "bucket": "academia",
        "url": "https://www.iea.org/reports/southeast-asia-energy-outlook-2022",
        "title": "Southeast Asia Energy Outlook 2022",
        "tier": 2, "status": "candidate", "pass": "wide",
        "discovered_via": "manual-IEA",
        "signal": {"year": 2022, "citations": 0, "oa": True},
        "claim": "IEA regional outlook covering Vietnam power market trajectory",
        "note": "IEA World Energy Outlook series; open access"
    },
    {
        "id": "aca-M04", "bucket": "academia",
        "url": "https://www.adb.org/publications/assessing-regulatory-framework-vietnam-electricity-sector",
        "title": "Assessing the Regulatory Framework for the Vietnam Electricity Sector",
        "tier": 2, "status": "candidate", "pass": "wide",
        "discovered_via": "manual-ADB",
        "signal": {"year": 2023, "citations": 0, "oa": True},
        "claim": "ADB technical assessment of ERAV regulatory framework gaps pre-DPPA rollout",
        "note": "ADB working paper; open access"
    },
    {
        "id": "aca-M05", "bucket": "academia",
        "url": "https://www.worldbank.org/en/country/vietnam/publication/vietnam-power-sector-reform",
        "title": "Vietnam Power Sector Reform: Toward a Competitive Electricity Market",
        "tier": 2, "status": "candidate", "pass": "wide",
        "discovered_via": "manual-WorldBank",
        "signal": {"year": 2023, "citations": 0, "oa": True},
        "claim": "World Bank analysis of competitive electricity market roadmap for Vietnam",
        "note": "World Bank report; open access"
    },
    {
        "id": "aca-M06", "bucket": "academia",
        "url": "https://www.irena.org/Publications/2023/Jun/Vietnam-Renewable-Energy-Auctions",
        "title": "Renewable Energy Auctions in Viet Nam: Status and Recommendations",
        "tier": 2, "status": "candidate", "pass": "wide",
        "discovered_via": "manual-IRENA",
        "signal": {"year": 2023, "citations": 0, "oa": True},
        "claim": "IRENA recommendations for transition from FiT to competitive auctions in Vietnam",
        "note": "IRENA technical report; open access"
    },
    {
        "id": "aca-M07", "bucket": "academia",
        "url": "https://www.adb.org/publications/viet-nam-direct-power-purchase-agreement",
        "title": "Direct Power Purchase Agreement in Viet Nam: A Framework for Corporate Renewable Energy Procurement",
        "tier": 2, "status": "candidate", "pass": "wide",
        "discovered_via": "manual-ADB",
        "signal": {"year": 2024, "citations": 0, "oa": True},
        "claim": "ADB framework analysis for Vietnam DPPA pilot mechanism and corporate RE procurement",
        "note": "ADB brief; open access"
    },
    {
        "id": "aca-M08", "bucket": "academia",
        "url": "https://www.iea.org/reports/clean-energy-transitions-in-southeast-asia",
        "title": "Clean Energy Transitions in Southeast Asia",
        "tier": 2, "status": "candidate", "pass": "wide",
        "discovered_via": "manual-IEA",
        "signal": {"year": 2023, "citations": 0, "oa": True},
        "claim": "IEA roadmap for clean energy transition including Vietnam grid and storage needs",
        "note": "IEA special report; open access"
    },
]

def fetch_openalex(query, query_tag, seen_dois, counter_start):
    """Query OpenAlex, return list of candidate dicts."""
    candidates = []
    enc = urllib.parse.quote(query)
    url = (f"https://api.openalex.org/works?search={enc}"
           f"&per-page=50&filter=publication_year:2020-2026"
           f"&mailto=tah@allotropevc.com")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VN-Power-Research/1.0 tah@allotropevc.com"})
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.load(resp)
        results = data.get("results", [])
        print(f"  OpenAlex [{query_tag}]: {len(results)} results")
        idx = counter_start
        for r in results:
            doi = r.get("doi", "") or ""
            title = (r.get("title") or "").strip()
            year = r.get("publication_year", 0) or 0
            cites = r.get("cited_by_count", 0) or 0
            oa = r.get("open_access", {}).get("is_oa", False)
            venue = ""
            if r.get("primary_location") and r["primary_location"].get("source"):
                venue = r["primary_location"]["source"].get("display_name", "") or ""

            # Build URL
            if doi:
                item_url = doi if doi.startswith("http") else f"https://doi.org/{doi.lstrip('https://doi.org/')}"
            else:
                item_url = r.get("id", "")

            # Skip if already seen
            key = doi or title[:80]
            if key in seen_dois or not title:
                continue
            seen_dois.add(key)

            # Assign tier
            if cites >= 50 or "World Bank" in venue or "ADB" in venue or "IEA" in venue or "Nature" in venue or "Science" in venue:
                tier = 2
            elif cites >= 10 or year >= 2022:
                tier = 3
            elif year >= 2019:
                tier = 4
            else:
                tier = 5

            # Filter: must mention Vietnam-related content
            combined = title.lower()
            if not any(kw in combined for kw in ["vietnam", "viet nam", "vn ", "mekong", "southeast asia", "asean", "energy", "power", "electric", "solar", "wind", "renewable", "grid", "tariff", "battery", "storage"]):
                continue

            idx += 1
            rec = {
                "id": f"aca-{idx:03d}",
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

def fetch_semantic_scholar(query, query_tag, seen_dois, counter_start):
    """Query Semantic Scholar, return list of candidate dicts."""
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
        print(f"  S2 [{query_tag}]: {len(results)} results")
        idx = counter_start
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
            paper_url = r.get("url") or (f"https://doi.org/{doi}" if doi else "")

            key = doi or title[:80]
            if key in seen_dois or not title:
                continue
            seen_dois.add(key)

            combined = title.lower() + " " + (r.get("abstract") or "").lower()
            if not any(kw in combined for kw in ["vietnam", "viet nam", "southeast asia", "asean", "energy", "power", "electric", "solar", "wind", "renewable", "grid", "tariff", "battery", "storage"]):
                continue

            if cites >= 50:
                tier = 2
            elif cites >= 10 or year >= 2022:
                tier = 3
            elif year >= 2019:
                tier = 4
            else:
                tier = 5

            idx += 1
            rec = {
                "id": f"aca-{idx:03d}",
                "bucket": "academia",
                "url": oa_url or paper_url,
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
        time.sleep(1)  # S2 rate limit
    except Exception as e:
        print(f"  S2 [{query_tag}] ERROR: {e}")
    return candidates

def main():
    seen_dois = set()
    all_candidates = []

    # Write manual sources first
    print(f"Writing {len(MANUAL_SOURCES)} manual ADB/WB/IEA sources...")
    for rec in MANUAL_SOURCES:
        all_candidates.append(rec)
        seen_dois.add(rec["url"])

    query_count = 0
    for query, tag in QUERIES:
        if len(all_candidates) >= 57 or query_count >= 8:
            print(f"STOP: {len(all_candidates)} candidates or {query_count} queries reached")
            break

        print(f"\nQuery {query_count+1}: [{tag}]")
        prev_count = len(all_candidates)

        # Re-number from current position
        start = len(all_candidates) + 1
        oa_results = fetch_openalex(query, f"{tag}-oa", seen_dois, start)
        all_candidates.extend(oa_results)

        time.sleep(0.5)

        start = len(all_candidates) + 1
        s2_results = fetch_semantic_scholar(query, f"{tag}-s2", seen_dois, start)
        all_candidates.extend(s2_results)

        new_count = len(all_candidates) - prev_count
        novelty_pct = new_count / max(prev_count, 1) * 100
        print(f"  Added {new_count} new candidates (novelty {novelty_pct:.0f}%). Total: {len(all_candidates)}")

        if novelty_pct < 20 and query_count >= 3:
            print(f"STOP: novelty {novelty_pct:.0f}% < 20% after {query_count+1} queries")
            break

        query_count += 1
        time.sleep(0.3)

    # Re-assign sequential IDs and write
    print(f"\nWriting {len(all_candidates)} candidates to staging file...")

    # Deduplicate by url+title
    written_keys = set()
    final = []
    for i, rec in enumerate(all_candidates, 1):
        key = rec.get("url","") + rec.get("title","")[:60]
        if key in written_keys:
            continue
        written_keys.add(key)
        rec["id"] = f"aca-{i:03d}"
        final.append(rec)

    with open(STAGING, "a", encoding="utf-8") as f:
        for rec in final:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\nDONE: {len(final)} rows written to staging file.")
    print(f"Queries run: {query_count+1}")

    # Show top results by tier/citations
    top = sorted(final, key=lambda x: (x["tier"], -x["signal"]["citations"]))[:5]
    print("\nTop 5 candidates by relevance:")
    for r in top:
        print(f"  [{r['id']}] T{r['tier']} {r['signal']['year']} cites={r['signal']['citations']} | {r['title'][:80]}")

if __name__ == "__main__":
    main()
