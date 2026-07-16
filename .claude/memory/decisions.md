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

## ADR-007 — Decisioni di dettaglio per il backend reale di M1

Data: 15/07/2026.
Decisione: collisione sul nome di `folder` risolta con suffisso incrementale (`_2`, `_3`,
...) invece di rifiutare la richiesta, per restare fedeli alla forma del contratto (il
nome cartella resta quello scelto dall'utente, solo reso univoco); pulizia TTL delle
cartelle di output inclusa gia' in M1 (non rimandata a M3), ma limitata alle sole cartelle
gia' archiviate con successo sulla share (vedi ADR-008), per non cancellare mai l'unica
copia di un risultato; lo scheletro `frontend_esempio/index.html` aggiornato solo nelle
chiamate API (endpoint, nomi campo, `EventSource` al posto del polling) senza toccare
grafica/stile, che resta compito di M2.
Motivazione: sono i tre punti dove il contratto lasciava un grado di liberta' non coperto
esplicitamente da `API_CONTRACT.md`/roadmap; le scelte sono state fatte con l'utente prima
di scrivere il codice.

## ADR-008 — Archivio dei crawl completati su share di rete, non solo su /srv

Data: 15/07/2026.
Decisione: il backend continua a far scrivere il crawl a `scarica_sito_webcopy.py` in
locale su `/srv/output` (staging, invariato da ADR-005/006); a fine job, se il crawl e'
riuscito, una copia bulk (`shutil.copytree`) sposta l'intera cartella su una share SMB
esterna montata in CIFS su `/mnt/downloaded-websites` (UNC
`\\192.168.20.177\utili(new)\downloaded-websites`, credenziali in
`/etc/samba/creds`, utente dedicato `webanalyst`). Un marcatore `.archiviato` nella
cartella locale segnala che la copia e' andata a buon fine; la pulizia TTL (ADR-007) non
tocca mai una cartella priva del marcatore, indipendentemente dall'eta'. `/result` e
`/download` leggono sempre e solo da `/srv/output`, mai dalla share.
Motivazione, scartata l'alternativa di far scrivere il crawler direttamente sulla share:
Playwright produce centinaia di scritture piccole e sincrone per pagina (mirror, HTML
leggibile, testo estratto), e legarle alla latenza/disponibilita' di un host Windows
esterno per tutta la durata del crawl avrebbe reso l'intero job fragile a un intoppo di
rete; la copia finale e' invece un singolo trasferimento bulk, molto piu' tollerante.
Follow-up aperto: il mount usa `uid=intrawelt,gid=intrawelt` perche' e' l'utente con cui
gira il backend in questa fase di sviluppo; quando M3 creera' l'utente di servizio dedicato
`estrattore` (gia' previsto in `backend_esempio/estrattore.service`), la riga in
`/etc/fstab` andra' riallineata a quello (vedi `deployment.md`).
