#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scarica_sito_webcopy.py
====================================================================
Replica della struttura di Cyotek WebCopy, MA con il JavaScript
eseguito (quindi pagine con i testi reali, non vuote).

A differenza di Cyotek / wget / curl, questo script usa un browser
headless (Playwright/Chromium) che ESEGUE il JavaScript. Per questo
funziona anche sui siti costruiti con site-builder JS (es.
bemaritalia.it) che agli scraper classici restituiscono solo
"Please enable JavaScript to view this website".

STRUTTURA DI OUTPUT (identica a WebCopy)
  output/
    www.dominio.it/
      index.htm                         <- home renderizzata
      una-pagina/index.htm              <- ogni pagina nella sua cartella
      sezione/sottopagina/index.htm
      wp-content/uploads/.../file.pdf   <- PDF nel loro percorso originale
      webcopy-origin.txt                <- mappatura Uri / File Name / Content Type

  output/
    testi/                              <- testo pulito di pagine e PDF
    TESTI_COMPLETI.txt                  <- tutto concatenato (per conteggio)
    conteggio.csv                       <- URL, parole, caratteri per risorsa
    html_leggibile/
      index.htm                         <- copia stilizzata e navigabile di ogni
      una-pagina/index.htm                 pagina (Shadow DOM incorporato come
                                            <template shadowrootmode>, CSS/
                                            adoptedStyleSheets incorporati, link
                                            interni riscritti come nel mirror)

NOTE SULLA FEDELTA' A WEBCOPY
  - I link interni vengono riscritti in percorso RELATIVO (../ , index.htm)
    come fa WebCopy. La riscrittura copre i link a pagine e ai PDF scaricati.
  - I link esterni e gli asset non scaricati (immagini, css, js, font)
    restano in forma assoluta, esattamente come nel file di esempio fornito.
  - Vengono scaricati solo i PDF (come da esempio richiesto), oltre alle pagine.

