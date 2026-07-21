# API Contract - Website Analyst

Contratto tra frontend (3 stati) e backend crawler. Reimplementa ciò che nel prototipo
è simulato da `startDownload` / `buildResult`. Base path suggerito: `/api`.

## 1. Avvio job
`POST /api/jobs`

Request (JSON):
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
Note: `delay_sec` arriva dalla UI con virgola decimale ("1,0") → convertire in float.
Validare `url` (http/https, host risolvibile, no IP privati se non consentito),
`max_pages` 1..300, `folder` sanitizzato (no `/`, `..`).

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
`total_pages` può aggiornarsi durante il crawl (scoperta link). `log` alimenta la console
scura. In alternativa a SSE: polling `GET /api/jobs/{job_id}` che ritorna lo stesso stato.

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

Nota di correzione (15/07/2026, M1): lo schema sopra e' l'esempio illustrativo originale
del brief, ma non corrisponde ai nomi reali prodotti da `scarica_sito_webcopy.py` (vedi
`STACK.md`). L'implementazione di `/result` cammina la cartella di output effettiva e vi
si trovano invece: `www.<dominio>/` (mirror con `webcopy-origin.txt`), `testi/`,
`html_leggibile/`, `TESTI_COMPLETI.txt`, `conteggio.csv`, opzionale `_raw_html/`. Non
esistono `_report.json`, `sitemap.txt` ne' una cartella `pdf/` separata (i PDF finiscono
nel mirror, nel loro percorso originale). La forma del JSON (`type`/`path`/`depth`/`bytes`/
`children`) resta quella qui sopra; sono solo i nomi di file/cartella reali a differire
dall'esempio.

## 4. Download ZIP
`GET /api/jobs/{job_id}/download`  → `application/zip`

Header: `Content-Disposition: attachment; filename="{folder}.zip"`.
Lo zip contiene la cartella `{folder}/` con tutti i file. Il frontend punta il link/bottone
"Scarica {folder}.zip" a questo endpoint (o crea un `<a download>` verso di esso).

## Comportamento crawler (backend)
- Coda dei link interni allo stesso host, dedup, rispetto di `robots.txt`.
- `delay_sec` di attesa tra le richieste; stop a `max_pages`.
- Estrazione testo: rimuovere nav/script/style, salvare testo leggibile + metadati.
- `headful=true`: browser reale via Playwright sotto `xvfb` (siti anti-bot); altrimenti
  fetch HTTP semplice.
- `pdf=true`: scaricare i file `.pdf` linkati nella cartella `pdf/`.
- Pulizia job/zip vecchi (TTL) per non riempire il disco della VM.
