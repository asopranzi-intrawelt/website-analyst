#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mappa_sito.py
====================================================================
Fase di ricognizione: mappa un sito PRIMA di scaricarlo con
scarica_sito_webcopy.py, senza salvarne il contenuto. Produce un
manifesto JSON dell'albero del sito con una classificazione per
ciascuna risorsa (pagina istituzionale, articolo, archivio generato
dal CMS come tag/categoria/autore/paginazione, PDF, dominio esterno),
cosi' che un frontend possa presentare l'albero e lasciare scegliere
il perimetro da scaricare davvero, invece di scaricare tutto e
scartare a valle.

FONTE PRIMARIA: sitemap.xml (anche sitemap-index, ricorsiva), che
sulla maggior parte dei siti WordPress elenca gia' ogni pagina reale
con una data di ultima modifica (<lastmod>) - non serve aprire un
browser per scoprire URL e date quando la sitemap c'e' ed e' completa.

FALLBACK: solo per gli URL non coperti dalla sitemap (o quando la
sitemap manca del tutto), un giro con Chromium che segue i link,
esattamente come fa scarica_sito_webcopy.py, ma senza salvare nulla:
serve solo a scoprire URL aggiuntivi, non a classificarli (la
classificazione resta sempre basata sul pattern dell'URL, non sul
contenuto della pagina).

USO
  python mappa_sito.py https://www.sito.it/ --out manifest.json --max 40
