<?php
/**
 * Contactformulier van pixelforges.nl.
 * Stuurt een aanvraag per e-mail naar het adres in content.json (settings.email).
 * Spam-bescherming: verborgen veld, minimale invultijd en maximaal 5 berichten per uur per IP.
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

$raw = file_get_contents('php://input');
if ($raw === false || strlen($raw) > 32 * 1024) {
    reply(413, ['ok' => false, 'error' => 'Bericht is te lang.']);
}
$in = json_decode($raw, true);
if (!is_array($in)) $in = $_POST;

$clean = fn($v, $max) => mb_substr(trim(preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', (string)($v ?? ''))), 0, $max);
$name    = $clean($in['name'] ?? '', 100);
$company = $clean($in['company'] ?? '', 100);
$email   = $clean($in['email'] ?? '', 160);
$phone   = $clean($in['phone'] ?? '', 40);
$package = $clean($in['package'] ?? '', 40);
$message = $clean($in['message'] ?? '', 5000);

// Spam: honeypot ingevuld of te snel verstuurd -> doen alsof het gelukt is
if (!empty($in['website']) || (int)($in['elapsed'] ?? 0) < 2500) {
    reply(200, ['ok' => true]);
}

if ($name === '' || !filter_var($email, FILTER_VALIDATE_EMAIL) || mb_strlen($message) < 10) {
    reply(400, ['ok' => false, 'error' => 'Vul je naam, een geldig e-mailadres en een bericht in.']);
}
// Geen header-injectie via naam of e-mail
if (preg_match('/[\r\n]/', $name . $email)) {
    reply(400, ['ok' => false, 'error' => 'Ongeldige invoer.']);
}

// Maximaal 5 berichten per uur per IP
$ip = $_SERVER['REMOTE_ADDR'] ?? '0';
$rlFile = sys_get_temp_dir() . '/pf-contact-' . hash('sha256', $ip . __DIR__) . '.json';
$now = time();
$hits = array_filter((array)json_decode((string)@file_get_contents($rlFile), true), fn($t) => $t > $now - 3600);
if (count($hits) >= 5) {
    reply(429, ['ok' => false, 'error' => 'Je hebt al een paar berichten gestuurd. Probeer het later opnieuw.']);
}
$hits[] = $now;
@file_put_contents($rlFile, json_encode(array_values($hits)));

// Ontvanger uit content.json
$content = json_decode((string)@file_get_contents(__DIR__ . '/content.json'), true);
$to = $content['settings']['email'] ?? 'info@pixelforges.nl';
if (!filter_var($to, FILTER_VALIDATE_EMAIL)) $to = 'info@pixelforges.nl';

$labels = [];
foreach (($content['packages'] ?? []) as $p) $labels[$p['id'] ?? ''] = $p['name'] ?? '';
$labels += ['anders' => 'Iets anders', 'weet-niet' => 'Weet ik nog niet'];
$pkgLabel = $labels[$package] ?? ($package ?: '-');

$domain = preg_replace('/^www\./', '', strtolower(preg_replace('/:\d+$/', '', $host))) ?: 'pixelforges.nl';
$subject = 'Nieuwe aanvraag via ' . $domain . ': ' . $name . ($company !== '' ? ' (' . $company . ')' : '');
$body = "Nieuwe aanvraag via het contactformulier\n"
      . str_repeat('-', 42) . "\n"
      . "Naam:      $name\n"
      . "Bedrijf:   " . ($company ?: '-') . "\n"
      . "E-mail:    $email\n"
      . "Telefoon:  " . ($phone ?: '-') . "\n"
      . "Pakket:    $pkgLabel\n"
      . str_repeat('-', 42) . "\n\n"
      . $message . "\n\n"
      . str_repeat('-', 42) . "\n"
      . 'Verstuurd op ' . date('d-m-Y H:i') . ' vanaf ' . $ip . "\n";

$fromName = '=?UTF-8?B?' . base64_encode('PixelForges website') . '?=';
$headers = [
    'From: ' . $fromName . ' <noreply@' . $domain . '>',
    'Reply-To: ' . '=?UTF-8?B?' . base64_encode($name) . '?= <' . $email . '>',
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: 8bit',
    'X-Mailer: PixelForges',
];
$ok = @mail($to, '=?UTF-8?B?' . base64_encode($subject) . '?=', $body, implode("\r\n", $headers), '-f noreply@' . $domain);
if (!$ok) {
    reply(500, ['ok' => false, 'error' => 'De mailserver gaf een fout.']);
}
reply(200, ['ok' => true]);
