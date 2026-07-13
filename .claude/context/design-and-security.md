---
generated-from-commit: PENDING-FIRST-COMMIT
generated-from-branch: main
generated-date: 2026-07-13
covers-paths:
  - scarica_sito_webcopy.py
  - backend_esempio/**
  - API_CONTRACT.md
last-verified-commit: PENDING-FIRST-COMMIT
---

# Design e sicurezza

## Perimetro di esposizione

Il tool va esposto **solo in LAN** (rete 192.168.20.0/19 della VM), mai direttamente su
Internet senza reverse proxy e autenticazione davanti. Bind consigliato del backend:
`192.168.20.24:8000` (o `127.0.0.1` dietro reverse proxy).

## Rischi applicativi da mitigare (dal design brief e da API_CONTRACT.md)

SSRF: validare `url` (solo schema http/https, host risolvibile), bloccare host/IP privati
se non esplicitamente consentiti prima di far partire un crawl.

Path traversal sul parametro `folder`: sanitizzare rifiutando `/` e `..`.

Limiti di risorse: `max_pages` vincolato 1..300, un job di crawl alla volta (o piccola
coda) perche' ogni run apre un Chromium reale: troppi crawl paralleli su 6 vCPU degradano
la VM.

Pulizia: TTL su job/zip vecchi per non saturare il disco (disco dati 96G su `/srv`,
separato dal disco di sistema da 32G).

Rispetto di `robots.txt` e dei ToS dei siti bersaglio, rate limiting tramite `delay_sec`.

Nessuna credenziale hardcoded nel codice.

## Gap di igiene rilevato (non ancora risolto)

Il 13/07/2026, durante l'allineamento al template, e' stato trovato un file
`~/Scrivania/passworg_gmail_intra` (13 byte) sul desktop della VM: dal nome sembra una
password Gmail aziendale in chiaro. Non e' stato letto ne' spostato da questa sessione.
Da mettere in sicurezza (rimuovere dal desktop, ruotare la password se valida) prima di
considerare la VM pronta per un uso non transitorio.

## Stato ISO27001

Fuori perimetro rispetto all'angolo ISO27001 di `network-design` (quel progetto copre la
rete Intrawelt nel suo complesso; VM207 vi e' censita come voce di inventario). Le
politiche di sicurezza applicative specifiche di questo tool vivono qui.
