# Snapshot di sincronizzazione

> Da leggere per primo a inizio sessione.

## Stato

```
Branch attivo:         main
Commit di riferimento: babb092e15a27bf1eb672c25c84930de6a8308d5
Data snapshot:         2026-07-13
```

Primo commit eseguito (`babb092`, "Allineamento al sistema di contesto portabile + handoff
design/sizing"). Remote configurato:
`git@github-corp:asopranzi-intrawelt/website-analyst.git` (identita' locale asopranzi/lavoro).

## Stato di verifica delle schede

| Scheda | last-verified | Stato |
|---|---|---|
| STACK.md | babb092 | ancorata al primo commit |
| design-and-security.md | babb092 | ancorata al primo commit |
| deployment.md | babb092 | ancorata al primo commit |
| dev-testing.md | babb092 | ancorata al primo commit |
| current-work.md | babb092 | ancorata al primo commit |
| roadmap.md | babb092 | ancorata al primo commit |

## Punto di ripresa

Posizionamento completato: disco dati montato su `/srv` (`/srv/output/` per l'archivio di
questo progetto, `/srv/crawl4ai-docling/` riservato al futuro, vedi ADR-005/006 in
`decisions.md`); il repository resta in `~/Scrivania/website-analyst`, non spostato. Le
modifiche a `CLAUDE.md`, `deployment.md` e `backend_esempio/estrattore.service` fatte in
questa sessione non sono ancora committate. Prossimo passo: far committare all'utente
queste modifiche, poi implementare il backend FastAPI secondo `API_CONTRACT.md` (M1 di
`roadmap.md`), lanciando `scarica_sito_webcopy.py` come sottoprocesso.
