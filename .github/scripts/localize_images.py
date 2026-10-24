"""Kopieert afbeeldingen met een https-adres in site/content.json naar site/img als WebP.

Zo blijft de site werken als de externe bron (bijv. Base44) verdwijnt.
Schrijft content.json alleen terug als er iets veranderd is en meldt dat via GITHUB_OUTPUT.
"""
import io
import json
import os
import re
import sys
import urllib.request

from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "site")
CONTENT = os.path.join(ROOT, "content.json")
FIELDS = {"projects": ("image", 1200), "reviews": ("photo", 320)}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "img"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "pixelforges-site-build"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read(15 * 1024 * 1024)


def main() -> int:
    with open(CONTENT, encoding="utf-8") as f:
        data = json.load(f)
    changed = 0
    for section, (key, max_side) in FIELDS.items():
        for item in data.get(section, []):
            url = item.get(key) or ""
            if not url.startswith(("http://", "https://")):
                continue
            name = f"img/{slug(item.get('id') or item.get('name', ''))}.webp"
            try:
                im = Image.open(io.BytesIO(fetch(url)))
                im = im.convert("RGBA") if im.mode in ("P", "LA", "RGBA") else im.convert("RGB")
                im.thumbnail((max_side, max_side), Image.LANCZOS)
                im.save(os.path.join(ROOT, name), "WEBP", quality=82, method=6)
            except Exception as e:  # externe bron onbereikbaar: link laten staan
                print(f"::warning::Kon {url} niet ophalen voor {item.get('name')}: {e}")
                continue
            item[key] = name
            changed += 1
            print(f"{item.get('name')}: {url[:60]}… -> {name}")
    if changed:
        with open(CONTENT, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            f.write("\n")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"changed={changed}\n")
    print(f"{changed} afbeelding(en) lokaal gemaakt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
