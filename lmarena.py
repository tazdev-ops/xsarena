#!/usr/bin/env python3
import sys, gi, urllib.parse, shutil, threading
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
# Try newer WebKit2 first, fall back if unavailable
try:
    gi.require_version('WebKit2', '4.1')
except ValueError:
    gi.require_version('WebKit2', '4.0')

# Soup version differs by distro; try 3.0 then 2.4
try:
    gi.require_version('Soup', '3.0')
    SOUP_VER = '3.0'
except ValueError:
    gi.require_version('Soup', '2.4')
    SOUP_VER = '2.4'

from gi.repository import Gtk, Gdk, WebKit2, Gio, GLib, Soup

# Prefer cloudscraper; fall back to cfscrape
CLOUDSCRAPER_IMPORT_ERR, CF_IMPORT_ERR = None, None
try:
    import cloudscraper as _cloudscraper
    HAVE_CLOUDSCRAPER = True
except Exception as e:
    HAVE_CLOUDSCRAPER, CLOUDSCRAPER_IMPORT_ERR = False, str(e)

try:
    import cfscrape as _cfscrape
    HAVE_CF = True
except Exception as e:
    HAVE_CF, CF_IMPORT_ERR = False, str(e)

URL = sys.argv[1] if len(sys.argv) > 1 else "https://lmarena.ai/"

# Inject as early as possible
INJECT_START = getattr(WebKit2.UserScriptInjectionTime, 'DOCUMENT_START',
                getattr(WebKit2.UserScriptInjectionTime, 'START', 0))

CSS = """
/* Hide by default */
[data-sentry-component="EvaluationHeader"] { display: none !important; }
[data-variant="sidebar"][data-side="left"] { display: none !important; }

/* Show on toggle */
html.lm-show-header [data-sentry-component="EvaluationHeader"] { display: revert !important; }
html.lm-show-sidebar [data-variant="sidebar"][data-side="left"] { display: revert !important; }

/* Extra panel (shown by default; hide when toggled) */
html.lm-hide-extra .flex.flex-col.items-center.px-4.pb-6 { display: none !important; }
"""

JS_KEYS = r"""
(function(){
  function isEditable(el){ return !!(el && (el.closest('input, textarea, select, [contenteditable]'))); }
  let headerTimer = null, extraTimer = null;

  function showHeaderBrief(ms=5000){
    const html = document.documentElement;
    html.classList.add('lm-show-header');
    clearTimeout(headerTimer);
    headerTimer = setTimeout(() => html.classList.remove('lm-show-header'), ms);
  }
  function hideExtraBrief(ms=5000){
    const html = document.documentElement;
    html.classList.add('lm-hide-extra');
    clearTimeout(extraTimer);
    extraTimer = setTimeout(() => html.classList.remove('lm-hide-extra'), ms);
  }

  window.addEventListener('keydown', function(e){
    if (isEditable(e.target)) return;
    if (e.ctrlKey && e.altKey && !e.shiftKey && !e.metaKey) {
      const html = document.documentElement;
      switch (e.code) {
        case 'KeyP': showHeaderBrief(5000); e.preventDefault(); break;  // Ctrl+Alt+P
        case 'KeyH': html.classList.toggle('lm-show-header'); e.preventDefault(); break; // Ctrl+Alt+H
        case 'KeyB': html.classList.toggle('lm-show-sidebar'); e.preventDefault(); break; // Ctrl+Alt+B
        case 'KeyJ': hideExtraBrief(5000); e.preventDefault(); break; // Ctrl+Alt+J
        case 'KeyE': html.classList.toggle('lm-hide-extra'); e.preventDefault(); break; // Ctrl+Alt+E
      }
    }
  }, true);
})();
"""

def get_host(url: str) -> str:
    return urllib.parse.urlparse(url).hostname or ""