------------------------------------------------------------
INSTALLAZIONE (una volta sola, su qualsiasi OS)
------------------------------------------------------------
  python -m pip install playwright beautifulsoup4 lxml pdfminer.six
  python -m playwright install chromium
  (su Linux la prima volta puo' servire: python -m playwright install-deps chromium)

------------------------------------------------------------
USO
------------------------------------------------------------
  python scarica_sito_webcopy.py https://www.bemaritalia.it/

  Opzioni:
    --out CARTELLA      cartella di output (default: ./output)
    --max N             massimo numero di pagine (default: 300)
    --delay SECONDI     pausa tra una pagina e l'altra (default: 1.0)
    --include-subdomains  segui anche i sottodomini (default: no)
====================================================================
"""

import argparse
import csv
import os
import re
import sys
import time
from collections import deque
from urllib.parse import (urljoin, urldefrag, urlparse, unquote,
                          parse_qsl, urlencode, urlunparse)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("ERRORE: manca Playwright. Esegui:\n"
             "  python -m pip install playwright beautifulsoup4 lxml pdfminer.six\n"
             "  python -m playwright install chromium")

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("ERRORE: manca BeautifulSoup. Esegui: python -m pip install beautifulsoup4 lxml")

# Impostato da main(): True = headless (default), False = finestra visibile (--headful)
HEADLESS = True

# --- JS che attraversa lo Shadow DOM ---------------------------------------
# Il framework APS/Alkemy renderizza i contenuti dentro shadow root, quindi
# innerText / page.content() standard restituiscono vuoto. Queste funzioni
# scendono ricorsivamente in tutti gli shadow root per recuperare testo e HTML.
JS_DEEP_TEXT = r"""
() => {
  function walk(node, out) {
    if (!node) return;
    if (node.nodeType === Node.TEXT_NODE) {
      const t = node.textContent.trim();
      if (t) out.push(t);
      return;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    const tag = node.tagName ? node.tagName.toLowerCase() : '';
    if (tag === 'script' || tag === 'style' || tag === 'noscript') return;
    if (node.shadowRoot) {
      node.shadowRoot.childNodes.forEach(c => walk(c, out));
    }
    node.childNodes.forEach(c => walk(c, out));
  }
  const out = [];
  walk(document.body, out);
  return out.join('\n');
}
"""

JS_DEEP_HTML = r"""
() => {
  function expand(node) {
    if (!node) return '';
    if (node.nodeType === Node.TEXT_NODE) return node.textContent;
    if (node.nodeType !== Node.ELEMENT_NODE) return '';
    const tag = node.tagName.toLowerCase();
    if (tag === 'script' || tag === 'style' || tag === 'noscript') return '';
    let inner = '';
    if (node.shadowRoot) {
      node.shadowRoot.childNodes.forEach(c => { inner += expand(c); });
    }
    node.childNodes.forEach(c => { inner += expand(c); });
    const attrs = [];
    if (node.attributes) {
      for (const a of node.attributes) attrs.push(a.name + '="' + a.value + '"');
    }
    const open = '<' + tag + (attrs.length ? ' ' + attrs.join(' ') : '') + '>';
    return open + inner + '</' + tag + '>';
  }
  return expand(document.body);
}
"""

# --- JS per html_leggibile/: serializza la pagina con Shadow DOM dichiarativo
# e CSS "adottati" (adoptedStyleSheets, applicati via JS e altrimenti invisibili)
# incorporati. A differenza di JS_DEEP_HTML (solo testo/struttura), qui si
# preserva anche lo stile cosi' com'e' calcolato dal browser.
JS_FLATTEN = r"""
() => {
  const VOID = new Set(['area','base','br','col','embed','hr','img','input',
    'link','meta','param','source','track','wbr']);
  function esc(t){return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
  function adoptedCss(sheets){
    let css = '';
    for (const sh of (sheets || [])) {
      try { for (const r of sh.cssRules) css += r.cssText + '\n'; } catch(e) {}
    }
    return css;
  }
  function ser(node){
    if (node.nodeType === 3) return esc(node.textContent);
    if (node.nodeType !== 1) return '';
    const tag = node.tagName.toLowerCase();
    if (tag === 'script' || tag === 'noscript') return '';
    let attrs = '';
    for (const a of (node.attributes||[])) {
      attrs += ' ' + a.name + '="' + String(a.value).replace(/"/g,'&quot;') + '"';
    }
    if (VOID.has(tag)) return '<' + tag + attrs + '>';
    let inner = '';
    if (node.shadowRoot) {
      let sh = '';
      const acss = adoptedCss(node.shadowRoot.adoptedStyleSheets);
      if (acss) sh += '<style>' + acss + '</style>';
      node.shadowRoot.childNodes.forEach(c => { sh += ser(c); });
      inner += '<template shadowrootmode="open">' + sh + '</template>';
    }
    node.childNodes.forEach(c => { inner += ser(c); });
    return '<' + tag + attrs + '>' + inner + '</' + tag + '>';
  }
  const lang = document.documentElement.getAttribute('lang');
  let headInner = '';
  if (document.head) document.head.childNodes.forEach(c => { headInner += ser(c); });
  const docCss = adoptedCss(document.adoptedStyleSheets);
  if (docCss) headInner = '<style>' + docCss + '</style>' + headInner;
  const body = document.body ? ser(document.body) : '';
  return '<!DOCTYPE html>\n<html' + (lang ? ' lang="'+lang+'"' : '') +
         '><head>' + headInner + '</head>' + body + '</html>';
}
"""

# --- JS per html_leggibile/: rivela le tab standard (ARIA/Bootstrap) prima
# della cattura, cosi' il loro contenuto non resta nascosto nella resa finale.
# Generico e sicuro: agisce solo sui pannelli tab riconoscibili.
JS_REVEAL_GENERIC = r"""
() => {
  function dq(sel){const a=[];(function w(r){try{r.querySelectorAll(sel).forEach(e=>a.push(e));}catch(e){}
    r.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)w(e.shadowRoot);});})(document);return a;}
  function show(el){ try{
    const cs = el.ownerDocument.defaultView.getComputedStyle(el);
    if (cs){
      if (cs.display==='none') el.style.setProperty('display','block','important');
      if (cs.visibility==='hidden') el.style.setProperty('visibility','visible','important');
      if (parseFloat(cs.opacity)===0) el.style.setProperty('opacity','1','important');
    }
    if (el.hasAttribute && el.hasAttribute('hidden')) el.removeAttribute('hidden');
    if (el.getAttribute && el.getAttribute('aria-hidden')==='true') el.setAttribute('aria-hidden','false');
  }catch(e){} }
  dq('[role=tabpanel], .tab-pane, .tab-content > *').forEach(show);
  dq('[role=tab][aria-controls], [data-toggle="tab"], [data-bs-toggle="tab"], [data-toggle="pill"]').forEach(t => {
    let id = t.getAttribute('aria-controls');
    if (!id){ const h = t.getAttribute('href')||''; if (h.startsWith('#')) id = h.slice(1); }
    if (id){ try{ const root=t.getRootNode(); const p=(root.getElementById?root.getElementById(id):document.getElementById(id)); if(p) show(p); }catch(e){} }
  });
  return true;
}
"""


# ------------------------------------------------------------------------
# Mappatura URL -> percorso file in stile WebCopy
# ------------------------------------------------------------------------
def _san_component(comp: str) -> str:
    """
    Ripulisce un singolo segmento di percorso per renderlo valido su Windows:
    - nessun nome puo' terminare con spazio o punto;
    - nessun nome puo' essere composto solo da spazi (es. da %20 nell'URL);
    - i caratteri illegali (< > : " | ? *) diventano '_'.
    Restituisce "" se dopo la pulizia il segmento e' vuoto (va scartato).
    """
    comp = re.sub(r'[<>:"|?*]', "_", comp)
    comp = comp.strip().rstrip(". ")
    return comp


def url_to_relpath(url: str) -> str:
    """
    Converte un URL nel percorso file relativo (dentro www.dominio/),
    seguendo la logica WebCopy:
      https://dominio/                 -> index.htm
      https://dominio/pagina/          -> pagina/index.htm
      https://dominio/sez/sub/         -> sez/sub/index.htm
      https://dominio/file.pdf         -> file.pdf
      https://dominio/a/b/file.pdf     -> a/b/file.pdf
    I segmenti vuoti o non validi su Windows (es. da %20 = spazio) vengono
    ripuliti/scartati per evitare percorsi impossibili da creare.
    """
    p = urlparse(url)
    path = unquote(p.path or "/")
    # PDF (o file con estensione esplicita): mantieni nome file
    last = path.rstrip("/").split("/")[-1]
    is_file = "." in last and not path.endswith("/")
    comps = [_san_component(c) for c in path.split("/")]
    comps = [c for c in comps if c]  # scarta segmenti vuoti/whitespace-only
    if not comps:
        return "index.htm"
    if is_file:
        return "/".join(comps)
    return "/".join(comps) + "/index.htm"


def rel_link(from_relpath: str, to_relpath: str) -> str:
    """Percorso relativo da una pagina (file) verso un'altra risorsa (file)."""
    from_dir = os.path.dirname(from_relpath)
    rel = os.path.relpath(to_relpath, from_dir if from_dir else ".")
    return rel.replace(os.sep, "/")


def absolutize_css_urls(css_text: str, css_base: str) -> str:
    """Rende assolute le url(...) e @import dentro un CSS scaricato, cosi'
    font/immagini di sfondo caricano anche fuori dalla pagina originale."""
    def repl(m):
        raw = m.group(1).strip().strip("'\"")
        if raw.startswith(("data:", "http://", "https://", "//")):
            return f"url({raw})"
        return f"url({urljoin(css_base, raw)})"
    css_text = re.sub(r"url\(([^)]+)\)", repl, css_text)

    def imp(m):
        raw = m.group(1).strip().strip("'\"")
        return f'@import "{urljoin(css_base, raw)}"'
    return re.sub(r'@import\s+["\']([^"\']+)["\']', imp, css_text)


def embed_page_css(soup, page_url: str, context, css_cache: dict):
    """Incorpora nella pagina i CSS esterni (<link rel=stylesheet>) e rende
    assolute le URL di CSS/style inline/immagini, cosi' html_leggibile/ resta
    leggibile con lo stile originale anche aperto da un'altra cartella.
    css_cache evita di riscaricare lo stesso foglio condiviso per ogni pagina."""
    for link in soup.find_all("link", rel=lambda v: v and "stylesheet" in v):
        href = link.get("href")
        if not href:
            link.decompose()
            continue
        abs_href = urljoin(page_url, href)
        css = css_cache.get(abs_href)
        if css is None:
            try:
                r = context.request.get(abs_href, timeout=30000)
                css = r.text() if r.ok else ""
            except Exception:  # noqa: BLE001
                css = ""
            css = absolutize_css_urls(css, abs_href) if css else ""
            css_cache[abs_href] = css
        if css:
            style = soup.new_tag("style")
            style.string = css
            link.replace_with(style)
        else:
            link["href"] = abs_href

    for st in soup.find_all("style"):
        if st.string:
            st.string.replace_with(absolutize_css_urls(st.string, page_url))

    for el in soup.find_all(style=True):
        stv = el.get("style", "")
        if "url(" in stv:
            el["style"] = absolutize_css_urls(stv, page_url)

    for tag, attr in [("img", "src"), ("img", "data-src"), ("source", "src"),
                      ("video", "poster"), ("use", "href"), ("use", "xlink:href")]:
        for el in soup.find_all(tag):
            v = el.get(attr)
            if v and not v.startswith(("data:", "http://", "https://", "//")):
                el[attr] = urljoin(page_url, v)
    for el in soup.find_all(attrs={"srcset": True}):
        parts = []
        for piece in el["srcset"].split(","):
            piece = piece.strip()
            if not piece:
                continue
            bits = piece.split()
            bits[0] = urljoin(page_url, bits[0]) if not bits[0].startswith(("data:", "http", "//")) else bits[0]
            parts.append(" ".join(bits))
        el["srcset"] = ", ".join(parts)

    return soup


# Parametri di query di puro tracking/cache: NON cambiano il contenuto della
# pagina, ma generano URL diversi -> duplicati. Vanno rimossi per non contare
# piu' volte la stessa pagina (e non sprecare il budget --max sui doppioni).
# NB: i parametri che veicolano contenuto reale (es. c__contentId, CodiceISIN__c)
# NON sono in questa lista, quindi vengono conservati.
TRACKING_PARAMS = {"nocache", "_gl", "gclid", "fbclid", "_ga", "msclkid",
                   "mc_cid", "mc_eid", "yclid", "igshid", "_hsenc", "_hsmi"}


def canonicalize(url: str) -> str:
    """Rimuove i parametri di query di puro tracking/cache (nocache, _gl,
    gclid, utm_*, ...) mantenendo quelli che identificano contenuti reali."""
    p = urlparse(url)
    if not p.query:
        return url
    kept = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
            if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")]
    return urlunparse(p._replace(query=urlencode(kept)))


def same_site(url: str, root_netloc: str, include_sub: bool) -> bool:
    netloc = urlparse(url).netloc.lower()
    root = root_netloc.lower()
    if netloc == root:
        return True
    if include_sub:
        base = ".".join(root.split(".")[-2:])
        return netloc.endswith("." + base) or netloc == base
    return netloc.replace("www.", "") == root.replace("www.", "")


def clean_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE))


