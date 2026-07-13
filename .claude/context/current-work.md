---
generated-from-commit: PENDING-FIRST-COMMIT
generated-from-branch: main
generated-date: 2026-07-13
covers-paths:
  - backend_esempio/**
  - frontend_esempio/**
last-verified-commit: PENDING-FIRST-COMMIT
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

## Stato al 13/07/2026 (allineamento al template)

Fatto in questa sessione: sistema di contesto portabile importato da
`E:\template-claude-developing`; handoff di sizing (`_notes/handoff-vm207-sizing-crawl4ai-docling.md`)
e di design frontend (`_notes/design-handoff-*`, `API_CONTRACT.md`,
`frontend_esempio/design/`) integrati nella cartella di progetto; repository git
inizializzato (non ancora committato) con identita' `asopranzi`/lavoro e remote
`github-corp:asopranzi-intrawelt/website-analyst`; VM raggiungibile via SSH (alias
`vm207`) e in grado di autenticarsi su GitHub (alias `github-corp`).

## Domande aperte

Nessun commit ancora eseguito: i frontmatter delle schede restano a
`PENDING-FIRST-COMMIT` finche' l'utente non fa il primo commit e si esegue `sync-context`.

Il file `~/Scrivania/passworg_gmail_intra` (password Gmail in chiaro, sospetta) va messo
in sicurezza — vedi `design-and-security.md`.

Backend e frontend restano scheletri (`backend_esempio/`, `frontend_esempio/`): il grosso
del lavoro applicativo (endpoint reali, UI fedele al design) e' ancora da fare, previsto
dopo l'handoff a Claude Code in esecuzione direttamente sulla VM.