def get_gnome_proxies_for_url(url: str):
    # Use GNOME/System proxy resolver so scrapers use same proxy as WebKit
    try:
        resolver = Gio.ProxyResolver.get_default()
        if not resolver:
            return None
        lst = resolver.lookup(url, None) or []
        for p in lst:
            if p and not p.startswith('direct'):
                return {"http": p, "https": p}
    except Exception:
        pass
    return None

def set_user_agent(view: WebKit2.WebView, ua: str):
    if not ua or not isinstance(ua, str):
        return
    try:
        settings = view.get_settings() or WebKit2.Settings()
        if hasattr(settings, "set_user_agent"):
            settings.set_user_agent(ua)
        view.set_settings(settings)
    except Exception as e:
        print(f"[warn] Could not set User-Agent: {e}")

def build_origin_uri(origin_str: str):
    try:
        if SOUP_VER == '2.4':
            return Soup.URI.new(origin_str)
        # Soup 3 expects GUri
        return GLib.Uri.parse(origin_str, GLib.UriFlags.NONE)
    except Exception:
        return None

def add_cookie_sync(cm: WebKit2.CookieManager, cookie: Soup.Cookie, origin_uri):
    loop = GLib.MainLoop()
    def _cb(manager, result):
        try:
            manager.add_cookie_finish(result)
        except Exception as e:
            print(f"[warn] add_cookie_finish: {e}")
        loop.quit()
    try:
        cm.add_cookie(cookie, origin_uri, _cb)
        loop.run()
    except Exception as e:
        print(f"[warn] add_cookie_async failed: {e}")

def set_cf_cookies(context: WebKit2.WebContext, url: str, tokens: dict):
    if not tokens:
        return
    cm = context.get_cookie_manager()
    host = get_host(url)
    if not host:
        return
    origin_str = f"https://{host}/"
    origin_uri = build_origin_uri(origin_str)
    for name, value in tokens.items():
        cookie_str = f"{name}={value}; Domain={host}; Path=/; Secure; HttpOnly; SameSite=Lax"
        try:
            cookie = Soup.Cookie.parse(cookie_str, origin_uri)
            if not cookie:
                print(f"[warn] Could not parse cookie: {cookie_str}")
                continue
            add_cookie_sync(cm, cookie, origin_uri)
        except Exception as e:
            print(f"[warn] Failed to set cookie {name}: {e}")

def get_tokens_cloudscraper(url: str, proxies: dict):
    # Use cloudscraper's get_tokens to ensure UA is a string
    try:
        tokens, ua = _cloudscraper.get_tokens(url, proxies=proxies)
        # tokens might be empty when no challenge; UA should be a str
        if ua and not isinstance(ua, str):
            try:
                ua = str(ua)
            except Exception:
                ua = None
        print(f"[info] cloudscraper tokens={list((tokens or {}).keys())} ua_len={len(ua) if ua else 0}")
        return tokens, ua
    except Exception as e:
        print(f"[warn] cloudscraper failed: {e}")
        return None, None

def get_tokens_cfscrape(url: str, proxies: dict):
    # Use create_scraper(delay=10) and read cookies + UA
    try:
        delay = 10
        scraper = _cfscrape.create_scraper(delay=delay)
        if proxies:
            try:
                scraper.proxies.update(proxies)
            except Exception:
                scraper.proxies = proxies
        r = scraper.get(url, allow_redirects=True, timeout=60)
        tokens = {}
        for c in scraper.cookies:
            n = (getattr(c, 'name', '') or '').lower()
            if n.startswith('cf') or n.startswith('__cf'):
                tokens[c.name] = c.value
        ua = scraper.headers.get('User-Agent')
        print(f"[info] cfscrape status={getattr(r,'status_code',None)} tokens={list(tokens.keys())} ua_len={len(ua) if ua else 0}")
        return tokens, ua
    except Exception as e:
        print(f"[warn] cfscrape failed: {e}")
        return None, None

