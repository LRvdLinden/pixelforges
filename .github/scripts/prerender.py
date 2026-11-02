"""Zet de inhoud van content.json vooraf in build/index.html en maakt sitemap.xml en robots.txt.

Waarom: de site laadt teksten met JavaScript. Zoekmachines en deelvoorbeelden (WhatsApp,
LinkedIn) zien zo direct de pakketten, het portfolio en de vragen. De pagina wordt in een
headless browser gerenderd en de gevulde blokken worden letterlijk teruggezet, zodat de
opmaak gelijk is aan wat bezoekers zien. In de browser vult JavaScript ze daarna gewoon opnieuw.

Gebruik: python .github/scripts/prerender.py build https://pixelforges.nl
"""
import asyncio
import datetime as dt
import functools
import html
import http.server
import json
import re
import socketserver
import sys
import threading
from pathlib import Path

from playwright.async_api import async_playwright

BUILD = Path(sys.argv[1] if len(sys.argv) > 1 else "build").resolve()
SITE_URL = (sys.argv[2] if len(sys.argv) > 2 else "https://pixelforges.nl").rstrip("/")
BLOCKS = ["marquee", "steps", "pricing", "pkgPick", "filters", "projects", "stats", "review",
          "aboutText", "values", "faqList", "cList", "footContact", "socials", "footLegal"]


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=str(BUILD))
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


async def snapshot(port):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
        await pg.route(re.compile(r"^https://(fonts|cdn)"), lambda r: r.abort())
        await pg.goto(f"http://127.0.0.1:{port}/index.html", wait_until="domcontentloaded")
        await pg.wait_for_function("document.querySelectorAll('#pricing .plan').length > 0", timeout=15000)
        await pg.wait_for_timeout(300)
        data = await pg.evaluate("""(ids) => {
          const out = { blocks: {}, texts: {}, more: null };
          for (const id of ids) { const el = document.getElementById(id); if (el) out.blocks[id] = el.innerHTML; }
          document.querySelectorAll('[data-c]').forEach(el => out.texts[el.dataset.c] = el.textContent);
          const m = document.getElementById('moreWrap'); out.more = m && m.getAttribute('style');
          out.moreText = document.getElementById('moreBtn')?.textContent;
          out.count = document.querySelector('[data-count="projects"]')?.textContent;
          return out;
        }""", BLOCKS)
        await b.close()
        return data


