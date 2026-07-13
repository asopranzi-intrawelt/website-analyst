---
generated-from-commit: PENDING-FIRST-COMMIT
generated-from-branch: main
generated-date: 2026-07-13
covers-paths:
  - scarica_sito_webcopy.py
  - requirements.txt
  - backend_esempio/**
  - frontend_esempio/**
  - API_CONTRACT.md
last-verified-commit: PENDING-FIRST-COMMIT
---

# Stack applicativo

> Popolato leggendo il codice e i documenti di handoff presenti nel progetto al momento
> dell'allineamento al template (13/07/2026), non inventato.

## Stack e runtime

Crawler CLI (`scarica_sito_webcopy.py`, gia' funzionante): Python 3.10+, Playwright
(Chromium headless, esegue JavaScript), BeautifulSoup4, lxml, pdfminer.six per l'estrazione
testo dai PDF. Dipendenze in `requirements.txt`.

Backend pianificato (`backend_esempio/app.py`, scheletro): FastAPI + Uvicorn, servizio
systemd di produzione in `backend_esempio/estrattore.service`. Il contratto di tutti gli
endpoint (avvio job, avanzamento SSE, riepilogo, download zip) e' specificato in
`API_CONTRACT.md`.

Frontend pianificato (`frontend_esempio/index.html`, scheletro): pagina statica servita
dallo stesso FastAPI, deve riprodurre 1:1 il prototipo hi-fi in
`frontend_esempio/design/Website Analyst.dc.html`, riusando i design token in
`frontend_esempio/design/colors_and_type.css` e i font proprietari Altro Grotesk/Altro
Serif in `frontend_esempio/design/fonts/`. Vincolo di stile del brief: niente trattino
lungo (usare " - "), nessuna emoji.

Deploy: VM Proxmox 207 "websiteAnalyst" (Ubuntu 24.04 LTS, 6 vCPU, 16 GB RAM), esposizione
solo LAN.

## Alternative deliberatamente escluse

Reimplementare la logica di crawling dentro il backend FastAPI: il brief impone di
lanciare `scarica_sito_webcopy.py` come sottoprocesso e non duplicarne la logica.

Adottare l'intero stack Crawl4AI + Docling (crawling + OCR + Qdrant/MCP) descritto in
`_notes/handoff-vm207-sizing-crawl4ai-docling.md`: quello e' un progetto diverso ("sito
-> Markdown/RAG" per documentazione tecnica), non il conteggio testi di questo strumento.
L'unico travaso di valore da quello stack e' Docling per l'OCR dei PDF scansionati, come
upgrade puntuale futuro (vedi roadmap.md).

Reinventare lo stile del frontend: il design brief impone fedelta' 1:1 ai token del
prototipo hi-fi, niente palette o layout alternativi.

## Flussi di codice e ruolo architetturale dei file

`scarica_sito_webcopy.py` e' un crawler a file singolo (stdlib + Playwright/bs4/pdfminer):
apre le pagine con Chromium headless, estrae testo pulito, segue i link interni, scarica
i PDF collegati. Output per run: `testi/` (un .txt per risorsa), `html_leggibile/`,
`TESTI_COMPLETI.txt`, `conteggio.csv`, mirror `www.dominio/`, opzionale `_raw_html/`.

`backend_esempio/app.py` e' il punto di partenza per un endpoint `POST /api/jobs` che
avvia il crawler come sottoprocesso, traccia i job (id/stato/log/cartella output) ed
espone `GET /api/jobs/{id}/events` (SSE), `GET /api/jobs/{id}/result` e
`GET /api/jobs/{id}/download` secondo `API_CONTRACT.md`.

`frontend_esempio/index.html` e' il form + polling/SSE dei tre stati (form -> loading con
log in tempo reale -> riepilogo con albero file e download zip), da rifinire secondo il
prototipo in `frontend_esempio/design/`.

`guida/Guida_estrazione_testi_sito.md` documenta l'uso della CLI per un operatore umano,
indipendente dal frontend.

## Riferimenti a snippet

`scarica_sito_webcopy.py` (CLI completa) · `backend_esempio/app.py` (scheletro FastAPI) ·
`backend_esempio/estrattore.service` (unit systemd) · `frontend_esempio/index.html`
(scheletro pagina) · `API_CONTRACT.md` (contratto endpoint) ·
`frontend_esempio/design/colors_and_type.css` (design token).