def extract_pdf_text(path: str) -> str:
    try:
        from pdfminer.high_level import extract_text
    except ImportError:
        return "[pdfminer.six non installato: testo PDF non estratto]"
    try:
        return extract_text(path) or ""
    except Exception as e:  # noqa: BLE001
        return f"[errore estrazione PDF: {e}]"


def slug_txt(url: str) -> str:
    p = urlparse(url)
    path = (p.path or "/").strip("/") or "index"
    # includi la query nel nome file: le pagine che differiscono solo per query
    # (es. scheda-prodotto?CodiceISIN__c=..., news?c__contentId=...) hanno cosi'
    # nomi file distinti e riconoscibili, invece di doppioni _1, _2, ...
    base = f"{path}_{p.query}" if p.query else path
    return re.sub(r"[^A-Za-z0-9._-]+", "_", base)[:150]


# ------------------------------------------------------------------------
# Crawl + salvataggio stile WebCopy
# ------------------------------------------------------------------------
def run(start_urls, out_dir, max_pages, delay, include_sub,
        follow_links=True, grab_pdf=True, dump_html=False):
    root_netloc = urlparse(start_urls[0]).netloc
    site_root = os.path.join(out_dir, root_netloc)
    dir_testi = os.path.join(out_dir, "testi")
    dir_leggibile = os.path.join(out_dir, "html_leggibile")
    os.makedirs(site_root, exist_ok=True)
    os.makedirs(dir_testi, exist_ok=True)
    os.makedirs(dir_leggibile, exist_ok=True)

    seen = set()
    queue = deque()
    for u in start_urls:
        u = canonicalize(urldefrag(u)[0])
        if u not in seen:
            seen.add(u)
            queue.append(u)

    origin_entries = []   # (uri, relpath, content_type)
    rows = []
    all_text_parts = []
    pdf_seen = set()
    pages_done = 0
    warnings_log = []   # righe [XXX SKIP]/errori raccolte per _errori.log

    def warn(msg: str):
        print(msg)
        warnings_log.append(msg)

    # Prima passata: scopri tutte le pagine e i PDF, salva HTML grezzo
    # (la riscrittura dei link la facciamo a fine crawl, quando conosciamo
    #  tutti i percorsi di destinazione)
    page_html = {}        # url -> html renderizzato
    page_relpath = {}     # url -> relpath
    pdf_relpath = {}      # pdf_url -> relpath
    leggibile_soup = {}   # url -> soup per html_leggibile/ (stile+Shadow DOM incorporati)
    css_cache = {}        # url foglio di stile -> testo CSS gia' assolutizzato

    with sync_playwright() as pw:
        # --- launch: headless di default, ma --headful e' molto piu' affidabile
        #     contro i siti che bloccano i bot (come questo) ---
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-features=IsolateOrigins,site-per-process",
            "--lang=it-IT",
        ]
        browser = pw.chromium.launch(headless=HEADLESS, args=launch_args)
        context = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"),
            locale="it-IT",
            timezone_id="Europe/Rome",
            viewport={"width": 1366, "height": 900},
            device_scale_factor=1,
            extra_http_headers={"Accept-Language": "it-IT,it;q=0.9,en;q=0.8"},
        )
        # nasconde i marcatori tipici dell'automazione (navigator.webdriver, ecc.)
        context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};"
            "Object.defineProperty(navigator,'languages',{get:()=>['it-IT','it','en']});"
            "Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});"
            "Object.defineProperty(navigator,'platform',{get:()=>'Win32'});"
            "window.__botUser=false;"
        )
        page = context.new_page()

        def save_pdf(absu, only_if_pdf=False):
            """Scarica un PDF ed estrae il testo. only_if_pdf=True per gli endpoint
            di download senza estensione: scarica solo se il content-type e' PDF."""
            if absu in pdf_seen:
                return
            try:
                pr = context.request.get(absu, timeout=60000)
            except Exception as e:  # noqa: BLE001
                warn(f"    [PDF SKIP] {absu}  ({e})")
                return
            ctype = (pr.headers or {}).get("content-type", "").lower()
            if only_if_pdf and "pdf" not in ctype:
                return  # non e' un PDF (immagine o altro media): ignora
            pdf_seen.add(absu)
            rp = url_to_relpath(absu)
            if not rp.lower().endswith(".pdf"):
                # endpoint senza estensione -> forza un nome file .pdf sensato
                rp = "documenti_scaricati/" + slug_txt(absu) + ".pdf"
            dest = os.path.join(site_root, rp)
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as pf:
                    pf.write(pr.body())
            except Exception as e:  # noqa: BLE001
                warn(f"    [PDF SKIP] {absu}  ({e})")
                return
            pdf_relpath[absu] = rp
            origin_entries.append((absu, rp, "application/pdf"))
            ptxt = extract_pdf_text(dest)
            pwords = count_words(ptxt)
            ptxt_path = os.path.join(dir_testi, "PDF_" + slug_txt(absu) + ".txt")
            n = 1
            while os.path.exists(ptxt_path):
                ptxt_path = os.path.join(dir_testi, "PDF_" + slug_txt(absu) + f"_{n}.txt"); n += 1
            with open(ptxt_path, "w", encoding="utf-8") as pf:
                pf.write(f"PDF: {absu}\n{'='*70}\n{ptxt}\n")
            rows.append({"tipo": "pdf", "url": absu, "parole": pwords,
                         "caratteri": len(ptxt),
                         "file": os.path.relpath(ptxt_path, out_dir)})
            all_text_parts.append(f"\n\n{'#'*70}\n# [PDF] {absu}\n{'#'*70}\n{ptxt}")
            print(f"    [PDF] {absu}  ({pwords} parole)")

        first_page_diag = True
        while queue and pages_done < max_pages:
            url = queue.popleft()
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:  # noqa: BLE001
                warn(f"  [SKIP] {url}  ({e})")
                continue

            # --- attendi che il contenuto JS sia EFFETTIVAMENTE renderizzato ---
            # Il sito (framework APS/Alkemy) popola <aps-app> dopo aver scaricato
            # i bundle JS e i dati. Il contenuto arriva tramite il service worker,
            # quindi NON va bloccato. Attendiamo con margine ampio.
            try:
                page.wait_for_load_state("networkidle", timeout=40000)
            except Exception:  # noqa: BLE001
                pass

            # --- gestisci i popup che bloccano il contenuto ---
            # 1) Gate "Operatore sanitario" (obbligatorio sui siti di dispositivi
            #    medici): finche' non si conferma, il contenuto resta oscurato.
            #    Attendi qualche istante che il modale compaia, poi confermalo.
            try:
                page.wait_for_selector("text=operatore sanitario", timeout=6000)
            except Exception:  # noqa: BLE001
                pass
            for sel in ["text=SI, sono un operatore sanitario",
                        "text=SÌ, sono un operatore sanitario",
                        "button:has-text('sono un operatore sanitario')",
                        "text=sono un operatore sanitario"]:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.click(timeout=3000)
                        page.wait_for_timeout(1000)
                        break
                except Exception:  # noqa: BLE001
                    pass

            # 2) banner cookie (puo' coprire/ritardare il contenuto)
            for sel in ["text=ACCETTA", "text=Accetta tutti", "text=Accetta",
                        "button:has-text('ACCETTA')", "[aria-label*='cookie']"]:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.click(timeout=2000)
                        page.wait_for_timeout(500)
                        break
                except Exception:  # noqa: BLE001
                    pass

            # attendi che il contenuto reale compaia (attraversando lo Shadow DOM)
            try:
                page.wait_for_function(
                    "() => {"
                    " function walk(n,o){ if(!n)return;"
                    "  if(n.nodeType===3){const t=n.textContent.trim(); if(t)o.push(t); return;}"
                    "  if(n.nodeType!==1)return;"
                    "  const g=n.tagName.toLowerCase(); if(g==='script'||g==='style')return;"
                    "  if(n.shadowRoot)n.shadowRoot.childNodes.forEach(c=>walk(c,o));"
                    "  n.childNodes.forEach(c=>walk(c,o)); }"
                    " const o=[]; walk(document.body,o); return o.join(' ').trim().length>250; }",
                    timeout=45000,
                )
            except Exception:  # noqa: BLE001
                pass

            # scroll per innescare il lazy-loading di sezioni/immagini
            try:
                for _ in range(8):
                    page.mouse.wheel(0, 1500)
                    page.wait_for_timeout(400)
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(800)
            except Exception:  # noqa: BLE001
                pass

            # rivela le tab standard (ARIA/Bootstrap) prima della cattura, per
            # html_leggibile/: altrimenti il loro contenuto resta nascosto
            try:
                page.evaluate(JS_REVEAL_GENERIC)
            except Exception:  # noqa: BLE001
                pass

            page.wait_for_timeout(int(delay * 1000))
            html = page.content()
            # testo e HTML presi attraversando lo Shadow DOM (il framework APS
            # nasconde i contenuti nei shadow root: innerText normale = vuoto)
            try:
                live_text = page.evaluate(JS_DEEP_TEXT)
            except Exception:  # noqa: BLE001
                live_text = ""
            try:
                live_html = page.evaluate(JS_DEEP_HTML)
            except Exception:  # noqa: BLE001
                live_html = ""
            # HTML per html_leggibile/: Shadow DOM come <template shadowrootmode>
            # e CSS "adottati" incorporati, per una resa fedele allo stile originale
            try:
                flat_html = page.evaluate(JS_FLATTEN)
            except Exception:  # noqa: BLE001
                flat_html = ""
            pages_done += 1

            # --- dump dell'HTML renderizzato (opzione --dump-html) ---
            # utile per riprocessare le pagine (es. estrarre gli attributi
            # data-* dei documenti) senza doverle ri-scaricare.
            if dump_html:
                dir_raw = os.path.join(out_dir, "_raw_html")
                os.makedirs(dir_raw, exist_ok=True)
                rawp = os.path.join(dir_raw, slug_txt(url) + ".html")
                m = 1
                while os.path.exists(rawp):
                    rawp = os.path.join(dir_raw, slug_txt(url) + f"_{m}.html"); m += 1
                try:
                    with open(rawp, "w", encoding="utf-8") as rf:
                        rf.write(f"<!-- URL: {url} -->\n" + (live_html or html))
                except Exception:  # noqa: BLE001
                    pass

            # --- DIAGNOSTICA sulla prima pagina ---
            if first_page_diag:
                first_page_diag = False
                visible_len = len((live_text or "").strip())
                shot = os.path.join(out_dir, "_diagnostica_prima_pagina.png")
                try:
                    page.screenshot(path=shot, full_page=True)
                except Exception:  # noqa: BLE001
                    shot = "(screenshot non riuscito)"
                print("-" * 60)
                print(f"DIAGNOSTICA prima pagina: {url}")
                print(f"  caratteri di testo estratti: {visible_len}")
                print(f"  screenshot salvato in: {shot}")
                if 0 <= visible_len < 250:
                    warn(f"  ATTENZIONE: {url} sembra ancora vuota ({visible_len} caratteri).")
                    print("  -> Manda lo screenshot e questo output per la verifica.")
                else:
                    print("  OK: contenuto estratto correttamente.")
                print("-" * 60)

            relpath = url_to_relpath(url)
            # Inietta nell'HTML grezzo il contenuto estratto dallo Shadow DOM,
            # cosi' anche il mirror stile WebCopy contiene il testo visibile
            # (altrimenti il body resterebbe vuoto come con Cyotek).
            html_to_save = html
            if live_html and len(live_html) > 200:
                marker = "<!--CONTENUTO-RENDERIZZATO-->"
                injected = (f"\n{marker}\n<div id='aps-rendered-content'>"
                            f"{live_html}</div>\n")
                if "</body>" in html_to_save:
                    html_to_save = html_to_save.replace("</body>", injected + "</body>", 1)
                else:
                    html_to_save = html_to_save + injected
            page_html[url] = html_to_save
            page_relpath[url] = relpath
            origin_entries.append((url, relpath, "text/html"))

            # testo pulito + conteggio (usa il DOM vivo come fonte affidabile)
            text = clean_text_from_html(html)
            if len(text) < len((live_text or "").strip()):
                # il testo dal DOM vivo e' piu' completo: usalo
                lines = [ln.strip() for ln in (live_text or "").splitlines()]
                text = "\n".join(ln for ln in lines if ln)
            words = count_words(text)
            tpath = os.path.join(dir_testi, slug_txt(url) + ".txt")
            n = 1
            while os.path.exists(tpath):
                tpath = os.path.join(dir_testi, slug_txt(url) + f"_{n}.txt"); n += 1
            with open(tpath, "w", encoding="utf-8") as f:
                f.write(f"URL: {url}\n{'='*70}\n{text}\n")
            rows.append({"tipo": "pagina", "url": url, "parole": words,
                         "caratteri": len(text), "file": os.path.relpath(tpath, out_dir)})
            all_text_parts.append(f"\n\n{'#'*70}\n# {url}\n{'#'*70}\n{text}")

            print(f"[{pages_done}/{max_pages}] {url}  ({words} parole)")

            # html_leggibile/: copia stilizzata e navigabile della pagina (Shadow
            # DOM incorporato, CSS incorporati). Passo silenzioso e a se stante
            # (scarica dal vivo i fogli di stile esterni: non deve ritardare la
            # riga di avanzamento sopra, che e' il segnale osservato dalla UI).
            # La scrittura su file avviene nella seconda passata, insieme alla
            # riscrittura dei link, con lo stesso relpath usato per il mirror.
            source_html = flat_html if flat_html and len(flat_html) > 200 else (
                "<body>" + (live_html or "") + "</body>" if live_html and len(live_html) > 200 else html)
            try:
                leggibile_soup[url] = embed_page_css(
                    BeautifulSoup(source_html, "lxml"), url, context, css_cache)
            except Exception as e:  # noqa: BLE001
                warn(f"  [LEGGIBILE SKIP] {url}  ({e})")

            # raccogli link. Saltato solo se NON si segue nulla e NON si scaricano
            # PDF (in --no-follow senza --grab-pdf si tiene solo la pagina resa).
            if not (follow_links or grab_pdf):
                continue
            try:
                hrefs = page.eval_on_selector_all(
                    "a[href]", "els => els.map(e => e.getAttribute('href'))")
            except Exception:  # noqa: BLE001
                hrefs = []

            for href in hrefs:
                if not href:
                    continue
                absu = canonicalize(urldefrag(urljoin(url, href))[0])
                low = absu.lower()

                # PDF con estensione esplicita: rispetta --no-pdf come gli altri
                if low.endswith(".pdf"):
                    if grab_pdf:
                        save_pdf(absu)
                    continue
                # endpoint di download senza estensione (KIID/prospetti serviti
                # da /cms/delivery/media/ o /docs/getdoc/): solo con --grab-pdf,
                # e solo se il content-type risulta davvero un PDF
                if grab_pdf and ("/cms/delivery/media/" in low or "/docs/getdoc/" in low):
                    save_pdf(absu, only_if_pdf=True)
                    continue

                # da qui in poi si tratta di pagine: in --no-follow non si accodano
                if not follow_links:
                    continue

                # pagine interne
                if absu in seen:
                    continue
                if not same_site(absu, root_netloc, include_sub):
                    continue
                if re.search(r"\.(jpg|jpeg|png|webp|gif|svg|css|js|ico|zip|"
                             r"mp4|webm|woff2?|ttf|eot)(\?|$)", low):
                    continue
                if any(x in low for x in ("mailto:", "tel:", "javascript:")):
                    continue
                seen.add(absu)
                queue.append(absu)

        browser.close()

    # ---- seconda passata: riscrivi i link interni in relativo e salva .htm ----
    # mappa url->relpath per pagine e pdf scaricati
    target_map = {}
    target_map.update(page_relpath)
    target_map.update(pdf_relpath)
    # versioni normalizzate (con/senza slash finale) per il matching
    norm_map = {}
    for u, rp in target_map.items():
        norm_map[u.rstrip("/")] = rp

    for url, html in page_html.items():
        try:
            relpath = page_relpath[url]
            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True):
                absu = urldefrag(urljoin(url, a["href"]))[0]
                key = absu.rstrip("/")
                if key in norm_map:
                    a["href"] = rel_link(relpath, norm_map[key])
                # altrimenti lascia il link assoluto (come WebCopy con risorse non scaricate)
            dest = os.path.join(site_root, relpath)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(str(soup))
        except Exception as e:  # noqa: BLE001
            # una singola pagina problematica non deve abortire tutto l'export:
            # i riepiloghi finali (TESTI_COMPLETI/conteggio) vanno comunque scritti.
            warn(f"  [MIRROR SKIP] {url}  ({e})")

    # ---- stessa riscrittura link, per html_leggibile/ (stessa struttura del mirror) ----
    indice_entries = []   # (titolo, relpath), per _indice.html
    for url, leg_soup in leggibile_soup.items():
        try:
            relpath = page_relpath[url]
            for a in leg_soup.find_all("a", href=True):
                absu = urldefrag(urljoin(url, a["href"]))[0]
                key = absu.rstrip("/")
                if key in norm_map:
                    a["href"] = rel_link(relpath, norm_map[key])
            dest = os.path.join(dir_leggibile, relpath)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(str(leg_soup))
            title = (leg_soup.title.string if leg_soup.title and leg_soup.title.string else None)
            indice_entries.append(((title or url).strip(), relpath))
        except Exception as e:  # noqa: BLE001
            warn(f"  [LEGGIBILE SKIP] {url}  ({e})")

    # ---- _indice.html: elenco cliccabile di tutte le pagine, cosi' nessuna
    # resta raggiungibile solo se gia' linkata dal menu del sito originale ----
    if indice_entries:
        righe = "\n".join(
            f'<li><a href="{relpath}">{titolo}</a></li>'
            for titolo, relpath in sorted(indice_entries, key=lambda t: t[1]))
        indice_html = f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<title>Indice — {root_netloc}</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:760px;
 margin:32px auto;padding:0 20px;line-height:1.6;color:#1a1a1a}}
 li{{margin:4px 0}}
