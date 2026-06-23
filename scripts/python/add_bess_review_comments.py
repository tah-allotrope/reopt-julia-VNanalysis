"""
Inject PowerPoint review comments into the CEBA BESS session deck.

Targets:
  Slide 1  — overall review summary
  Slide 5  — B1 confirmed correct (Decision 963 peak hours)
  Slide 9  — B2 error (Decree 58 50% vs 20%) + B4 threshold question (Decree 61 3MW vs 30MW)
  Slide 17 — B3 error (capacity charge tier 209,459 vs 235,414 VND/kW/month)

Output: ceba-review/cong bess session [reviewed].pptx
"""

import zipfile, shutil, os, re
from io import BytesIO
from lxml import etree
from pptx import Presentation

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PPTX_IN  = os.path.join(BASE_DIR, "ceba-review", "cong bess session.pptx")
PPTX_OUT = os.path.join(BASE_DIR, "ceba-review", "cong bess session [reviewed].pptx")

# ---------------------------------------------------------------------------
# OOXML namespaces / relationship types
# ---------------------------------------------------------------------------
PPTX_NS       = "http://schemas.openxmlformats.org/presentationml/2006/main"
REL_NS        = "http://schemas.openxmlformats.org/package/2006/relationships"
CM_REL_TYPE   = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
AUTH_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/commentAuthors"
CT_CM         = "application/vnd.openxmlformats-officedocument.presentationml.comments+xml"
CT_AUTH       = "application/vnd.openxmlformats-officedocument.presentationml.commentAuthors+xml"

# ---------------------------------------------------------------------------
# Review comments keyed by 0-based slide index
# Each entry: list of (global_idx, text, x_emu, y_emu)
#   EMU: 1 inch = 914400; slide is typically 12192000 x 6858000 EMU (16:9 widescreen)
# ---------------------------------------------------------------------------
REVIEW_DATE = "2026-06-21T10:00:00.000Z"

