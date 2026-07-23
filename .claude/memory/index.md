# Snapshot di sincronizzazione

> Da leggere per primo a inizio sessione.

## Stato

```
Branch attivo:         main
Commit di riferimento: 7feccdd (M3 di questa sessione non ancora committato)
Data snapshot:         2026-07-23
```

Cinque commit sul repository: `babb092`, `b31cdad`, `be26553`, `8d3977b`, `7feccdd`. Due
remote configurati: `origin` (`git@github-corp:asopranzi-intrawelt/website-analyst.git`) e
`origin-tommy` (`git@github-corp-tommy:tommyvezeni/website-analyst.git`, tracciato da
`main`); entrambi allineati sullo stesso HEAD. Identita' locale di default di questa
cartella: `tommyvezeni <tvezeni@intrawelt.com>`. Lavoro di M3 (servizio di produzione,
utente `estrattore`, hostname mDNS) fatto in questa sessione ma non ancora committato: vedi
`progress.md` 2026-07-23.

## Stato di verifica delle schede

| Scheda | last-verified | Stato |
|---|---|---|
| STACK.md | b31cdad | contenuto aggiornato (html_leggibile navigabile), frontmatter da bumpare al prossimo commit |
| design-and-security.md | babb092 | ancorata al primo commit |
| deployment.md | b31cdad | contenuto aggiornato con M3 (utente estrattore, systemd, mDNS), frontmatter da bumpare al prossimo commit |
| dev-testing.md | babb092 | contenuto aggiornato con verifica M1, frontmatter da bumpare al prossimo commit |
| current-work.md | babb092 | contenuto aggiornato a stato M3 completato, frontmatter da bumpare al prossimo commit |
| roadmap.md | babb092 | contenuto aggiornato a M1/M2/M3 completati, frontmatter da bumpare al prossimo commit |

## Punto di ripresa

M1, M2 e M3 completati (M1+M2 committati come `be26553`/`8d3977b`/`7feccdd`, M3 non ancora
committato): backend reale, frontend fedele al prototipo, pulsante Interrompi con
interruzione automatica alla chiusura pagina, `html_leggibile/` navigabile (Shadow DOM/CSS
incorporati), e ora il servizio di produzione sotto systemd (utente dedicato `estrattore`,
share CIFS riallineata, Chromium condiviso via `PLAYWRIGHT_BROWSERS_PATH`), verificato con
un crawl reale end-to-end contro il servizio vero (porta 8000). Aggiunto anche un hostname
mDNS (`website-analyst.local`) per non scrivere l'IP. Prossimo passo eventuale: M4 (OCR PDF
scansionati, opzionale) — vedi `roadmap.md`. Vedi `current-work.md` per il dettaglio.
