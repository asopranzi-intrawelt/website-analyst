---
generated-from-commit: babb092e15a27bf1eb672c25c84930de6a8308d5
generated-from-branch: main
generated-date: 2026-07-13
covers-paths:
  - requirements.txt
  - backend_esempio/estrattore.service
last-verified-commit: b31cdad
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

Fatto il 21/07/2026: `.venv` creato con l'intero `requirements.txt` installato (fastapi,
uvicorn, playwright, beautifulsoup4, lxml, pdfminer.six) e il binario Chromium scaricato
con `playwright install chromium` (senza `--with-deps`: nessuna libreria di sistema
mancante su questa VM, il lancio headless ha funzionato al primo tentativo). Verificato con
un crawl reale (`http://example.com/`, 1 pagina) sia da CLI sia attraverso il backend reale
(`POST /api/jobs` -> SSE -> `/result` -> `/download`, zip valido con i file veri). Se in
futuro un sito richiedesse `--headful` e il lancio fallisse per librerie mancanti, il
comando di ripiego resta `playwright install-deps chromium` (richiede sudo).

Fatto il 13/07/2026: il disco dati scsi1 (96G, `/dev/sdb1`, ext4, UUID
`5cb1f056-8d7f-4d6d-af92-857bac1952c2`) e' montato su `/srv` (voce in `/etc/fstab`
confermata). Il repository resta in `~/Scrivania/website-analyst`: si e' verificato che il
problema di spazio riguarda solo l'archivio di output, non il codice, quindi si sposta solo
quello. `/srv/output/` (proprietario `intrawelt`) e' la destinazione degli `--out` dei
crawl; `/srv/crawl4ai-docling/` resta riservato al progetto futuro descritto in
`_notes/handoff-vm207-sizing-crawl4ai-docling.md`, che aveva dimensionato originariamente
questo stesso disco.

Fatto il 15/07/2026 (M1): share SMB esterna montata in CIFS su `/mnt/downloaded-websites`
(UNC `\\192.168.20.177\utili(new)\downloaded-websites`, utente dedicato `webanalyst`,
credenziali in `/etc/samba/creds`, proprietario root, `chmod 600`; riga in `/etc/fstab` con
`uid=intrawelt,gid=intrawelt,_netdev`). E' la destinazione finale (ADR-008) dove il backend
copia ogni cartella di crawl completata; `/srv/output` resta lo staging locale dove il
crawler scrive davvero. Follow-up aperto: quando M3 crea l'utente di servizio dedicato
`estrattore`, la riga fstab va riallineata (`uid`/`gid` da `intrawelt` a `estrattore`) e la
share rimontata.

## Avvio

```bash
python scarica_sito_webcopy.py https://www.sito.it/ --out /srv/output/sito --max 2000
# backend reale (M1), dalla cartella del repo:
cd ~/Scrivania/website-analyst && uvicorn backend_esempio.app:app --host 192.168.20.24 --port 8000
# variabili d'ambiente lette da backend_esempio/app.py (default gia' corretti in produzione):
#   OUTPUT_BASE=/srv/output (staging locale del crawl)
#   ARCHIVE_BASE=/mnt/downloaded-websites (share di rete, destinazione finale)
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
