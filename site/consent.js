// Cookiemelding (AVG/ePrivacy), zelfde werking als weekdot.com.
// Noodzakelijke opslag (alleen deze keuze) staat altijd aan. Google Fonts (Inter en JetBrains Mono,
// een derde partij die je IP-adres ziet) laden pas na "Accepteren". De keuze geldt 12 maanden.
// Daarna staat linksonder een rond cookieknopje waarmee je de melding opnieuw opent.
(function () {
  "use strict";
  var KEY = "pf_consent", MAX = 365 * 24 * 3600, MAX_MS = MAX * 1000;
  var FONTS = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap";
  var PRIVACY = /privacy/.test(location.pathname) ? "#cookies" : "/privacy#cookies";
  var T = {
    title: "Cookies en privacy",
    text: "PixelForges gebruikt alleen opslag die nodig is om deze keuze te onthouden. Met je toestemming laden we ook de lettertypes Inter en JetBrains Mono van Google Fonts; daarbij ziet Google je IP-adres. Geen advertenties, geen tracking.",
    more: "Meer in de privacyverklaring",
    accept: "Accepteren",
    necessary: "Alleen noodzakelijk",
    settings: "Cookie-instellingen"
  };

  function valid(v) { return v && (v.choice === "all" || v.choice === "necessary") && !(Date.now() - Date.parse(v.at) > MAX_MS); }
  function read() {
    try { var v = JSON.parse(localStorage.getItem(KEY)); if (valid(v)) return v; } catch (e) {}
    var m = document.cookie.match(/(?:^|; )pf_consent=([^;]+)/);
    if (m) { try { var c = JSON.parse(decodeURIComponent(m[1])); if (valid(c)) return c; } catch (e) {} }
    return null;
  }
  function save(choice) {
    var v = { choice: choice, at: new Date().toISOString(), v: 1 };
    try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {}
    try {
      document.cookie = KEY + "=" + encodeURIComponent(JSON.stringify(v)) + "; Max-Age=" + MAX + "; Path=/; SameSite=Lax" +
        (location.protocol === "https:" ? "; Secure" : "");
    } catch (e) {}
    return v;
  }
  function fonts() {
    if (document.getElementById("pf-fonts")) return;
    var l = document.createElement("link"); l.id = "pf-fonts"; l.rel = "stylesheet"; l.href = FONTS;
    document.head.appendChild(l);
  }

  var CSS = [
    "#pf-consent{position:fixed;left:max(16px,env(safe-area-inset-left,0px));right:max(16px,env(safe-area-inset-right,0px));bottom:calc(16px + env(safe-area-inset-bottom,0px));z-index:9999;max-width:560px;margin:0 auto;background:rgba(18,18,27,.92);-webkit-backdrop-filter:saturate(160%) blur(16px);backdrop-filter:saturate(160%) blur(16px);border:1px solid rgba(208,251,101,.22);border-radius:22px;padding:20px 22px;color:#f5f5f7;font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif;box-shadow:0 24px 60px -10px rgba(0,0,0,.65);animation:pf-up .35s cubic-bezier(.2,.8,.2,1);text-align:start}",
    "@keyframes pf-up{from{opacity:0;transform:translateY(16px)}}",
    "#pf-consent .t{display:flex;align-items:center;gap:10px;font-size:17px;font-weight:700;margin:0 0 6px;letter-spacing:-.01em}",
    "#pf-consent .t svg{width:22px;height:22px;color:#d0fb65;flex:none}",
    "#pf-consent p{margin:0;color:#b4b4c0;font-size:14px}",
    "#pf-consent a{color:#f5f5f7;text-decoration:underline;text-underline-offset:2px}",
    "#pf-consent a:hover{color:#d0fb65}",
    "#pf-consent .b{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}",
    "#pf-consent button{font:inherit;font-weight:700;border:0;border-radius:999px;padding:12px 20px;min-height:44px;cursor:pointer;transition:filter .15s,background .15s,box-shadow .2s}",
    "#pf-consent .y{background:#d0fb65;color:#0a0a0f}",
    "#pf-consent .y:hover{filter:brightness(1.05);box-shadow:0 8px 28px -8px rgba(208,251,101,.6)}",
    "#pf-consent .n{background:rgba(255,255,255,.1);color:#f5f5f7;border:1px solid rgba(255,255,255,.14)}",
    "#pf-consent .n:hover{background:rgba(255,255,255,.16)}",
    "#pf-consent button:focus-visible{outline:3px solid #d0fb65;outline-offset:2px}",
    "#pf-consent:focus{outline:none}",
    "@media (max-width:420px){#pf-consent .b button{flex:1 1 auto}}",
    "#pf-cookie-btn{position:fixed;left:max(16px,env(safe-area-inset-left,0px));bottom:calc(16px + env(safe-area-inset-bottom,0px));z-index:45;width:44px;height:44px;border-radius:50%;padding:0;border:1px solid rgba(255,255,255,.16);background:rgba(18,18,27,.88);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);color:#f5f5f7;display:grid;place-items:center;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.4);transition:transform .2s,background .2s,color .2s,bottom .35s cubic-bezier(.2,.7,.2,1)}",
    "#pf-cookie-btn:hover{transform:scale(1.08);background:#d0fb65;color:#0a0a0f;border-color:#d0fb65}",
    "#pf-cookie-btn:focus-visible{outline:3px solid #d0fb65;outline-offset:3px}",
    "#pf-cookie-btn svg{width:24px;height:24px}",
    "@media (max-width:560px){#pf-cookie-btn{width:40px;height:40px;left:max(12px,env(safe-area-inset-left,0px));bottom:calc(12px + env(safe-area-inset-bottom,0px));opacity:.92}#pf-cookie-btn svg{width:20px;height:20px}}",
    // boven de mobiele 'Start je project'-balk als die zichtbaar is
    "body:has(.m-cta.show) #pf-cookie-btn{bottom:calc(80px + env(safe-area-inset-bottom,0px))}",
    "@media (prefers-reduced-motion:reduce){#pf-consent{animation:none}#pf-cookie-btn{transition:none}}"
  ].join("\n");
  function style() {
    if (document.getElementById("pf-consent-css")) return;
    var s = document.createElement("style"); s.id = "pf-consent-css"; s.textContent = CSS;
    document.head.appendChild(s);
  }

  var COOKIE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.3A9 9 0 1 1 11.7 3a3 3 0 0 0 3.8 3.8 3 3 0 0 0 3.7 3.7 3 3 0 0 0 1.8 1.8z"/><circle cx="8.5" cy="10.5" r="1" fill="currentColor"/><circle cx="12" cy="15.5" r="1" fill="currentColor"/><circle cx="16" cy="14" r="1" fill="currentColor"/><circle cx="8" cy="15" r=".6" fill="currentColor"/></svg>';

  // niet-modale dialoog: krijgt de focus bij openen en geeft die terug bij sluiten
  function banner() {
    if (document.getElementById("pf-consent")) return;
    style();
    var prev = document.activeElement;
    var d = document.createElement("div");
    d.id = "pf-consent"; d.setAttribute("role", "dialog"); d.setAttribute("aria-modal", "false");
    d.setAttribute("aria-labelledby", "pf-consent-t"); d.setAttribute("aria-describedby", "pf-consent-p"); d.tabIndex = -1;
    d.innerHTML = '<div class="t" id="pf-consent-t">' + COOKIE + T.title + "</div>" +
      '<p id="pf-consent-p">' + T.text + ' <a href="' + PRIVACY + '">' + T.more + "</a></p>" +
      '<div class="b"><button type="button" class="y">' + T.accept + '</button><button type="button" class="n">' + T.necessary + "</button></div>";
    function close(choice) {
      save(choice); if (choice === "all") fonts();
      var hadFocus = d.contains(document.activeElement);
      d.remove(); bubble();
      if (hadFocus) {
        var back = prev && prev !== document.body && document.contains(prev) ? prev : document.getElementById("pf-cookie-btn");
        if (back && back.focus) try { back.focus({ preventScroll: true }); } catch (e) { back.focus(); }
      }
    }
    d.querySelector(".y").onclick = function () { close("all"); };
    d.querySelector(".n").onclick = function () { close("necessary"); };
    document.body.appendChild(d);
    try { d.focus({ preventScroll: true }); } catch (e) { d.focus(); }
  }

  // rond cookieknopje linksonder (zodra er een keuze is): tikken = melding opnieuw tonen
  function bubble() {
    if (document.getElementById("pf-cookie-btn")) return;
    style();
    var b = document.createElement("button"); b.id = "pf-cookie-btn"; b.type = "button";
    b.title = T.settings; b.setAttribute("aria-label", T.settings);
    b.innerHTML = COOKIE;
    b.onclick = open;
    document.body.appendChild(b);
  }
  function open() {
    var x = document.getElementById("pf-consent"); if (x) x.remove();
    var b = document.getElementById("pf-cookie-btn"); if (b) b.remove();
    banner();
  }
  // Als in beheer een CookieYes-ID is ingevuld, neemt CookieYes het over
  function disable() {
    ["pf-consent", "pf-cookie-btn"].forEach(function (id) { var e = document.getElementById(id); if (e) e.remove(); });
    window.PixelConsent.disabled = true;
  }

  window.PixelConsent = { open: open, get: read, disable: disable };
  var c = read();
  if (c && c.choice === "all") fonts();
  function start() {
    if (window.PixelConsent.disabled) return;
    if (c) bubble(); else banner();
    // footerlink "Cookie-instellingen" (zonder JavaScript gaat die naar de privacyverklaring)
    Array.prototype.forEach.call(document.querySelectorAll("[data-consent-open]"), function (a) {
      a.addEventListener("click", function (e) { e.preventDefault(); open(); });
    });
  }
  if (document.readyState !== "loading") start();
  else document.addEventListener("DOMContentLoaded", start);
})();