</style></head><body>
<h1>Indice delle pagine — {root_netloc}</h1>
<p>{len(indice_entries)} pagine navigabili.</p>
<ul>
{righe}
</ul>
</body></html>"""
        with open(os.path.join(dir_leggibile, "_indice.html"), "w", encoding="utf-8") as f:
            f.write(indice_html)

    # ---- webcopy-origin.txt ----
    origin_path = os.path.join(site_root, "webcopy-origin.txt")
    win_root = "C:\\Downloaded Web Sites\\" + root_netloc
    with open(origin_path, "w", encoding="utf-8", newline="") as f:
        for uri, rp, ctype in origin_entries:
            win_path = win_root + "\\" + rp.replace("/", "\\")
            f.write(f"Uri: {uri}\r\n")
            f.write(f"File Name: {win_path}\r\n")
            f.write(f"Content Type: {ctype}\r\n")
            f.write("\r\n")

    # ---- riepiloghi testi ----
    with open(os.path.join(out_dir, "TESTI_COMPLETI.txt"), "w", encoding="utf-8") as f:
        f.write("".join(all_text_parts))
    with open(os.path.join(out_dir, "conteggio.csv"), "w",
              encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tipo", "url", "parole", "caratteri", "file"])
        w.writeheader()
        w.writerows(rows)

    # ---- _errori.log: raccolta di tutti gli avvisi/errori del crawl, per non
    # doverli ripescare a mano nel log completo del job ----
    with open(os.path.join(out_dir, "_errori.log"), "w", encoding="utf-8") as f:
        if warnings_log:
            f.write(f"{len(warnings_log)} avvisi durante questo crawl:\n\n")
            f.write("\n".join(warnings_log))
            f.write("\n")
        else:
            f.write("Nessun avviso: crawl completato senza errori rilevati.\n")

    tot_pagine = sum(r["parole"] for r in rows if r["tipo"] == "pagina")
    tot_pdf = sum(r["parole"] for r in rows if r["tipo"] == "pdf")
    print("\n" + "=" * 60)
    print(f"FATTO. Struttura WebCopy in: {os.path.abspath(site_root)}")
    print(f"Pagine: {sum(1 for r in rows if r['tipo']=='pagina')}  "
          f"PDF: {sum(1 for r in rows if r['tipo']=='pdf')}")
    print(f"PAROLE TOTALI (pagine+PDF): {tot_pagine + tot_pdf}")
    print(f"Testi per conteggio in: {os.path.abspath(dir_testi)}")
    print(f"HTML leggibile (per i PM) in: {os.path.abspath(dir_leggibile)}")
    if warnings_log:
        print(f"AVVISI: {len(warnings_log)} durante questo crawl, vedi _errori.log")
    print("=" * 60)


def main():
    global HEADLESS
    ap = argparse.ArgumentParser(
        description="Mirror sito in stile Cyotek WebCopy ma con JS eseguito (pagine con testi reali).")
    ap.add_argument("urls", nargs="*", help="URL iniziale/i (es. https://www.bemaritalia.it/)")
    ap.add_argument("--out", default="output", help="cartella di output (default: output)")
    ap.add_argument("--max", type=int, default=300, help="max pagine (default: 300)")
    ap.add_argument("--delay", type=float, default=1.0, help="pausa per pagina in secondi (default: 1.0)")
    ap.add_argument("--include-subdomains", action="store_true", help="segui anche i sottodomini")
    ap.add_argument("--urls-file", help="file di testo con un URL per riga da aggiungere alla lista di partenza "
                                        "(utile per scaricare tante pagine specifiche, es. schede prodotto)")
    ap.add_argument("--no-follow", action="store_true",
                    help="NON inseguire i link trovati: scarica solo gli URL indicati (con urls/--urls-file)")
    ap.add_argument("--no-pdf", action="store_true",
                    help="NON scaricare i PDF collegati (di default vengono scaricati ed estratti, "
                         "inclusi i documenti serviti come download da /cms/delivery/media e /docs/getdoc)")
    ap.add_argument("--dump-html", action="store_true",
                    help="salva l'HTML renderizzato di ogni pagina in _raw_html/ (per riprocessarle poi)")
    ap.add_argument("--headful", action="store_true",
                    help="apri una finestra browser visibile: molto piu' efficace contro i siti "
                         "che bloccano i bot (consigliato se le pagine escono vuote)")
    args = ap.parse_args()

    urls = list(args.urls)
    if args.urls_file:
        with open(args.urls_file, encoding="utf-8") as f:
            urls.extend(ln.strip() for ln in f if ln.strip() and not ln.startswith("#"))
    if not urls:
        ap.error("nessun URL fornito: indicane almeno uno come argomento o con --urls-file")

    HEADLESS = not args.headful
    if args.headful:
        print(">> Modalita' HEADFUL: si aprira' una finestra browser. Non chiuderla durante il lavoro.")
    run(urls, args.out, args.max, args.delay, args.include_subdomains,
        follow_links=not args.no_follow, grab_pdf=not args.no_pdf, dump_html=args.dump_html)


if __name__ == "__main__":
    main()
