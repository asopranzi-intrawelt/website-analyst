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
credenziali in `/etc/samba/creds`, proprietario root, `chmod 600`; riga in `/etc/fstab`,
`_netdev`). E' la destinazione finale (ADR-008) dove il backend copia ogni cartella di
crawl completata; `/srv/output` resta lo staging locale dove il crawler scrive davvero.

Fatto il 23/07/2026 (M3): utente di servizio dedicato `estrattore` creato
(`sudo useradd -r -s /usr/sbin/nologin -G intrawelt estrattore`, uid 997/gid 984 su questa
VM), membro supplementare del gruppo `intrawelt` per ereditare i permessi di gruppo gia'
presenti su home/Scrivania/repo (750/755/775) senza allargarli ad "altri". Due permessi
puntuali aggiunti: `chmod g+rx /home/intrawelt/.cache` (la home di `intrawelt` e' 750, senza
questo `estrattore` non raggiungerebbe `ms-playwright/` nonostante sia gia' 775) e
`chmod g+w /srv/output` (il gruppo aveva solo lettura). Riga fstab della share CIFS
riallineata da `uid=intrawelt,gid=intrawelt` a `uid=estrattore,gid=estrattore` (mount.cifs
accetta nomi utente/gruppo, non serve conoscere gli id numerici in anticipo) e rimontata.
`xvfb` installato per l'eventuale `--headful` in produzione.

Servizio avviato e verificato con un crawl reale end-to-end contro la porta 8000: file
scritti sulla share risultano di proprieta' `estrattore` (leggibili da `intrawelt` grazie a
`file_mode=0664`/`dir_mode=0775` gia' nel mount), log applicativo visibile in
`journalctl -u estrattore`. Il server di prova ad hoc usato nelle sessioni precedenti
(porta 8010) e' stato fermato: il servizio di produzione (porta 8000) lo sostituisce.

Fatto lo stesso giorno: hostname mDNS annunciato tramite Avahi (gia' installato di
default su questa VM, non serve installarlo): `host-name=website-analyst` in
`/etc/avahi/avahi-daemon.conf`. La VM e' raggiungibile in LAN anche come
`http://website-analyst.local:8000/`, senza scrivere l'IP. Il suffisso `.local` e'
obbligatorio (parte del protocollo mDNS, non una scelta di configurazione); un nome senza
`.local` richiederebbe una voce su un server DNS vero della rete Intrawelt, non configurato
da questa VM.

## Avvio

```bash
python scarica_sito_webcopy.py https://www.sito.it/ --out /srv/output/sito --max 2000
# backend reale, dalla cartella del repo (solo per sviluppo: in produzione parte da systemd):
cd ~/Scrivania/website-analyst && uvicorn backend_esempio.app:app --host 192.168.20.24 --port 8000
# variabili d'ambiente lette da backend_esempio/app.py (gia' impostate in estrattore.service):
#   OUTPUT_BASE=/srv/output (staging locale del crawl)
#   ARCHIVE_BASE=/mnt/downloaded-websites (share di rete, destinazione finale)
#   PLAYWRIGHT_BROWSERS_PATH=/home/intrawelt/.cache/ms-playwright (Chromium condiviso)
```

## Produzione

`backend_esempio/estrattore.service` e' installato in `/etc/systemd/system/`, abilitato e
attivo (`systemctl status estrattore`, `journalctl -u estrattore`). Gira come utente
`estrattore`, bind LAN-only su `192.168.20.24:8000` (o `http://website-analyst.local:8000/`
via mDNS). Restart automatico (`Restart=on-failure`) in caso di crash.

## Accesso alla VM

Raggiungibile da questa rete via SSH (alias `vm207` sulle macchine di sviluppo, chiave
dedicata senza passphrase). Il repository ha remote `origin` su
`github.com/asopranzi-intrawelt/website-analyst` via alias SSH `github-corp`, e un secondo
remote personale `origin-tommy` (`tommyvezeni/website-analyst`, tracciato da `main`, vedi
`memory/index.md`), entrambi configurati localmente su questa VM.
