---
generated-from-commit: babb092e15a27bf1eb672c25c84930de6a8308d5
generated-from-branch: main
generated-date: 2026-07-13
covers-paths:
  - backend_esempio/**
  - frontend_esempio/**
last-verified-commit: babb092e15a27bf1eb672c25c84930de6a8308d5
---

# Feature attiva

## Migrazione da CLI a frontend LAN + backend

Obiettivo: implementare il backend FastAPI (`backend_esempio/app.py`) secondo
`API_CONTRACT.md` e il frontend (`frontend_esempio/index.html`) fedele al prototipo hi-fi
in `frontend_esempio/design/`, cosi' che `scarica_sito_webcopy.py` sia utilizzabile da
un'interfaccia web invece che solo da riga di comando.

## Definition of done

Vedi `dev-testing.md` §Definizione di "fatto": i tre stati end-to-end contro backend
reale, albero file e download zip funzionanti, gestione errore con "Riprova".

## Stato al 15/07/2026 (M1 completato)

`backend_esempio/app.py` riscritto secondo `API_CONTRACT.md`: i quattro endpoint reali
(`POST /api/jobs`, `GET .../events` SSE, `GET .../result`, `GET .../download`), validazione
SSRF/path-traversal/limiti, coda a un job alla volta, archiviazione a fine job sulla share
di rete montata in CIFS (ADR-008) con pulizia TTL solo su cio' che e' gia' archiviato
(ADR-007). Verificato con `TestClient` e un finto crawler (Playwright non installato in
questa sessione), incluso un job reale contro la share montata su `/mnt/downloaded-websites`.
`frontend_esempio/index.html` aggiornato solo nelle chiamate API (nuovi endpoint, `EventSource`
al posto del polling); resta uno scheletro non fedele al prototipo hi-fi, compito di M2.

Emersa e corretta nelle schede una discrepanza tra l'esempio illustrativo dell'albero in
`API_CONTRACT.md` §3 e la struttura reale prodotta da `scarica_sito_webcopy.py` (vedi nota
in `API_CONTRACT.md` e `dev-testing.md`): `/result` cammina il disco vero, non l'esempio.

## Stato al 21/07/2026 (M2 completato, Playwright installato)

`frontend_esempio/index.html` riscritto fedele al prototipo hi-fi (ADR-002): token e
markup di `colors_and_type.css`/`design/Website Analyst.dc.html` ricreati con CSS normale,
quattro stati (form, avanzamento, riepilogo, errore) tutti collegati ai veri endpoint del
backend (nessuna simulazione lato JS). Aggiunto in `backend_esempio/app.py` il mount
statico `/design` (mancava) ed escluso il marcatore `.archiviato` da albero/statistiche/
zip. Verificato via `curl` l'intero ciclo POST->SSE->result->download; la verifica visiva
pixel-perfect nel browser resta da confermare dall'utente (nessuno strumento di
automazione browser disponibile in questa sessione).

Installati Playwright/Chromium sul `.venv` del progetto e verificato un crawl reale
end-to-end (CLI e backend/frontend), chiudendo l'ultima domanda aperta rimasta da M1.

## Stato al 23/07/2026 (M3 completato)

Servizio di produzione attivo: utente dedicato `estrattore`, permessi su repo/cache
Playwright/`/srv/output` sistemati, share CIFS rimontata con l'identita' di `estrattore`,
`estrattore.service` installato/abilitato in systemd, verificato con un crawl reale
end-to-end (archiviazione sulla share confermata, log applicativo in `journalctl`). Vedi
`deployment.md` per il dettaglio dei comandi. Nel frattempo aggiunte anche due funzionalita'
non pianificate ma emerse dall'uso reale: pulsante "Interrompi" per fermare un job in corso
(con interruzione automatica anche alla chiusura della pagina), e un hostname mDNS
(`website-analyst.local`) per non dover scrivere l'IP della VM.

## Domande aperte

Nessun blocco noto su M1/M2/M3. Prossimo passo eventuale: M4 (OCR per PDF scansionati,
opzionale) — vedi `roadmap.md`.

Verifica visiva pixel-perfect del frontend nel browser non ancora confermata dall'utente
(solo verifica funzionale via `curl`); il flusso end-to-end reale (incluso il pulsante
Interrompi) e' pero' stato usato e confermato funzionante dall'utente stesso in sessione.

Il file `~/Scrivania/passworg_gmail_intra` (password Gmail in chiaro, sospetta) va messo
in sicurezza — vedi `design-and-security.md`, non ancora risolto.
