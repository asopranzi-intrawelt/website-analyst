---
generated-from-commit: babb092e15a27bf1eb672c25c84930de6a8308d5
generated-from-branch: main
generated-date: 2026-07-13
covers-paths:
  - backend_esempio/**
  - frontend_esempio/**
last-verified-commit: babb092e15a27bf1eb672c25c84930de6a8308d5
---

# Verifica e casi limite

## Definizione di "fatto" (dal design brief in _notes/design-handoff-CLAUDE.md)

I tre stati del frontend funzionano end-to-end contro un backend reale, non simulato:

1. Form -> avvio job.
2. Loading con avanzamento reale (SSE) e log in tempo reale.
3. Riepilogo con statistiche, albero file e download zip funzionante dal browser.

L'albero mostrato in UI deve combaciare esattamente con la struttura reale prodotta su
disco da `scarica_sito_webcopy.py`: `www.<dominio>/`, `testi/`, `html_leggibile/`,
`TESTI_COMPLETI.txt`, `conteggio.csv`, opzionale `_raw_html/` (l'esempio in
`API_CONTRACT.md` §3 era illustrativo e non corrispondeva ai nomi reali; corretto in M1,
vedi nota nello stesso file e `STACK.md`). Lo stato di errore (crawl fallito) deve mostrare
un messaggio e un'azione "Riprova".

## Verifica di M1 (backend reale)

Eseguita il 15/07/2026 senza Playwright installato: `backend_esempio/app.py` verificato con
`fastapi.testclient.TestClient` e un finto crawler che riproduce solo la forma di output
rilevante (righe di progresso `[n/max]` su stdout, struttura reale su disco), coprendo tutti
i casi della tabella sotto piu' la copia di archiviazione sulla share reale montata in CIFS.
Verifica di un crawl vero (Playwright/Chromium) resta manuale, vedi `roadmap.md`.

## Casi limite da verificare quando il backend sara' implementato

| Caso | Comportamento atteso |
|---|---|
| `delay_sec` con virgola decimale dalla UI ("1,0") | Convertito in float lato backend |
| `max_pages` fuori range 1..300 | Errore di validazione, job non avviato |
| `url` non http/https o host privato non consentito | `400` con messaggio esplicito |
| PDF scansionato (immagine) | Testo vuoto con `pdfminer` (limite noto, vedi roadmap OCR) |
| Sito con crawl falllito/timeout | Evento `error` SSE, frontend mostra "Riprova" |
| Job concorrenti | Un job alla volta o piccola coda, non parallelismo illimitato |

## Verifica CLI (gia' funzionante, indipendente dal frontend)

```bash
python scarica_sito_webcopy.py --help
```

Vedi `guida/Guida_estrazione_testi_sito.md` per l'uso completo della CLI.
