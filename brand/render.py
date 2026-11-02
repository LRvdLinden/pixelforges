"""Maakt alle PixelForges-banners, social afbeeldingen, logo's en site-iconen.

Gebruik (vanuit de repo-root):
    pip install playwright pillow && python -m playwright install chromium
    python brand/render.py            # alles opnieuw maken
    python brand/render.py --zip      # en ook brand/pixelforges-brand.zip maken

Teksten, pakketten en portfolio komen uit site/content.json, dus na wijzigingen
in beheer kun je de banners opnieuw laten maken.
"""
import asyncio
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "brand"
OUT = BRAND / "export"
SITE = ROOT / "site"
TEMPLATE = (BRAND / "templates" / "banner.html").as_uri()

# (map, bestandsnaam, type, breedte, hoogte, formaat)
FORMATS = [
    ("og", "og-image-1200x630", "og", 1200, 630, "png"),
    ("social", "x-twitter-header-1500x500", "x-header", 1500, 500, "png"),
    ("social", "linkedin-bedrijf-1128x191", "linkedin-banner", 1128, 191, "png"),
    ("social", "linkedin-persoonlijk-1584x396", "linkedin-personal", 1584, 396, "png"),
    ("social", "facebook-omslag-1640x624", "facebook-cover", 1640, 624, "png"),
    ("social", "instagram-post-1080x1080", "instagram-post", 1080, 1080, "png"),
    ("social", "instagram-story-1080x1920", "instagram-story", 1080, 1920, "png"),
    ("social", "instagram-portfolio-1080x1350", "instagram-portfolio", 1080, 1350, "png"),
    ("social", "instagram-prijzen-1080x1350", "instagram-pricing", 1080, 1350, "png"),
    ("social", "profielfoto-lime-1080x1080", "profile-lime", 1080, 1080, "png"),
    ("social", "profielfoto-donker-1080x1080", "profile-dark", 1080, 1080, "png"),
    ("web", "banner-leaderboard-728x90", "web-728x90", 728, 90, "png"),
    ("web", "banner-billboard-970x250", "web-970x250", 970, 250, "png"),
    ("web", "banner-rectangle-300x250", "web-300x250", 300, 250, "png"),
    ("web", "banner-skyscraper-160x600", "web-160x600", 160, 600, "png"),
    ("web", "presentatie-1920x1080", "presentation-1920x1080", 1920, 1080, "png"),
    ("web", "email-handtekening-600x150", "email-signature", 600, 150, "png"),
]
LOGOS = [  # transparante achtergrond, daarna strak bijgesneden
    ("logo", "pixelforges-logo-donkere-achtergrond", "logo-dark", 1400, 400),
    ("logo", "pixelforges-logo-lichte-achtergrond", "logo-light", 1400, 400),
]
MARK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="9" fill="#d0fb65"/><g fill="#0a0a0f"><rect x="8" y="7" width="4" height="18" rx="1"/><rect x="12" y="7" width="8" height="4" rx="1"/><rect x="20" y="11" width="4" height="4" rx="1"/><rect x="12" y="15" width="8" height="4" rx="1"/></g><rect x="20" y="21" width="4" height="4" rx="1" fill="#0a0a0f" opacity=".35"/></svg>"""


async def shoot(page, data, kind, w, h, scale=1, transparent=False):
    await page.set_viewport_size({"width": w, "height": h})
    await page.add_init_script(f"window.DATA = {json.dumps(data, ensure_ascii=False)};")
    url = f"{TEMPLATE}?type={kind}&w={w}&h={h}" + ("&transparent=1" if transparent else "")
    await page.goto(url)
    await page.evaluate("window.__ready")
    await page.wait_for_timeout(150)
    return await page.screenshot(omit_background=transparent, type="png")


def save(png: bytes, path: Path, fmt: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(io.BytesIO(png))
    if fmt == "jpg":
        im.convert("RGB").save(path.with_suffix(".jpg"), "JPEG", quality=90, optimize=True, progressive=True)
    else:
        im.save(path.with_suffix(".png"), "PNG", optimize=True)


async def main(make_zip: bool):
    data = json.loads((SITE / "content.json").read_text(encoding="utf-8"))
    if OUT.exists():
        shutil.rmtree(OUT)
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--allow-file-access-from-files"])
        for folder, name, kind, w, h, fmt in FORMATS:
            ctx = await browser.new_context(device_scale_factor=1)
            page = await ctx.new_page()
            png = await shoot(page, data, kind, w, h)
            save(png, OUT / folder / name, fmt)
            # @2x voor scherpe weergave op retina (behalve de grootste formaten)
            if w * h <= 1600 * 900:
                ctx2 = await browser.new_context(device_scale_factor=2)
                page2 = await ctx2.new_page()
                save(await shoot(page2, data, kind, w, h), OUT / folder / "2x" / f"{name}@2x", fmt)
                await ctx2.close()
            await ctx.close()
            print("✓", folder, name)
        for folder, name, kind, w, h in LOGOS:
            ctx = await browser.new_context(device_scale_factor=1)
            page = await ctx.new_page()
            png = await shoot(page, data, kind, w, h, transparent=True)
            im = Image.open(io.BytesIO(png))
            im = im.crop(im.getbbox())
            (OUT / folder).mkdir(parents=True, exist_ok=True)
            im.save(OUT / folder / f"{name}.png", optimize=True)
            await ctx.close()
            print("✓", folder, name)
        await browser.close()

    # Beeldmerk in verschillende maten + SVG
    mark_dir = OUT / "logo"
    (mark_dir / "pixelforges-beeldmerk.svg").write_text(MARK_SVG, encoding="utf-8")
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1024, "height": 1024})
        await pg.set_content(f'<body style="margin:0;background:transparent">{MARK_SVG.replace("<svg ", "<svg width=1024 height=1024 ")}</body>')
        mark = Image.open(io.BytesIO(await pg.screenshot(omit_background=True)))
        await b.close()
    for s in (1024, 512, 256, 128):
        mark.resize((s, s), Image.LANCZOS).save(mark_dir / f"pixelforges-beeldmerk-{s}.png", optimize=True)

    # Site-iconen (favicon.ico, PWA-iconen, apple-touch-icon) en OG-afbeelding
    shutil.copy(OUT / "og" / "og-image-1200x630.png", SITE / "og.png")
    mark.resize((180, 180), Image.LANCZOS).save(SITE / "apple-touch-icon.png", optimize=True)
    for s in (192, 512):
        mark.resize((s, s), Image.LANCZOS).save(SITE / f"icon-{s}.png", optimize=True)
    maskable = Image.new("RGBA", (512, 512), (208, 251, 101, 255))
    inner = mark.resize((360, 360), Image.LANCZOS)
    maskable.alpha_composite(inner, (76, 76))
    maskable.save(SITE / "icon-maskable-512.png", optimize=True)
    mark.resize((64, 64), Image.LANCZOS).save(SITE / "favicon.png", optimize=True)
    mark.save(SITE / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print("✓ site-iconen en og.png bijgewerkt")

    (OUT / "LEESMIJ.txt").write_text(LEESMIJ, encoding="utf-8")
    if make_zip:
        z = BRAND / "pixelforges-brand.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(OUT.rglob("*")):
                if f.is_file():
                    zf.write(f, f"pixelforges-brand/{f.relative_to(OUT)}")
        print("✓", z.relative_to(ROOT), f"({z.stat().st_size // 1024} KB)")


LEESMIJ = """PixelForges · banners en social afbeeldingen
=============================================

