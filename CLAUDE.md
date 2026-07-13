# CLAUDE.md — Contesto progetto per Claude Code (VM Linux)

Questo file dà a Claude Code, in esecuzione sulla VM, il contesto per (a) far girare
lo strumento di estrazione testi e (b) aiutare a sviluppare un piccolo frontend LAN
con un backend che esegue le stesse operazioni oggi lanciate da riga di comando.

## Procedura di ripresa in una sessione nuova

Leggere per primo `.claude/memory/index.md` (branch, commit di riferimento, stato
schede, punto di ripresa). Leggere poi `.claude/context/current-work.md` per la feature
attiva e le domande aperte. Le altre schede di `.claude/context/` (STACK, design-and-security,
deployment, dev-testing, roadmap) si leggono solo quando pertinenti al task. Il
materiale grezzo di handoff sotto `_notes/` (ignorato da git) si apre solo per
approfondire una decisione già riassunta nelle schede.

## 1. Cos'è questo progetto

`scarica_sito_webcopy.py` è un crawler Python che apre le pagine con Chromium
headless (Playwright), **esegue il JavaScript**, ne estrae il testo pulito, segue i
link interni, scarica i PDF collegati e ne estrae il testo. Serve a stimare il
**volume di testo** di un sito (conteggio parole per pagina/documento).

Output per ogni run (nella cartella `--out`): `testi/` (un .txt per risorsa),
`html_leggibile/`, `TESTI_COMPLETI.txt`, `conteggio.csv` (tipo,url,parole,caratteri,file),
mirror `www.dominio/`, e `_raw_html/` se `--dump-html`.

Setup e uso: vedi `README.md`. Guida funzionale: `guida/Guida_estrazione_testi_sito.md`.

## 2. La VM (Proxmox 207 "websiteAnalyst")

- Rete: IP **192.168.20.24**, netmask **255.255.224.0** (/19), gateway **192.168.20.1**. Solo LAN.
- Risorse: 16 GiB RAM, 6 vCPU (tipo host), disco sistema 32G (scsi0) + disco dati 96G (scsi1).
- Suggerimento: montare il disco dati su `/srv` e tenere qui il progetto e gli output
  (es. `/srv/estrattore-testi-sito/` e `/srv/output/`), così l'archivio crescente non
  satura il disco di sistema. Verificare che il mount sia in `/etc/fstab`.
- La VM è stata dimensionata (16GB, modelli Docling ~2GB) pensando anche a un eventuale
  stack Crawl4AI+Docling (vedi §6): per il solo strumento attuale è sovrabbondante, il che
  lascia margine se si aggiunge l'OCR.
- Accesso: alias SSH `vm207` dalle postazioni di sviluppo (chiave dedicata); questo
  repository ha remote `origin` su GitHub via alias `github-corp` configurato in locale.

## 3. Obiettivo della migrazione: frontend LAN + backend

L'utente vuole servire lo strumento in LAN: una pagina web semplice dove inserire
URL e opzioni, e un backend che esegua lo stesso lavoro della CLI e mostri
avanzamento e risultati. Il frontend verrà sviluppato qui nella VM, fedele al
prototipo hi-fi in `frontend_esempio/design/Website Analyst.dc.html` (design token in
`frontend_esempio/design/colors_and_type.css` e font in `frontend_esempio/design/fonts/`).
Il contratto degli endpoint è specificato per intero in `API_CONTRACT.md`.

### Architettura consigliata (semplice e robusta)

1. **Backend FastAPI** (`backend_esempio/app.py` è il punto di partenza):
   - un endpoint `POST /crawl` che avvia `scarica_sito_webcopy.py` come **sottoprocesso**
     (es. `python scarica_sito_webcopy.py <url> --out <dir> ...`), NON reimplementare la logica;
   - traccia i job in memoria/su file (id, stato, log, cartella output);
   - endpoint `GET /jobs/{id}` per stato/log e `GET /jobs/{id}/download` per scaricare
     un archivio zip dell'output;
   - esegue un job alla volta (o una piccola coda): ogni run apre un Chromium, quindi
     evitare troppi crawl paralleli su 6 vCPU.
2. **Frontend statico** (`frontend_esempio/index.html`): form (URL, --max, --delay,
   --headful, --no-pdf) + polling dello stato del job. Servibile dallo stesso FastAPI
   (`StaticFiles`) per non gestire due processi.
3. **Servizio systemd** per tenere il backend sempre attivo. Bind consigliato:
   `--host 192.168.20.24 --port 8000` (solo LAN) oppure `127.0.0.1` dietro reverse proxy.
4. **Headless vs headful**: di default headless. Per i siti che bloccano l'headless, il
   backend può lanciare il sottoprocesso con `xvfb-run -a` e `--headful` (installare `xvfb`).

