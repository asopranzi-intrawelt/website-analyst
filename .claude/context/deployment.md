---
generated-from-commit: babb092e15a27bf1eb672c25c84930de6a8308d5
generated-from-branch: main
generated-date: 2026-07-13
covers-paths:
  - requirements.txt
  - backend_esempio/estrattore.service
last-verified-commit: babb092e15a27bf1eb672c25c84930de6a8308d5
---

# Deployment

## Setup una tantum (VM207, Ubuntu 24.04)

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip
cd ~/Scrivania/website-analyst
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
```

Fatto il 13/07/2026: il disco dati scsi1 (96G, `/dev/sdb1`, ext4, UUID
`5cb1f056-8d7f-4d6d-af92-857bac1952c2`) e' montato su `/srv` (voce in `/etc/fstab`
confermata). Il repository resta in `~/Scrivania/website-analyst`: si e' verificato che il
problema di spazio riguarda solo l'archivio di output, non il codice, quindi si sposta solo
quello. `/srv/output/` (proprietario `intrawelt`) e' la destinazione degli `--out` dei
crawl; `/srv/crawl4ai-docling/` resta riservato al progetto futuro descritto in
`_notes/handoff-vm207-sizing-crawl4ai-docling.md`, che aveva dimensionato originariamente
questo stesso disco.

## Avvio

```bash
python scarica_sito_webcopy.py https://www.sito.it/ --out /srv/output/sito --max 2000
# backend di esempio, quando implementato secondo API_CONTRACT.md (dalla cartella del repo):
cd ~/Scrivania/website-analyst && uvicorn backend_esempio.app:app --host 192.168.20.24 --port 8000
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
