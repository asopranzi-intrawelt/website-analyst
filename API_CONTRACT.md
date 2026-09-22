# API Contract - Website Analyst

Contratto tra frontend (sei stati: form, scan, select, loading, done, error — vedi §5 per scan/select, aggiunti dal 22/09/2026) e backend crawler. Reimplementa ciò che nel prototipo è simulato da `startDownload` / `buildResult`. Base path suggerito: `/api`.

## 1. Avvio job
`POST /api/jobs`

Request (JSON), crawl aperto (comportamento di sempre):
```json
{
  "url": "https://www.sito.it/",
  "folder": "output",
  "max_pages": 300,
  "delay_sec": 1.0,
  "pdf": true,
  "headful": false
}
```
Note: `delay_sec` arriva dalla UI con virgola decimale ("1,0") → convertire in float. Validare `url` (http/https, host risolvibile, no IP privati se non consentito), `max_pages` 1..2000, `folder` sanitizzato (no `/`, `..`).

Request (JSON), crawl vincolato a una selezione (dal 22/09/2026, branch `feat/selezione-perimetro`): campo opzionale `selection`, alternativo a `max_pages`/`pdf` che in questo caso vengono ignorati.
```json
{
  "url": "https://www.sito.it/",
  "folder": "output",
  "delay_sec": 1.0,
  "headful": false,
  "selection": {
    "scan_id": "a1b2c3",
    "tipi_inclusi": ["istituzionale", "articolo", "pdf"],
    "data_da": "2026-01-01",
    "data_a": null,
    "esclusioni": ["https://www.sito.it/tag/foo/"]
  }
}
```
`scan_id` deve riferirsi a una ricognizione gia' completata (`GET /api/scans/{scan_id}/manifest` con `200`); `400` se non trovata o non ancora completata. Le regole si valutano contro il manifesto di quella ricognizione, non contro un elenco letterale di URL, cosi' restano interpretabili anche se il sito cambia tra la ricognizione e il crawl. `tipi_inclusi` e' uno o piu' tra le categorie di `mappa_sito.py` (`istituzionale`, `articolo`, `pdf`, `archivio_tag`, `archivio_categoria`, `archivio_autore`, `archivio_paginazione`, `esterno`, `da_rivedere`). `data_da`/`data_a` (`YYYY-MM-DD`) filtrano solo le risorse di tipo `articolo`; una risorsa `articolo` senza data nota viene esclusa se e' impostato un intervallo, perche' non e' verificabile. `esclusioni` toglie puntualmente degli URL anche se il loro tipo sarebbe incluso. Il backend valuta le regole (`_resolve_selection`), produce due file temporanei (`--urls-file` per le pagine, il nuovo `--pdf-urls-file` per i PDF, vedi `STACK.md`) e lancia `scarica_sito_webcopy.py` con `--no-follow --no-pdf` invece che con `<url> --max N`: `--no-pdf` e' obbligatorio anche quando la selezione include PDF, perche' altrimenti il crawler scaricherebbe comunque ogni PDF collegato dalle pagine selezionate, indipendentemente dalla selezione. `400` se la selezione valutata non produce nessuna risorsa, o se le pagine risultanti superano `MAX_PAGES_LIMIT`.

Response `202`:
```json
{ "job_id": "a1b2c3", "status": "running" }
```
Errori: `400` `{ "error": "url non valido" }`.

## 2. Avanzamento in tempo reale (consigliato: SSE)
`GET /api/jobs/{job_id}/events`  → `text/event-stream`

Ogni evento è JSON. Tipi:
```
event: progress
data: { "current_page": 3, "total_pages": 12, "percent": 25, "log": "[3/12] estraggo /servizi (1,0s)" }

event: progress
data: { "log": "scrittura file su disco …" }

event: done
data: { "job_id": "a1b2c3" }      // il client poi chiama GET /result

event: error
data: { "message": "timeout sul sito" }
```
`total_pages` può aggiornarsi durante il crawl (scoperta link). `log` alimenta la console scura. In alternativa a SSE: polling `GET /api/jobs/{job_id}` che ritorna lo stesso stato.

## 3. Riepilogo risultato
`GET /api/jobs/{job_id}/result`

Response `200`:
```json
{
  "host": "sito.it",
  "folder": "output",
  "stats": { "pages": 8, "pdfs": 3, "total_files": 13, "total_bytes": 1887436 },
  "tree": [
    { "type": "dir",  "path": "output",           "depth": 0, "bytes": null },
    { "type": "file", "path": "_report.json",      "depth": 1, "bytes": 218 },
    { "type": "file", "path": "sitemap.txt",       "depth": 1, "bytes": 281 },
    { "type": "dir",  "path": "testi",             "depth": 1, "children": 8 },
    { "type": "file", "path": "0001-home.txt",     "depth": 2, "bytes": 342 },
    { "type": "dir",  "path": "pdf",               "depth": 1, "children": 3 },
    { "type": "file", "path": "brochure.pdf",      "depth": 2, "bytes": 148213 }
  ]
}
```
Il frontend disegna l'albero ASCII da `tree` (usa `type`/`depth` per `├─ └─ │`, mostra
`bytes` formattati a destra, e collassa le liste lunghe in "… +N file"). `total_bytes`
va formattato B/KB/MB lato client.