### Sicurezza (rete interna)

- Esporre **solo in LAN** (192.168.20.0/19). Mai su internet senza reverse proxy + auth.
- Nessuna credenziale hardcoded. Validare/limitare gli URL accettati (evitare SSRF verso
  IP interni: bloccare schemi non http/https e host privati se non voluti).
- Rispettare `robots.txt` e i ToS dei siti; rate limiting ragionevole (`--delay`).
- Limitare la dimensione/tempo dei job per evitare che saturino disco/CPU.
- Vedi `.claude/context/design-and-security.md` per il dettaglio completo, incluso un
  gap di igiene trovato sul desktop della VM (file di password in chiaro, non ancora
  risolto).

## 4. Come estendere lo strumento

- È un singolo file, stdlib + Playwright/bs4/pdfminer. Mantieni lo stile: commenti in
  italiano, funzioni piccole, niente dipendenze superflue.
- Punti di estensione già presenti: `--urls-file`, `--no-follow`, `--no-pdf`, `--dump-html`,
  rimozione parametri di tracking (`canonicalize`), download PDF anche da endpoint di
  download (`save_pdf`, `/cms/delivery/media`, `/docs/getdoc`).
- Il conteggio "contenuto unico" (deduplica per hash del testo) NON è nello script: è stato
  fatto a valle in analisi. Se serve nel frontend, aggiungere una colonna `contenuto_unico`
  in `conteggio.csv` calcolando l'hash md5 del corpo di ogni `testi/*.txt`.

## 5. OCR / Docling (unico upgrade davvero utile)

Limite attuale: i PDF **scansionati** (immagini) escono vuoti perché `pdfminer` legge solo
il testo digitale. Se serve gestirli, l'integrazione sensata è **Docling** (IBM, MIT, OCR
integrato Tesseract/EasyOCR/RapidOCR):
- opzione minimale: quando `extract_pdf_text()` restituisce ~0 parole ma il PDF ha pagine,
  fare fallback su Docling per quel file;
- oppure eseguire Docling come servizio (`docling-serve`) e chiamarlo dal backend.
Questo è l'unico pezzo dello stack "Crawl4AI/Docling" (vedi §6) che colma un buco reale
di questo strumento.

## 6. Relazione con l'handoff Crawl4AI/Docling

`_notes/handoff-vm207-sizing-crawl4ai-docling.md` (spostato qui dal desktop della VM il
13/07/2026, materiale grezzo/narrativo, ignorato da git) descrive un progetto **diverso**:
"Sito → Markdown → Claude/RAG" per documentazione tecnica, basato su Crawl4AI (crawling) +
Docling (OCR) via MCP.

- Scopo diverso: quello punta a Markdown fedele + OCR + metadati per RAG; **questo**
  strumento punta al **conteggio del testo** (analisi volume) con testo pulito e mirror.
- Non sostituire questo strumento con Crawl4AI per il caso "conteggio": si perderebbe la
  gestione custom di Shadow DOM / cataloghi JavaScript (es. schede prodotto per ISIN) e
  l'output orientato al conteggio.
- L'unico travaso di valore è **Docling per l'OCR** (§5). Il resto dello stack (adaptive
  crawling, MCP, Qdrant) serve al caso RAG, non a questo.

## 7. Design handoff frontend

Il brief di design originale e l'API contract sono stati integrati qui il 13/07/2026:
`API_CONTRACT.md` (radice, contratto completo endpoint), `frontend_esempio/design/`
(prototipo hi-fi `Website Analyst.dc.html`, `colors_and_type.css`, font), e il brief
originale in `_notes/design-handoff-CLAUDE.md`/`_notes/design-handoff-README.md` per
riferimento. La definizione di "fatto" del brief è riportata in
`.claude/context/dev-testing.md`.

## 8. Comandi utili

```bash
source .venv/bin/activate
python scarica_sito_webcopy.py https://www.sito.it/ --out /srv/output/sito --max 2000
# backend di esempio:
uvicorn backend_esempio.app:app --host 192.168.20.24 --port 8000
```

## Indice dei file satellite tracciati

```
.claude/memory/index.md       snapshot e stato di verifica delle schede
.claude/memory/progress.md    work-log
.claude/memory/decisions.md   registro ADR-lite
.claude/context/STACK.md                stack e ruolo architetturale dei file
.claude/context/design-and-security.md  sicurezza applicativa
.claude/context/deployment.md           setup e avvio
.claude/context/dev-testing.md          verifica e casi limite
.claude/context/current-work.md         feature attiva e definition of done
.claude/context/roadmap.md              fasi future (M1-M4)
```

`_notes/` (ignorato da git) contiene il materiale grezzo di handoff: diario, resoconto,
i due handoff originali di sizing e design.