====================================================================
"""
import argparse
import datetime
import html
import json
import os
import re
import sys
from collections import deque
from urllib.parse import urljoin, urldefrag, urlparse, unquote

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("ERRORE: manca Playwright. Esegui:\n"
             "  python -m pip install playwright beautifulsoup4 lxml pdfminer.six\n"
             "  python -m playwright install chromium")

# same_site() e' la stessa identica regola di appartenenza al sito usata dal
# crawler principale: riusata da qui, non duplicata, cosi' i due strumenti
# concordano sempre su cosa e' "dello stesso sito".
from scarica_sito_webcopy import same_site  # noqa: E402

HEADLESS = True

# --- pattern di classificazione -------------------------------------------
# Archivi generati dal CMS: quasi sempre da escludere dal perimetro di
# traduzione, ricorrenti su ogni sito WordPress. Riconosciuti dal solo URL,
# nessun bisogno di aprire la pagina.
_RE_TAG = re.compile(r"/tags?/", re.I)
_RE_CATEGORIA = re.compile(r"/(category|categorie|categoria)/", re.I)
_RE_AUTORE = re.compile(r"/(author|autori|autore)/", re.I)
_RE_PAGINAZIONE = re.compile(r"/page/\d+/?", re.I)
# Articolo: prefisso data tipico dei permalink WordPress (YYYY/MM/DD/slug o
# YYYY/MM/slug), riscontrato per davvero sui dati reali (bergamofiera.it).
_RE_DATA_ARTICOLO = re.compile(r"^/\d{4}/\d{2}(?:/\d{2})?/")


def classify(url: str, root_netloc: str, include_sub: bool, in_sitemap: bool) -> str:
    """Classifica un URL solo in base al suo pattern (mai al contenuto della
    pagina): 'pdf', 'esterno', 'archivio_tag', 'archivio_categoria',
    'archivio_autore', 'archivio_paginazione', 'articolo', 'istituzionale',
    'da_rivedere'. Euristica, non certezza: quando nessun pattern combacia,
    la presenza nella sitemap (un segnale deliberato del sito, "questa e'
    una pagina reale") fa propendere per 'istituzionale'; l'assenza dalla
    sitemap (scoperta solo seguendo i link, un segnale piu' debole) fa
    propendere per 'da_rivedere' - cosi' l'utente decide esplicitamente,
    invece di rischiare di includere per errore cio' che l'euristica non
    ha saputo riconoscere. Il PDF si controlla PRIMA dell'appartenenza al
    sito (non dopo, a differenza di tutte le altre classificazioni): il
    crawler vero (scarica_sito_webcopy.py, save_pdf()) scarica un PDF con
    estensione esplicita indipendentemente dal dominio che lo ospita - un
    pattern comune per i siti che tengono gli allegati su un sottodominio
    dedicato (es. file.<dominio>, riscontrato per davvero su un sito
    reale). Il manifesto deve rispecchiare questo comportamento, non
    nasconderlo dietro 'esterno' facendo perdere di vista un PDF che il
    crawl scaricherebbe comunque."""
    path = unquote(urlparse(url).path or "/").lower()
    if path.endswith(".pdf"):
        return "pdf"
    if not same_site(url, root_netloc, include_sub):
        return "esterno"
    if _RE_TAG.search(path):
        return "archivio_tag"
    if _RE_CATEGORIA.search(path):
        return "archivio_categoria"
    if _RE_AUTORE.search(path):
        return "archivio_autore"
    if _RE_PAGINAZIONE.search(path):
        return "archivio_paginazione"
    if _RE_DATA_ARTICOLO.search(path):
        return "articolo"
    return "istituzionale" if in_sitemap else "da_rivedere"


# --- sitemap.xml, ricorsiva, con lastmod per URL ----------------------------
def get_sitemap_entries(ctx, root_base: str) -> dict:
    """Legge la/le sitemap in modo ricorsivo (gestisce anche i sitemap-index).
    Restituisce {url: lastmod_o_None}. A differenza di un semplice elenco di
    <loc>, qui si estrae anche <lastmod> per ciascun URL (assente nell'
    esplorazione originale di cui questo script riprende l'impostazione),
    perche' e' la fonte piu' economica della data richiesta per gli articoli:
    non serve aprire la pagina per saperla."""
    entries, seen_sm = {}, set()
    to_fetch = [root_base + "/sitemap.xml", root_base + "/sitemap_index.xml"]
    try:
        rb = ctx.request.get(root_base + "/robots.txt", timeout=15000)
        if rb.ok:
            to_fetch += re.findall(r"(?im)^\s*sitemap:\s*(\S+)", rb.text())
    except Exception:  # noqa: BLE001
        pass
    while to_fetch:
        sm = to_fetch.pop()
        if sm in seen_sm:
            continue
        seen_sm.add(sm)
        try:
            r = ctx.request.get(sm, timeout=20000)
            if not r.ok:
                continue
            txt = r.text()
        except Exception:  # noqa: BLE001
            continue
        if "<sitemapindex" in txt.lower():
            to_fetch.extend(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", txt))
            continue
        for block in re.findall(r"<url>(.*?)</url>", txt, re.S):
            m_loc = re.search(r"<loc>\s*([^<\s]+)\s*</loc>", block)
            if not m_loc:
                continue
            m_lastmod = re.search(r"<lastmod>\s*([^<\s]+)\s*</lastmod>", block)
            entries[m_loc.group(1)] = m_lastmod.group(1) if m_lastmod else None
    return entries


def build_albero(nodes: list, root_label: str) -> list:
    """Trasforma l'elenco piatto di risorse (una per URL) nella stessa forma
    (type/path/depth/children) gia' prodotta da _build_tree() nel backend
    per l'albero post-download: l'algoritmo di alberizzazione gia' scritto
    lato frontend (buildNestedTree) si riusa cosi' senza modifiche anche
    qui, prima ancora che un solo file sia stato scaricato. A differenza di
    _build_tree() (che cammina un filesystem reale, dove un percorso e' o
    una cartella o un file, mai entrambi), qui un segmento di URL PUO'
    essere contemporaneamente una risorsa vera (es. l'archivio /2016/) e un
    genitore di altre risorse (es. /2016/04/...): e' esattamente il caso
    che un tentativo precedente, esterno a questo progetto, non sapeva
    rappresentare, perdendo le pagine-archivio dall'albero. Qui entrambi i
    fatti vengono emessi esplicitamente, sullo stesso 'path'."""
    root: dict = {}
    for n in nodes:
        path = unquote(urlparse(n["url"]).path or "/").strip("/")
        segs = [s for s in path.split("/") if s] or ["index"]
        cur = root
        for seg in segs[:-1]:
            cur = cur.setdefault(seg, {}).setdefault("__children__", {})
        cur.setdefault(segs[-1], {})["__nodo__"] = n

    entries = [{"type": "dir", "path": root_label, "depth": 0, "children": len(root)}]

    def walk(subtree: dict, prefix: str, depth: int):
        for seg in sorted(subtree):
            item = subtree[seg]
            path = f"{prefix}/{seg}"
            nodo = item.get("__nodo__")
            children = item.get("__children__")
            if nodo is not None:
                entries.append({"type": "risorsa", "path": path, "depth": depth,
                                 "url": nodo["url"], "tipo": nodo["tipo"], "data": nodo["data"]})
            if children:
                entries.append({"type": "dir", "path": path, "depth": depth,
                                 "children": len(children)})
                walk(children, path, depth + 1)

    walk(root, root_label, 1)
    return entries


_RE_HREF_PDF = re.compile(r'href=["\']([^"\']+\.pdf(?:[?#][^"\']*)?)["\']', re.I)


def scan_pdf_links(ctx, known: dict) -> int:
    """Scansione leggera (una richiesta HTTP semplice per pagina, MAI un
    rendering Chromium) dell'HTML grezzo di ogni pagina gia' nota dalla
    sitemap, alla ricerca di link a PDF. Necessaria perche' le sitemap
    WordPress (anche quella nativa, come verificato su un sito reale)
    escludono per default gli allegati: senza questo passo la quasi
    totalita' dei PDF di un sito resterebbe invisibile alla ricognizione,
    pur restando MOLTO piu' economica di un rendering completo per pagina
    (nessuna esecuzione JS, nessuna attesa di networkidle). Nessun filtro
    di appartenenza al sito qui: un PDF va raccolto da qualunque dominio
    lo ospiti (stesso motivo per cui classify() lo riconosce prima del
    controllo same_site, vedi il suo commento), la classificazione decide
    poi come mostrarlo."""
    pagine = [u for u in list(known) if not u.lower().endswith(".pdf")]
    trovati = 0
    for i, url in enumerate(pagine, 1):
        try:
            r = ctx.request.get(url, timeout=20000)
            if not r.ok:
                continue
            pagina_html = r.text()
        except Exception:  # noqa: BLE001
            continue
        for href in _RE_HREF_PDF.findall(pagina_html):
            # html.unescape: l'href grezzo puo' contenere entita' HTML (es.
            # "&amp;" per un "&" letterale nel nome file); senza decodificarle,
            # il ";" di "&amp;" viene scambiato da urlparse() per il separatore
            # dei parametri di percorso legacy, troncando l'URL (verificato su
            # un PDF reale il cui percorso veniva tagliato prima dell'estensione).
            absu = urldefrag(urljoin(url, html.unescape(href)))[0]
            if absu.startswith(("http://", "https://")) and absu not in known:
                known[absu] = None
                trovati += 1
        if i % 100 == 0:
            print(f"  scansione PDF: {i}/{len(pagine)} pagine, {trovati} PDF trovati finora")
    return trovati


def render(page, url, delay):
    """Stessa gestione popup/scroll gia' collaudata in scarica_sito_webcopy.py
    e nel precedente explorer_sito.py: qui serve solo a far comparire i link
    reali della pagina, non a estrarne il contenuto."""
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:  # noqa: BLE001
        pass
    for txt in ["sono un operatore sanitario", "SI, sono un operatore sanitario"]:
        try:
            el = page.query_selector(f"text={txt}")
            if el and el.is_visible():
                el.click(timeout=3000)
                page.wait_for_timeout(800)
                break
        except Exception:  # noqa: BLE001
            pass
    for txt in ["ACCETTA", "Accetta tutti", "Accept all", "OK"]:
        try:
            el = page.query_selector(f"text={txt}")
            if el and el.is_visible():
                el.click(timeout=2000)
                page.wait_for_timeout(300)
                break
        except Exception:  # noqa: BLE001
            pass
    try:
        for _ in range(6):
            page.mouse.wheel(0, 1600)
            page.wait_for_timeout(300)
        page.evaluate("window.scrollTo(0,0)")
    except Exception:  # noqa: BLE001
        pass
    page.wait_for_timeout(int(delay * 1000))


ASSET_EXT = re.compile(r"\.(jpg|jpeg|png|webp|gif|svg|css|js|ico|zip|"
                        r"mp4|webm|woff2?|ttf|eot)(\?|$)", re.I)


def esplora(start_url, out_path, max_pages, delay, include_sub):
    p0 = urlparse(start_url)
    root_netloc, root_base = p0.netloc, f"{p0.scheme}://{p0.netloc}"
    start = urldefrag(start_url)[0]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=HEADLESS, args=[
            "--no-sandbox", "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled", "--lang=it-IT"])
        ctx = browser.new_context(
            locale="it-IT", viewport={"width": 1366, "height": 900},
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"))

        # --- fonte primaria: sitemap.xml -----------------------------------
        sitemap_entries = get_sitemap_entries(ctx, root_base)
        known = {}   # url -> lastmod (None se non nota)
        for u, lastmod in sitemap_entries.items():
            u = urldefrag(u)[0]
            if same_site(u, root_netloc, include_sub) and not ASSET_EXT.search(u.lower()):
                known[u] = lastmod
        known.setdefault(start, None)
        print(f"Sitemap: {len(sitemap_entries)} URL trovati, {len(known)} pertinenti al sito"
              if sitemap_entries else "Sitemap: assente o vuota -> ci si affida solo ai link")

        # --- scansione leggera per i PDF che la sitemap non elenca ---------
        if known:
            n_pdf = scan_pdf_links(ctx, known)
            print(f"Scansione PDF (via HTTP, senza Chromium): {n_pdf} PDF trovati "
                  f"su {len(known)} pagine note dalla sitemap")

        # --- fallback: segui i link per scoprire cio' che la sitemap non ---
        # elenca. Le pagine gia' note dalla sitemap NON vengono ri-aperte con
        # Chromium (la classificazione resta sempre solo su pattern URL,
        # renderle non aggiungerebbe informazione, solo tempo), tranne la
        # homepage: viene sempre resa una volta, sitemap o no, per
        # intercettare pagine di menu importanti che il sito potrebbe non
        # elencare in sitemap. Se la sitemap e' assente/vuota, questo giro
        # diventa la scoperta primaria, esattamente come nel vecchio
        # explorer_sito.py, delimitata da --max.
        rendered = set()
        queue = deque([start])
        page = ctx.new_page()
        done = 0
        while queue and done < max_pages:
            url = queue.popleft()
            if url in rendered:
                continue
            rendered.add(url)
            try:
                render(page, url, delay)
            except Exception as e:  # noqa: BLE001
                print(f"  [SKIP] {url} ({e})")
                continue
            done += 1
            known.setdefault(url, None)
            try:
                hrefs = page.eval_on_selector_all("a[href]", "els=>els.map(e=>e.getAttribute('href'))")
            except Exception:  # noqa: BLE001
                hrefs = []
            new_found = 0
            for h in hrefs:
                if not h:
                    continue
                absu = urldefrag(urljoin(url, h))[0]
                if not absu.startswith(("http://", "https://")):
                    continue
                if ASSET_EXT.search(absu.lower()):
                    continue
                if any(x in absu.lower() for x in ("mailto:", "tel:", "javascript:")):
                    continue
                if not same_site(absu, root_netloc, include_sub):
                    known.setdefault(absu, None)  # dominio esterno: registrato, mai renderizzato
                    continue
                if absu in known:
                    continue  # gia' nota (da sitemap o gia' scoperta): non riaccodare
                known.setdefault(absu, None)
                if absu not in rendered:
                    queue.append(absu)
                    new_found += 1
            print(f"[{done}] {url}  (nuovi link scoperti: {new_found})")
        browser.close()

    # --- classificazione + costruzione dell'albero (stessa forma piatta
    # path/depth/type gia' usata da _build_tree() nel backend) -------------
    nodes = []
    for url in sorted(known):
        tipo = classify(url, root_netloc, include_sub, in_sitemap=url in sitemap_entries)
        data = None
        if tipo == "articolo":
            lastmod = known.get(url)
            if lastmod:
                data = lastmod[:10]  # YYYY-MM-DD, tronca l'eventuale orario/timezone
            else:
                m = _RE_DATA_ARTICOLO.search(unquote(urlparse(url).path or ""))
                if m:
                    data = m.group(0).strip("/").replace("/", "-")
        nodes.append({"url": url, "tipo": tipo, "data": data})

    manifest = {
        "sito": start_url,
        "generato": datetime.datetime.now().isoformat(timespec="seconds"),
        "sitemap_url_trovati": len(sitemap_entries),
        "n_risorse": len(nodes),
        "risorse": nodes,                            # elenco piatto: per valutare regole di selezione
        "albero": build_albero(nodes, root_netloc),   # gerarchico: per la vista ad albero del frontend
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    conteggio_tipi = {}
    for n in nodes:
        conteggio_tipi[n["tipo"]] = conteggio_tipi.get(n["tipo"], 0) + 1
    print("\n" + "=" * 60)
    print(f"MANIFESTO salvato in: {os.path.abspath(out_path)}")
    print(f"Risorse totali: {len(nodes)}")
    for tipo, n in sorted(conteggio_tipi.items()):
        print(f"  {tipo}: {n}")
    print("=" * 60)


def main():
    ap = argparse.ArgumentParser(
        description="Mappa un sito e produce un manifesto JSON classificato (ricognizione, senza scaricare nulla).")
    ap.add_argument("url", help="URL iniziale (es. https://www.sito.it/)")
    ap.add_argument("--out", default="manifest.json", help="file JSON di output (default: manifest.json)")
    ap.add_argument("--max", type=int, default=60,
                    help="max pagine rese con Chromium per il fallback di scoperta (default: 60); "
                         "non limita le risorse gia' trovate in sitemap")
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--include-subdomains", action="store_true")
    args = ap.parse_args()
    esplora(args.url, args.out, args.max, args.delay, args.include_subdomains)


if __name__ == "__main__":
    main()