og/        Deelafbeelding voor de website (WhatsApp, LinkedIn, Facebook, iMessage). Staat ook live als pixelforges.nl/og.png.
social/    X-header, LinkedIn (bedrijf en persoonlijk), Facebook-omslag, Instagram post/story/portfolio/prijzen, profielfoto's.
web/       Advertentiebanners (728x90, 970x250, 300x250, 160x600), presentatie 1920x1080, e-mailhandtekening 600x150.
logo/      Logo voor donkere en lichte achtergrond (transparant), beeldmerk als SVG en PNG.
*/2x/      Dubbele resolutie voor scherpe weergave op retina-schermen.

Tips
- X: de profielfoto valt linksonder over de header; daar staat bewust niets belangrijks.
- LinkedIn bedrijfspagina: het logo valt links over de banner; de tekst begint daarom rechts daarvan.
- Facebook: op mobiel vallen de zijkanten weg; de inhoud staat in het midden.
- Instagram story: bovenste en onderste 250 px zijn vrij voor de app-knoppen.
- Profielfoto's worden rond bijgesneden; het beeldmerk staat ruim in het midden.

Opnieuw maken (na wijzigingen in prijzen of portfolio): python brand/render.py --zip
"""

if __name__ == "__main__":
    asyncio.run(main("--zip" in sys.argv))
