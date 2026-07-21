# Snapshot di sincronizzazione

> Da leggere per primo a inizio sessione.

## Stato

```
Branch attivo:         main
Commit di riferimento: be26553 (M1; M2 di questa sessione non ancora committato)
Data snapshot:         2026-07-21
```

Tre commit sul repository: `babb092`, `b31cdad`, `be26553` ("M1: backend FastAPI reale,
archiviazione su share di rete CIFS" — riattribuito da asopranzi a tommyvezeni con
`--amend --reset-author`, vedi `progress.md` 2026-07-21). Due remote configurati: `origin`
(`git@github-corp:asopranzi-intrawelt/website-analyst.git`) e `origin-tommy`
(`git@github-corp-tommy:tommyvezeni/website-analyst.git`, tracciato da `main`); entrambi
ora allineati sullo stesso commit `be26553`. Identita' locale di default di questa cartella:
`tommyvezeni <tvezeni@intrawelt.com>` (cambiata da asopranzi in questa sessione). Lavoro di
M2 (frontend fedele + Playwright/Chromium installati) fatto in questa sessione ma non
ancora committato: vedi `progress.md` 2026-07-21.

## Stato di verifica delle schede

| Scheda | last-verified | Stato |
|---|---|---|
| STACK.md | b31cdad | aggiornata (estrattore.service); da rivedere per M2 |
| design-and-security.md | babb092 | ancorata al primo commit |
| deployment.md | b31cdad | contenuto aggiornato con mount CIFS (M1) + Playwright (M2), frontmatter da bumpare al prossimo commit |
| dev-testing.md | babb092 | contenuto aggiornato con verifica M1, frontmatter da bumpare al prossimo commit |
| current-work.md | babb092 | contenuto aggiornato a stato M2 completato, frontmatter da bumpare al prossimo commit |
| roadmap.md | babb092 | ancorata al primo commit |

## Punto di ripresa

M1 e M2 completati in questa sessione (M1 committato come `be26553`, M2 non ancora
committato): backend reale secondo `API_CONTRACT.md` con archiviazione su share CIFS
(ADR-007/008), frontend riscritto fedele al prototipo hi-fi (ADR-002) e collegato ai veri
endpoint (niente piu' simulazione lato JS). Playwright/Chromium installati e verificati con
un crawl reale end-to-end. Verifica visiva pixel-perfect del frontend nel browser non
ancora confermata dall'utente (nessuno strumento di automazione browser disponibile in
sessione: verificato funzionalmente via `curl`). Prossimo passo: M3, servizio di
produzione. Vedi `current-work.md` per il dettaglio.
