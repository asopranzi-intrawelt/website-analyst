# Snapshot di sincronizzazione

> Da leggere per primo a inizio sessione.

## Stato

```
Branch attivo:         main
Commit di riferimento: PENDING-FIRST-COMMIT
Data snapshot:         2026-07-13
```

Repository non ancora committato. Remote configurato:
`git@github-corp:asopranzi-intrawelt/website-analyst.git` (identita' locale asopranzi/lavoro).

## Stato di verifica delle schede

| Scheda | last-verified | Stato |
|---|---|---|
| STACK.md | PENDING-FIRST-COMMIT | creata in allineamento, da verificare dopo il primo commit |
| design-and-security.md | PENDING-FIRST-COMMIT | creata in allineamento, da verificare dopo il primo commit |
| deployment.md | PENDING-FIRST-COMMIT | creata in allineamento, da verificare dopo il primo commit |
| dev-testing.md | PENDING-FIRST-COMMIT | creata in allineamento, da verificare dopo il primo commit |
| current-work.md | PENDING-FIRST-COMMIT | creata in allineamento, da verificare dopo il primo commit |
| roadmap.md | PENDING-FIRST-COMMIT | creata in allineamento, da verificare dopo il primo commit |

## Punto di ripresa

Fare il primo commit (vedi comandi in fondo a questa sessione), poi eseguire la skill
`sync-context` per sostituire `PENDING-FIRST-COMMIT` con l'hash reale. Dopo di che:
implementare il backend FastAPI secondo `API_CONTRACT.md` (M1 di `roadmap.md`), lanciando
`scarica_sito_webcopy.py` come sottoprocesso.
