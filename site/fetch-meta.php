<?php
/**
 * Haalt titel, omschrijving en deelafbeelding (og:image) op van een website,
 * voor nieuwe portfolio-items in beheer.html.
 *
 * Beveiligd met dezelfde gebruikersnaam en hetzelfde wachtwoord als beheer.html (zie .htaccess).
 * Haalt alleen openbare http(s)-adressen op, nooit adressen in een intern netwerk.
 */

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function reply(int $code, array $body): void {
    http_response_code($code);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    reply(405, ['ok' => false, 'error' => 'Alleen POST is toegestaan.']);
}
$host = $_SERVER['HTTP_HOST'] ?? '';
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if ($origin !== '' && strtolower((string)parse_url($origin, PHP_URL_HOST)) !== strtolower(preg_replace('/:\d+$/', '', $host))) {
    reply(403, ['ok' => false, 'error' => 'Aanvraag van een andere website geweigerd.']);
}
if (($_SERVER['HTTP_X_PF_BEHEER'] ?? '') !== '1') {
    reply(403, ['ok' => false, 'error' => 'Ontbrekende beheer-header.']);
}
if (!function_exists('curl_init')) {
    reply(500, ['ok' => false, 'error' => 'PHP-curl staat niet aan op de server.']);
}

$in = json_decode((string)file_get_contents('php://input'), true);
$url = trim((string)($in['url'] ?? ''));
if ($url !== '' && !preg_match('#^https?://#i', $url)) $url = 'https://' . $url;
if (!filter_var($url, FILTER_VALIDATE_URL) || !preg_match('#^https?://#i', $url)) {
    reply(400, ['ok' => false, 'error' => 'Vul een geldig website-adres in, bijv. https://voorbeeld.nl']);
}

/** Controleert dat een adres naar een openbaar IP wijst en geeft dat IP terug. */
function public_ip(string $url): string {
    $p = parse_url($url);
    $scheme = strtolower($p['scheme'] ?? '');
    $port = $p['port'] ?? ($scheme === 'https' ? 443 : 80);
    if (!in_array($scheme, ['http', 'https'], true) || !in_array((int)$port, [80, 443], true)) {
        throw new RuntimeException('Alleen gewone http- en https-adressen kunnen worden opgehaald.');
    }
    $h = $p['host'] ?? '';
    $ips = filter_var($h, FILTER_VALIDATE_IP) ? [$h] : (gethostbynamel($h) ?: []);
    if (!$ips) throw new RuntimeException('Het domein ' . $h . ' bestaat niet of is (nog) niet bereikbaar.');
    foreach ($ips as $ip) {
        if (!filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE)) {
            throw new RuntimeException('Dit adres wijst naar een intern netwerk en wordt niet opgehaald.');
        }
    }
    return $ips[0];
}

/** Haalt een adres op, volgt maximaal 5 doorverwijzingen en controleert elke stap. */
function get(string $url, int $max, string $accept): array {
    for ($i = 0; $i < 6; $i++) {
        $ip = public_ip($url);
        $p = parse_url($url);
        $port = $p['port'] ?? (strtolower($p['scheme']) === 'https' ? 443 : 80);
        $body = '';
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => false,
            CURLOPT_FOLLOWLOCATION => false,
            CURLOPT_TIMEOUT => 15,
            CURLOPT_CONNECTTIMEOUT => 8,
            CURLOPT_RESOLVE => [$p['host'] . ':' . $port . ':' . $ip],
            CURLOPT_ENCODING => '',
            CURLOPT_USERAGENT => 'Mozilla/5.0 (compatible; PixelForgesBot/1.0; +https://pixelforges.nl)',
            CURLOPT_HTTPHEADER => ['Accept: ' . $accept, 'Accept-Language: nl,en;q=0.8'],
            CURLOPT_WRITEFUNCTION => function ($ch, $chunk) use (&$body, $max) {
                $body .= $chunk;
                return strlen($body) > $max ? 0 : strlen($chunk);
            },
        ]);
        curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $type = (string)curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
        $loc = (string)curl_getinfo($ch, CURLINFO_REDIRECT_URL);
        $err = curl_errno($ch);
        curl_close($ch);
        if ($code >= 300 && $code < 400 && $loc !== '') { $url = $loc; continue; }
        if ($err && $err !== CURLE_WRITE_ERROR) throw new RuntimeException('De website reageerde niet (fout ' . $err . ').');
        if ($code < 200 || $code >= 300) throw new RuntimeException('De website gaf HTTP ' . $code . '.');
        return ['body' => $body, 'type' => $type, 'url' => $url];
    }
    throw new RuntimeException('Te veel doorverwijzingen.');
}

function absolute(string $rel, string $base): string {
    if ($rel === '') return '';
    if (preg_match('#^https?://#i', $rel)) return $rel;
    $b = parse_url($base);
    $root = $b['scheme'] . '://' . $b['host'] . (isset($b['port']) ? ':' . $b['port'] : '');
    if (str_starts_with($rel, '//')) return $b['scheme'] . ':' . $rel;
    if (str_starts_with($rel, '/')) return $root . $rel;
    $dir = preg_replace('#/[^/]*$#', '/', $b['path'] ?? '/');
    return $root . $dir . $rel;
}

