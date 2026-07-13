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

## M3 — Servizio di produzione

Istanziare `backend_esempio/estrattore.service`, montare il disco dati (96G) su `/srv`,
bind LAN-only.

## M4 — OCR per PDF scansionati (opzionale)

Unico upgrade con valore reale ereditato dallo stack Crawl4AI/Docling valutato per un
progetto diverso (vedi `_notes/handoff-vm207-sizing-crawl4ai-docling.md`): quando
`extract_pdf_text()` restituisce ~0 parole su un PDF con pagine, fallback su Docling
(IBM, OCR Tesseract/EasyOCR/RapidOCR integrato), come funzione locale o come servizio
`docling-serve` chiamato dal backend. Non adottare il resto dello stack (Crawl4AI,
Qdrant, MCP): serve al caso d'uso RAG, non al conteggio testi di questo tool.