def inject(src: str, data: dict, C: dict) -> str:
    # Lege blokken vullen
    for bid, inner in data["blocks"].items():
        pat = re.compile(r'(<(\w+)\b[^>]*\bid="' + re.escape(bid) + r'"[^>]*>)(.*?)(</\2>)', re.S)
        m = pat.search(src)
        if not m:
            print(f"::warning::Blok #{bid} niet gevonden")
            continue
        if m.group(3).strip():  # al gevuld in de bron: laten staan
            continue
        src = src[:m.start()] + m.group(1) + inner + m.group(4) + src[m.end():]
    # Teksten met data-c (alleen eenvoudige tekst-elementen)
    for key, text in data["texts"].items():
        src = re.sub(r'(data-c="' + re.escape(key) + r'"[^>]*>)[^<]*(<)', lambda m: m.group(1) + html.escape(text, quote=False) + m.group(2), src)
    if data.get("count"):
        src = re.sub(r'(data-count="projects">)[^<]*(<)', lambda m: m.group(1) + data["count"] + m.group(2), src)
    if data.get("moreText"):
        src = re.sub(r'(id="moreBtn">)[^<]*(<)', lambda m: m.group(1) + html.escape(data["moreText"]) + m.group(2), src)

    # Structured data: organisatie, aanbod, portfolio en veelgestelde vragen
    S = C.get("settings", {})
    same = [S[k] for k in ("facebook", "instagram", "linkedin") if S.get(k)]
    offers = []
    for p in C.get("packages", []):
        price = re.sub(r"[^\d,]", "", p.get("price", "")).replace(",", ".")
        try:
            price = f"{float(price):.2f}"
        except ValueError:
            continue
        spec = {"@type": "UnitPriceSpecification", "price": price, "priceCurrency": "EUR", "valueAddedTaxIncluded": False}
        if "maand" in p.get("suffix", ""):
            spec.update({"unitCode": "MON", "unitText": "maand"})
        offers.append({"@type": "Offer", "name": p.get("name"), "description": p.get("description"),
                       "priceSpecification": spec, "url": f"{SITE_URL}/#aanbod",
                       "itemOffered": {"@type": "Service", "name": p.get("name"), "serviceType": "Webdesign"}})
    org = {"@type": "Organization", "@id": f"{SITE_URL}/#org", "name": "PixelForges", "url": f"{SITE_URL}/",
           "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/icon-512.png", "width": 512, "height": 512},
           "email": S.get("email") or "hallo@pixelforges.nl", "sameAs": same}
    if S.get("phone"):
        org["telephone"] = S["phone"]
    if S.get("kvk"):
        org["identifier"] = {"@type": "PropertyValue", "propertyID": "KvK", "value": S["kvk"]}
    service = {"@type": "ProfessionalService", "@id": f"{SITE_URL}/#service", "name": "PixelForges", "url": f"{SITE_URL}/",
               "image": f"{SITE_URL}/og.png", "logo": f"{SITE_URL}/icon-512.png", "email": org["email"],
               "description": C.get("hero", {}).get("text", "Professionele websites voor MKB en ZZP."),
               "priceRange": "€€", "areaServed": {"@type": "Country", "name": "Nederland"},
               "address": {"@type": "PostalAddress", "addressLocality": S.get("city") or "Apeldoorn", "addressCountry": "NL"},
               "knowsAbout": ["Webdesign", "Website laten maken", "SEO", "Responsive design", "Websitebeheer"],
               "parentOrganization": {"@id": f"{SITE_URL}/#org"},
               "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Websitepakketten", "itemListElement": offers}}
    if S.get("phone"):
        service["telephone"] = S["phone"]
    projects = [p for p in C.get("projects", []) if p.get("url")]
    portfolio = {"@type": "ItemList", "@id": f"{SITE_URL}/#portfolio", "name": "Portfolio PixelForges",
                 "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": {
                     "@type": "WebSite", "name": p["name"], "url": p["url"], "description": p.get("description", ""),
                     **({"image": f"{SITE_URL}/{p['image']}"} if p.get("image", "").startswith("img/") else {})}}
                     for i, p in enumerate(projects)]}
    graph = {"@context": "https://schema.org", "@graph": [
        org,
        {"@type": "WebSite", "@id": f"{SITE_URL}/#website", "url": f"{SITE_URL}/", "name": "PixelForges", "inLanguage": "nl-NL", "publisher": {"@id": f"{SITE_URL}/#org"}},
        {"@type": "WebPage", "@id": f"{SITE_URL}/#webpage", "url": f"{SITE_URL}/", "name": "Website laten maken vanaf €750 · PixelForges Apeldoorn",
         "isPartOf": {"@id": f"{SITE_URL}/#website"}, "about": {"@id": f"{SITE_URL}/#service"}, "inLanguage": "nl-NL",
         "primaryImageOfPage": {"@type": "ImageObject", "url": f"{SITE_URL}/og.png", "width": 1200, "height": 630},
         "dateModified": dt.date.today().isoformat()},
        service, portfolio]}
    ld = json.dumps(graph, ensure_ascii=False).replace("</", "<\\/")
    src = re.sub(r'<script type="application/ld\+json" id="ld-site">.*?</script>',
                 lambda m: f'<script type="application/ld+json" id="ld-site">{ld}</script>', src, flags=re.S)
    faq = C.get("faq", [])
    if faq:
        fld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faq]},
            ensure_ascii=False).replace("</", "<\\/")
        src = src.replace("</head>", f'<script type="application/ld+json" id="ld-faq">{fld}</script>\n</head>', 1)
    return src


def sitemap(C: dict):
    today = dt.date.today().isoformat()
    imgs = ["og.png"] + [p["image"] for p in C.get("projects", []) if p.get("image", "").startswith("img/")]
    img_xml = "".join(f"\n    <image:image><image:loc>{SITE_URL}/{html.escape(i)}</image:loc></image:image>" for i in imgs)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>{SITE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>{img_xml}
  </url>
  <url>
    <loc>{SITE_URL}/privacy</loc>
    <lastmod>{today}</lastmod>
    <changefreq>yearly</changefreq>
    <priority>0.3</priority>
  </url>
</urlset>
"""
    (BUILD / "sitemap.xml").write_text(xml, encoding="utf-8")
    (BUILD / "robots.txt").write_text(f"""User-agent: *
Allow: /
Disallow: /beheer.html
Disallow: /publish.php
Disallow: /fetch-meta.php
Disallow: /contact.php

Sitemap: {SITE_URL}/sitemap.xml
""", encoding="utf-8")
    print(f"sitemap.xml: 2 pagina's, {len(imgs)} afbeeldingen")


def main():
    C = json.loads((BUILD / "content.json").read_text(encoding="utf-8"))
    srv = serve()
    try:
        data = asyncio.run(snapshot(srv.server_address[1]))
    finally:
        srv.shutdown()
    idx = BUILD / "index.html"
    out = inject(idx.read_text(encoding="utf-8"), data, C)
    idx.write_text(out, encoding="utf-8")
    print(f"index.html vooraf gevuld: {len(data['blocks'])} blokken, {len(data['texts'])} teksten")
    sitemap(C)


if __name__ == "__main__":
    main()
