"""Extract slide text from both CEBA review PPTX files."""
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
REPO = Path(__file__).resolve().parents[2]


def extract_pptx_text(path: Path) -> str:
    slides = []
    with zipfile.ZipFile(path) as z:
        names = sorted(
            [n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml", n)],
            key=lambda x: int(re.search(r"\d+", x.split("/")[-1]).group()),
        )
        for i, sn in enumerate(names, 1):
            root = ET.fromstring(z.read(sn))
            texts = [t.text.strip() for t in root.iter(f"{{{NS}}}t") if t.text and t.text.strip()]
            if texts:
                slides.append(f"[Slide {i}]\n" + "\n".join(texts))
    return "\n\n".join(slides)


for pptx_name in ["cong bess session.pptx", "cong_session_6.2_DPPA.pptx"]:
    p = REPO / "ceba-review" / pptx_name
    text = extract_pptx_text(p)
    out = REPO / "ceba-review" / (p.stem + "_text.txt")
    out.write_text(text, encoding="utf-8")
    print(f"Written {out}  ({len(text):,} chars, {text.count('[Slide')} slides)")