Struttura cartella prodotta dal backend (deve combaciare con l'albero):
```
{folder}/
  _report.json          # parametri job + esito
  sitemap.txt           # elenco URL crawlate
  testi/
    0001-<slug>.txt      # un file per pagina: URL, titolo, n. parole, testo estratto
    0002-<slug>.txt
    …
  pdf/                   # solo se pdf=true e sono stati trovati PDF
    <nome>.pdf
```

Nota di correzione (15/07/2026, M1): lo schema sopra e' l'esempio illustrativo originale del brief, ma non corrisponde ai nomi reali prodotti da `scarica_sito_webcopy.py` (vedi `STACK.md`). L'implementazione di `/result` cammina la cartella di output effettiva e vi si trovano invece: `www.<dominio>/` (mirror con `webcopy-origin.txt`), `testi/`, `html_leggibile/`, `TESTI_COMPLETI.txt`, `conteggio.csv`, opzionale `_raw_html/`. Non esistono `_report.json`, `sitemap.txt` ne' una cartella `pdf/` separata (i PDF finiscono nel mirror, nel loro percorso originale). La forma del JSON (`type`/`path`/`depth`/`bytes`/ `children`) resta quella qui sopra; sono solo i nomi di file/cartella reali a differire dall'esempio.

## 4. Download ZIP
`GET /api/jobs/{job_id}/download`  → `application/zip`

Header: `Content-Disposition: attachment; filename="{folder}.zip"`. Lo zip contiene la cartella `{folder}/` con tutti i file. Il frontend punta il link/bottone "Scarica {folder}.zip" a questo endpoint (o crea un `<a download>` verso di esso).

## 5. Ricognizione (prima del download)

Dal 22/09/2026 (branch `feat/selezione-perimetro`): mappa un sito senza scaricarne il contenuto, per lasciare scegliere il perimetro prima del crawl vero e proprio. Stessa famiglia di quattro endpoint di `/api/jobs`, sotto `/api/scans`, con lo stesso pattern di validazione/SSE/cancel; lancia `mappa_sito.py` come sottoprocesso invece di `scarica_sito_webcopy.py`. Condivide la stessa coda a un job alla volta dei crawl: una ricognizione avviata mentre un crawl e' in corso (o viceversa) resta in coda finche' non tocca a lei, perche' entrambi aprono un Chromium.

### 5.1 Avvio ricognizione
`POST /api/scans`

Request:
```json
{ "url": "https://www.sito.it/", "max_pages": 60 }
```
`max_pages` (1..2000, stesso tetto di `/api/jobs`) limita solo le pagine rese con Chromium nel fallback di scoperta (per gli URL non coperti dalla sitemap), non le risorse gia' trovate in sitemap, che non hanno limite.

Response `202`: `{ "scan_id": "a1b2c3", "status": "running" }`. Stessa validazione URL di `POST /api/jobs` (SSRF, schema http/https).

### 5.2 Avanzamento
`GET /api/scans/{scan_id}/events` → `text/event-stream`, stesso schema di `/api/jobs/{id}/events`. Le righe di avanzamento reali di `mappa_sito.py` sono `[N] url (...)` (un solo numero, non N/max: a differenza del crawl, il totale non e' noto in anticipo durante la scoperta), quindi l'evento `progress` porta `pagina_corrente` invece di `current_page`/`total_pages`/`percent`. Eventi `done`/`error`/`cancelled` identici.

### 5.3 Manifesto
`GET /api/scans/{scan_id}/manifest` → `200` con il JSON prodotto da `mappa_sito.py` (vedi il suo stesso file per la forma: `risorse` elenco piatto, `albero` gerarchico nella stessa forma `type`/`path`/`depth`/`children` di `/api/jobs/{id}/result`). `409` se la ricognizione non e' ancora completata.

### 5.4 Interruzione
`POST /api/scans/{scan_id}/cancel`, stesso comportamento di `/api/jobs/{id}/cancel`: funziona sia su una ricognizione in coda (non parte mai) sia su una in corso (processo terminato via `killpg`).

## Comportamento crawler (backend)
- Coda dei link interni allo stesso host, dedup, rispetto di `robots.txt`.
- `delay_sec` di attesa tra le richieste; stop a `max_pages`.
- Estrazione testo: rimuovere nav/script/style, salvare testo leggibile + metadati.
- `headful=true`: browser reale via Playwright sotto `xvfb` (siti anti-bot); altrimenti fetch HTTP semplice.
- `pdf=true`: scaricare i file `.pdf` linkati nella cartella `pdf/`.
- Pulizia job/zip vecchi (TTL) per non riempire il disco della VM.
- Coda a un job alla volta, condivisa fra `/api/jobs` e `/api/scans` (vedi §5): un solo Chromium alla volta, indipendentemente da quale delle due famiglie di endpoint lo apre.