function clean(string $s, int $max): string {
    $s = trim(preg_replace('/\s+/u', ' ', html_entity_decode(strip_tags($s), ENT_QUOTES | ENT_HTML5, 'UTF-8')));
    if (mb_strlen($s) > $max) $s = rtrim(mb_substr($s, 0, $max - 1), " ,.;:-") . '…';
    return $s;
}

try {
    $page = get($url, 3 * 1024 * 1024, 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.5');
    $html = $page['body'];
    $final = $page['url'];

    // Naar UTF-8
    $cs = '';
    if (preg_match('/charset=([\w-]+)/i', $page['type'], $m)) $cs = $m[1];
    elseif (preg_match('/<meta[^>]+charset=["\']?([\w-]+)/i', $html, $m)) $cs = $m[1];
    if ($cs && strtoupper($cs) !== 'UTF-8') $html = @mb_convert_encoding($html, 'UTF-8', $cs) ?: $html;

    $meta = [];
    $title = '';
    $icons = [];
    if (class_exists('DOMDocument')) {
        $doc = new DOMDocument();
        libxml_use_internal_errors(true);
        $doc->loadHTML('<?xml encoding="UTF-8">' . $html, LIBXML_NOERROR | LIBXML_NOWARNING);
        foreach ($doc->getElementsByTagName('meta') as $el) {
            $k = strtolower($el->getAttribute('property') ?: $el->getAttribute('name'));
            if ($k !== '' && !isset($meta[$k])) $meta[$k] = $el->getAttribute('content');
        }
        $t = $doc->getElementsByTagName('title');
        if ($t->length) $title = $t->item(0)->textContent;
        foreach ($doc->getElementsByTagName('link') as $el) {
            $rel = strtolower($el->getAttribute('rel'));
            if (preg_match('/apple-touch-icon|icon/', $rel)) $icons[] = ['rel' => $rel, 'href' => $el->getAttribute('href'), 'sizes' => $el->getAttribute('sizes')];
        }
    } else {
        preg_match_all('/<meta\s[^>]*>/i', $html, $tags);
        foreach ($tags[0] as $tag) {
            if (preg_match('/(?:property|name)=["\']([^"\']+)["\']/i', $tag, $k) && preg_match('/content=["\']([^"\']*)["\']/i', $tag, $c)) {
                $meta[strtolower($k[1])] ??= $c[1];
            }
        }
        if (preg_match('/<title[^>]*>(.*?)<\/title>/is', $html, $m)) $title = $m[1];
    }

    $siteName = clean($meta['og:site_name'] ?? '', 60);
    $ogTitle = clean($meta['og:title'] ?? $meta['twitter:title'] ?? '', 120);
    $title = clean($title, 120);
    $hostName = preg_replace('/^www\./', '', strtolower(parse_url($final, PHP_URL_HOST)));

    // Naam: site_name, anders het eerste deel van de titel ("Naam - slogan")
    $name = $siteName;
    if ($name === '') {
        $base = $ogTitle ?: $title;
        $parts = preg_split('/\s+[|\-–—·:]\s+/u', $base);
        $name = trim($parts[0] ?? '');
        if ($name === '' || mb_strlen($name) > 40) $name = $hostName;
    }

    $desc = clean($meta['og:description'] ?? $meta['description'] ?? $meta['twitter:description'] ?? '', 220);

    // Afbeelding: og:image, twitter:image, anders het grootste app-icoon
    $imgUrl = trim($meta['og:image:secure_url'] ?? $meta['og:image'] ?? $meta['og:image:url'] ?? $meta['twitter:image'] ?? $meta['twitter:image:src'] ?? '');
    $imgSource = $imgUrl !== '' ? 'og:image' : '';
    if ($imgUrl === '' && $icons) {
        usort($icons, fn($a, $b) => (str_contains($b['rel'], 'apple') <=> str_contains($a['rel'], 'apple')) ?: ((int)$b['sizes'] <=> (int)$a['sizes']));
        $imgUrl = $icons[0]['href'];
        $imgSource = 'icoon';
    }
    $image = null;
    $imgError = '';
    if ($imgUrl !== '') {
        try {
            $img = get(absolute(html_entity_decode($imgUrl), $final), 8 * 1024 * 1024, 'image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8');
            $info = @getimagesizefromstring($img['body']);
            if ($info === false) throw new RuntimeException('geen geldige afbeelding');
            $image = ['mime' => $info['mime'], 'data' => base64_encode($img['body']), 'width' => $info[0], 'height' => $info[1], 'source' => $imgSource];
        } catch (Throwable $e) {
            $imgError = 'Afbeelding niet opgehaald: ' . $e->getMessage();
        }
    } else {
        $imgError = 'Deze website heeft geen deelafbeelding (og:image).';
    }

    reply(200, [
        'ok' => true,
        'url' => rtrim($final, '/'),
        'host' => $hostName,
        'name' => $name,
        'title' => $ogTitle ?: $title,
        'description' => $desc,
        'image' => $image,
        'imageError' => $imgError,
    ]);
} catch (Throwable $e) {
    reply(200, ['ok' => false, 'error' => $e->getMessage()]);
}
