---
generated-from-commit: PENDING-FIRST-COMMIT
generated-from-branch: main
generated-date: 2026-07-13
covers-paths:
  - requirements.txt
  - backend_esempio/estrattore.service
last-verified-commit: PENDING-FIRST-COMMIT
---

# Deployment

## Setup una tantum (VM207, Ubuntu 24.04)

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip
cd ~/Scrivania/website-analyst        # o /srv/estrattore-testi-sito una volta montato il disco dati
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
```

Promemoria dal contesto VM (non ancora verificato in questa sessione): montare il disco
dati scsi1 (96G) su `/srv` per tenere li' progetto e output, cosi' il disco di sistema da
32G non si satura con gli archivi di crawl crescenti. Verificare la voce in `/etc/fstab`.

## Avvio

```bash
python scarica_sito_webcopy.py https://www.sito.it/ --out /srv/output/sito --max 2000
# backend di esempio, quando implementato secondo API_CONTRACT.md:
uvicorn backend_esempio.app:app --host 192.168.20.24 --port 8000
```

## Produzione

`backend_esempio/estrattore.service` e' il punto di partenza per il servizio systemd che
tiene il backend sempre attivo. Da istanziare e abilitare (`systemctl enable --now`) solo
dopo che il backend reale sostituisce lo scheletro.

## Accesso alla VM

Raggiungibile da questa rete via SSH (alias `vm207` sulle macchine di sviluppo, chiave
dedicata senza passphrase). Il repository ha remote `origin` su
`github.com/asopranzi-intrawelt/website-analyst` via alias SSH `github-corp`, configurato
localmente su questa VM.
