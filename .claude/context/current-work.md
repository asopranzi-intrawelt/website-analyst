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

## Domande aperte

Prossimo passo: M2, rendere `frontend_esempio/index.html` fedele 1:1 al prototipo hi-fi in
`frontend_esempio/design/` (ADR-002), ora che gli endpoint reali esistono.

Verifica di un crawl vero con Playwright/Chromium non ancora fatta in questa sessione
(dipendenze non installate): resta un passo manuale, vedi `dev-testing.md`.

Follow-up di infrastruttura: quando M3 crea l'utente di servizio dedicato `estrattore`, la
riga `/etc/fstab` della share CIFS va riallineata da `uid=intrawelt,gid=intrawelt` a quello
(vedi `deployment.md`, ADR-008). `sudo systemctl daemon-reload` andrebbe eseguito una volta
per allineare systemd alla voce fstab gia' aggiunta.

Il file `~/Scrivania/passworg_gmail_intra` (password Gmail in chiaro, sospetta) va messo
in sicurezza — vedi `design-and-security.md`, non ancora risolto.
