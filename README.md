# pixelforges.nl

Website van PixelForges: professionele websites voor MKB en ZZP.

## Structuur

- `site/` – alles wat online komt
  - `index.html` – de site
  - `privacy.html` – privacyverklaring (ook bereikbaar als `/privacy`)
  - `content.json` – alle teksten, pakketten, portfolio, reviews en vragen
  - `beheer.html` – beheerpagina om `content.json` te bewerken (achter wachtwoord)
  - `publish.php` – Publiceren-knop: zet wijzigingen live en commit ze naar deze repo
  - `fetch-meta.php` – haalt naam, omschrijving en og:image op van een website voor nieuwe portfolio-items (achter wachtwoord)
  - `consent.js` – cookiemelding en cookieknopje (zoals weekdot.com); Google Fonts laden pas na toestemming
  - `contact.php` – contactformulier, mailt naar het e-mailadres onder *Algemeen* in beheer
  - `img/` – afbeeldingen (portfolio en reviews)
- `.github/workflows/release.yml` – zet elke wijziging in `site/` via FTP live en maakt een zip-release
- `.github/scripts/localize_images.py` – kopieert afbeeldingen met een https-link (bijv. nog van Base44) naar `site/img`

## Secrets

Zet deze onder **Settings → Secrets and variables → Actions → New repository secret**:

| Naam | Inhoud |
|---|---|
| `BEHEER_USER` | Gebruikersnaam voor `beheer.html` |
| `BEHEER_PASSWORD` | Wachtwoord voor `beheer.html` |
| `BEHEER_HTPASSWD_PATH` | Volledig pad naar `.htpasswd` in de webmap, bijv. `/home/GEBRUIKER/public_html/pixelforges.nl/.htpasswd` |
| `FTP_SERVER` | FTP-server uit cPanel (bijv. `ftp.pixelforges.nl`) |
| `FTP_USER` | Volledige FTP-gebruikersnaam (bijv. `naam@pixelforges.nl`) |
| `FTP_PASSWORD` | Wachtwoord van dat FTP-account |
| `FTP_PORT` | Meestal `21` (`22` = SFTP) |
| `FTP_DIR` | Doelmap als het FTP-account in je thuismap start, bijv. `public_html` of `public_html/pixelforges.nl` |
| `PUBLISH_GITHUB_TOKEN` | Fine-grained token, alleen voor deze repo, met *Contents: Read and write* |

Zonder FTP-secrets maakt de workflow alleen een zip-release. Wachtwoord en token komen alleen op de server terecht, nooit in de repo of in de (publieke) zip-releases.

## Een update doen

1. Open `https://pixelforges.nl/beheer.html` en log in.
2. Pas teksten, pakketten, portfolio, reviews of vragen aan. Upload eventueel afbeeldingen (worden automatisch verkleind naar WebP).
3. Klik **Publiceren**. De wijziging staat direct live en wordt als commit in deze repo opgeslagen.
4. De workflow zet daarna de hele site via FTP opnieuw neer en maakt een zip-release als back-up.

Wijzigingen aan de code (bijv. `index.html`) gaan via een commit in `site/`; ook die worden automatisch live gezet.
Handmatig opnieuw uitrollen: **Actions → Release site → Run workflow**.

## Overstappen van Base44

1. Zet de secrets hierboven en draai de workflow. De site staat dan klaar op je hosting.
2. Laat het domein `pixelforges.nl` (A-record en `www`) naar je eigen hosting wijzen in plaats van Base44.
3. Zorg dat er een SSL-certificaat is (bijv. AutoSSL in cPanel). De site stuurt alles naar `https://` zonder `www`.
4. Test het contactformulier: het gebruikt de PHP-mailfunctie van je hosting en mailt vanaf `noreply@pixelforges.nl`.

## SEO

Bij elke deploy draait `.github/scripts/prerender.py`:

- zet pakketten, portfolio, vragen en andere teksten uit `content.json` vooraf in `index.html`, zodat zoekmachines en deelvoorbeelden alles direct zien;
- maakt de structured data (organisatie, dienst met prijzen, portfolio, veelgestelde vragen) uit `content.json`;
- maakt `sitemap.xml` (met afbeeldingen) en `robots.txt`.

Na een wijziging via beheer worden deze bestanden bij de volgende deploy automatisch bijgewerkt.

## Huisstijl, banners en social afbeeldingen

`brand/` bevat alle beeldmateriaal:

- `brand/export/` – OG-afbeelding, social banners (X, LinkedIn, Facebook, Instagram), webbanners, presentatie, e-mailhandtekening en logo's
- `brand/pixelforges-brand.zip` – hetzelfde als één zip
- `brand/templates/banner.html` – het ontwerp van alle formaten
- `brand/render.py` – maakt alles opnieuw, ook `site/og.png`, `favicon.ico` en de app-iconen

Opnieuw maken na een prijs- of portfoliowijziging:

```
pip install playwright pillow && python -m playwright install chromium
python brand/render.py --zip
```