def maybe_get_cf_tokens(url: str):
    proxies = get_gnome_proxies_for_url(url)
    # Try cloudscraper first
    if HAVE_CLOUDSCRAPER:
        t, ua = get_tokens_cloudscraper(url, proxies)
        if t or ua:
            return t, ua
    else:
        if CLOUDSCRAPER_IMPORT_ERR:
            print(f"[info] cloudscraper not available: {CLOUDSCRAPER_IMPORT_ERR}")
    # Fallback to cfscrape
    if HAVE_CF:
        if shutil.which("node") is None:
            print("[info] Node.js not found; cfscrape may fail to solve Cloudflare challenges.")
        t, ua = get_tokens_cfscrape(url, proxies)
        if t or ua:
            return t, ua
    else:
        if CF_IMPORT_ERR:
            print(f"[info] cfscrape not available: {CF_IMPORT_ERR}")
    print("[info] No CF solver available or no challenge detected; loading normally.")
    return None, None

def solve_cf_async(view: WebKit2.WebView):
    # Run token solving off the UI thread; apply on main
    current = view.get_uri() or URL
    def worker():
        t, ua = maybe_get_cf_tokens(current)
        def apply_tokens():
            if ua:
                set_user_agent(view, ua)
            if t:
                context = view.get_context()
                set_cf_cookies(context, current, t)
            # Reload to use new UA/cookies
            view.reload()
            return False
        GLib.idle_add(apply_tokens)
    threading.Thread(target=worker, daemon=True).start()

def main():
    win = Gtk.Window()
    win.set_default_size(1200, 800)
    win.set_title("LM Arena — 100%")

    ucm = WebKit2.UserContentManager()
    view = WebKit2.WebView.new_with_user_content_manager(ucm)

    # Try to pre-solve Cloudflare and inject cookies + UA BEFORE first load
    tokens, ua = maybe_get_cf_tokens(URL)
    if ua:
        set_user_agent(view, ua)
    if tokens:
        context = view.get_context()
        set_cf_cookies(context, URL, tokens)

    # Inject CSS and JS (as early as possible)
    style = WebKit2.UserStyleSheet.new(
        CSS,
        WebKit2.UserContentInjectedFrames.ALL_FRAMES,
        WebKit2.UserStyleLevel.USER,
        None, None
    )
    ucm.add_style_sheet(style)

    script = WebKit2.UserScript.new(
        JS_KEYS,
        WebKit2.UserContentInjectedFrames.ALL_FRAMES,
        INJECT_START,
        None, None
    )
    ucm.add_script(script)

    win.add(view)
    view.load_uri(URL)

    # Zoom handlers (Ctrl+= / Ctrl++ / Ctrl+- / Ctrl+0)
    def set_zoom(z):
        z = max(0.3, min(3.0, z))
        view.set_zoom_level(z)
        win.set_title(f"LM Arena — {int(z*100)}%")

    def on_zoom_keys(widget, event):
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        if not ctrl:
            return False
        name = Gdk.keyval_name(event.keyval) or ""
        if name in ('plus', 'KP_Add', 'equal'):  # Ctrl+= or Ctrl++
            set_zoom(view.get_zoom_level() * 1.1)
            return True
        if name in ('minus', 'KP_Subtract'):
            set_zoom(view.get_zoom_level() / 1.1)
            return True
        if name in ('0', 'KP_0'):
            set_zoom(1.0)
            return True
        return False

    def on_cf_keys(widget, event):
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        alt  = bool(event.state & Gdk.ModifierType.MOD1_MASK)
        if ctrl and alt and not (event.state & Gdk.ModifierType.SHIFT_MASK):
            name = Gdk.keyval_name(event.keyval) or ""
            if name in ('r', 'R'):
                print("[info] Re-solving Cloudflare and reloading…")
                solve_cf_async(view)
                return True
        return False

    view.connect("key-press-event", on_zoom_keys)
    win.connect("key-press-event", on_zoom_keys)
    view.connect("key-press-event", on_cf_keys)
    win.connect("key-press-event", on_cf_keys)

    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == '__main__':
    main()