COMMENTS = {
    0: [  # Slide 1 — summary banner
        (1,
         "[REVIEW SUMMARY — Tah Allotrope, 2026-06-21]\n"
         "Fact-checked against EVN tier-1 sources, LuatVietnam, Arcus Energy, Norton Rose Fulbright, Vietnam.vn.\n"
         "▶ 2 confirmed errors (Slides 9 and 17)\n"
         "▶ 1 threshold needing your confirmation (Slide 9)\n"
         "▶ 1 confirmed correct (Slide 5 — Decision 963 hours ✓)\n"
         "Please review inline comments and reply with corrections or rationale.",
         1828800, 457200),
    ],
    4: [  # Slide 5 — B1 confirmed
        (2,
         "[✅ B1 — CONFIRMED CORRECT]\n"
         "Decision 963 peak window 17:30–22:30 (Mon–Sat) is verified against Arcus Energy "
         "manufacturing tariff page and the Allotrope repo vn_tariff_2025.json. No action needed.",
         1828800, 457200),
    ],
    8: [  # Slide 9 — B2 and B4
        (3,
         "[❌ B2 — ERROR: Decree 58 export cap stated as 50%]\n"
         "The slide says Decree 58 'raises the ceiling for selling excess rooftop solar up to 50% of actual generation.'\n\n"
         "WHAT THE LAW SAYS:\n"
         "Decree 58/2025/ND-CP (effective March 3, 2025) caps surplus export at 20% of installed capacity.\n"
         "The 50% figure is a MOIT draft amendment proposed January 2026 — still under public consultation, not enacted.\n\n"
         "SOURCES: LuatVietnam (official legal text, tier-1); Viet An Law; Duane Morris (Aug 2025).\n\n"
         "→ ACTION: Please correct to 20%, or explicitly label this as a proposed future change (not current law).",
         1828800, 457200),
        (4,
         "[⚠️ B4 — NEEDS VERIFICATION: Decree 61 BESS threshold stated as 3 MW]\n"
         "The slide states Decree 61 'proposes complete exemption of generation licenses for BESS under 3 MW.'\n\n"
         "PRIMARY SOURCES SHOW:\n"
         "Vietnam.vn official government portal (tier-1) states the Decree 61 exemption for self-use "
         "projects connected to the national grid is <30 MW — not 3 MW.\n\n"
         "POSSIBLE EXPLANATION: The 3 MW may refer to a sub-provision in Circular 62/2025 or an implementing "
         "guideline I could not locate in public sources.\n\n"
         "→ ACTION: Can you cite the specific article/circular where the 3 MW threshold appears? "
         "If it cannot be cited, the figure may need updating to 30 MW.",
         1828800, 2743200),
    ],
    16: [  # Slide 17 — B3
        (5,
         "[❌ B3 — ERROR: Wrong capacity charge tier in Case 3]\n"
         "The slide uses ~209,459 VND/kW/month for the two-part tariff capacity charge.\n\n"
         "WHAT DECREE 146/2025 ACTUALLY SAYS (EVN official, tier-1):\n"
         "  ≥110 kV  →  209,459 VND/kW/month  ← this is what the slide uses\n"
         "  22–<110 kV  →  235,414 VND/kW/month  ← Factory A's actual tier (22kV, per Slide 14)\n"
         "  6–<22 kV  →  240,050 VND/kW/month\n"
         "  <6 kV  →  286,153 VND/kW/month\n\n"
         "IMPACT:\n"
         "Case 3 demand reduction: 2,428 → 1,311 kW (−1,117 kW saved).\n"
         "At the correct rate: savings understated by ~26M VND/month (~$1k/month, ~$12k/year).\n"
         "This affects the Case 3 IRR (12.4%) and NPV — likely improves both slightly.\n\n"
         "SOURCES: EVN official two-component tariff pilot announcement (tier-1); Norton Rose Fulbright (tier-3).\n\n"
         "→ ACTION: Please update Case 3 to 235,414 VND/kW/month and rerun the optimizer. "
         "Confirm Factory A's grid connection voltage is 22kV.",
         1828800, 457200),
    ],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_comment_authors_xml(last_idx: int) -> bytes:
    root = etree.Element(f"{{{PPTX_NS}}}cmAuthorLst")
    a = etree.SubElement(root, f"{{{PPTX_NS}}}cmAuthor")
    a.set("id", "0")
    a.set("name", "Tah Allotrope")
    a.set("initials", "TA")
    a.set("lastIdx", str(last_idx))
    a.set("clrIdx", "0")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def make_slide_comments_xml(entries) -> bytes:
    """entries: list of (idx, text, x, y)"""
    root = etree.Element(f"{{{PPTX_NS}}}cmLst")
    for idx, text, x, y in entries:
        cm = etree.SubElement(root, f"{{{PPTX_NS}}}cm")
        cm.set("authorId", "0")
        cm.set("dt", REVIEW_DATE)
        cm.set("idx", str(idx))
        pos = etree.SubElement(cm, f"{{{PPTX_NS}}}pos")
        pos.set("x", str(x))
        pos.set("y", str(y))
        txt = etree.SubElement(cm, f"{{{PPTX_NS}}}text")
        txt.text = text
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def add_relationship(rels_xml: bytes, rel_id: str, rel_type: str, target: str) -> bytes:
    tree = etree.fromstring(rels_xml)
    rel = etree.SubElement(tree, f"{{{REL_NS}}}Relationship")
    rel.set("Id", rel_id)
    rel.set("Type", rel_type)
    rel.set("Target", target)
    return etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)


def next_rel_id(rels_xml: bytes) -> str:
    tree = etree.fromstring(rels_xml)
    ids = [el.get("Id", "rId0") for el in tree]
    nums = [int(re.search(r'\d+', i).group()) for i in ids if re.search(r'\d+', i)]
    return f"rId{max(nums, default=0) + 1}"


