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

## ADR-005 — Repository sul disco di sistema, solo l'output su /srv

Data: 13/07/2026.
Decisione: il repository `website-analyst` resta in `~/Scrivania/website-analyst` sul
disco di sistema (scsi0); solo l'archivio di output dei crawl usa il disco dati montato su
`/srv` (`/srv/output/`). Non si sposta ne' si rinomina la cartella del progetto.
Motivazione: il rischio di saturazione riguarda solo l'archivio di output, che cresce senza
limite, non il codice, che pesa poche decine di KB. Spostare l'intero repository non
avrebbe risolto nulla in piu' e avrebbe introdotto un rischio di confusione tra il nome
locale della cartella e il nome del progetto/repository GitHub (`website-analyst`), che
l'utente ha esplicitamente scelto di non cambiare.

## ADR-006 — Disco dati /srv condiviso tra questo progetto e il futuro Crawl4AI/Docling

Data: 13/07/2026.
Decisione: il disco da 96G (scsi1, montato su `/srv`) e' condiviso tra due usi tramite
sottocartelle: `/srv/output/` per l'archivio di questo strumento, `/srv/crawl4ai-docling/`
riservato al progetto futuro "Sito -> Markdown -> RAG" descritto in
`_notes/handoff-vm207-sizing-crawl4ai-docling.md`, per il quale il disco era stato
originariamente dimensionato.
Motivazione: 96G e' ampiamente sufficiente per entrambi (l'archivio di solo testo di questo
strumento resta dell'ordine di pochi GB anche su siti grandi; i modelli Docling pesano
~2GB); creare un disco separato per ciascun uso non avrebbe aggiunto valore.
