---
generated-from-commit: babb092e15a27bf1eb672c25c84930de6a8308d5
generated-from-branch: main
generated-date: 2026-07-13
covers-paths:
  - scarica_sito_webcopy.py
  - requirements.txt
  - backend_esempio/**
  - frontend_esempio/**
  - API_CONTRACT.md
last-verified-commit: b31cdad
---

# Stack applicativo

> Popolato leggendo il codice e i documenti di handoff presenti nel progetto al momento dell'allineamento al template (13/07/2026), non inventato.

## Stack e runtime

Crawler CLI (`scarica_sito_webcopy.py`, gia' funzionante): Python 3.10+, Playwright (Chromium headless, esegue JavaScript), BeautifulSoup4, lxml, pdfminer.six per l'estrazione testo dai PDF. Dipendenze in `requirements.txt`.

Backend pianificato (`backend_esempio/app.py`, scheletro): FastAPI + Uvicorn, servizio systemd di produzione in `backend_esempio/estrattore.service`. Il contratto di tutti gli endpoint (avvio job, avanzamento SSE, riepilogo, download zip) e' specificato in `API_CONTRACT.md`.

Frontend pianificato (`frontend_esempio/index.html`, scheletro): pagina statica servita dallo stesso FastAPI, deve riprodurre 1:1 il prototipo hi-fi in `frontend_esempio/design/Website Analyst.dc.html`, riusando i design token in `frontend_esempio/design/colors_and_type.css` e i font proprietari Altro Grotesk/Altro Serif in `frontend_esempio/design/fonts/`. Vincolo di stile del brief: niente trattino lungo (usare " - "), nessuna emoji.

Deploy: VM Proxmox 207 "websiteAnalyst" (Ubuntu 24.04 LTS, 6 vCPU, 16 GB RAM), esposizione solo LAN.

## Alternative deliberatamente escluse

Reimplementare la logica di crawling dentro il backend FastAPI: il brief impone di lanciare `scarica_sito_webcopy.py` come sottoprocesso e non duplicarne la logica.

Adottare l'intero stack Crawl4AI + Docling (crawling + OCR + Qdrant/MCP) descritto in `_notes/handoff-vm207-sizing-crawl4ai-docling.md`: quello e' un progetto diverso ("sito -> Markdown/RAG" per documentazione tecnica), non il conteggio testi di questo strumento. L'unico travaso di valore da quello stack e' Docling per l'OCR dei PDF scansionati, come upgrade puntuale futuro (vedi roadmap.md).

Reinventare lo stile del frontend: il design brief impone fedelta' 1:1 ai token del prototipo hi-fi, niente palette o layout alternativi.

## Flussi di codice e ruolo architetturale dei file

`scarica_sito_webcopy.py` e' un crawler a file singolo (stdlib + Playwright/bs4/pdfminer): apre le pagine con Chromium headless, estrae testo pulito, segue i link interni, scarica i PDF collegati. Output per run: `testi/` (un .txt per risorsa), `TESTI_COMPLETI.txt`, `conteggio.csv`, mirror `www.dominio/`, opzionale `_raw_html/`. `html_leggibile/` (dal 23/07/2026) e' una copia stilizzata e navigabile di ogni pagina, non piu' testo minimale: Shadow DOM incorporato come `<template shadowrootmode="open">`, CSS esterni e `adoptedStyleSheets` incorporati, tab ARIA/Bootstrap rivelate prima della cattura, link interni riscritti in relativo con la stessa logica gia' usata per il mirror (stessa struttura a cartelle annidate, non piu' file piatti per slug). Dal 22/09/2026 (branch `feat/selezione-perimetro`) supporta anche `--pdf-urls-file` (parametro `extra_pdf_urls` su `run()`): a differenza di `--urls-file`, che tratta ogni riga come una pagina da aprire con `page.goto()`, ogni riga di questo file passa direttamente a `save_pdf()`, perche' un URL iniziale non passava mai da li' (solo i link scoperti dentro una pagina ci passavano). Serve a includere PDF specifici in un crawl vincolato a `--urls-file --no-follow`, dove altrimenti non sarebbero mai scoperti seguendo i link.

`mappa_sito.py` (dal 22/09/2026, branch `feat/selezione-perimetro`) e' lo script di ricognizione: mappa un sito SENZA scaricarne il contenuto, prima che parta un crawl vero con `scarica_sito_webcopy.py`. Fonte primaria sitemap.xml/sitemap-index (ricorsiva, con `<lastmod>` per URL) e una scansione HTTP leggera (mai Chromium) per i PDF collegati alle pagine note, che le sitemap escludono per default; rendering Chromium riservato al solo fallback di scoperta per URL non coperti da sitemap - il controllo "e' gia' coperto dalla sitemap" usa `_canon()` (netloc senza www., path senza barra finale) invece della stringa URL esatta, altrimenti un link interno scritto con uno scheme/www/barra diversi da quelli della sitemap risulterebbe "nuovo" e verrebbe ri-renderizzato con Chromium per ogni variante (riscontrato per davvero su un sito reale: 159 render di fallback per un numero di pagine reali molto minore, vedi `progress.md`). Classifica ogni risorsa per pattern URL (pdf / esterno / archivio_tag / archivio_categoria / archivio_autore / archivio_paginazione / articolo / istituzionale / da_rivedere) e produce un manifesto JSON sia in forma piatta (`risorse`, per valutare regole di selezione) sia gerarchica (`albero`, stessa forma path/depth/type di `_build_tree()` nel backend, pronta per `buildNestedTree()` lato frontend). Riusa `same_site()` da `scarica_sito_webcopy.py` via import, non la duplica.

`backend_esempio/app.py` e' il punto di partenza per un endpoint `POST /api/jobs` che avvia il crawler come sottoprocesso, traccia i job (id/stato/log/cartella output) ed espone `GET /api/jobs/{id}/events` (SSE), `GET /api/jobs/{id}/result` e `GET /api/jobs/{id}/download` secondo `API_CONTRACT.md`. Dal 22/09/2026 (branch `feat/selezione-perimetro`) espone anche `POST /api/scans` + `GET .../events` + `GET .../manifest` + `POST .../cancel`, che lanciano `mappa_sito.py` come sottoprocesso sullo stesso pattern; crawl e ricognizioni condividono la stessa coda a un job alla volta (`_JOB_QUEUE`, ogni elemento taggato `("job"|"scan", id)`), perche' entrambi aprono un Chromium. Sempre dal 22/09/2026, `POST /api/jobs` accetta un campo opzionale `selection` (modello `SelectionRule`: `scan_id`, `tipi_inclusi`, `data_da`/`data_a`, `esclusioni`): `_resolve_selection()` valuta le regole contro il manifesto di una ricognizione gia' completata (non un elenco letterale di URL, cosi' restano valide anche se il sito cambia nel frattempo) e restituisce due elenchi di URL distinti (pagine, PDF), scritti su due file temporanei e passati a `scarica_sito_webcopy.py` come `--urls-file`/`--pdf-urls-file` insieme a `--no-follow --no-pdf`, al posto dell'invocazione aperta `<url> --max N`. Vedi `API_CONTRACT.md` §1 per il contratto completo e per il motivo per cui `--no-pdf` e' obbligatorio anche quando la selezione include PDF.

`frontend_esempio/index.html` e' la pagina unica a stati (`showStep()`), dal 22/09/2026 (branch `feat/selezione-perimetro`) sei invece di tre: `form -> scan -> select -> loading -> done -> error`. Dal form si sceglie fra "Avvia download" (crawl aperto, comportamento di sempre) e "Analizza la struttura prima di scaricare" (avvia una ricognizione via `/api/scans`, stesso pattern SSE gia' usato per i job di crawl, generalizzato in `followEvents(kind, id)`/`cancelCurrent()`/`cancelBeacon()` cosi' da condividere codice fra le due famiglie invece di duplicarlo). Lo step `select` mostra l'albero del manifesto (`manifest.albero`, riusa `buildNestedTree()` gia' scritta per il riepilogo post-crawl) con una checkbox a tre stati per nodo: un tipo entra nella regola solo se almeno una sua risorsa e' spuntata, le risorse dello stesso tipo rimaste non spuntate diventano esclusioni puntuali (`computeSelectionRule()`), un intervallo di date si applica solo alle risorse `articolo` disabilitandone la checkbox quando sono fuori intervallo (la loro spunta non potrebbe comunque avere effetto, il backend le esclude a prescindere, vedi `_resolve_selection()` in `app.py`). `evaluateRule()` ricalcola lato client, con la stessa logica di `_resolve_selection()`, l'anteprima di pagine/PDF risultanti (riepilogo numerico sotto l'albero) - solo un'anteprima, la valutazione autorevole resta quella del backend all'avvio del job. Salvataggio/caricamento selezione: la regola (non un elenco di URL) si scarica/ricarica come JSON via `Blob`/`<input type="file">`, nessuna persistenza lato server. La submit della selezione riusa `startJob()`, la stessa funzione del crawl aperto, passandole il campo `selection`.

`guida/Guida_estrazione_testi_sito.md` documenta l'uso della CLI per un operatore umano, indipendente dal frontend.

## Riferimenti a snippet

`scarica_sito_webcopy.py` (CLI completa) · `backend_esempio/app.py` (scheletro FastAPI) · `backend_esempio/estrattore.service` (unit systemd) · `frontend_esempio/index.html` (scheletro pagina) · `API_CONTRACT.md` (contratto endpoint) · `frontend_esempio/design/colors_and_type.css` (design token).