def update_content_types(ct_xml: bytes, new_entries: list) -> bytes:
    """new_entries: list of (part_name, content_type)"""
    tree = etree.fromstring(ct_xml)
    ns = "http://schemas.openxmlformats.org/package/2006/content-types"
    existing = {el.get("PartName") for el in tree if el.get("PartName")}
    for part_name, ct in new_entries:
        if part_name not in existing:
            override = etree.SubElement(tree, f"{{{ns}}}Override")
            override.set("PartName", part_name)
            override.set("ContentType", ct)
    return etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # 1. Get slide part names in presentation order
    prs = Presentation(PPTX_IN)
    slide_partnames = [slide.part.partname for slide in prs.slides]
    print(f"Total slides: {len(slide_partnames)}")
    for i, name in enumerate(slide_partnames):
        mark = " <--" if i in COMMENTS else ""
        print(f"  [{i}] {name}{mark}")

    total_comments = sum(len(v) for v in COMMENTS.values())

    # Build dict of overrides: zip-path -> bytes (new or modified files)
    overrides = {}

    with zipfile.ZipFile(PPTX_IN, "r") as zin:
        existing_names = set(zin.namelist())

        # 2. commentAuthors.xml (new)
        auth_path = "ppt/commentAuthors.xml"
        overrides[auth_path] = make_comment_authors_xml(total_comments)
        print(f"  + Added: {auth_path}")

        # 3. Update presentation .rels
        prs_rels_path = "ppt/_rels/presentation.xml.rels"
        prs_rels_xml  = zin.read(prs_rels_path)
        rel_id = next_rel_id(prs_rels_xml)
        overrides[prs_rels_path] = add_relationship(
            prs_rels_xml, rel_id, AUTH_REL_TYPE, "commentAuthors.xml"
        )
        print(f"  + Updated: {prs_rels_path} (commentAuthors rel {rel_id})")

        # 4. Per-slide comment XMLs + slide .rels
        ct_additions = [("/ppt/commentAuthors.xml", CT_AUTH)]
        for slide_idx, entries in COMMENTS.items():
            if slide_idx >= len(slide_partnames):
                print(f"  ! Slide {slide_idx} out of range, skipping")
                continue

            slide_filename   = slide_partnames[slide_idx].lstrip("/")
            slide_basename   = os.path.basename(slide_filename)
            slide_name_noext = os.path.splitext(slide_basename)[0]

            comment_part   = f"ppt/comments/{slide_name_noext}Comment.xml"
            comment_target = f"../comments/{slide_name_noext}Comment.xml"

            overrides[comment_part] = make_slide_comments_xml(entries)
            ct_additions.append(("/" + comment_part, CT_CM))
            print(f"  + Added: {comment_part} ({len(entries)} comment(s))")

            slide_dir  = os.path.dirname(slide_filename)
            rels_path  = f"{slide_dir}/_rels/{slide_basename}.rels"
            rels_xml   = zin.read(rels_path) if rels_path in existing_names else (
                b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
            )
            rel_id = next_rel_id(rels_xml)
            overrides[rels_path] = add_relationship(rels_xml, rel_id, CM_REL_TYPE, comment_target)
            print(f"  + Updated: {rels_path} (comments rel {rel_id})")

        # 5. [Content_Types].xml
        overrides["[Content_Types].xml"] = update_content_types(
            zin.read("[Content_Types].xml"), ct_additions
        )
        print(f"  + Updated: [Content_Types].xml")

        # 6. Rebuild ZIP without duplicates
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for name in zin.namelist():
                data = overrides.pop(name, None)
                zout.writestr(name, data if data is not None else zin.read(name))
            for name, data in overrides.items():  # new files not in original
                zout.writestr(name, data)
                print(f"  + New entry written: {name}")

    with open(PPTX_OUT, "wb") as f:
        f.write(buf.getvalue())

    print(f"\nDone -> {PPTX_OUT}")


if __name__ == "__main__":
    main()
