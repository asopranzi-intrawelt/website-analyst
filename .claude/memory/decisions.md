# Decisioni architetturali (ADR-lite)

## ADR-001 — Il backend lancia il crawler come sottoprocesso

Data: dal design brief originale (preesistente all'allineamento).
Decisione: `backend_esempio/app.py` deve invocare `scarica_sito_webcopy.py` come
sottoprocesso (`python scarica_sito_webcopy.py <url> --out <dir> ...`), mai reimplementarne
la logica di crawling/estrazione.
Motivazione: lo script CLI e' gia' funzionante e testato; duplicarne la logica nel backend
introdurrebbe deriva tra le due implementazioni.

## ADR-002 — Frontend fedele 1:1 al prototipo hi-fi

Decisione: riprodurre esattamente i design token (`colors_and_type.css`, font Altro
Grotesk/Serif) e il comportamento dei tre stati visti in
`frontend_esempio/design/Website Analyst.dc.html`, ricreando il markup con CSS normale
invece di copiare le utility inline del runtime del design tool.
Motivazione: il prototipo e' gia' stato validato come riferimento visivo/comportamentale
dall'utente; l'obiettivo e' l'implementazione fedele, non una nuova proposta di design.

## ADR-003 — Solo Docling per l'OCR, non l'intero stack Crawl4AI

Decisione: dello stack Crawl4AI+Docling valutato in
`_notes/handoff-vm207-sizing-crawl4ai-docling.md` per un progetto diverso (RAG su
documentazione tecnica), integrare in questo progetto **solo** un fallback OCR via
Docling per i PDF scansionati che oggi escono vuoti da `pdfminer`.
Motivazione: Crawl4AI/Qdrant/MCP risolvono un caso d'uso diverso (Markdown fedele per
RAG); questo tool punta al conteggio del volume di testo e perderebbe la gestione custom
di Shadow DOM/cataloghi JavaScript se sostituito.

## ADR-004 — Esposizione solo LAN

Decisione: il servizio non va mai esposto direttamente su Internet; solo sulla rete
192.168.20.0/19, eventualmente dietro reverse proxy + autenticazione se in futuro serve
accesso remoto.
Motivazione: nessuna necessita' di accesso esterno per il caso d'uso attuale (stima volume
testi di siti aziendali); riduce superficie di attacco (SSRF verso rete interna, crawling
arbitrario esposto pubblicamente).
