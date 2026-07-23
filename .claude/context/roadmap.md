---
generated-from-commit: babb092e15a27bf1eb672c25c84930de6a8308d5
generated-from-branch: main
generated-date: 2026-07-13
covers-paths:
  - backend_esempio/**
  - frontend_esempio/**
last-verified-commit: babb092e15a27bf1eb672c25c84930de6a8308d5
---

# Roadmap

## M1 — Backend reale

Implementare `POST /api/jobs`, `GET /api/jobs/{id}/events` (SSE), `GET /api/jobs/{id}/result`,
`GET /api/jobs/{id}/download` secondo `API_CONTRACT.md`, lanciando
`scarica_sito_webcopy.py` come sottoprocesso (mai reimplementarne la logica).

## M2 — Frontend fedele al prototipo

Rifinire `frontend_esempio/index.html` per riprodurre 1:1 `frontend_esempio/design/Website
Analyst.dc.html`, riusando `colors_and_type.css` e i font in `design/fonts/`.

## M3 — Servizio di produzione (completato 23/07/2026)

Istanziare `backend_esempio/estrattore.service`, montare il disco dati (96G) su `/srv`,
bind LAN-only. Fatto: utente dedicato `estrattore` (`useradd -r -s /usr/sbin/nologin -G
intrawelt estrattore`, membro supplementare del gruppo `intrawelt` per ereditare i permessi
gia' presenti su home/Scrivania/repo senza allargarli ad "altri"); `chmod g+rx` su
`/home/intrawelt/.cache` (necessario per raggiungere `ms-playwright/`, altrimenti bloccato
dal 700 della home) e `chmod g+w` su `/srv/output`; riga fstab della share CIFS
riallineata da `uid=intrawelt,gid=intrawelt` a `uid=estrattore,gid=estrattore` (ADR-008);
`estrattore.service` con `ARCHIVE_BASE` e `PLAYWRIGHT_BROWSERS_PATH` espliciti, installato
in `/etc/systemd/system/`, abilitato e attivo. Verificato con un crawl reale end-to-end
contro il servizio vero (porta 8000): archiviazione sulla share confermata scritta
dall'utente `estrattore`, log applicativo visibile in `journalctl -u estrattore`. Bind LAN
raggiungibile anche come `http://website-analyst.local:8000/` (Avahi/mDNS, gia' installato
di default su questa VM: solo configurato l'hostname annunciato).

## M4 — OCR per PDF scansionati (opzionale)

Unico upgrade con valore reale ereditato dallo stack Crawl4AI/Docling valutato per un
progetto diverso (vedi `_notes/handoff-vm207-sizing-crawl4ai-docling.md`): quando
`extract_pdf_text()` restituisce ~0 parole su un PDF con pagine, fallback su Docling
(IBM, OCR Tesseract/EasyOCR/RapidOCR integrato), come funzione locale o come servizio
`docling-serve` chiamato dal backend. Non adottare il resto dello stack (Crawl4AI,
Qdrant, MCP): serve al caso d'uso RAG, non al conteggio testi di questo tool.
